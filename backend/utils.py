"""Shared utility functions."""

import re
import unicodedata


def normalize_product_name(name: str) -> str:
    """Normalize a product name for matching.

    NFD decompose, strip combining diacritics, lowercase, collapse whitespace.
    """
    if not name:
        return ""
    # NFD decompose and strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase and collapse whitespace
    lower = stripped.lower().strip()
    return re.sub(r"\s+", " ", lower)
