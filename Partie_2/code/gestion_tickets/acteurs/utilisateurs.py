"""Identite (User) et registre des comptes (UserRegistry).

Conventions (legende du diagramme) :
- une methode controlee renvoie False, None ou une liste vide en cas de refus,
  sans effet de bord ; le motif est ecrit dans le journal ;
- l'acteur est le compte authentifie du registre unique, fourni par la couche
  appelante : le registre verifie qu'il est bien l'un de ses comptes.
"""
import logging
import re
from typing import List, Optional

from .._texte import texte_valide
from .permissions import Permission
from .roles import AdminRole, DeveloperRole, ReporterRole, Role

_journal = logging.getLogger(__name__)
_FORMAT_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ROLES_CONNUS = (ReporterRole, DeveloperRole, AdminRole)



class User:
    """Une identite. Les droits viennent uniquement des roles attribues."""

    def __init__(self, id: int, name: str, email: str) -> None:
        # Constructeur de paquetage (~) : seul UserRegistry cree des comptes.
        self.__user_id = id
        self.__name = name
        self.__email = email
        self.__active = True
        self.__assigned_roles = set()  # association assignedRoles (1..*)

    # ------------------------------------------------ accesseurs en lecture
    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def active(self) -> bool:
        return self.__active

    def _get_email(self) -> str:
        """~ getEmail : l'email n'est lisible que dans le paquetage."""
        return self.__email

    # ------------------------------------------------ mutateurs de paquetage
    def _add_role(self, r: Role) -> None:
        self.__assigned_roles.add(r)

    def _remove_role(self, r: Role) -> None:
        self.__assigned_roles.discard(r)

    def _deactivate(self) -> None:
        self.__active = False

    def _reactivate(self) -> None:
        self.__active = True

    # ------------------------------------------------ operations publiques
    def get_roles(self) -> frozenset:
        """Copie immuable : modifier le resultat ne change pas les roles."""
        return frozenset(self.__assigned_roles)

    def can_globally(self, p: Permission) -> bool:
        """Droit global : faux si le compte est desactive."""
        return self.__active and any(r.allows(p) for r in self.__assigned_roles)

    def __repr__(self) -> str:
        roles = ", ".join(sorted(r.name() for r in self.__assigned_roles))
        etat = "actif" if self.__active else "desactive"
        return f"User#{self.__user_id} {self.__name} [{roles}] ({etat})"


class UserRegistry:
    """Registre des comptes. Il nait avec son premier administrateur.

    Le registre est injecte dans TicketRegistry : un compte qui n'appartient pas
    a ce registre (autre registre, objet copie, User construit a la main) est
    refuse partout, sans etat global.
    """

    def __init__(self, admin_name: str, admin_email: str) -> None:
        self.__next_id = 1
        self.__users = {}  # association users : id -> User
        admin = self.register(admin_name, admin_email)
        if admin is None:
            raise ValueError("nom ou email du premier administrateur invalide")
        admin._add_role(DeveloperRole())
        admin._add_role(AdminRole())

    @property
    def next_id(self) -> int:
        return self.__next_id

    # ------------------------------------------------ outils prives
    def __refuse(self, motif: str, valeur=False):
        _journal.info("refus : %s", motif)
        return valeur

    def __authorize(self, actor: object, p: Permission) -> bool:
        return self.contains(actor) and actor.can_globally(p)

    def __active_admins(self) -> List[User]:
        return [u for u in self.__users.values() if u.active and AdminRole() in u.get_roles()]

    @staticmethod
    def __normalize(email: str) -> str:
        return email.strip().lower()

    # ------------------------------------------------ operations publiques
    def contains(self, u: User) -> bool:
        """Vrai si u est exactement l'un des comptes de ce registre (pas une copie, pas un faux)."""
        return isinstance(u, User) and self.__users.get(u.user_id) is u

    def register(self, name: str, email: str) -> Optional[User]:
        """Inscription libre : ReporterRole seul, email unique (casse ignoree)."""
        if not texte_valide(name, 100):
            return self.__refuse("nom vide, trop long ou contenant un caractere de controle", None)
        if not isinstance(email, str) or not _FORMAT_EMAIL.match(email.strip()):
            return self.__refuse(f"email invalide : {email!r}", None)
        email = self.__normalize(email)
        if any(u._get_email() == email for u in self.__users.values()):
            return self.__refuse(f"email deja utilise : {email}", None)
        user = User(self.__next_id, name.strip(), email)
        user._add_role(ReporterRole())
        self.__users[user.user_id] = user
        self.__next_id += 1
        return user

    def find_by_id(self, actor: User, id: int) -> Optional[User]:
        """Comptes actifs pour tout acteur actif ; desactives avec MANAGE_USERS."""
        if not self.contains(actor) or not actor.active:
            return self.__refuse("acteur inconnu ou desactive", None)
        if not isinstance(id, int) or isinstance(id, bool):
            return self.__refuse(f"identifiant invalide : {id!r}", None)
        target = self.__users.get(id)
        if target is None:
            return None
        if not target.active and not actor.can_globally(Permission.MANAGE_USERS):
            return self.__refuse("compte desactive visible seulement avec MANAGE_USERS", None)
        return target

    def find_all(self, actor: User) -> List[User]:
        if not self.__authorize(actor, Permission.MANAGE_USERS):
            return self.__refuse("find_all exige MANAGE_USERS", [])
        return sorted(self.__users.values(), key=lambda u: u.user_id)

    def grant_role(self, actor: User, target: User, r: Role) -> bool:
        """MANAGE_USERS ; attribuer AdminRole ajoute aussi DeveloperRole."""
        if not self.__authorize(actor, Permission.MANAGE_USERS):
            return self.__refuse("grant_role exige MANAGE_USERS")
        if not self.contains(target) or type(r) not in _ROLES_CONNUS:
            return self.__refuse("cible inconnue ou role hors des trois roles du systeme")
        if r in target.get_roles():
            return self.__refuse(f"{target.name} a deja le role {r.name()}")
        if isinstance(r, AdminRole):
            target._add_role(DeveloperRole())
        target._add_role(r)
        return True

    def revoke_role(self, actor: User, target: User, r: Role) -> bool:
        """MANAGE_USERS ; ni ReporterRole, ni DeveloperRole d'un admin,
        ni le dernier AdminRole actif."""
        if not self.__authorize(actor, Permission.MANAGE_USERS):
            return self.__refuse("revoke_role exige MANAGE_USERS")
        if not self.contains(target) or type(r) not in _ROLES_CONNUS:
            return self.__refuse("cible inconnue ou role hors des trois roles du systeme")
        roles = target.get_roles()
        if r not in roles:
            return self.__refuse(f"{target.name} n'a pas le role {r.name()}")
        if isinstance(r, ReporterRole):
            return self.__refuse("ReporterRole ne se retire jamais")
        if isinstance(r, DeveloperRole) and AdminRole() in roles:
            return self.__refuse("un admin garde DeveloperRole")
        if isinstance(r, AdminRole) and self.__active_admins() == [target]:
            return self.__refuse("dernier AdminRole actif")
        target._remove_role(r)
        return True

    def deactivate(self, actor: User, target: User) -> bool:
        """MANAGE_USERS ; le compte reste auteur et assigne ; pas le dernier admin actif."""
        if not self.__authorize(actor, Permission.MANAGE_USERS):
            return self.__refuse("deactivate exige MANAGE_USERS")
        if not self.contains(target):
            return self.__refuse("cible inconnue")
        if not target.active:
            return self.__refuse(f"{target.name} est deja desactive")
        if self.__active_admins() == [target]:
            return self.__refuse("dernier admin actif")
        target._deactivate()
        return True

    def reactivate(self, actor: User, target: User) -> bool:
        if not self.__authorize(actor, Permission.MANAGE_USERS):
            return self.__refuse("reactivate exige MANAGE_USERS")
        if not self.contains(target):
            return self.__refuse("cible inconnue")
        if target.active:
            return self.__refuse(f"{target.name} est deja actif")
        target._reactivate()
        return True
