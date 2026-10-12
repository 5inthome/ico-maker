"""
font_utils.py
Énumération des polices TrueType/OpenType installées.

- Windows : registre (HKLM + HKCU), complété par les polices Adobe Fonts
  activées via Creative Cloud (cache local, voir _scan_adobe_fonts).
- Linux : fontconfig (commande `fc-list`), qui connaît les polices du
  système et celles de l'utilisateur (~/.local/share/fonts) ; à défaut,
  parcours direct des dossiers de polices habituels.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from functools import lru_cache

from PIL import ImageFont

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    # winreg n'existe que sous Windows : l'importer sans condition fait
    # planter l'application au démarrage sur tout autre système.
    import winreg


# Répertoires de polices standard Windows
_FONT_DIRS = [
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
]

# Clés de registre contenant les polices installées (Windows uniquement)
_REGISTRY_KEYS = [
    # Polices système (HKLM)
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    # Polices utilisateur (HKCU) – inclut Adobe Fonts via Creative Cloud
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
] if IS_WINDOWS else []

# Dossiers de polices habituels sous Linux (utilisés seulement si
# fontconfig/fc-list n'est pas disponible).
_LINUX_FONT_DIRS = [
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path.home() / ".local" / "share" / "fonts",
    Path.home() / ".fonts",
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


def _display_name(family: str, style: str) -> str:
    """'DejaVu Sans' + 'Bold' -> 'DejaVu Sans Bold' ; le style Regular est omis."""
    if not style or style.lower() in ("regular", "normal", "book", "roman"):
        return family
    return f"{family} {style}"


def _scan_fontconfig() -> dict[str, Path] | None:
    """
    Linux : interroge fontconfig via `fc-list`. Renvoie None si la commande
    est absente ou échoue (on se rabat alors sur _scan_font_dirs).
    Pour chaque fichier, fontconfig fournit la famille et le style ; on
    garde le premier nom de chaque liste (fontconfig en donne parfois
    plusieurs, dans différentes langues).
    """
    if not shutil.which("fc-list"):
        return None
    try:
        out = subprocess.run(
            ["fc-list", "--format", "%{file}\t%{family[0]}\t%{style[0]}\n"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
    except Exception:
        return None
    fonts: dict[str, Path] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        file, family, style = parts
        path = Path(file)
        if path.suffix.lower() not in _VALID_EXT or not family:
            continue
        fonts.setdefault(_display_name(family, style), path)
    return fonts


def _scan_font_dirs() -> dict[str, Path]:
    """Linux, solution de secours : lit les noms directement dans les fichiers."""
    fonts: dict[str, Path] = {}
    for base in _LINUX_FONT_DIRS:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in _VALID_EXT or not path.is_file():
                continue
            try:
                family, style = ImageFont.truetype(str(path), size=10).getname()
            except Exception:
                continue
            if family:
                fonts.setdefault(_display_name(family, style), path)
    return fonts


def _windows_font_map() -> dict[str, Path]:
    """
    Windows : toutes les polices TTF/OTF du registre, fusionnées avec les
    polices Adobe Fonts détectées dans le cache Creative Cloud.
    Fusionne les clés HKLM et HKCU ; HKCU (Adobe CC classique) a priorité
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


@lru_cache(maxsize=1)
def get_font_map() -> dict[str, Path]:
    """
    Retourne un dict {nom_affichage: chemin_absolu} des polices disponibles
    sur le système courant (Windows ou Linux).
    """
    if IS_WINDOWS:
        return _windows_font_map()
    fonts = _scan_fontconfig()
    if fonts is None:
        fonts = _scan_font_dirs()
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
