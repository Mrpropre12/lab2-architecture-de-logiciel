
from user import User
from admin import Admin
from ticket import Ticket

# Fonctions utilitaires de recherche

#cherche un utilisateur et le retourne si il existe
def find_user_by_id(users, user_id):
    for u in users:
        if u.userID == user_id:
            return u
    return None

#cherche un admistrateur et le retourne si il existe
def find_admin_by_id(admins, admin_id):
    for a in admins:
        if a.adminID == admin_id:
            return a
    return None

#cherche un ticker et le retourne si il existe
def find_ticket_by_id(tickets, ticket_id):
    for t in tickets:
        if t.ticketID == ticket_id:
            return t
    return None

#function permettant de lire un message
def lire_entier(message):
    while True:
        valeur = input(message).strip()
        if valeur.isdigit():
            return int(valeur)
        print("Entrée invalide : veuillez entrer un nombre entier.")

# Actions du menu Utilisateur
#function permettant a un utilisateur de créer un ticker 
def creer_ticket(tickets, utilisateur, prochain_id):
    print("\n--- Création d'un ticket ---")
    titre = input("Titre du ticket : ").strip()
    description = input("Description : ").strip()
    priorite = input("Priorité (BASSE / NORMALE / HAUTE) [NORMALE] : ").strip().upper()
    if priorite not in ("BASSE", "NORMALE", "HAUTE"):
        priorite = "NORMALE"

    ticket = Ticket(ticket_id=prochain_id, title=titre, description=description,
                     priority=priorite)
    tickets.append(ticket)
    utilisateur.createTicket(ticket)
    print("Ticket créé avec succès.")
    return prochain_id + 1

#function permmettant a un utilisateur de consulter l'état d'un ticker
def voir_etat_ticket(tickets, utilisateur):
    print("\n--- Voir l'état d'un ticket ---")
    ticket_id = lire_entier("ID du ticket : ")
    ticket = find_ticket_by_id(tickets, ticket_id)
    if ticket is None:
        print("Ticket introuvable.")
        return
    utilisateur.viewTicket(ticket)

#function permettant a un utilisateur de modifier le statut d'un ticker
def changer_statut_ticket(tickets):
    print("\n--- Changer le statut d'un ticket ---")
    ticket_id = lire_entier("ID du ticket : ")
    ticket = find_ticket_by_id(tickets, ticket_id)
    if ticket is None:
        print("Ticket introuvable.")
        return

    print("\nStatuts disponibles :")
    print("1. VALIDATION")
    print("2. TERMINÉ")
    choix = input("Choix : ").strip()

    if choix == "1":
        ticket.updateStatus("VALIDATION")
    elif choix == "2":
        ticket.updateStatus("TERMINÉ")
    else:
        print("Choix invalide.")

# Actions du menu Admin

#function permmetant a un admin d'assiger un nticker a un utilisateur 
def assigner_ticket(tickets, users, admin):
    print("\n--- Assignation d'un ticket ---")
    if not tickets:
        print("Aucun ticket à assigner pour le moment.")
        return

    print("\nTickets disponibles :")
    for t in tickets:
        print(f"  #{t.ticketID} - {t.title} (statut : {t.status})")

    print("\nMembres de l'équipe :")
    for u in users:
        print(f"  #{u.userID} - {u.name} ({u.role})")

    ticket_id = lire_entier("\nID du ticket à assigner : ")
    ticket = find_ticket_by_id(tickets, ticket_id)
    if ticket is None:
        print("Ticket introuvable.")
        return

    user_id = lire_entier("ID du membre à qui assigner le ticket : ")
    utilisateur = find_user_by_id(users, user_id)
    if utilisateur is None:
        print("Membre introuvable.")
        return

    admin.assignTicket(ticket, utilisateur)

#function permettant a un admin de fermer un ticker
def fermer_ticket(tickets, admin):
    print("\n--- Fermeture d'un ticket ---")
    ticket_id = lire_entier("ID du ticket à fermer : ")
    ticket = find_ticket_by_id(tickets, ticket_id)
    if ticket is None:
        print("Ticket introuvable.")
        return
    admin.closeTicket(ticket)

#function permettant de lister tout les tickers
def voir_tous_les_tickets(tickets, admin):
    print("\n--- Liste de tous les tickets ---")
    resultat = admin.viewAllTickets()
    if not resultat:
        print("Aucun ticket enregistré pour le moment.")
        return
    for t in resultat:
        print(f"  #{t.ticketID} - {t.title} (statut : {t.status})")



# Menus par rôle

#Menu utilisateur : boucle de menu pour authentifier un utilisateur et le retourner
def menu_utilisateur(tickets, utilisateur, prochain_id):
    while True:
        print("\n" + "=" * 50)
        print(f"MENU UTILISATEUR - {utilisateur.name}")
        print("=" * 50)
        print("1. Créer un ticket")
        print("2. Voir l'état d'un ticket")
        print("3. Changer le statut d'un ticket")
        print("0. Quitter (retour à l'authentification)")
        choix = input("Votre choix : ").strip()

        if choix == "1":
            prochain_id = creer_ticket(tickets, utilisateur, prochain_id)
        elif choix == "2":
            voir_etat_ticket(tickets, utilisateur)
        elif choix == "3":
            changer_statut_ticket(tickets)
        elif choix == "0":
            break
        else:
            print("Choix invalide, veuillez réessayer.")

    return prochain_id

#Boucle de menu pour admin authentifié
def menu_admin(tickets, users, admin):
    while True:
        print("\n" + "=" * 50)
        print(f"MENU ADMIN - {admin.name}")
        print("=" * 50)
        print("1. Assigner un ticket")
        print("2. Fermer un ticket")
        print("3. Voir tous les tickets")
        print("0. Quitter (retour à l'authentification)")
        choix = input("Votre choix : ").strip()

        if choix == "1":
            assigner_ticket(tickets, users, admin)
        elif choix == "2":
            fermer_ticket(tickets, admin)
        elif choix == "3":
            voir_tous_les_tickets(tickets, admin)
        elif choix == "0":
            break
        else:
            print("Choix invalide, veuillez réessayer.")


# Menu d'authentification et point d'entrée
# affichage du menu principale
def afficher_menu_authentification():
    print("\n" + "=" * 50)
    print("SYSTÈME DE GESTION DE TICKETS")
    print("=" * 50)
    print("1. Je suis un utilisateur")
    print("2. Je suis un admin")
    print("0. Quitter")


def main():
    # Création des utilisateurs et administrateurs de départ
    user1 = User(user_id=1, name="Alice Tremblay",
                 email="alice.tremblay@uqac.ca", role="Utilisateur")
    user2 = User(user_id=2, name="Marc Bouchard",
                 email="marc.bouchard@uqac.ca", role="Utilisateur")

    users = [user1, user2]
    tickets = []

    #Creation de l'admin
    admin1 = Admin(admin_id=1, name="Bob Gagnon", email="bob.gagnon@uqac.ca",
                    tickets=tickets)
    admins = [admin1]
    prochain_id = 101  # identifiant auto-incrémenté pour les nouveaux tickets

    while True:
        afficher_menu_authentification()
        choix = input("Votre choix : ").strip()

        if choix == "1":
            user_id = lire_entier("Votre ID utilisateur : ")
            utilisateur = find_user_by_id(users, user_id)
            if utilisateur is None:
                print("Cette personne n'existe pas.")
                continue
            print(f"\nBienvenue, {utilisateur.name} !")
            prochain_id = menu_utilisateur(tickets, utilisateur, prochain_id)

        elif choix == "2":
            admin_id = lire_entier("Votre ID admin : ")
            admin = find_admin_by_id(admins, admin_id)
            if admin is None:
                print("Cette personne n'existe pas.")
                continue
            print(f"\nBienvenue, {admin.name} !")
            menu_admin(tickets, users, admin)

        elif choix == "0":
            print("\nAu revoir !")
            break
        else:
            print("Choix invalide, veuillez réessayer.")


if __name__ == "__main__":
    main()