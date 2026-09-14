
from ticket import Ticket
from user import User


class Admin:
    #initialisation d'un admin 
    def __init__(self, admin_id: int, name: str, email: str,
                 tickets: list[Ticket] = None):
        self.adminID = admin_id
        self.name = name
        self.email = email
        self._tickets: list[Ticket] = tickets if tickets is not None else []

    #function qui permet d'assigner un ticker
    def assignTicket(self, ticket: Ticket, user: User) -> None:
        ticket.assignTo(user)

    #function pour fermer un ticker
    def closeTicket(self, ticket: Ticket) -> None:
        ticket.updateStatus("FERMÉ")
        print(f"[Admin {self.name}] a fermé le ticket #{ticket.ticketID}")

    #function permettant de lister tous les tickers
    def viewAllTickets(self) -> list[Ticket]:
        return self._tickets

    def __str__(self) -> str:
        return f"Admin(id={self.adminID}, name='{self.name}')"