# "Ico Maker" : Favicon Maker - Dessinateur d’Icons et Favicons 
***Choose a font, colors, sizes and frames... Make .ico et .png, and convert .png to .ico***

***Choisir police de caractère, couleurs, tailles et formes... produit les .ico et .png, et convertit .png en .ico***

> **English summary** — Ico Maker is a small Tkinter desktop app for Windows that creates favicons and multi-size `.ico` files from scratch (background + shape + text), or converts an existing PNG into a multi-size `.ico`. Everything runs locally with Pillow — no network calls, no online service. A ready-to-run Windows executable is available on the [Releases](../../releases) page (no Python install required); see [Téléchargement](#téléchargement--download) below. The rest of this README is in French; open an issue if an English version of any section would help.

Interface graphique Tkinter pour créer des favicons et fichiers `.ico` à partir de zéro (fond + texte + forme), ou pour convertir un PNG existant en `.ico` multi-tailles. Aucun service en ligne, aucune dépendance réseau : tout le rendu se fait localement avec Pillow.

## Aperçu

<img src="images/icon-app.png" width="96" alt="Icône de l'application Ico Maker">

Quelques exemples d'icônes réalisables avec l'application (fond + forme additionnelle + texte) :

<p>
  <img src="images/exemple-1.png" width="96" alt="Exemple : lettre simple sur fond arrondi, et cercle orange">
  <img src="images/exemple-2-forme-etoile.png" width="96" alt="Exemple : forme étoile en transparence">
  <img src="images/exemple-3-forme-hexagone.png" width="96" alt="Exemple : forme hexagone en transparence">
  <img src="images/exemple-4.png" width="96" alt="Exemple : Jeu de police et de couleurs">
</p>

## Téléchargement / Download

- **Sans Python (recommandé pour la plupart des utilisateurs)** : téléchargez `IcoMaker.exe` depuis la page [Releases](../../releases) du dépôt et lancez-le directement.
- **Depuis le code source** (pour modifier ou contribuer) : voir [Installation sur PC Windows](#installation-sur-pc-windows) ci-dessous.

## Présentation

L'application affiche un panneau de réglages à gauche (organisé en quatre onglets) et un aperçu en temps réel à droite. L'icône est composée de trois couches, dessinées dans cet ordre :

1. **Fond** — une forme pleine (carré, carré à coins arrondis, cercle, ou aucun fond) dans une couleur avec opacité réglable.
2. **Forme additionnelle** (optionnelle) — une figure géométrique (cercle, carré, triangle, losange, pentagone, hexagone, étoile) positionnable et redimensionnable, posée par-dessus le fond.
3. **Texte** — une lettre ou un mot, avec choix de police (parmi celles installées sur Windows, y compris les polices Adobe Fonts activées via Creative Cloud), taille, couleur, opacité et décalage.

Le rendu interne se fait sur un canevas carré de 256×256, puis est redimensionné à l'export selon les tailles choisies.

## Fonctions principales

- **Onglet Fond** : couleur (sélecteur ou code hex saisi directement), opacité, forme du fond, rayon des coins arrondis.
- **Onglet Texte** : contenu du texte, police (liste déroulante avec aperçu au survol façon Word/InDesign — survoler un nom de police met à jour l'aperçu sans valider le choix), taille, couleur, opacité, décalage horizontal/vertical.
- **Onglet Forme** : activation d'une forme additionnelle, type, couleur, opacité, taille et position.
- **Onglet Export** :
  - sélection des tailles à inclure dans le `.ico` (16, 24, 32, 48, 64, 128, 256 px, cochables individuellement) ;
  - **Exporter en .ico** : génère un fichier `.ico` multi-tailles à partir du rendu courant ;
  - **Exporter en .png** : génère une image PNG (512×512 par défaut) du rendu courant ;
  - **PNG → ICO** : convertit un PNG existant (par exemple un logo déjà prêt) en `.ico` multi-tailles, sans repasser par l'éditeur.
- **Couleurs** : chaque champ couleur accepte soit un clic sur la pastille (sélecteur Windows), soit la saisie directe d'un code hexadécimal (`#rrggbb` ou raccourci `#rgb`), validé et normalisé automatiquement à la touche Entrée ou à la perte de focus.
- **Polices Adobe Fonts** : les polices activées via l'application Creative Cloud Desktop sont détectées automatiquement (en plus des polices classiques du registre Windows) et apparaissent dans la liste déroulante avec le suffixe « (Adobe Fonts) ».

## Fichiers du projet

- `ico_maker.py` — point d'entrée, interface graphique complète.
- `utils/renderer.py` — moteur de rendu Pillow (fond, formes, texte) et fonctions d'export (`export_ico`, `export_png`, `png_to_ico`).
- `utils/font_utils.py` — détection des polices disponibles (registre Windows + cache Adobe Creative Cloud).
- `diagnose_adobe_fonts.py` — script de diagnostic autonome à lancer en cas de souci de détection des polices Adobe (affiche le contenu brut du cache Creative Cloud).
- `data/output/` — dossier proposé par défaut pour l'enregistrement des fichiers exportés.

## Installation sur PC Windows

### Prérequis

- **Python 3.10 ou plus récent**, installé avec l'option *Tcl/Tk and IDLE* cochée (cochée par défaut dans l'installeur officiel python.org — c'est elle qui fournit le module `tkinter` utilisé par l'interface). Sans cette option, l'application ne se lance pas (`ModuleNotFoundError: No module named 'tkinter'`).
- **Pillow**, à installer via pip :

  ```
  pip install Pillow
  ```

### Lancement

Depuis une invite de commande (cmd ou PowerShell), dans le dossier du projet :

```
python ico_maker.py
```

Lancer depuis une console plutôt qu'en double-cliquant sur le fichier permet de voir les éventuels messages d'erreur ou de diagnostic affichés dans le terminal (utile notamment pour le dépannage de la détection des polices ou de l'aperçu au survol).

### Points d'attention

- **Détection des polices** : les polices classiques sont lues depuis le registre Windows (`HKEY_LOCAL_MACHINE` et `HKEY_CURRENT_USER`). Les polices Adobe Fonts activées via Creative Cloud n'y figurent pas : elles sont détectées séparément en parcourant le cache local de l'application Creative Cloud Desktop (`%APPDATA%\Adobe\CoreSync\plugins\livetype` et son équivalent dans `%LOCALAPPDATA%`). Pour qu'une police Adobe apparaisse dans la liste, l'application Creative Cloud Desktop doit avoir déjà été lancée au moins une fois et la police doit être activée dans le panneau « Polices ». Si une police Adobe attendue n'apparaît pas, lancer `python diagnose_adobe_fonts.py` et examiner sa sortie.
- **Premier lancement lent** : la détection des polices (registre + cache Adobe) est mise en cache en mémoire pour la durée de la session (elle n'est donc faite qu'une fois par lancement), mais peut prendre quelques secondes la première fois si le cache Creative Cloud contient beaucoup de polices activées.
- **Dossier d'enregistrement par défaut** : les boîtes de dialogue d'export proposent par défaut `data/output/` à côté du script ; ce dossier doit exister (il est déjà présent dans le projet) et doit rester accessible en écriture.
- **Export .ico et tailles multiples** : Pillow génère lui-même les variantes de taille à partir de l'image de rendu en pleine résolution (256×256) — il ne faut donc jamais modifier le code pour appeler la sauvegarde sur une image déjà réduite, sous peine de ne conserver que les plus petites tailles cochées (icône floue entourée d'une bordure blanche).
- **Caractères accentués / emojis dans l'interface** : les onglets utilisent des emojis (🎨 🔤 ⬡ 💾) à titre décoratif ; si la police système par défaut de Windows ne les affiche pas correctement, cela n'affecte pas le fonctionnement de l'application.
- **Aperçu au survol des polices** : cette fonctionnalité s'appuie sur des mécanismes internes de Tcl/Tk (non documentés officiellement par Tkinter) pour accéder à la liste déroulante ouverte. Le code est conçu pour échouer silencieusement si la structure interne diffère selon la version de Tk installée — dans ce cas, la sélection au clic continue de fonctionner normalement, seul l'aperçu au survol est indisponible.

## Licence

Distribué sous licence MIT — voir le fichier [LICENSE](LICENSE). Utilisation, modification et redistribution libres, y compris à titre commercial, à condition de conserver la mention de copyright.
