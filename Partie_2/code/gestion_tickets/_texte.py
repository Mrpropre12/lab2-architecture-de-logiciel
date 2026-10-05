"""Regle commune pour le texte saisi par les utilisateurs (noms, titres, commentaires, motifs).

Module utilitaire sans dependance, partage par tous les paquets.
Refuse ce qui permettrait de falsifier l'affichage : caracteres de controle,
separateurs de ligne Unicode et controles de direction du texte. Les autres
caracteres (accents, emojis, trait d'union conditionnel ...) sont acceptes.
"""
import unicodedata

_BIDI = set("‪‫‬‭‮⁦⁧⁨⁩")


def normaliser(texte: str) -> str:
    """Fins de ligne Windows et Mac ramenees a \\n."""
    return texte.replace("\r\n", "\n").replace("\r", "\n")


def caractere_interdit(ch: str, multiligne: bool) -> bool:
    if multiligne and ch in "\n\t":
        return False
    return unicodedata.category(ch) in ("Cc", "Cs", "Zl", "Zp") or ch in _BIDI


def texte_valide(texte: object, maximum: int, multiligne: bool = False) -> bool:
    """Non vide apres nettoyage des espaces, au plus `maximum` caracteres, aucun caractere interdit."""
    if not isinstance(texte, str):
        return False
    texte = normaliser(texte)
    return (bool(texte.strip()) and len(texte.strip()) <= maximum
            and not any(caractere_interdit(ch, multiligne) for ch in texte))


def affichable(texte: str) -> str:
    """Remplace par ? tout caractere interdit (affichage defensif)."""
    return "".join("?" if caractere_interdit(ch, True) else ch for ch in normaliser(texte))
