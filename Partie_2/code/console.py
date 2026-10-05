"""Mode interactif : l'utilisateur se connecte avec un compte et teste lui-meme le systeme.

Le menu ne montre que les actions permises par les roles du compte (la console
le demande au modele avec can_globally) ; la touche T affiche aussi les autres,
pour voir le modele refuser. Les regles liees au contexte (etat du ticket,
auteur, assigne) restent verifiees par le modele, qui donne le motif du refus.

Cette console ne contient AUCUNE regle metier : elle lit des entrees, appelle
l'API publique du paquet gestion_tickets et affiche le resultat. Quand le
systeme refuse une action, elle affiche le motif qu'il a ecrit dans son
journal. Elle joue aussi le role de la couche d'authentification (hors
perimetre du diagramme) : se connecter consiste a choisir un compte connu.
"""
import logging
import os
import sys

from donnees_demo import TELEVERSEMENTS, preparer_fichiers
from gestion_tickets.acteurs import AdminRole, DeveloperRole, Permission, ReporterRole, UserRegistry
from gestion_tickets.consultation import PDFExportVisitor, ScreenRenderVisitor
from gestion_tickets.ticket import ContentFactory, Priority, Status, TicketRegistry

ROLES = {"R": ReporterRole, "D": DeveloperRole, "A": AdminRole}
_VERT, _ROUGE, _CYAN, _GRIS, _GRAS, _FIN = "\033[32m", "\033[31m", "\033[36m", "\033[90m", "\033[1m", "\033[0m"


class _Motifs(logging.Handler):
    """Recueille les motifs de refus ecrits par le systeme pendant une action."""

    def __init__(self):
        super().__init__(logging.INFO)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class Console:
    """Chaque action s'affiche sur son propre ecran : on lit le resultat, puis Entree ramene au menu."""

    def __init__(self, ecran_interactif=None):
        """ecran_interactif : True force le mode terminal complet, False le texte brut, None decide seul.

        Par defaut, une pause suit chaque action (meme dans IDLE ou la console d'un IDE). L'effacement et
        les couleurs ne sont utilises que dans un vrai terminal. TICKETS_CONSOLE_BRUTE=1 donne le texte
        brut, sans pause, pour piloter la console par un script.
        """
        terminal = sys.stdout.isatty() and "idlelib" not in sys.modules
        if ecran_interactif is None:
            self.interactif = os.environ.get("TICKETS_CONSOLE_BRUTE") != "1"
            self.effacement = self.interactif and terminal
        else:
            self.interactif = self.effacement = ecran_interactif
        self.couleurs = self.effacement and "NO_COLOR" not in os.environ
        if self.couleurs and os.name == "nt":
            os.system("")  # active les sequences de couleur ANSI de la console Windows
        self.avis = ""     # message court affiche sous le menu (choix invalide, etc.)
        self.dernier = ""  # rappel du dernier resultat, affiche sous le menu
        self.tout_afficher = False  # le menu ne montre que les actions permises par les roles
        self.motifs = _Motifs()
        journal = logging.getLogger("gestion_tickets")
        journal.handlers[:] = [self.motifs]
        journal.setLevel(logging.INFO)
        journal.propagate = False
        self.users = self.tickets = self.acteur = None
        self.comptes = {}  # couche d'authentification simulee : comptes connus de la console

    # ================================================================ entrees et sorties
    @staticmethod
    def lire(message, obligatoire=True):
        """Une ligne saisie, ou None si l'utilisateur abandonne (Ctrl+C, Ctrl+D, fin d'entree)."""
        while True:
            try:
                valeur = input(message).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            if valeur or not obligatoire:
                return valeur
            print("  -> Une valeur est obligatoire.")

    def lire_entier(self, message):
        while True:
            valeur = self.lire(message)
            if valeur is None:
                return None
            try:
                return int(valeur)
            except ValueError:
                print("  -> Entrez un nombre entier.")

    def lire_choix(self, message, choix):
        """Valeur parmi un dictionnaire de choix (cles insensibles a la casse)."""
        while True:
            valeur = self.lire(f"{message} [{'/'.join(choix)}] : ")
            if valeur is None:
                return None
            if valeur.upper() in choix:
                return choix[valeur.upper()]
            print("  -> Choix inconnu.")

    # ================================================================ ecran
    def couleur(self, texte, code):
        return f"{code}{texte}{_FIN}" if self.couleurs else texte

    def effacer(self):
        if self.effacement:
            os.system("cls" if os.name == "nt" else "clear")
        elif self.interactif:
            print("\n" * 2)  # IDLE ou console d'IDE : pas d'effacement possible, on aere

    def pause(self):
        """Laisse lire le resultat ; Entree ramene au menu."""
        print("\n" + "-" * 64)
        if self.interactif:
            self.lire(self.couleur("Appuyez sur Entree pour revenir au menu...", _GRIS), obligatoire=False)

    def titre(self, texte, sous_titre=""):
        print("=" * 64)
        print(self.couleur(f" {texte}", _GRAS + _CYAN))
        if sous_titre:
            print(self.couleur(f" {sous_titre}", _GRIS))
        print("=" * 64)

    def ecran_action(self, libelle, action):
        """Un ecran par action : titre, saisies, resultat, puis pause."""
        self.effacer()
        connecte = f"connecte : {self.decrire(self.acteur)}" if self.acteur else ""
        self.titre(libelle, connecte)
        self.motifs.messages.clear()
        action()
        self.pause()

    def afficher_avis(self):
        if self.dernier:
            print(self.couleur(f"\n  Derniere action : {self.dernier}", _GRIS))
        if self.avis:
            print(self.couleur(f"  -> {self.avis}", _ROUGE))
            self.avis = ""

    @staticmethod
    def _sans_prefixe(motif):
        return motif[len("refus : "):] if motif.startswith("refus : ") else motif

    def executer(self, appel, succes):
        """Appelle le systeme et affiche OK, ou REFUSE suivi des motifs du systeme."""
        self.motifs.messages.clear()
        resultat = appel()
        print()
        if resultat not in (False, None):
            message = succes(resultat) if callable(succes) else succes
            print(self.couleur("  OK", _VERT + _GRAS) + f" : {message}")
            self.dernier = f"OK : {message}"
        else:
            motifs = [self._sans_prefixe(m) for m in self.motifs.messages] or ["(aucun motif)"]
            print(self.couleur("  REFUSE", _ROUGE + _GRAS))
            for motif in motifs:
                print(f"     motif : {motif}")
            self.dernier = f"REFUSE : {motifs[-1]}"
        return resultat

    def refus(self, titre="REFUSE"):
        print(self.couleur(f"  {titre}", _ROUGE + _GRAS))
        self.motifs_eventuels()
        motifs = [self._sans_prefixe(m) for m in self.motifs.messages]
        self.dernier = f"{titre} : {motifs[-1]}" if motifs else titre

    def motifs_eventuels(self):
        for motif in self.motifs.messages:
            print(f"     motif : {self._sans_prefixe(motif)}")

    @staticmethod
    def decrire(u):
        roles = ", ".join(sorted(r.name() for r in u.get_roles()))
        etat = "" if u.active else "  (desactive)"
        return f"#{u.user_id:<3} {u.name:<16} {roles}{etat}"

    @staticmethod
    def ligne_ticket(t):
        assigne = t.get_assignee().name if t.get_assignee() else "aucun"
        archive = "  archive" if t.is_archived() else ""
        return (f"#{t.ticket_id:<3} [{t.get_status().value:<10}] {t.priority.value:<7} "
                f"{t.title}  (auteur {t.get_author().name}, assigne {assigne}){archive}")

    def lister(self, tickets):
        self.motifs_eventuels()
        if not tickets:
            print("  (aucun ticket)")
        for t in tickets:
            print("  " + self.ligne_ticket(t))

    # ================================================================ donnees de depart
    def peupler(self):
        """Comptes et tickets de depart, pour pouvoir tester tout de suite."""
        preparer_fichiers()
        self.users = UserRegistry("Alice", "alice@uqac.ca")
        self.tickets = TicketRegistry(self.users)
        remi = self.users.register("Remi", "remi@uqac.ca")
        alice = self.users.find_by_id(remi, 1)  # la couche d'authentification connait ses comptes
        rita = self.users.register("Rita", "rita@uqac.ca")
        diane = self.users.register("Diane", "diane@uqac.ca")
        damien = self.users.register("Damien", "damien@uqac.ca")
        for dev in (diane, damien):
            self.users.grant_role(alice, dev, DeveloperRole())
        self.comptes = {u.user_id: u for u in (alice, remi, rita, diane, damien)}
        t1 = self.tickets.create(remi, "Ecran noir au demarrage du portail", Priority.HAUTE)
        t1.add_content(remi, ContentFactory.from_path("trace.txt"))
        t1.add_content(remi, ContentFactory.from_path("capture.png"))
        t1.add_comment(remi, "Arrive a chaque redemarrage.")
        t1.assign(diane, damien)
        self.tickets.create(rita, "Faute dans le menu Aide", Priority.BASSE)

    # ================================================================ boucle principale
    def lancer(self):
        self.peupler()
        while True:
            self.effacer()
            self.titre("GESTION DE TICKETS 6GEI311", "mode interactif : vous testez vous-meme le systeme")
            print("   1. Se connecter\n   2. Creer un compte (inscription libre, role Rapporteur)\n"
                  "   3. Comptes connus\n   0. Quitter")
            self.afficher_avis()
            choix = self.lire("\nVotre choix : ", obligatoire=False)
            if choix is None or choix == "0":
                print("Au revoir.")
                return
            if choix == "1":
                self.connexion()
            elif choix == "2":
                self.ecran_action("Creer un compte", self.inscription)
            elif choix == "3":
                self.ecran_action("Comptes connus", self.comptes_connus)
            else:
                self.avis = f"Choix invalide : {choix}"

    def comptes_connus(self):
        for u in self.comptes.values():
            print("  " + self.decrire(u))

    def inscription(self):
        nom = self.lire("Nom : ")
        email = None if nom is None else self.lire("Email : ")
        if email is None:
            return
        u = self.executer(lambda: self.users.register(nom, email), lambda u: f"compte {self.decrire(u)}")
        if u:
            self.comptes[u.user_id] = u

    def connexion(self):
        self.effacer()
        self.titre("Se connecter", "authentification simulee : choisissez un compte")
        self.comptes_connus()
        ident = self.lire_entier("\nVotre ID : ")
        if ident is None:
            return
        if ident not in self.comptes:
            self.avis = f"Compte inconnu : {ident}"
            return
        self.acteur = self.comptes[ident]
        if not self.acteur.active:
            self.avis = "Compte desactive : le systeme refusera vos actions."
        self.dernier = ""
        self.tout_afficher = False
        self.menu()
        self.acteur = None
        self.dernier = ""

    # ================================================================ menu de l'acteur connecte
    def actions(self):
        """(libelle, action, permission exigee). Numeros stables : l'action 13 est toujours Valider."""
        P = Permission
        return [
            ("Tickets", None, None),
            ("Mes tickets", self.mes_tickets, P.VIEW),
            ("Tous les tickets actifs", lambda: self.lister(self.tickets.find_all(self.acteur)), P.VIEW_ALL),
            ("Rechercher (statut, priorite)", self.rechercher, P.VIEW),
            ("Voir les archives", lambda: self.lister(self.tickets.find_archived(self.acteur)), P.VIEW),
            ("Creer un ticket", self.creer, P.CREATE),
            ("Consulter un ticket", self.consulter, P.VIEW),
            ("Exporter un ticket en PDF", self.exporter, P.EXPORT),
            ("Description", None, None),
            ("Modifier le titre", self.modifier_titre, P.EDIT),
            ("Joindre un fichier televerse", self.joindre, P.ATTACH),
            ("Commenter", self.commenter, P.COMMENT),
            ("Cycle de vie", None, None),
            ("Assigner", self.assigner, P.ASSIGN),
            ("Soumettre a validation", lambda: self.transition("submit"), P.SUBMIT),
            ("Valider", lambda: self.transition("validate"), P.VALIDATE),
            ("Rejeter (avec motif)", lambda: self.transition("reject", motif=True), P.REJECT),
            ("Fermer (avec motif)", lambda: self.transition("close", motif=True), P.CLOSE),
            ("Rouvrir (avec motif)", lambda: self.transition("reopen", motif=True), P.REOPEN),
            ("Changer la priorite", self.priorite, P.SET_PRIORITY),
            ("Archiver", self.archiver, P.ARCHIVE),
            ("Comptes", None, None),
            ("Mon profil et permissions", self.profil, None),
            ("Lister les comptes", self.lister_comptes, P.MANAGE_USERS),
            ("Attribuer un role", lambda: self.role(attribuer=True), P.MANAGE_USERS),
            ("Retirer un role", lambda: self.role(attribuer=False), P.MANAGE_USERS),
            ("Desactiver un compte", lambda: self.activation(False), P.MANAGE_USERS),
            ("Reactiver un compte", lambda: self.activation(True), P.MANAGE_USERS),
        ]

    def permis(self, permission):
        """La console ne decide rien : elle demande au modele ce que les roles de l'acteur permettent."""
        return permission is None or self.acteur.can_globally(permission)

    def menu(self):
        """Le menu ne montre que les actions permises par les roles (T affiche aussi les autres)."""
        while True:
            self.effacer()
            self.titre(f"Connecte : {self.acteur.name}",
                       ", ".join(sorted(r.name() for r in self.acteur.get_roles()))
                       + ("" if self.acteur.active else "  (compte desactive)"))
            numeros, masques, n, section, titre_section = {}, set(), 0, [], None
            for libelle, action, permission in self.actions() + [("", None, None)]:
                if action is None:  # titre de section : on affiche la section precedente sur 2 colonnes
                    if section:
                        print(self.couleur(f" {titre_section}", _GRAS))
                        for i in range(0, len(section), 2):
                            print("  " + "".join(f"{case:<40}" for case in section[i:i + 2]).rstrip())
                    titre_section, section = libelle, []
                    continue
                n += 1
                if self.permis(permission):
                    numeros[str(n)] = (libelle, action)
                    section.append(f"{n:>2}. {libelle}")
                elif self.tout_afficher:
                    numeros[str(n)] = (libelle, action)
                    section.append(f"{n:>2}. {libelle} *")
                else:
                    masques.add(str(n))
            print("   0. Se deconnecter")
            bascule = "masquer les actions hors de vos roles" if self.tout_afficher else \
                "afficher aussi les actions hors de vos roles (pour voir le systeme refuser)"
            print(self.couleur(f"   T. {bascule}", _GRIS))
            if self.tout_afficher:
                print(self.couleur("   * hors de vos roles : le systeme refusera", _GRIS))
            self.afficher_avis()
            choix = self.lire("\nVotre choix : ", obligatoire=False)
            if choix is None or choix == "0":
                return
            if choix.upper() == "T":
                self.tout_afficher = not self.tout_afficher
                continue
            if choix in masques:
                self.avis = f"Action {choix} non disponible pour vos roles (T pour l'afficher quand meme)."
                continue
            if choix not in numeros:
                self.avis = f"Choix invalide : {choix}"
                continue
            self.ecran_action(*numeros[choix])

    # ================================================================ outils de selection
    def choisir_ticket(self):
        """Le ticket est cherche par le systeme : un ticket invisible pour l'acteur est refuse."""
        ident = self.lire_entier("ID du ticket : ")
        if ident is None:
            return None
        self.motifs.messages.clear()
        t = self.tickets.find_by_id(self.acteur, ident)
        if t is None:
            self.refus()
        return t

    def choisir_compte(self, message="ID du compte : "):
        ident = self.lire_entier(message)
        if ident is None:
            return None
        self.motifs.messages.clear()
        u = self.users.find_by_id(self.acteur, ident)
        if u is None:
            self.refus()
        return u

    # ================================================================ actions sur les tickets
    def mes_tickets(self):
        vus = []
        for t in self.tickets.find_by_author(self.acteur, self.acteur) + \
                self.tickets.find_by_assignee(self.acteur, self.acteur):
            if t not in vus:
                vus.append(t)
        self.lister(vus)

    def rechercher(self):
        critere = self.lire_choix("Critere", {"S": "statut", "P": "priorite"})
        if critere == "statut":
            s = self.lire_choix("Statut", {v.value: v for v in Status})
            if s is not None:
                self.lister(self.tickets.find_by_status(self.acteur, s))
        elif critere == "priorite":
            p = self.lire_choix("Priorite", {v.value: v for v in Priority})
            if p is not None:
                self.lister(self.tickets.find_by_priority(self.acteur, p))

    def creer(self):
        titre = self.lire("Titre : ")
        p = None if titre is None else self.lire_choix("Priorite", {v.value: v for v in Priority})
        if p is not None:
            self.executer(lambda: self.tickets.create(self.acteur, titre, p),
                          lambda t: f"ticket cree : {self.ligne_ticket(t)}")

    def consulter(self):
        t = self.choisir_ticket()
        if t is None:
            return
        ecran = ScreenRenderVisitor()
        if self.executer(lambda: t.consult(self.acteur, ecran), "consultation"):
            print("\n" + ecran.result())

    def exporter(self):
        t = self.choisir_ticket()
        if t is None:
            return
        pdf = PDFExportVisitor()
        if self.executer(lambda: t.export(self.acteur, pdf), "parcours du ticket termine"):
            fichier = pdf.result()
            print(f"  PDF : {fichier}" if fichier else "  (aucun fichier : installez fpdf2)")

    def modifier_titre(self):
        t = self.choisir_ticket()
        titre = None if t is None else self.lire("Nouveau titre : ")
        if titre is not None:
            self.executer(lambda: t.edit(self.acteur, titre), "titre modifie")

    def joindre(self):
        t = self.choisir_ticket()
        if t is None:
            return
        print(f"  Dossier de televersement : {TELEVERSEMENTS}")
        print("  Fichiers presents : " + ", ".join(sorted(os.listdir(TELEVERSEMENTS))))
        nom = self.lire("Nom du fichier (ou chemin) : ")
        if nom is None:
            return
        self.motifs.messages.clear()
        contenu = ContentFactory.from_path(nom)
        if contenu is None:
            self.refus("REFUSE par la fabrique")
            return
        print(f"  La fabrique a cree un {type(contenu).__name__}")
        self.executer(lambda: t.add_content(self.acteur, contenu), "fichier joint")

    def commenter(self):
        t = self.choisir_ticket()
        texte = None if t is None else self.lire("Commentaire : ")
        if texte is not None:
            self.executer(lambda: t.add_comment(self.acteur, texte), lambda c: f"commentaire #{c.comment_id} ajoute")

    def assigner(self):
        t = self.choisir_ticket()
        if t is None:
            return
        ident = self.lire_entier("ID du developpeur a assigner : ")
        if ident is None:
            return
        assigne = self.comptes.get(ident)  # le systeme verifiera lui-meme qu'il peut etre assigne
        self.executer(lambda: t.assign(self.acteur, assigne),
                      lambda _: f"ticket #{t.ticket_id} assigne a {assigne.name} [{t.get_status().value}]")

    def transition(self, nom, motif=False):
        t = self.choisir_ticket()
        if t is None:
            return
        raison = self.lire("Motif : ", obligatoire=False) if motif else None
        if motif and raison is None:
            return
        operation = getattr(t, nom)
        appel = (lambda: operation(self.acteur, raison)) if motif else (lambda: operation(self.acteur))
        self.executer(appel, lambda _: f"ticket #{t.ticket_id} maintenant {t.get_status().value}")

    def priorite(self):
        t = self.choisir_ticket()
        p = None if t is None else self.lire_choix("Nouvelle priorite", {v.value: v for v in Priority})
        if p is not None:
            self.executer(lambda: t.set_priority(self.acteur, p), f"priorite {p.value}")

    def archiver(self):
        ident = self.lire_entier("ID du ticket a archiver : ")
        if ident is not None:
            self.executer(lambda: self.tickets.archive(self.acteur, ident), f"ticket #{ident} archive (definitif)")

    # ================================================================ actions sur les comptes
    def profil(self):
        u = self.acteur
        print("  " + self.decrire(u))
        permises = sorted(p.value for r in u.get_roles() for p in r.permissions())
        print("  Permissions accordees par les roles : " + ", ".join(permises))
        if not u.active:
            print("  Compte desactive : aucune permission n'est utilisable.")

    def lister_comptes(self):
        comptes = self.executer(lambda: self.users.find_all(self.acteur) or None, "comptes du registre :")
        for u in comptes or []:
            print("  " + self.decrire(u))

    def role(self, attribuer):
        cible = self.choisir_compte()
        if cible is None:
            return
        classe = self.lire_choix("Role (Rapporteur, Developpeur, Administrateur)", ROLES)
        if classe is None:
            return
        operation = self.users.grant_role if attribuer else self.users.revoke_role
        self.executer(lambda: operation(self.acteur, cible, classe()), lambda _: self.decrire(cible))

    def activation(self, activer):
        cible = self.choisir_compte()
        if cible is None:
            return
        operation = self.users.reactivate if activer else self.users.deactivate
        self.executer(lambda: operation(self.acteur, cible), lambda _: self.decrire(cible))
