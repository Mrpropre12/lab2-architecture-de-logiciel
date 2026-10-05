"""Acces aux fichiers : Fabrique (seule voie de creation d'un contenu) et confinement."""
import logging
import os
from typing import Optional

from .contenus import Content, ImageFileContent, TextFileContent, VideoFileContent

_journal = logging.getLogger(__name__)
_CODE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PathGuard:
    """Refuse tout chemin qui sort du dossier racine autorise."""

    @staticmethod
    def confine(path: str, root: str) -> Optional[str]:
        """Chemin reel confine dans root, ou None (.., lien symbolique, chemin absolu externe)."""
        if not isinstance(path, str) or not isinstance(root, str) or not path or "\x00" in path:
            _journal.info("refus : chemin invalide %r", path)
            return None
        try:
            racine = os.path.realpath(root)
            cible = os.path.realpath(os.path.join(racine, path))  # un chemin absolu remplace racine
            commun = os.path.commonpath([os.path.normcase(racine), os.path.normcase(cible)])
        except (OSError, ValueError):  # lecteurs differents (C: et D:), nom non encodable ...
            _journal.info("refus : chemin inutilisable %r", path)
            return None
        if commun != os.path.normcase(racine):
            _journal.info("refus : %r sort de %s", path, racine)
            return None
        return cible


class ContentFactory:
    """Cree le bon type de contenu selon l'extension, puis le valide."""

    __UPLOAD_DIR = os.environ.get("TICKETS_UPLOAD_DIR", os.path.join(_CODE, "donnees", "televersements"))
    __TYPES = {".txt": TextFileContent,
               ".png": ImageFileContent, ".jpg": ImageFileContent,
               ".jpeg": ImageFileContent, ".gif": ImageFileContent,
               ".mp4": VideoFileContent, ".mov": VideoFileContent, ".avi": VideoFileContent}

    @staticmethod
    def from_path(path: str) -> Optional[Content]:
        """Contenu valide situe dans UPLOAD_DIR, ou None."""
        chemin = PathGuard.confine(path, ContentFactory.__UPLOAD_DIR)
        if chemin is None:
            return None
        type_contenu = ContentFactory.__TYPES.get(os.path.splitext(chemin)[1].lower())
        if type_contenu is None:
            _journal.info("refus : extension non prise en charge : %s", chemin)
            return None
        contenu = type_contenu(chemin)
        return contenu if contenu._is_valid() else None
