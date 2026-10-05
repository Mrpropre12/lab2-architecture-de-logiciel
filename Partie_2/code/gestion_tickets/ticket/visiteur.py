"""Contrat du Visiteur : le paquet ticket possede l'interface qu'il appelle.

Les visiteurs concrets (ecran, PDF) vivent dans le paquet consultation et
dependent de ce contrat, jamais l'inverse.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # annotations seulement : aucun import circulaire a l'execution
    from .contenus import ImageFileContent, TextFileContent, VideoFileContent
    from .ticket import Comment, Ticket


class TicketVisitor(ABC):
    """Parcourt un ticket, ses commentaires et sa description (double dispatch)."""

    @abstractmethod
    def visit_ticket(self, t: "Ticket") -> None:
        """Appele une fois, au debut du parcours."""

    @abstractmethod
    def visit_comment(self, c: "Comment") -> None:
        """Appele pour chaque commentaire, dans l'ordre."""

    @abstractmethod
    def visit_text(self, c: "TextFileContent") -> None:
        """Appele pour chaque contenu texte."""

    @abstractmethod
    def visit_image(self, c: "ImageFileContent") -> None:
        """Appele pour chaque image."""

    @abstractmethod
    def visit_video(self, c: "VideoFileContent") -> None:
        """Appele pour chaque video."""


class ViewVisitor(TicketVisitor):
    """Visiteur de consultation : exige la permission VIEW."""

    @abstractmethod
    def result(self) -> str:
        """Rendu produit par le parcours."""


class ExportVisitor(TicketVisitor):
    """Visiteur d'export : exige la permission EXPORT."""

    @abstractmethod
    def result(self) -> Optional[Path]:
        """Fichier produit, ou None tant qu'aucun export n'a reussi."""
