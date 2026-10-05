"""Le ticket, ses commentaires et sa priorite.

Chaque action suit le meme ordre de controle :
1. droit global : __authorize (permission du role, compte actif, ticket non archive) ;
2. arguments ;
3. etat : la transition est-elle permise dans l'etat courant ? (patron State) ;
4. regle contextuelle : auteur, assigne, visibilite ;
5. effet, puis mise a jour de la date de modification.
Un refus renvoie False ou None, sans aucun effet, et son motif va dans le journal.
"""
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Optional

from .._texte import normaliser, texte_valide
from ..acteurs import Permission, User, UserRegistry
from .contenus import Content
from .etats import OpenState, Status, TicketState
from .fichiers import ContentFactory
from .visiteur import ExportVisitor, TicketVisitor, ViewVisitor

_journal = logging.getLogger(__name__)
_TITRE_MAX = 200
_TEXTE_MAX = 5000  # commentaires et motifs
_LECTURE_SEULE = (Permission.VIEW, Permission.EXPORT)  # seules actions permises sur une archive


def _refus(motif: str, valeur=False):
    _journal.info("refus : %s", motif)
    return valeur


def _texte_valide(texte: object, maximum: int, multiligne: bool = False) -> bool:
    """Voir gestion_tickets._texte : non vide, borne, rien qui puisse falsifier l'affichage."""
    return texte_valide(texte, maximum, multiligne)


class Priority(Enum):
    BASSE = "BASSE"
    NORMALE = "NORMALE"
    HAUTE = "HAUTE"


class Comment:
    """Un message ajoute a un ticket. Il n'est jamais modifie ni supprime."""

    def __init__(self, id: int, author: User, text: str) -> None:
        # Constructeur de paquetage (~) : seul Ticket cree des commentaires.
        self.__comment_id = id
        self.__author = author
        self.__text = text
        self.__posted_at = datetime.now()

    @property
    def comment_id(self) -> int:
        return self.__comment_id

    @property
    def text(self) -> str:
        return self.__text

    @property
    def posted_at(self) -> datetime:
        return self.__posted_at

    def get_author(self) -> User:
        return self.__author

    def _accept(self, v: TicketVisitor) -> None:
        v.visit_comment(self)

    def __repr__(self) -> str:
        return f"Comment#{self.__comment_id} de {self.__author.name} : {self.__text}"


class Ticket:
    """Un signalement et son cycle de vie."""

    def __init__(self, id: int, author: User, title: str, p: Priority, users: UserRegistry) -> None:
        # Constructeur de paquetage (~) : seul TicketRegistry cree des tickets.
        maintenant = datetime.now()
        self.__ticket_id = id
        self.__title = title
        self.__priority = p
        self.__creation_date = maintenant
        self.__update_date = maintenant
        self.__archive_date = None
        self.__next_comment_id = 1
        self.__users = users             # association comptes (1) : qui a le droit d'agir
        self.__author = author           # association author (1)
        self.__assignee = None           # association assignee (0..1)
        self.__state = OpenState()       # association state (1)
        self.__comments = []             # composition comments
        self.__description = []          # composition description

    # ------------------------------------------------ accesseurs en lecture (legende)
    @property
    def ticket_id(self) -> int:
        return self.__ticket_id

    @property
    def title(self) -> str:
        return self.__title

    @property
    def priority(self) -> Priority:
        return self.__priority

    @property
    def creation_date(self) -> datetime:
        return self.__creation_date

    @property
    def update_date(self) -> datetime:
        return self.__update_date

    @property
    def archive_date(self) -> Optional[datetime]:
        return self.__archive_date

    @property
    def next_comment_id(self) -> int:
        return self.__next_comment_id

    # ------------------------------------------------ controles prives
    def __authorize(self, actor: User, p: Permission) -> bool:
        """Droit global : permission du role, compte actif ; une archive est en lecture seule."""
        if not self.__users.contains(actor):
            return _refus(f"{p.value} : acteur inconnu du registre des comptes")
        if not actor.can_globally(p):
            return _refus(f"{p.value} : permission absente ou compte desactive")
        if self.__archive_date is not None and p not in _LECTURE_SEULE:
            return _refus(f"ticket #{self.__ticket_id} archive : lecture et export seulement")
        return True

    def __is_author(self, u: User) -> bool:
        """Regle contextuelle : u est-il l'auteur ?"""
        return u is self.__author

    def __accept(self, v: TicketVisitor) -> None:
        """Parcours complet : le ticket, sa description, puis ses commentaires."""
        v.visit_ticket(self)
        for contenu in self.__description:
            contenu._accept(v)
        for commentaire in self.__comments:
            commentaire._accept(v)

    def __append_comment(self, author: User, text: str) -> Comment:
        commentaire = Comment(self.__next_comment_id, author, normaliser(text).strip())
        self.__comments.append(commentaire)
        self.__next_comment_id += 1
        return commentaire

    # ------------------------------------------------ mutateurs de paquetage (~)
    def _set_state(self, s: TicketState) -> None:
        self.__state = s

    def _set_assignee(self, u: Optional[User]) -> None:
        self.__assignee = u

    def _mark_archived(self) -> None:
        self.__archive_date = datetime.now()
        self._touch()

    def _touch(self) -> None:
        self.__update_date = datetime.now()

    # ------------------------------------------------ transitions du cycle de vie
    def assign(self, actor: User, assignee: User) -> bool:
        """ASSIGN ; l'assigne doit pouvoir soumettre (developpeur actif)."""
        if not self.__authorize(actor, Permission.ASSIGN):
            return False
        if not self.__users.contains(assignee) or not assignee.can_globally(Permission.SUBMIT):
            return _refus("l'assigne doit etre un developpeur actif du registre")
        if not self.__state._assign(self, actor, assignee):
            return False
        self._touch()
        return True

    def submit(self, actor: User) -> bool:
        if not self.__authorize(actor, Permission.SUBMIT) or not self.__state._submit(self, actor):
            return False
        self._touch()
        return True

    def validate(self, actor: User) -> bool:
        if not self.__authorize(actor, Permission.VALIDATE) or not self.__state._validate(self, actor):
            return False
        self._touch()
        return True

    def reject(self, actor: User, reason: str) -> bool:
        """REJECT ; retour a ASSIGNE, motif ajoute en commentaire."""
        return self.__avec_motif(actor, Permission.REJECT, "Rejet", reason, self.__state._reject)

    def close(self, actor: User, reason: str) -> bool:
        """CLOSE ; vers FERME, motif ajoute en commentaire."""
        return self.__avec_motif(actor, Permission.CLOSE, "Fermeture", reason, self.__state._close)

    def reopen(self, actor: User, reason: str) -> bool:
        """REOPEN ; vers OUVERT sans assigne, motif ajoute en commentaire."""
        return self.__avec_motif(actor, Permission.REOPEN, "Reouverture", reason, self.__state._reopen)

    def __avec_motif(self, actor, permission, action, reason, transition) -> bool:
        if not self.__authorize(actor, permission):
            return False
        if not _texte_valide(reason, _TEXTE_MAX, multiligne=True):
            return _refus(f"{action} : un motif est obligatoire")
        if not transition(self, actor, reason):
            return False
        self.__append_comment(actor, f"{action} : {normaliser(reason).strip()}")
        self._touch()
        return True

    # ------------------------------------------------ autres actions
    def edit(self, actor: User, title: str) -> bool:
        """EDIT ; reserve a l'auteur, tant que l'etat le permet."""
        if not self.__authorize(actor, Permission.EDIT):
            return False
        if not _texte_valide(title, _TITRE_MAX):
            return _refus(f"titre vide, sur plusieurs lignes ou de plus de {_TITRE_MAX} caracteres")
        if not self.__state.allows_edit():
            return _refus(f"ticket non modifiable en {self.get_status().value}")
        if not self.__is_author(actor):
            return _refus("seul l'auteur modifie son ticket")
        self.__title = title.strip()
        self._touch()
        return True

    def set_priority(self, actor: User, p: Priority) -> bool:
        if not self.__authorize(actor, Permission.SET_PRIORITY):
            return False
        if not isinstance(p, Priority):
            return _refus(f"priorite invalide : {p!r}")
        if p is self.__priority:
            return _refus(f"la priorite est deja {p.value}")
        self.__priority = p
        self._touch()
        return True

    def add_comment(self, author: User, text: str) -> Optional[Comment]:
        """COMMENT et visibilite ; permis meme sur un ticket ferme, jamais sur une archive."""
        if not self.__authorize(author, Permission.COMMENT):
            return None
        if not self.is_visible_to(author):
            return _refus("commentaire sur un ticket invisible pour l'auteur", None)
        if not _texte_valide(text, _TEXTE_MAX, multiligne=True):
            return _refus(f"commentaire vide, de plus de {_TEXTE_MAX} caracteres ou avec un caractere de controle", None)
        commentaire = self.__append_comment(author, text)
        self._touch()
        return commentaire

    def add_content(self, actor: User, c: Content) -> bool:
        """ATTACH ; reserve a l'auteur, tant que l'etat le permet. Le contenu repasse
        par la fabrique : un contenu construit a la main hors de UPLOAD_DIR est refuse."""
        if not self.__authorize(actor, Permission.ATTACH):
            return False
        if not isinstance(c, Content):
            return _refus("ce n'est pas un contenu")
        if not self.__state.allows_edit():
            return _refus(f"ticket non modifiable en {self.get_status().value}")
        if not self.__is_author(actor):
            return _refus("seul l'auteur complete la description")
        # On rejoue la fabrique : le contenu joint est celui qu'elle produit, jamais l'objet recu.
        verifie = ContentFactory.from_path(c.path) if isinstance(c.path, str) else None
        if (verifie is None or type(verifie) is not type(c)
                or os.path.normcase(os.path.realpath(c.path)) != os.path.normcase(verifie.path)):
            return _refus(f"contenu non valide ou hors du dossier autorise : {c.path!r}")
        if any(os.path.normcase(d.path) == os.path.normcase(verifie.path) for d in self.__description):
            return _refus(f"fichier deja joint : {os.path.basename(verifie.path)}")
        self.__description.append(verifie)
        self._touch()
        return True

    def consult(self, actor: User, v: ViewVisitor) -> bool:
        """VIEW et visibilite ; le type du visiteur fixe la permission exigee."""
        if not isinstance(v, ViewVisitor) or isinstance(v, ExportVisitor):
            return _refus("consulter exige un ViewVisitor qui ne soit pas aussi un ExportVisitor")
        if not self.__authorize(actor, Permission.VIEW):
            return False
        if not self.is_visible_to(actor):
            return _refus("consultation d'un ticket invisible pour l'acteur")
        self.__accept(v)
        return True

    def export(self, actor: User, v: ExportVisitor) -> bool:
        """EXPORT et visibilite."""
        if not isinstance(v, ExportVisitor) or isinstance(v, ViewVisitor):
            return _refus("exporter exige un ExportVisitor qui ne soit pas aussi un ViewVisitor")
        if not self.__authorize(actor, Permission.EXPORT):
            return False
        if not self.is_visible_to(actor):
            return _refus("export d'un ticket invisible pour l'acteur")
        self.__accept(v)
        return True

    # ------------------------------------------------ lectures
    def get_status(self) -> Status:
        return self.__state.name()

    def get_author(self) -> User:
        return self.__author

    def get_assignee(self) -> Optional[User]:
        return self.__assignee

    def is_archived(self) -> bool:
        return self.__archive_date is not None

    def is_visible_to(self, u: User) -> bool:
        """Compte du registre qui est l'auteur, l'assigne, ou detenteur de VIEW_ALL."""
        return self.__users.contains(u) and (u is self.__author or u is self.__assignee
                                             or u.can_globally(Permission.VIEW_ALL))

    def __repr__(self) -> str:
        archive = ", archive" if self.is_archived() else ""
        return f"Ticket#{self.__ticket_id} [{self.get_status().value}{archive}] {self.__title}"
