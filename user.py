
from datetime import datetime
from ticket import Ticket

class User:
    #function qui permet d'initialiser un ticker 
    def __init__(self, user_id: int, name: str, email: str, role: str):
        self.userID = user_id
        self.name = name
        self.email = email
        self.role = role

    #function qui permet de créer un utilisateur 
    def createTicket(self, ticket: Ticket) -> None:
        print(f"[User {self.name}] a créé le {ticket}")

    #function qui permet de consulter un ticker 
    def viewTicket(self, ticket: Ticket) -> None:
        print(f"[User {self.name}] consulte : {ticket}")

    #function qui permet de mettre a jour un ticker
    def updateTicket(self, ticket: Ticket) -> None:
        ticket.updateDate = datetime.now()
        print(f"[User {self.name}] a mis à jour : {ticket}")

    def __str__(self) -> str:
        return f"User(id={self.userID}, name='{self.name}', role={self.role})"