"""
renderer.py
Moteur de rendu d'icônes avec Pillow.

Chaîne de rendu (ordre des couches) :
  1. Fond coloré découpé selon la forme choisie
  2. Formes géométriques additionnelles
  3. Texte

Toutes les opérations travaillent en RGBA 256×256, puis sont
redimensionnées à la demande pour l'export.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Types de données
# ---------------------------------------------------------------------------

BgShape   = Literal["square", "rounded", "circle", "none"]
ShapeType = Literal["circle", "square", "triangle", "star",
                    "hexagon", "rhombus", "pentagon"]

CANVAS = 256  # taille de travail interne


@dataclass
class BackgroundConfig:
    color: tuple[int, int, int, int] = (67, 97, 238, 255)  # RGBA
    shape: BgShape = "rounded"
    corner_radius: int = 48  # utilisé si shape == "rounded"


@dataclass
class TextConfig:
    text: str = "A"
    font_path: Path | None = None
    font_size: int = 140
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    bold: bool = False
    italic: bool = False
    offset_x: int = 0   # décalage en pixels par rapport au centre
    offset_y: int = 0


@dataclass
class ShapeConfig:
    kind: ShapeType = "circle"
    color: tuple[int, int, int, int] = (255, 255, 255, 180)
    size: int = 80          # rayon ou demi-côté, en pixels (sur 256)
    x: int = 200            # centre X
    y: int = 200            # centre Y


@dataclass
class IconConfig:
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    text: TextConfig = field(default_factory=TextConfig)
    shapes: list[ShapeConfig] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------

class IconRenderer:

    def render(self, cfg: IconConfig) -> Image.Image:
        """Retourne une image RGBA 256×256."""
        img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        self._draw_background(img, cfg.background)
        for s in cfg.shapes:
            self._draw_shape(img, s)
        if cfg.text.text.strip():
            self._draw_text(img, cfg.text)
        return img

    # ------------------------------------------------------------------
    # Fond
    # ------------------------------------------------------------------

    def _draw_background(self, img: Image.Image, bg: BackgroundConfig) -> None:
        if bg.shape == "none":
            return
        mask = Image.new("L", (CANVAS, CANVAS), 0)
        d = ImageDraw.Draw(mask)
        if bg.shape == "square":
            d.rectangle([0, 0, CANVAS - 1, CANVAS - 1], fill=255)
        elif bg.shape == "rounded":
            r = max(0, min(bg.corner_radius, CANVAS // 2))
            d.rounded_rectangle([0, 0, CANVAS - 1, CANVAS - 1], radius=r, fill=255)
        elif bg.shape == "circle":
            d.ellipse([0, 0, CANVAS - 1, CANVAS - 1], fill=255)

        color_img = Image.new("RGBA", (CANVAS, CANVAS), bg.color)
        img.paste(color_img, mask=mask)

    # ------------------------------------------------------------------
    # Formes additionnelles
    # ------------------------------------------------------------------

    def _draw_shape(self, img: Image.Image, s: ShapeConfig) -> None:
        overlay = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        x, y, r = s.x, s.y, s.size

        if s.kind == "circle":
            d.ellipse([x - r, y - r, x + r, y + r], fill=s.color)

        elif s.kind == "square":
            d.rectangle([x - r, y - r, x + r, y + r], fill=s.color)

        elif s.kind == "triangle":
            pts = [
                (x, y - r),
                (x - int(r * math.sqrt(3) / 2), y + r // 2),
                (x + int(r * math.sqrt(3) / 2), y + r // 2),
            ]
            d.polygon(pts, fill=s.color)

        elif s.kind == "rhombus":
            pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
            d.polygon(pts, fill=s.color)

        elif s.kind == "pentagon":
            pts = _regular_polygon(x, y, r, 5, -math.pi / 2)
            d.polygon(pts, fill=s.color)

        elif s.kind == "hexagon":
            pts = _regular_polygon(x, y, r, 6, 0)
            d.polygon(pts, fill=s.color)

        elif s.kind == "star":
            pts = _star_polygon(x, y, r, r // 2, 5)
            d.polygon(pts, fill=s.color)

        img.alpha_composite(overlay)

    # ------------------------------------------------------------------
    # Texte
    # ------------------------------------------------------------------

    def _draw_text(self, img: Image.Image, t: TextConfig) -> None:
        font = self._load_font(t)
        overlay = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        bbox = d.textbbox((0, 0), t.text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (CANVAS - tw) // 2 - bbox[0] + t.offset_x
        ty = (CANVAS - th) // 2 - bbox[1] + t.offset_y
        d.text((tx, ty), t.text, font=font, fill=t.color)
        img.alpha_composite(overlay)

    def _load_font(self, t: TextConfig) -> ImageFont.FreeTypeFont:
        if t.font_path and Path(t.font_path).exists():
            try:
                return ImageFont.truetype(str(t.font_path), t.font_size)
            except Exception:
                pass
        return ImageFont.load_default(size=t.font_size)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_ico(
        self,
        cfg: IconConfig,
        dest: Path,
        sizes: list[int] | None = None,
    ) -> None:
        """
        Génère un .ico multi-tailles.
        Par défaut : 16, 24, 32, 48, 64, 128, 256.
        """
        if sizes is None:
            sizes = [16, 24, 32, 48, 64, 128, 256]
        base = self.render(cfg)
        frames: list[Image.Image] = []
        for s in sorted(sizes):
            frame = base.resize((s, s), Image.LANCZOS)
            frames.append(frame)
        frames[0].save(
            dest,
            format="ICO",
            sizes=[(s, s) for s in sorted(sizes)],
            append_images=frames[1:],
        )

    def export_png(self, cfg: IconConfig, dest: Path, size: int = 512) -> None:
        """Exporte une image PNG à la taille demandée."""
        img = self.render(cfg)
        if size != CANVAS:
            img = img.resize((size, size), Image.LANCZOS)
        img.save(dest, format="PNG")

    @staticmethod
    def png_to_ico(
        src: Path,
        dest: Path,
        sizes: list[int] | None = None,
    ) -> None:
        """Convertit un PNG existant en ICO multi-tailles."""
        if sizes is None:
            sizes = [16, 24, 32, 48, 64, 128, 256]
        img = Image.open(src).convert("RGBA")
        frames = [img.resize((s, s), Image.LANCZOS) for s in sorted(sizes)]
        frames[0].save(
            dest,
            format="ICO",
            sizes=[(s, s) for s in sorted(sizes)],
            append_images=frames[1:],
        )


# ---------------------------------------------------------------------------
# Helpers géométriques
# ---------------------------------------------------------------------------

def _regular_polygon(
    cx: int, cy: int, r: int, n: int, start_angle: float
) -> list[tuple[int, int]]:
    pts = []
    for i in range(n):
        a = start_angle + 2 * math.pi * i / n
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    return pts


def _star_polygon(
    cx: int, cy: int, r_outer: int, r_inner: int, n: int
) -> list[tuple[int, int]]:
    pts = []
    for i in range(2 * n):
        r = r_outer if i % 2 == 0 else r_inner
        a = -math.pi / 2 + math.pi * i / n
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    return pts
