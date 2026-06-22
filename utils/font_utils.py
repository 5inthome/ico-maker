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

from PIL import ImageFont


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

# Répertoires où Creative Cloud met en cache les polices "Adobe Fonts"
# activées (ex: depuis l'app Creative Cloud Desktop, panneau Polices).
# Ces polices ne passent PAS par l'installeur Windows classique : elles
# sont chargées dynamiquement par le service "Adobe Desktop Service" et
# n'apparaissent donc jamais dans les clés de registre ci-dessus.
def _adobe_font_dirs() -> list[Path]:
    """
    Racine(s) du cache Creative Cloud à explorer. Les polices y sont
    réparties dans plusieurs sous-dossiers à noms courts ("r", "w", "e",
    "c", ...) dont la liste et le nommage varient selon la version de
    Creative Cloud et le nombre de polices activées (ce sont des "shards"
    internes, pas un schéma fixe) : on renvoie donc directement la racine
    "livetype" et on la parcourt entièrement, plutôt que de parier sur un
    nom de sous-dossier précis.
    """
    roots = []
    appdata = os.environ.get("APPDATA")
    localappdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        roots.append(Path(appdata) / "Adobe" / "CoreSync" / "plugins" / "livetype")
    if localappdata:
        roots.append(Path(localappdata) / "Adobe" / "CoreSync" / "plugins" / "livetype")
    return [d for d in roots if d.is_dir()]


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


def _scan_adobe_fonts() -> dict[str, Path]:
    """
    Détecte les polices Adobe Fonts activées via Creative Cloud en
    parcourant directement le cache local (elles n'ont pas d'entrée de
    registre). Les fichiers de ce cache n'ont ni nom ni extension
    significatifs (juste un hash, sans ".ttf"/".otf") : on ne peut donc
    pas filtrer par extension comme pour les polices classiques. On tente
    de charger chaque fichier comme police et on ignore silencieusement
    ceux qui n'en sont pas ; le nom affiché vient de la table 'name'
    interne du fichier, lue via Pillow/FreeType.
    """
    fonts: dict[str, Path] = {}
    for base in _adobe_font_dirs():
        try:
            paths = list(base.rglob("*"))
        except OSError:
            continue
        for path in paths:
            if not path.is_file():
                continue
            # On exclut juste les extensions clairement non concernées
            # (métadonnées/cache interne) pour éviter d'ouvrir des
            # milliers de petits fichiers inutiles ; tout le reste
            # (y compris les fichiers sans extension) est testé.
            if path.suffix.lower() in {".db", ".json", ".xml", ".lock",
                                       ".log", ".txt", ".ini"}:
                continue
            try:
                family, style = ImageFont.truetype(str(path), size=10).getname()
            except Exception:
                continue
            if not family:
                continue
            display = family if not style or style.lower() == "regular" else f"{family} {style}"
            fonts[f"{display}  (Adobe Fonts)"] = path
    return fonts


@lru_cache(maxsize=1)
def get_font_map() -> dict[str, Path]:
    """
    Retourne un dict {nom_affichage: chemin_absolu} pour toutes les polices
    TTF/OTF trouvées dans le registre Windows, fusionnées avec les polices
    Adobe Fonts détectées dans le cache Creative Cloud.
    Fusionnes les clés HKLM et HKCU ; HKCU (Adobe CC classique) a priorité
    en cas de doublon.
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

    # Polices Adobe Fonts (Creative Cloud) : absentes du registre, donc
    # ajoutées séparément depuis le cache local de l'app Creative Cloud.
    # La plupart des PC n'ont pas Creative Cloud installé : dans ce cas
    # _adobe_font_dirs() ne trouve aucun dossier et _scan_adobe_fonts()
    # renvoie simplement {} (aucune insistance, aucun blocage). Le
    # try/except ci-dessous est une sécurité supplémentaire : même une
    # erreur totalement imprévue pendant ce scan optionnel ne doit jamais
    # empêcher l'application de fonctionner avec les polices classiques.
    try:
        fonts.update(_scan_adobe_fonts())
    except Exception:
        pass

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
