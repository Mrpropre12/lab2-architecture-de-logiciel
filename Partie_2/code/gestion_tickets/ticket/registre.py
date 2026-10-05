"""Registre des tickets : creation, archivage et recherches filtrees selon l'acteur.

Aucun ticket n'est supprime : un ticket TERMINE ou FERME peut etre archive,
definitivement. Les recherches ordinaires ignorent les archives ; find_archived
et find_by_id les retrouvent si l'acteur peut les voir.
"""
import logging
from typing import List, Optional

from ..acteurs import Permission, User, UserRegistry
from .etats import Status
from .ticket import Priority, Ticket, _TITRE_MAX, _texte_valide

_journal = logging.getLogger(__name__)
_ARCHIVABLES = (Status.TERMINE, Status.FERME)


def _refus(motif: str, valeur=False):
    _journal.info("refus : %s", motif)
    return valeur


class TicketRegistry:

    def __init__(self, users: UserRegistry) -> None:
        if not isinstance(users, UserRegistry):
            raise TypeError("TicketRegistry exige le registre des comptes (UserRegistry)")
        self.__users = users  # association comptes (1) : injectee, jamais globale
        self.__next_id = 1
        self.__tickets = {}  # association tickets : id -> Ticket

    @property
    def next_id(self) -> int:
        return self.__next_id

    # ------------------------------------------------ outils prives
    def __authorize(self, actor: User, p: Permission) -> bool:
        """Compte de ce registre, actif, avec la permission."""
        return self.__users.contains(actor) and actor.can_globally(p)

    def __active_visible_to(self, actor: User) -> List[Ticket]:
        """Tickets non archives et visibles par l'acteur : base des autres recherches."""
        if not self.__authorize(actor, Permission.VIEW):
            return _refus("recherche : acteur hors registre, sans VIEW ou desactive", [])
        return [t for _, t in sorted(self.__tickets.items())
                if not t.is_archived() and t.is_visible_to(actor)]

    # ------------------------------------------------ operations publiques
    def create(self, author: User, title: str, p: Priority) -> Optional[Ticket]:
        if not self.__authorize(author, Permission.CREATE):
            return _refus("CREATE : auteur hors registre, sans permission ou desactive", None)
        if not _texte_valide(title, _TITRE_MAX):
            return _refus(f"titre vide, sur plusieurs lignes ou de plus de {_TITRE_MAX} caracteres", None)
        if not isinstance(p, Priority):
            return _refus(f"priorite invalide : {p!r}", None)
        ticket = Ticket(self.__next_id, author, title.strip(), p, self.__users)
        self.__tickets[ticket.ticket_id] = ticket
        self.__next_id += 1
        return ticket

    def archive(self, actor: User, id: int) -> bool:
        """ARCHIVE ; seulement un ticket TERMINE ou FERME ; definitif."""
        if not self.__authorize(actor, Permission.ARCHIVE):
            return _refus("ARCHIVE : acteur hors registre, sans permission ou desactive")
        ticket = self.__tickets.get(id) if isinstance(id, int) and not isinstance(id, bool) else None
        if ticket is None:
            return _refus(f"ticket introuvable : {id!r}")
        if ticket.is_archived():
            return _refus(f"ticket #{id} deja archive")
        if ticket.get_status() not in _ARCHIVABLES:
            return _refus(f"ticket #{id} en {ticket.get_status().value} : seul TERMINE ou FERME s'archive")
        ticket._mark_archived()
        return True

    def find_by_id(self, actor: User, id: int) -> Optional[Ticket]:
        """Si visible par l'acteur, archives comprises."""
        if not self.__authorize(actor, Permission.VIEW):
            return _refus("recherche : acteur hors registre, sans VIEW ou desactive", None)
        if not isinstance(id, int) or isinstance(id, bool):
            return _refus(f"identifiant invalide : {id!r}", None)
        ticket = self.__tickets.get(id)
        if ticket is None or not ticket.is_visible_to(actor):
            return _refus(f"ticket #{id} introuvable ou invisible pour l'acteur", None)
        return ticket

    def find_all(self, actor: User) -> List[Ticket]:
        """VIEW_ALL : tous les tickets non archives."""
        if not self.__authorize(actor, Permission.VIEW_ALL):
            return _refus("find_all exige VIEW_ALL", [])
        return self.__active_visible_to(actor)

    def find_by_author(self, actor: User, u: User) -> List[Ticket]:
        return [t for t in self.__active_visible_to(actor) if t.get_author() is u]

    def find_by_assignee(self, actor: User, u: User) -> List[Ticket]:
        return [t for t in self.__active_visible_to(actor) if t.get_assignee() is u]

    def find_by_status(self, actor: User, s: Status) -> List[Ticket]:
        if not isinstance(s, Status):
            return _refus(f"statut invalide : {s!r}", [])
        return [t for t in self.__active_visible_to(actor) if t.get_status() is s]

    def find_by_priority(self, actor: User, p: Priority) -> List[Ticket]:
        if not isinstance(p, Priority):
            return _refus(f"priorite invalide : {p!r}", [])
        return [t for t in self.__active_visible_to(actor) if t.priority is p]

    def find_archived(self, actor: User) -> List[Ticket]:
        """Archives visibles par l'acteur."""
        if not self.__authorize(actor, Permission.VIEW):
            return _refus("recherche : acteur hors registre, sans VIEW ou desactive", [])
        return [t for _, t in sorted(self.__tickets.items()) if t.is_archived() and t.is_visible_to(actor)]
