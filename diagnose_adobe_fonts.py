"""
diagnose_adobe_fonts.py
Script de diagnostic autonome : explore le cache de polices Creative Cloud
et affiche tout ce qu'il trouve, pour comprendre pourquoi les polices
Adobe Fonts ne sont pas détectées par ico_maker.py.

Lancement :  python diagnose_adobe_fonts.py
"""

import os
from collections import Counter
from pathlib import Path

try:
    from PIL import ImageFont
except ImportError:
    ImageFont = None


def find_roots() -> list[Path]:
    roots = []
    for var in ("APPDATA", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            p = Path(base) / "Adobe" / "CoreSync" / "plugins" / "livetype"
            roots.append(p)
    return roots


def main():
    print("=" * 70)
    print("Diagnostic du cache de polices Adobe Creative Cloud")
    print("=" * 70)

    for root in find_roots():
        print(f"\n--- Racine : {root} ---")
        if not root.exists():
            print("  N'existe pas.")
            continue
        if not root.is_dir():
            print("  Existe mais n'est pas un dossier (!).")
            continue

        print("  Contenu direct :")
        for entry in sorted(root.iterdir()):
            kind = "dossier" if entry.is_dir() else "fichier"
            print(f"    [{kind}] {entry.name}")

        # Explore récursivement tout ce qu'il y a sous chaque sous-dossier
        # candidat (".r", "r", "c", etc.) pour voir où sont vraiment les
        # fichiers de polices et avec quelles extensions.
        for sub in sorted(root.iterdir()):
            if not sub.is_dir():
                continue
            print(f"\n  --- Exploration de {sub} ---")
            all_files = [p for p in sub.rglob("*") if p.is_file()]
            print(f"    Nombre total de fichiers trouvés : {len(all_files)}")

            ext_counts = Counter(p.suffix.lower() for p in all_files)
            print(f"    Extensions rencontrées : {dict(ext_counts)}")

            print("    Exemples (jusqu'à 10 fichiers) :")
            for p in all_files[:10]:
                size = p.stat().st_size
                print(f"      {p.relative_to(sub)}  ({size} octets)")

            # Tente de lire les 5 premiers fichiers avec Pillow, quelle
            # que soit leur extension, pour voir si certains sont en
            # fait des polices valides malgré une extension inattendue.
            if ImageFont is not None:
                print("    Tentative de lecture (Pillow/FreeType) des "
                      "5 premiers fichiers :")
                for p in all_files[:5]:
                    try:
                        font = ImageFont.truetype(str(p), size=10)
                        print(f"      OK  {p.name} -> {font.getname()}")
                    except Exception as e:
                        print(f"      ÉCHEC  {p.name} -> {e}")

    print("\nTerminé. Copie/colle tout ce qui précède dans la conversation.")


if __name__ == "__main__":
    main()
