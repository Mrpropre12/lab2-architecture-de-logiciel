"""Gestionnaire de tickets (laboratoire 2, 6GEI311) : point d'entree interactif.

main() lance la console : au depart, cinq comptes et deux tickets existent ;
l'utilisateur se connecte avec un compte et teste lui-meme ce qu'il veut.
Chaque action s'affiche sur son propre ecran avec son resultat (OK, ou
REFUSE avec le motif donne par le systeme).

Le menu ne montre que les actions permises par les roles du compte connecte ;
le modele verifie quand meme chaque action et donne le motif de tout refus.

Lancement, depuis le dossier code :  python main.py
"""
import sys

from console import Console


def main():
    Console().lancer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
