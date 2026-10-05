"""Permissions globales du systeme (enum Permission du diagramme)."""
from enum import Enum


class Permission(Enum):
    """Droit global. Chaque permission appartient a un seul role."""

    VIEW = "VIEW"
    COMMENT = "COMMENT"
    EXPORT = "EXPORT"
    CREATE = "CREATE"
    EDIT = "EDIT"
    ATTACH = "ATTACH"
    ASSIGN = "ASSIGN"
    SUBMIT = "SUBMIT"
    VALIDATE = "VALIDATE"
    REJECT = "REJECT"
    CLOSE = "CLOSE"
    REOPEN = "REOPEN"
    SET_PRIORITY = "SET_PRIORITY"
    ARCHIVE = "ARCHIVE"
    VIEW_ALL = "VIEW_ALL"
    MANAGE_USERS = "MANAGE_USERS"
