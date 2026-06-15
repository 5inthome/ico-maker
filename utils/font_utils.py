"""
font_utils.py
Énumération des polices TrueType/OpenType installées sur Windows,
y compris les polices Adobe Creative Cloud.
"""

import os
import sys
import winreg
from pathlib import Path
from functools import lru_cache


# Répertoires de polices standard Windows
_FONT_DIRS = [
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
]

# Clés de registre contenant les polices installées
_REGISTRY_KEYS = [
    # Polices système (HKLM)
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    # Polices utilisateur (HKCU) – inclut Adobe Fonts via Creative Cloud
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
]

_VALID_EXT = {".ttf", ".otf", ".ttc"}


def _clean_name(raw: str) -> str:
    """Supprime les suffixes courants du nom de registre (ex: ' (TrueType)')."""
    for suffix in (" (TrueType)", " (OpenType)", " (TrueType & OpenType)",
                   " (All Res)", " Bold", " Italic"):
        raw = raw.replace(suffix, "")
    return raw.strip()


def _resolve_path(value: str) -> Path | None:
    """Retourne le chemin absolu d'une police, ou None si introuvable."""
    p = Path(value)
    if p.is_absolute():
        return p if p.exists() else None
    # Chemin relatif → chercher dans les répertoires connus
    for d in _FONT_DIRS:
        candidate = d / value
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def get_font_map() -> dict[str, Path]:
    """
    Retourne un dict {nom_affichage: chemin_absolu} pour toutes les polices
    TTF/OTF trouvées dans le registre Windows.
    Fusionnes les clés HKLM et HKCU ; HKCU (Adobe CC) a priorité en cas de doublon.
    """
    fonts: dict[str, Path] = {}

    for hive, key_path in _REGISTRY_KEYS:
        try:
            key = winreg.OpenKey(hive, key_path)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    i += 1
                except OSError:
                    break
                path = _resolve_path(value)
                if path and path.suffix.lower() in _VALID_EXT:
                    clean = _clean_name(name)
                    fonts[clean] = path
        finally:
            winreg.CloseKey(key)

    return fonts


def get_font_names() -> list[str]:
    """Liste triée des noms de polices disponibles."""
    return sorted(get_font_map().keys(), key=str.casefold)


def get_font_path(name: str) -> Path | None:
    """Retourne le chemin d'une police par son nom d'affichage."""
    return get_font_map().get(name)


def find_font(family: str) -> Path | None:
    """
    Recherche souple : retourne le premier chemin dont le nom contient `family`
    (insensible à la casse).  Utile pour les familles multi-variantes.
    """
    family_lower = family.casefold()
    for name, path in get_font_map().items():
        if family_lower in name.casefold():
            return path
    return None


if __name__ == "__main__":
    names = get_font_names()
    print(f"{len(names)} polices trouvées :\n")
    for n in names:
        print(f"  {n:40s}  {get_font_path(n)}")
