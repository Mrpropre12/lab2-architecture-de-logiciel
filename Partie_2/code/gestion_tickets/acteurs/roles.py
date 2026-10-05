"""Roles attribues aux utilisateurs a l'execution (RBAC par composition).

Role est l'interface, BaseRole factorise le comportement commun et chaque
role concret ne fait que declarer son ensemble de permissions.
"""
from abc import ABC, abstractmethod

from .permissions import Permission


class Role(ABC):
    """Interface d'un role."""

    @abstractmethod
    def name(self) -> str:
        """Nom lisible du role."""

    @abstractmethod
    def permissions(self) -> frozenset:
        """Ensemble immuable des permissions accordees."""

    @abstractmethod
    def allows(self, p: Permission) -> bool:
        """Vrai si le role accorde la permission p."""


class BaseRole(Role):
    """Comportement commun : detient l'ensemble recu a la construction."""

    def __init__(self, granted: frozenset) -> None:
        # Constructeur protege (#) : appele seulement par les sous-classes.
        self.__granted = frozenset(granted)

    @property
    def granted(self) -> frozenset:
        """Accesseur en lecture de l'attribut granted (convention de la legende)."""
        return self.__granted

    def permissions(self) -> frozenset:
        return self.__granted

    def allows(self, p: Permission) -> bool:
        return p in self.__granted

    def __eq__(self, o: object) -> bool:
        """equals : deux roles sont egaux s'ils sont de la meme classe."""
        return isinstance(o, BaseRole) and type(self) is type(o)

    def __hash__(self) -> int:
        """hash : coherent avec equals (depend seulement de la classe)."""
        return hash(type(self))

    def __repr__(self) -> str:
        return self.name()

    @abstractmethod
    def name(self) -> str:
        """Nom lisible du role."""


class ReporterRole(BaseRole):
    """Rapporteur : tout utilisateur l'a toujours."""

    __PERMISSIONS = frozenset({Permission.VIEW, Permission.COMMENT, Permission.EXPORT,
                               Permission.CREATE, Permission.EDIT, Permission.ATTACH})

    def __init__(self) -> None:
        super().__init__(ReporterRole.__PERMISSIONS)

    def name(self) -> str:
        return "Rapporteur"


class DeveloperRole(BaseRole):
    """Developpeur : fait avancer les tickets et voit tous les tickets."""

    __PERMISSIONS = frozenset({Permission.ASSIGN, Permission.SUBMIT, Permission.VALIDATE,
                               Permission.REJECT, Permission.CLOSE, Permission.VIEW_ALL})

    def __init__(self) -> None:
        super().__init__(DeveloperRole.__PERMISSIONS)

    def name(self) -> str:
        return "Developpeur"


class AdminRole(BaseRole):
    """Administrateur : reouvre, priorise, archive et gere les comptes."""

    __PERMISSIONS = frozenset({Permission.REOPEN, Permission.SET_PRIORITY,
                               Permission.ARCHIVE, Permission.MANAGE_USERS})

    def __init__(self) -> None:
        super().__init__(AdminRole.__PERMISSIONS)

    def name(self) -> str:
        return "Administrateur"
