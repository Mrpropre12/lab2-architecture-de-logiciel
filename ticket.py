
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import utilisé uniquement par l'analyseur de type 
    # jamais à l'exécution évite l'import circulaire avec user.py,
    # qui importe déjà Ticket depuis ce fichier.
    from user import User


class Ticket:
    #function pour initialiser un ticker
    def __init__(self, ticket_id: int, title: str, description: str,
                 priority: str = "NORMALE"):
        self.ticketID = ticket_id
        self.title = title
        self.description = description
        self.status = "OUVERT"
        self.priority = priority
        self.creationDate = datetime.now()
        self.updateDate = datetime.now()

    #function qui permet d'assigner un ticker a un utilisateur 
    def assignTo(self, user: "User") -> None:
        self.status = "ASSIGNÉ"
        self.updateDate = datetime.now()
        print(f"[Ticket #{self.ticketID}] assigné à {user.name}. "
              f"Statut -> {self.status}")
    #function qui permet de mettre a jour le status d'un ticker
    def updateStatus(self, status: str) -> None:
        self.status = status
        self.updateDate = datetime.now()
        print(f"[Ticket #{self.ticketID}] statut mis à jour -> {self.status}")

    #function qui permet d'ajouter un commentaire a un ticker  
    def addComment(self, comment: str) -> None:
        self.updateDate = datetime.now()
        print(f"[Ticket #{self.ticketID}] nouveau commentaire : \"{comment}\"")
    
    def __str__(self) -> str:
        return (f"Ticket(id={self.ticketID}, title='{self.title}', "
                f"status={self.status}, priority={self.priority}, "
                f"créé le {self.creationDate:%Y-%m-%d %H:%M})")