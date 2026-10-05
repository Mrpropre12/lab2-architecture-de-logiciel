"""Export PDF d'un ticket (bibliotheque fpdf2 : pip install fpdf2).

Le nom du fichier est genere a la construction, unique, et confine dans
EXPORT_DIR par PathGuard : l'utilisateur ne choisit jamais le chemin, donc il
ne peut ni ecraser ni lire l'export d'un autre.
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..ticket import ExportVisitor, PathGuard

try:
    from fpdf import FPDF
except ImportError:  # l'export est indisponible, le reste du systeme fonctionne
    FPDF = None

_journal = logging.getLogger(__name__)
_CODE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REMPLACEMENTS = {"’": "'", "‘": "'", "“": '"', "”": '"', "…": "...",
                  "–": "-", "—": "-", "œ": "oe", "Œ": "OE", " ": " "}


def _latin1(texte: str) -> str:
    """Les polices standard du PDF ne couvrent que le latin-1 : les autres caracteres sont remplaces."""
    for avant, apres in _REMPLACEMENTS.items():
        texte = texte.replace(avant, apres)
    return texte.encode("latin-1", "replace").decode("latin-1")


class PDFExportVisitor(ExportVisitor):

    __EXPORT_DIR = os.environ.get("TICKETS_EXPORT_DIR", os.path.join(_CODE, "donnees", "exports"))

    def __init__(self) -> None:
        self.__target_path = PDFExportVisitor.__nom_unique()
        self.__pdf = None  # document en cours de construction pendant le parcours

    @staticmethod
    def __nom_unique() -> str:
        nom = f"ticket_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.pdf"
        return PathGuard.confine(nom, PDFExportVisitor.__EXPORT_DIR)

    @property
    def target_path(self) -> str:
        return self.__target_path

    # ------------------------------------------------ mise en page
    def __texte(self, texte: str, taille: int = 10, gras: bool = False) -> None:
        self.__pdf.set_font("Helvetica", "B" if gras else "", taille)
        self.__pdf.multi_cell(0, taille * 0.55, _latin1(texte), new_x="LMARGIN", new_y="NEXT")

    def __titre(self, texte: str) -> None:
        self.__pdf.ln(3)
        self.__texte(texte, 12, gras=True)

    # ------------------------------------------------ visites
    def visit_ticket(self, t) -> None:
        if FPDF is None:
            _journal.warning("export PDF indisponible : installez fpdf2 (pip install fpdf2)")
            return
        if self.__pdf is not None:  # visiteur reutilise : nouveau fichier, l'export precedent est garde
            self.__target_path = PDFExportVisitor.__nom_unique()
        self.__pdf = FPDF()
        self.__pdf.set_title(_latin1(f"Ticket #{t.ticket_id}"))
        self.__pdf.add_page()
        assigne = t.get_assignee().name if t.get_assignee() else "aucun"
        archive = f" (archive le {t.archive_date:%Y-%m-%d})" if t.is_archived() else ""
        self.__texte(f"Ticket #{t.ticket_id} : {t.title}", 16, gras=True)
        self.__texte(f"Statut : {t.get_status().value}{archive}    Priorite : {t.priority.value}")
        self.__texte(f"Auteur : {t.get_author().name}    Assigne : {assigne}")
        self.__texte(f"Cree le {t.creation_date:%Y-%m-%d %H:%M}, modifie le {t.update_date:%Y-%m-%d %H:%M}")
        self.__titre("Description et commentaires")

    def visit_text(self, c) -> None:
        if self.__pdf is None:
            return
        self.__texte(f"[texte] {os.path.basename(c.path)}", gras=True)
        self.__texte(c.text or "")

    def visit_image(self, c) -> None:
        """Image integree dans le document ; si elle est illisible, seul son nom apparait."""
        if self.__pdf is None:
            return
        self.__texte(f"[image] {os.path.basename(c.path)}", gras=True)
        if not c.load():  # illisible ou plus de 25 megapixels : on ne la decompresse pas
            self.__texte("(image non integrable)")
            return
        try:
            self.__pdf.image(c.path, w=min(120, self.__pdf.epw))
        except Exception:  # fichier corrompu ou format non pris en charge par fpdf2
            _journal.info("image non integrable : %s", c.path)
            self.__texte("(image non integrable)")

    def visit_video(self, c) -> None:
        if self.__pdf is None:
            return
        self.__texte(f"[video] {os.path.basename(c.path)} (chemin seulement, la video n'est pas lue)", gras=True)

    def visit_comment(self, c) -> None:
        if self.__pdf is None:
            return
        self.__texte(f"Commentaire #{c.comment_id}, {c.get_author().name}, {c.posted_at:%Y-%m-%d %H:%M}", gras=True)
        self.__texte(c.text)

    def result(self) -> Optional[Path]:
        """Ecrit le fichier ; None tant qu'aucun parcours n'a eu lieu ou si l'ecriture echoue."""
        if self.__pdf is None or self.__target_path is None:
            return None
        try:
            os.makedirs(os.path.dirname(self.__target_path), exist_ok=True)
            self.__pdf.output(self.__target_path)
        except OSError as erreur:
            _journal.warning("export impossible : %s", erreur)
            return None
        return Path(self.__target_path)
