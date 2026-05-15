"""
Shared helpers for track identity matching across data sources.
"""
import re
from typing import Tuple


def normalize_key_component(value: str) -> str:
    if not value:
        return ""
    normalized = value.casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_song_key(title: str, artist: str) -> Tuple[str, str]:
    return (
        normalize_key_component(title),
        normalize_key_component(artist),
    )
