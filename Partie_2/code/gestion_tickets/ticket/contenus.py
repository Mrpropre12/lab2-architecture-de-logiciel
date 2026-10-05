"""Description d'un ticket : chaque type de fichier se valide et se charge differemment.

- texte : valide puis lu immediatement (UTF-8, 1 Mo au plus) ;
- image : signature verifiee, lue seulement au premier affichage, dimensions en cache ;
- video : signature verifiee, jamais lue, seul le chemin est conserve.

Les constructeurs sont reserves au paquetage (~) : ContentFactory est la seule
voie de creation, ce qui garantit le confinement et la validation.
"""
import logging
import os
import struct
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .visiteur import TicketVisitor

_journal = logging.getLogger(__name__)
_MO = 1024 * 1024
_PIXELS_MAX = 25_000_000  # au-dela, l'affichage ou l'export demanderait des Go de memoire


def _taille_ok(chemin: str, maximum: int) -> bool:
    try:
        return os.path.isfile(chemin) and 0 < os.path.getsize(chemin) <= maximum
    except OSError:
        return False


def _entete(chemin: str, n: int = 16) -> bytes:
    """Premiers octets du fichier, ou rien s'il est illisible (droits, verrou de Windows ...)."""
    try:
        with open(chemin, "rb") as f:
            return f.read(n)
    except OSError:
        _journal.info("refus : fichier illisible : %s", chemin)
        return b""


class Content(ABC):
    """Un element de la description, designe par son chemin."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._loaded = False

    @property
    def path(self) -> str:
        return self._path

    @property
    def loaded(self) -> bool:
        return self._loaded

    @abstractmethod
    def _is_valid(self) -> bool:
        """~ isValid : appele par la fabrique avant de livrer le contenu."""

    @abstractmethod
    def load(self) -> bool:
        """Charge le contenu selon la strategie propre au type."""

    @abstractmethod
    def _accept(self, v: "TicketVisitor") -> None:
        """~ accept : double dispatch, appele par Ticket pendant le parcours."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}({os.path.basename(self._path)})"


class TextFileContent(Content):
    __EXTENSIONS = (".txt",)
    __MAX = 1 * _MO

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.__text = None

    @property
    def text(self) -> Optional[str]:
        return self.__text

    def _is_valid(self) -> bool:
        """.txt en UTF-8, 1 Mo au plus. La lecture fait partie de la validation."""
        if not self._path.lower().endswith(TextFileContent.__EXTENSIONS):
            return False
        if not _taille_ok(self._path, TextFileContent.__MAX):
            _journal.info("refus : texte absent, vide ou de plus de 1 Mo : %s", self._path)
            return False
        return self.load()

    def load(self) -> bool:
        """Lu immediatement : le texte est garde en memoire."""
        try:
            with open(self._path, encoding="utf-8-sig") as f:  # -sig : ignore le BOM de Windows
                self.__text = f.read()
        except (OSError, UnicodeDecodeError):
            _journal.info("refus : texte illisible ou pas en UTF-8 : %s", self._path)
            self.__text, self._loaded = None, False
            return False
        self._loaded = True
        return True

    def _accept(self, v: "TicketVisitor") -> None:
        v.visit_text(self)


def _dimensions(donnees: bytes) -> Optional[Tuple[int, int]]:
    """Largeur et hauteur lues dans l'en-tete PNG, GIF ou JPEG (sans bibliotheque)."""
    if donnees.startswith(b"\x89PNG\r\n\x1a\n") and len(donnees) >= 24:
        return struct.unpack(">II", donnees[16:24])
    if donnees[:6] in (b"GIF87a", b"GIF89a") and len(donnees) >= 10:
        return struct.unpack("<HH", donnees[6:10])
    if donnees.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 <= len(donnees):
            if donnees[i] != 0xFF:
                return None
            marqueur = donnees[i + 1]
            if 0xC0 <= marqueur <= 0xCF and marqueur not in (0xC4, 0xC8, 0xCC):
                hauteur, largeur = struct.unpack(">HH", donnees[i + 5:i + 9])
                return largeur, hauteur
            i += 2 + struct.unpack(">H", donnees[i + 2:i + 4])[0]
    return None


class ImageFileContent(Content):
    __SIGNATURES = {".png": (b"\x89PNG\r\n\x1a\n",), ".gif": (b"GIF87a", b"GIF89a"),
                    ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",)}
    __MAX = 10 * _MO

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.__width = None
        self.__height = None

    @property
    def width(self) -> Optional[int]:
        return self.__width

    @property
    def height(self) -> Optional[int]:
        return self.__height

    def _is_valid(self) -> bool:
        """.png, .jpg ou .gif de 10 Mo au plus, dont la signature correspond a l'extension."""
        signatures = ImageFileContent.__SIGNATURES.get(os.path.splitext(self._path)[1].lower())
        if signatures is None or not _taille_ok(self._path, ImageFileContent.__MAX):
            _journal.info("refus : image absente, de type inconnu ou de plus de 10 Mo : %s", self._path)
            return False
        if not _entete(self._path).startswith(signatures):
            _journal.info("refus : le contenu ne correspond pas a l'extension : %s", self._path)
            return False
        return True

    def load(self) -> bool:
        """Lu au premier affichage seulement ; ensuite les dimensions sont en cache."""
        if self._loaded:
            return True
        try:
            with open(self._path, "rb") as f:
                dims = _dimensions(f.read())
        except OSError:
            dims = None
        if dims is None:
            _journal.info("image illisible : %s", self._path)
            return False
        if dims[0] * dims[1] > _PIXELS_MAX:
            _journal.info("image de plus de 25 megapixels refusee a l'affichage : %s", self._path)
            return False
        self.__width, self.__height = dims
        self._loaded = True
        return True

    def unload(self) -> None:
        """Libere le cache ; le prochain affichage relira le fichier."""
        self.__width = self.__height = None
        self._loaded = False

    def _accept(self, v: "TicketVisitor") -> None:
        v.visit_image(self)


class VideoFileContent(Content):
    __EXTENSIONS = (".mp4", ".mov", ".avi")
    __ATOMES = {".mp4": (b"ftyp",), ".mov": (b"ftyp", b"moov", b"wide", b"mdat", b"free", b"skip")}
    __MAX = 500 * _MO

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.__duration = None

    @property
    def duration(self) -> Optional[int]:
        """Metadonnee facultative : non calculee, la video n'est jamais lue."""
        return self.__duration

    def _is_valid(self) -> bool:
        """.mp4, .mov ou .avi de 500 Mo au plus, signature verifiee."""
        ext = os.path.splitext(self._path)[1].lower()
        if ext not in VideoFileContent.__EXTENSIONS or not _taille_ok(self._path, VideoFileContent.__MAX):
            _journal.info("refus : video absente, de type inconnu ou de plus de 500 Mo : %s", self._path)
            return False
        tete = _entete(self._path)
        if ext == ".avi":
            ok = tete[:4] == b"RIFF" and tete[8:12] == b"AVI "
        else:  # MP4 et QuickTime : premier atome a l'octet 4
            ok = tete[4:8] in VideoFileContent.__ATOMES[ext]
        if not ok:
            _journal.info("refus : le contenu ne correspond pas a l'extension : %s", self._path)
        return ok

    def load(self) -> bool:
        """Jamais lu : le chemin suffit pour l'afficher ou l'exporter."""
        self._loaded = True
        return True

    def _accept(self, v: "TicketVisitor") -> None:
        v.visit_video(self)
