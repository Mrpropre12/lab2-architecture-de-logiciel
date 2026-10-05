"""Consultation a l'ecran : rendu texte d'un ticket, affiche dans le terminal.

Une interface graphique (prevue au laboratoire suivant) serait un autre
ViewVisitor, ajoute ici sans toucher au paquet ticket.
"""
import os

from .._texte import affichable
from ..ticket import ViewVisitor

_APERCU_MAX = 1000  # caracteres de texte affiches par fichier


def _date(d) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


class ScreenRenderVisitor(ViewVisitor):
    """Construit le rendu texte ; un nouveau parcours recommence a zero."""

    def __init__(self) -> None:
        self.__output = ""

    @property
    def output(self) -> str:
        return self.__output

    def __ligne(self, texte: str = "", suite: str = "      ") -> None:
        """Une entree du rendu ; ses lignes suivantes sont indentees pour ne jamais imiter une autre entree."""
        premiere, *autres = affichable(texte).split("\n")
        self.__output += premiere + "\n" + "".join(suite + ligne + "\n" for ligne in autres)

    def visit_ticket(self, t) -> None:
        self.__output = ""
        archive = f", archive le {_date(t.archive_date)}" if t.is_archived() else ""
        assigne = t.get_assignee().name if t.get_assignee() else "aucun"
        self.__ligne(f"Ticket #{t.ticket_id}  [{t.get_status().value}{archive}]  priorite {t.priority.value}")
        self.__ligne(f"  Titre    : {t.title}")
        self.__ligne(f"  Auteur   : {t.get_author().name}    Assigne : {assigne}")
        self.__ligne(f"  Cree le  : {_date(t.creation_date)}    Modifie le : {_date(t.update_date)}")

    def visit_text(self, c) -> None:
        self.__ligne(f"  [texte] {os.path.basename(c.path)}")
        texte = c.text or ""
        if len(texte) > _APERCU_MAX:
            texte = texte[:_APERCU_MAX] + f" ... ({len(c.text) - _APERCU_MAX} caracteres de plus)"
        for ligne in texte.splitlines() or [""]:
            self.__ligne(f"      {ligne}", suite="      ")

    def visit_image(self, c) -> None:
        """Premier affichage : c'est ici que l'image est chargee (puis gardee en cache)."""
        taille = f"{c.width} x {c.height}" if c.load() else "illisible"
        self.__ligne(f"  [image] {os.path.basename(c.path)} ({taille})")

    def visit_video(self, c) -> None:
        self.__ligne(f"  [video] {os.path.basename(c.path)} (chemin conserve, non lue)")

    def visit_comment(self, c) -> None:
        self.__ligne(f"  [commentaire #{c.comment_id}] {c.get_author().name}, {_date(c.posted_at)} : {c.text}")

    def result(self) -> str:
        return self.__output
