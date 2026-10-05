# Gestionnaire de tickets : laboratoire 2 (6GEI311)

Implémentation Python du diagramme de classes de la partie 2.

## Lancer

Depuis ce dossier, avec Python 3.8 ou plus :

```
pip install -r requirements.txt
python main.py
```

`requirements.txt` installe fpdf2, qui sert à l'export PDF. Sans fpdf2, tout fonctionne sauf la production du fichier PDF.

## Utilisation

Au démarrage, cinq comptes et deux tickets existent déjà :
- #1 Alice, administratrice (elle a aussi les rôles Développeur et Rapporteur) ;
- #2 Remi et #3 Rita, rapporteurs ;
- #4 Diane et #5 Damien, développeurs.

On peut aussi créer un compte : l'inscription donne le rôle Rapporteur. Se connecter consiste à choisir un compte, car l'authentification est hors du périmètre du diagramme.

Le menu ne montre que les actions permises par les rôles du compte connecté. Un rapporteur ne voit donc ni « Assigner » ni « Valider ». La touche `T` affiche aussi les autres actions, marquées d'un `*`, pour voir le système les refuser.

Le système vérifie toujours chaque action, quel que soit le menu. Il contrôle le droit du rôle, puis l'état du ticket, puis la règle propre à la personne (auteur, assigné, qui peut voir le ticket). Le résultat s'affiche sur l'écran de l'action : `OK`, ou `REFUSE` suivi du motif donné par le système. On appuie ensuite sur Entrée pour revenir au menu.

Pour joindre vos propres fichiers, déposez-les dans `donnees/televersements`, qui est créé au premier lancement. Les PDF sont écrits dans `donnees/exports`.

## Organisation du code

Il y a un paquet Python par paquetage du diagramme. Les dépendances vont dans un seul sens : `consultation`, puis `ticket`, puis `acteurs`.

| Fichier ou paquet | Contenu | Patron |
|---|---|---|
| `gestion_tickets/acteurs` | Permission, Role, BaseRole, ReporterRole, DeveloperRole, AdminRole, User, UserRegistry | RBAC par composition |
| `gestion_tickets/ticket` | Ticket, Comment, Priority, TicketRegistry, TicketState et ses 5 états, Status | État (State) |
| `gestion_tickets/ticket` | Content, TextFileContent, ImageFileContent, VideoFileContent, ContentFactory, PathGuard | Fabrique |
| `gestion_tickets/ticket` | TicketVisitor, ViewVisitor, ExportVisitor (le contrat) | Visiteur |
| `gestion_tickets/consultation` | ScreenRenderVisitor (écran), PDFExportVisitor (PDF) | Visiteur |
| `gestion_tickets/_texte.py` | Règle commune pour le texte saisi | |
| `main.py`, `console.py` | Interface en mode console (aucune règle métier) | |
| `donnees_demo.py` | Fichiers de départ (texte, image, vidéo, exécutable refusé) | |

Le registre des comptes est injecté dans le registre des tickets : `TicketRegistry(users)`. Tout acteur qui n'est pas un compte de ce registre est refusé.

## Du diagramme au code

| UML | Python |
|---|---|
| `+ nom`, `~ nom` ou `# nom`, `- nom` | `nom`, `_nom`, `__nom` |
| `camelCase` | `snake_case` (PEP 8) |
| `<<create>>`, `equals`, `hash` | `__init__`, `__eq__`, `__hash__` |
| accesseur implicite de la légende | propriété en lecture seule |
| `[0..1]` | `None` possible |

Une action refusée renvoie `False`, `None` ou une liste vide, sans effet de bord. Son motif est écrit dans le journal (`logging`), et la console l'affiche.
