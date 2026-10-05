"""Fichiers de depart deposes dans le dossier de televersement, pour pouvoir joindre des fichiers tout de suite."""
import os
import struct
import zlib

ICI = os.path.dirname(os.path.abspath(__file__))
TELEVERSEMENTS = os.environ.get("TICKETS_UPLOAD_DIR", os.path.join(ICI, "donnees", "televersements"))


def png(largeur, hauteur, rgb):
    """Petite image PNG valide, ecrite sans bibliotheque."""
    def bloc(nature, donnees):
        return struct.pack(">I", len(donnees)) + nature + donnees + struct.pack(">I", zlib.crc32(nature + donnees))
    lignes = b"".join(b"\x00" + bytes(rgb) * largeur for _ in range(hauteur))
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(lignes)) + bloc(b"IEND", b""))


def preparer_fichiers():
    """Fichiers deposes par les utilisateurs dans le dossier de televersement."""
    os.makedirs(TELEVERSEMENTS, exist_ok=True)
    fichiers = {
        "trace.txt": "Traceback (most recent call last):\n  File \"portail.py\", line 42\nKeyError: 'session'".encode("utf-8"),
        "capture.png": png(320, 180, (25, 25, 35)),
        "demo.mp4": b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64,  # en-tete MP4 : la video n'est jamais lue
        "virus.exe": b"MZ\x90\x00",
    }
    for nom, donnees in fichiers.items():
        with open(os.path.join(TELEVERSEMENTS, nom), "wb") as f:
            f.write(donnees)
    print(f"  Fichiers de depart crees dans {TELEVERSEMENTS}")
