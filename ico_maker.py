"""
ico_maker.py
Interface graphique Tkinter pour créer des favicons et fichiers .ico.

Lancement :  python ico_maker.py
Dépendances : Pillow  (pip install Pillow)
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk

# Ajout du dossier parent au path pour les imports relatifs
sys.path.insert(0, str(Path(__file__).parent))

from utils.renderer import (
    BackgroundConfig, IconConfig, IconRenderer, ShapeConfig, TextConfig,
)
from utils.font_utils import get_font_names, get_font_path

# ---------------------------------------------------------------------------
# Constantes UI
# ---------------------------------------------------------------------------

PREVIEW_SIZE  = 256
PAD           = 8
BG_PANEL      = "#1e1e2e"
BG_SECTION    = "#2a2a3e"
FG_LABEL      = "#cdd6f4"
FG_ACCENT     = "#89b4fa"
BTN_EXPORT    = "#a6e3a1"
BTN_CONVERT   = "#f9e2af"

SHAPE_TYPES   = ["circle", "square", "triangle", "rhombus", "pentagon",
                 "hexagon", "star"]
BG_SHAPES     = ["rounded", "square", "circle", "none"]
ICO_SIZES     = [16, 24, 32, 48, 64, 128, 256]


# ---------------------------------------------------------------------------
# Helpers UI
# ---------------------------------------------------------------------------

def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)


def _rgba_to_hex(rgba: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(rgba[0], rgba[1], rgba[2])


def _color_button(parent, color_var: tk.StringVar, alpha_var: tk.IntVar | None,
                  command) -> tk.Frame:
    """Petit bouton carré affichant la couleur courante + swatch."""
    frame = tk.Frame(parent, bg=BG_PANEL)
    btn = tk.Button(frame, width=3, relief="flat", cursor="hand2",
                    command=command)
    btn.pack(side="left", padx=2)

    def refresh(*_):
        try:
            btn.config(bg=color_var.get())
        except Exception:
            pass
    color_var.trace_add("write", refresh)
    refresh()
    return frame


# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------

class IcoMakerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Ico Maker")
        self.resizable(False, False)
        self.configure(bg=BG_PANEL)

        self.renderer = IconRenderer()
        self._preview_image: Image.Image | None = None
        self._tk_image: ImageTk.PhotoImage | None = None

        # ── Variables ──────────────────────────────────────────────────
        # Fond
        self.bg_color    = tk.StringVar(value="#4361ee")
        self.bg_alpha    = tk.IntVar(value=255)
        self.bg_shape    = tk.StringVar(value="rounded")
        self.bg_radius   = tk.IntVar(value=48)

        # Texte
        self.text_str    = tk.StringVar(value="A")
        self.text_color  = tk.StringVar(value="#ffffff")
        self.text_alpha  = tk.IntVar(value=255)
        self.text_size   = tk.IntVar(value=140)
        self.text_font   = tk.StringVar(value="")
        self.text_off_x  = tk.IntVar(value=0)
        self.text_off_y  = tk.IntVar(value=0)

        # Forme additionelle
        self.shape_enabled = tk.BooleanVar(value=False)
        self.shape_kind    = tk.StringVar(value="circle")
        self.shape_color   = tk.StringVar(value="#ffffff")
        self.shape_alpha   = tk.IntVar(value=180)
        self.shape_size    = tk.IntVar(value=80)
        self.shape_x       = tk.IntVar(value=200)
        self.shape_y       = tk.IntVar(value=200)

        # Tailles ICO export
        self.ico_sizes: dict[int, tk.BooleanVar] = {
            s: tk.BooleanVar(value=True) for s in ICO_SIZES
        }

        self._build_ui()
        self._refresh_fonts()
        self._schedule_preview()

    # ------------------------------------------------------------------
    # Construction UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Colonne gauche : contrôles
        left = tk.Frame(self, bg=BG_PANEL, padx=PAD, pady=PAD)
        left.grid(row=0, column=0, sticky="nsew")

        notebook = ttk.Notebook(left)
        notebook.pack(fill="both", expand=True)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",        background=BG_PANEL)
        style.configure("TNotebook.Tab",    background=BG_SECTION,
                        foreground=FG_LABEL, padding=[10, 4])
        style.map("TNotebook.Tab",          background=[("selected", BG_PANEL)])

        tab_bg   = self._make_tab(notebook, "🎨 Fond")
        tab_text = self._make_tab(notebook, "🔤 Texte")
        tab_shp  = self._make_tab(notebook, "⬡ Forme")
        tab_exp  = self._make_tab(notebook, "💾 Export")

        self._build_bg_tab(tab_bg)
        self._build_text_tab(tab_text)
        self._build_shape_tab(tab_shp)
        self._build_export_tab(tab_exp)

        # Colonne droite : aperçu
        right = tk.Frame(self, bg=BG_PANEL, padx=PAD, pady=PAD)
        right.grid(row=0, column=1, sticky="nsew")

        tk.Label(right, text="Aperçu", fg=FG_ACCENT, bg=BG_PANEL,
                 font=("Segoe UI", 11, "bold")).pack()

        # Fond en damier pour simuler la transparence
        self.preview_canvas = tk.Canvas(
            right,
            width=PREVIEW_SIZE, height=PREVIEW_SIZE,
            bg="#888888", highlightthickness=1, highlightbackground="#555"
        )
        self.preview_canvas.pack(pady=(4, 8))
        self._draw_checkerboard()

        tk.Button(right, text="⟳  Actualiser", command=self._update_preview,
                  bg=BG_SECTION, fg=FG_LABEL, relief="flat", cursor="hand2",
                  font=("Segoe UI", 9)).pack()

    # ------------------------------------------------------------------
    # Onglet Fond
    # ------------------------------------------------------------------

    def _build_bg_tab(self, parent):
        self._section(parent, "Couleur de fond")
        self._color_row(parent, "Couleur", self.bg_color, self.bg_alpha,
                        self._pick_bg_color)
        self._slider_row(parent, "Opacité", self.bg_alpha, 0, 255)

        self._section(parent, "Forme")
        self._combo_row(parent, "Forme du fond", self.bg_shape, BG_SHAPES)
        self._slider_row(parent, "Rayon arrondi", self.bg_radius, 0, 128)

    # ------------------------------------------------------------------
    # Onglet Texte
    # ------------------------------------------------------------------

    def _build_text_tab(self, parent):
        self._section(parent, "Contenu")
        self._entry_row(parent, "Texte", self.text_str)

        self._section(parent, "Police")
        row = tk.Frame(parent, bg=BG_SECTION)
        row.pack(fill="x", padx=4, pady=2)
        tk.Label(row, text="Famille", fg=FG_LABEL, bg=BG_SECTION,
                 width=12, anchor="w").pack(side="left")
        self.font_combo = ttk.Combobox(row, textvariable=self.text_font,
                                       width=28, state="readonly")
        self.font_combo.pack(side="left")
        self.font_combo.bind("<<ComboboxSelected>>", lambda *_: self._update_preview())

        self._slider_row(parent, "Taille", self.text_size, 8, 240)

        self._section(parent, "Couleur du texte")
        self._color_row(parent, "Couleur", self.text_color, self.text_alpha,
                        self._pick_text_color)
        self._slider_row(parent, "Opacité", self.text_alpha, 0, 255)

        self._section(parent, "Position")
        self._slider_row(parent, "Décalage X", self.text_off_x, -120, 120)
        self._slider_row(parent, "Décalage Y", self.text_off_y, -120, 120)

    # ------------------------------------------------------------------
    # Onglet Forme
    # ------------------------------------------------------------------

    def _build_shape_tab(self, parent):
        tk.Checkbutton(
            parent, text="  Activer une forme additionnelle",
            variable=self.shape_enabled,
            fg=FG_LABEL, bg=BG_SECTION, selectcolor=BG_SECTION,
            activeforeground=FG_ACCENT, activebackground=BG_SECTION,
            command=self._update_preview,
        ).pack(fill="x", padx=4, pady=6)

        self._section(parent, "Type & couleur")
        self._combo_row(parent, "Forme", self.shape_kind, SHAPE_TYPES)
        self._color_row(parent, "Couleur", self.shape_color, self.shape_alpha,
                        self._pick_shape_color)
        self._slider_row(parent, "Opacité", self.shape_alpha, 0, 255)

        self._section(parent, "Taille & position")
        self._slider_row(parent, "Taille (rayon)", self.shape_size, 4, 128)
        self._slider_row(parent, "Position X",     self.shape_x,    0, 256)
        self._slider_row(parent, "Position Y",     self.shape_y,    0, 256)

    # ------------------------------------------------------------------
    # Onglet Export
    # ------------------------------------------------------------------

    def _build_export_tab(self, parent):
        self._section(parent, "Tailles ICO à inclure")
        grid = tk.Frame(parent, bg=BG_SECTION)
        grid.pack(fill="x", padx=4)
        for i, (sz, var) in enumerate(self.ico_sizes.items()):
            tk.Checkbutton(
                grid, text=f"{sz}×{sz}", variable=var,
                fg=FG_LABEL, bg=BG_SECTION, selectcolor=BG_SECTION,
                activeforeground=FG_ACCENT, activebackground=BG_SECTION,
            ).grid(row=i // 4, column=i % 4, sticky="w", padx=4, pady=2)

        self._section(parent, "Actions")
        tk.Button(parent, text="💾  Exporter en .ico",
                  command=self._export_ico,
                  bg=BTN_EXPORT, fg="#1e1e2e", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10, "bold"), pady=6
                  ).pack(fill="x", padx=4, pady=4)

        tk.Button(parent, text="🖼  Exporter en .png",
                  command=self._export_png,
                  bg=FG_ACCENT, fg="#1e1e2e", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10, "bold"), pady=6
                  ).pack(fill="x", padx=4, pady=2)

        self._section(parent, "Convertir un PNG existant")
        tk.Button(parent, text="📂  PNG → ICO",
                  command=self._convert_png_to_ico,
                  bg=BTN_CONVERT, fg="#1e1e2e", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10, "bold"), pady=6
                  ).pack(fill="x", padx=4, pady=4)

    # ------------------------------------------------------------------
    # Helpers UI
    # ------------------------------------------------------------------

    def _make_tab(self, notebook: ttk.Notebook, title: str) -> tk.Frame:
        frame = tk.Frame(notebook, bg=BG_SECTION, padx=6, pady=6)
        notebook.add(frame, text=title)
        return frame

    def _section(self, parent, title: str):
        tk.Label(parent, text=title, fg=FG_ACCENT, bg=BG_SECTION,
                 font=("Segoe UI", 9, "bold"), anchor="w"
                 ).pack(fill="x", padx=4, pady=(10, 2))
        tk.Frame(parent, height=1, bg="#44465a").pack(fill="x", padx=4, pady=(0, 4))

    def _slider_row(self, parent, label: str, var: tk.IntVar,
                    lo: int, hi: int):
        row = tk.Frame(parent, bg=BG_SECTION)
        row.pack(fill="x", padx=4, pady=1)
        tk.Label(row, text=label, fg=FG_LABEL, bg=BG_SECTION,
                 width=14, anchor="w").pack(side="left")
        val_lbl = tk.Label(row, textvariable=var, fg=FG_LABEL, bg=BG_SECTION,
                           width=4)
        val_lbl.pack(side="right")
        tk.Scale(
            row, variable=var, from_=lo, to=hi,
            orient="horizontal", length=160, showvalue=False,
            bg=BG_SECTION, fg=FG_LABEL, troughcolor="#44465a",
            activebackground=FG_ACCENT, highlightthickness=0,
            command=lambda *_: self._schedule_preview(),
        ).pack(side="left", fill="x", expand=True)

    def _combo_row(self, parent, label: str, var: tk.StringVar,
                   values: list[str]):
        row = tk.Frame(parent, bg=BG_SECTION)
        row.pack(fill="x", padx=4, pady=2)
        tk.Label(row, text=label, fg=FG_LABEL, bg=BG_SECTION,
                 width=14, anchor="w").pack(side="left")
        cb = ttk.Combobox(row, textvariable=var, values=values,
                          state="readonly", width=18)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda *_: self._update_preview())

    def _entry_row(self, parent, label: str, var: tk.StringVar):
        row = tk.Frame(parent, bg=BG_SECTION)
        row.pack(fill="x", padx=4, pady=2)
        tk.Label(row, text=label, fg=FG_LABEL, bg=BG_SECTION,
                 width=14, anchor="w").pack(side="left")
        e = tk.Entry(row, textvariable=var, bg="#313244", fg=FG_LABEL,
                     insertbackground=FG_LABEL, width=20, relief="flat")
        e.pack(side="left")
        var.trace_add("write", lambda *_: self._schedule_preview())

    def _color_row(self, parent, label: str, color_var: tk.StringVar,
                   alpha_var: tk.IntVar, command):
        row = tk.Frame(parent, bg=BG_SECTION)
        row.pack(fill="x", padx=4, pady=2)
        tk.Label(row, text=label, fg=FG_LABEL, bg=BG_SECTION,
                 width=14, anchor="w").pack(side="left")
        swatch = tk.Label(row, text="   ", relief="flat", cursor="hand2")
        swatch.pack(side="left", padx=4)
        swatch.bind("<Button-1>", lambda *_: command())

        def refresh(*_):
            try:
                swatch.config(bg=color_var.get())
            except Exception:
                pass
        color_var.trace_add("write", refresh)
        tk.Label(row, textvariable=color_var, fg=FG_LABEL, bg=BG_SECTION,
                 font=("Consolas", 9)).pack(side="left")
        refresh()

    # ------------------------------------------------------------------
    # Selecteurs de couleur
    # ------------------------------------------------------------------

    def _pick_color(self, var: tk.StringVar) -> bool:
        c = colorchooser.askcolor(color=var.get(), title="Choisir une couleur")
        if c[1]:
            var.set(c[1])
            self._update_preview()
            return True
        return False

    def _pick_bg_color(self):    self._pick_color(self.bg_color)
    def _pick_text_color(self):  self._pick_color(self.text_color)
    def _pick_shape_color(self): self._pick_color(self.shape_color)

    # ------------------------------------------------------------------
    # Polices
    # ------------------------------------------------------------------

    def _refresh_fonts(self):
        names = get_font_names()
        self.font_combo["values"] = names
        if names:
            # Tenter de présélectionner "Arial" ou la première disponible
            default = next(
                (n for n in names if "arial" in n.lower()), names[0]
            )
            self.text_font.set(default)

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------

    def _build_config(self) -> IconConfig:
        bg = BackgroundConfig(
            color=_hex_to_rgba(self.bg_color.get(), self.bg_alpha.get()),
            shape=self.bg_shape.get(),  # type: ignore[arg-type]
            corner_radius=self.bg_radius.get(),
        )
        font_path = get_font_path(self.text_font.get())
        text = TextConfig(
            text=self.text_str.get(),
            font_path=font_path,
            font_size=self.text_size.get(),
            color=_hex_to_rgba(self.text_color.get(), self.text_alpha.get()),
            offset_x=self.text_off_x.get(),
            offset_y=self.text_off_y.get(),
        )
        shapes = []
        if self.shape_enabled.get():
            shapes.append(ShapeConfig(
                kind=self.shape_kind.get(),  # type: ignore[arg-type]
                color=_hex_to_rgba(self.shape_color.get(), self.shape_alpha.get()),
                size=self.shape_size.get(),
                x=self.shape_x.get(),
                y=self.shape_y.get(),
            ))
        return IconConfig(background=bg, text=text, shapes=shapes)

    _preview_pending = False

    def _schedule_preview(self):
        """Limite les re-renders à un toutes les 80 ms."""
        if not self._preview_pending:
            self._preview_pending = True
            self.after(80, self._do_preview)

    def _do_preview(self):
        self._preview_pending = False
        self._update_preview()

    def _update_preview(self):
        try:
            cfg = self._build_config()
            img = self.renderer.render(cfg)
            self._preview_image = img
            self._tk_image = ImageTk.PhotoImage(
                img.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.NEAREST)
            )
            self.preview_canvas.delete("icon")
            self.preview_canvas.create_image(
                0, 0, anchor="nw", image=self._tk_image, tags="icon"
            )
        except Exception as e:
            print(f"Aperçu : {e}")

    def _draw_checkerboard(self):
        """Fond damier pour visualiser la transparence."""
        sq = 16
        for row in range(PREVIEW_SIZE // sq):
            for col in range(PREVIEW_SIZE // sq):
                c = "#aaaaaa" if (row + col) % 2 == 0 else "#888888"
                self.preview_canvas.create_rectangle(
                    col * sq, row * sq,
                    col * sq + sq, row * sq + sq,
                    fill=c, outline="", tags="checker"
                )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _selected_sizes(self) -> list[int]:
        return [s for s, var in self.ico_sizes.items() if var.get()]

    def _output_dir(self) -> Path:
        return Path(__file__).parent / "data" / "output"

    def _export_ico(self):
        sizes = self._selected_sizes()
        if not sizes:
            messagebox.showwarning("Export ICO", "Sélectionnez au moins une taille.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".ico",
            filetypes=[("Icône Windows", "*.ico")],
            initialdir=self._output_dir(),
            title="Enregistrer le fichier ICO",
        )
        if not dest:
            return
        try:
            cfg = self._build_config()
            self.renderer.export_ico(cfg, Path(dest), sizes)
            messagebox.showinfo("Export ICO",
                                f"Fichier enregistré :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _export_png(self):
        dest = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Image PNG", "*.png")],
            initialdir=self._output_dir(),
            title="Enregistrer le fichier PNG",
        )
        if not dest:
            return
        try:
            cfg = self._build_config()
            self.renderer.export_png(cfg, Path(dest), size=512)
            messagebox.showinfo("Export PNG",
                                f"Fichier enregistré :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _convert_png_to_ico(self):
        src = filedialog.askopenfilename(
            filetypes=[("Image PNG", "*.png")],
            title="Choisir le PNG source",
        )
        if not src:
            return
        sizes = self._selected_sizes() or [16, 32, 48, 64, 128, 256]
        dest = filedialog.asksaveasfilename(
            defaultextension=".ico",
            filetypes=[("Icône Windows", "*.ico")],
            initialdir=self._output_dir(),
            initialfile=Path(src).stem + ".ico",
            title="Enregistrer le fichier ICO",
        )
        if not dest:
            return
        try:
            IconRenderer.png_to_ico(Path(src), Path(dest), sizes)
            messagebox.showinfo("Conversion",
                                f"ICO créé :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = IcoMakerApp()
    app.update_idletasks()
    # Centrer la fenêtre
    w, h = app.winfo_width(), app.winfo_height()
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
    app.mainloop()
