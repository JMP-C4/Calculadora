"""Interfaz de escritorio de ODE Calculator.

Consume exclusivamente ``odecalc.api.solve``.  El cálculo se ejecuta en un
hilo y el tiempo límite real se aplica dentro de ``odecalc`` mediante un
proceso hijo, de modo que la ventana nunca queda bloqueada por SymPy.

La ventana está organizada como un pequeño producto: barra superior con menús
desplegables, tarjetas tipo *bento* para el editor, el lienzo, la solución y la
explicación paso a paso, y una barra de estado siempre visible.
"""

from __future__ import annotations

import io
import math
import queue
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from odecalc.api import solve
from odecalc.parsing import parse_ode
from odecalc.symbols import C, X, Y
from odecalc.timeout import TimeoutError

from core.notacion import (
    NATURAL,
    NOTACIONES,
    adaptar_latex_mathtext,
    codigo_a_latex,
    formatear,
    formatear_texto,
    fragmentos,
    guardar_preferencia,
    latex_a_infijo,
    latex_a_natural,
    leer_preferencia,
    normalizar,
)

_METHOD_LABELS: dict[str, str] = {
    "linear": "Lineal de primer orden",
    "separable": "Variables separables",
    "exact": "Ecuación exacta",
    "bernoulli": "Ecuación de Bernoulli",
    "homogeneous": "Homogénea de grado cero",
    "reducible_homogeneous": "Reducible a homogénea",
    "substitution_linear_combo": r"Sustitución lineal $u = a x + b y$",
    "riccati": "Ecuación de Riccati",
    "clairaut": "Ecuación de Clairaut",
    "lagrange": "Ecuación de Lagrange",
    "integrating_factor_x": "Factor integrante μ(x)",
    "integrating_factor_y": "Factor integrante μ(y)",
    "integrating_factor_xy": "Factor integrante μ(xy)",
    "integrating_factor_x_plus_y": "Factor integrante μ(x + y)",
    "integrating_factor_x2_plus_y2": "Factor integrante μ(x² + y²)",
    "dsolve": "Respaldo simbólico (dsolve)",
    "numeric": "Respaldo numérico (SciPy)",
}


def _etiqueta_metodo(method: str | None) -> str:
    if not method:
        return "—"
    human = _METHOD_LABELS.get(method)
    return f"{human} ({method})" if human else method

try:
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover - entorno sin Matplotlib
    Figure = None  # type: ignore[assignment,misc]

try:
    from ui.math_preview import MathPreview
except Exception:  # pragma: no cover - entorno sin Matplotlib
    MathPreview = None  # type: ignore[assignment,misc]

try:
    from apps.desktop.plot_panel import PlotMode, PlotPanel
except Exception:  # pragma: no cover - entorno sin Matplotlib/Pillow
    PlotMode = None  # type: ignore[assignment,misc]
    PlotPanel = None  # type: ignore[assignment,misc]

EXAMPLES = (
    "y' = x + y",
    "y' = exp(-x**2)*y + 1",
    "y' = y/x + sqrt(y)",
    "y' = (x+y+1)/(x-y-3)",
    "y = x*y' + y'**2",
)

# ---------------------------------------------------------------------------
# Paleta de la interfaz
# ---------------------------------------------------------------------------
BG = "#f3f6f9"
SURFACE = "#ffffff"
SURFACE_SOFT = "#f6f9fb"
SURFACE_TINT = "#eef5f2"
INK = "#0b1726"
INK_SOFT = "#28394d"
MUTED = "#65758a"
MUTED_2 = "#94a3b5"
LINE = "#dfe7ee"
LINE_STRONG = "#cfdae4"
ACCENT = "#116a5a"
ACCENT_DARK = "#0a5044"
ACCENT_SOFT = "#e3f3ee"
LIME = "#d8f37c"
VIOLET = "#6657d9"
VIOLET_SOFT = "#eeebff"
AMBER = "#b56a06"
AMBER_SOFT = "#fff4df"
ROSE = "#b43a4a"
ROSE_SOFT = "#ffedf0"
OK = "#157a55"
OK_SOFT = "#e3f6ed"
INK_BAR = "#0b1726"

FONT_SANS = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"


class _ScrollableFrame(tk.Frame):
    """Contenedor con scroll vertical reutilizable para tarjetas densas."""

    def __init__(self, parent: tk.Misc, *, background: str = SURFACE) -> None:
        super().__init__(parent, bg=background)
        self.canvas = tk.Canvas(
            self,
            bg=background,
            highlightthickness=0,
            bd=0,
            takefocus=False,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, bg=background)
        self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._sync_scrollregion)
        self.canvas.bind("<Configure>", self._sync_width)

    def _sync_scrollregion(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        else:
            direction = -1 if getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(direction, "units")
        return "break"

    def bind_wheel(self) -> None:
        """Activa la rueda sobre la tarjeta sin secuestrar los `Text` internos."""

        def bind(widget: tk.Misc) -> None:
            if isinstance(widget, tk.Text):
                return
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
            for child in widget.winfo_children():
                bind(child)

        bind(self.canvas)
        bind(self.content)

    def reset(self) -> None:
        self.canvas.yview_moveto(0.0)


class ODEApp(tk.Tk):
    """Ventana principal con editor, lienzo, resultados y explicación."""

    def __init__(self) -> None:
        super().__init__()
        self.title("ODE Calculator — workspace de ecuaciones diferenciales")
        ancho = min(1320, max(820, int(self.winfo_screenwidth() * 0.82)))
        alto = min(880, max(600, int(self.winfo_screenheight() * 0.84)))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(720, 520)
        self.configure(bg=BG)

        self._queue: queue.Queue[object] = queue.Queue()
        self._poll_id: str | None = None
        self._preview_after_id: str | None = None
        self._busy = False
        self._plot_bounds: tuple[float, float] = (-5.0, 5.0)
        self._started_at: float | None = None
        self._ultima_solicitud: tuple[str, dict[str, Any]] | None = None
        self._reintentos_por_solicitud = 0
        self._compacto: bool | None = None
        self._ejemplos_visibles = False
        self._wraplengths: dict[str, int] = {}
        self._notacion_salida = tk.StringVar(value=leer_preferencia(default="Algebraica"))
        self._vista = tk.StringVar(value="Lienzo")
        self._ultimo_resultado: Any = None
        self._input_preview: Any = None
        self._math_preview: Any = None
        self._math_images: list[tk.PhotoImage] = []

        self._configure_styles()
        self._build_layout()
        self._bind_shortcuts()
        self._actualizar_preview_entrada()
        self._poll_id = self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(120, self.equation_entry.focus_set)

    # ------------------------------------------------------------------ UI
    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            ".",
            background=BG,
            foreground=INK,
            font=(FONT_SANS, 10),
        )
        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("Soft.TFrame", background=SURFACE_SOFT)

        style.configure("Card.TLabel", background=SURFACE, foreground=INK)
        style.configure(
            "CardTitle.TLabel",
            background=SURFACE,
            foreground=INK,
            font=(FONT_SANS, 13, "bold"),
        )
        style.configure(
            "CardSub.TLabel",
            background=SURFACE,
            foreground=MUTED,
            font=(FONT_SANS, 9),
        )
        style.configure(
            "Eyebrow.TLabel",
            background=SURFACE,
            foreground=ACCENT,
            font=(FONT_MONO, 8, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=SURFACE,
            foreground=MUTED,
            font=(FONT_MONO, 8, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=SURFACE,
            foreground=MUTED_2,
            font=(FONT_SANS, 9),
        )
        style.configure(
            "Status.TLabel",
            background=BG,
            foreground=MUTED,
            font=(FONT_SANS, 9),
        )
        style.configure(
            "StatusOk.TLabel",
            background=BG,
            foreground=OK,
            font=(FONT_SANS, 9, "bold"),
        )
        style.configure(
            "StatusFail.TLabel",
            background=BG,
            foreground=ROSE,
            font=(FONT_SANS, 9, "bold"),
        )
        style.configure(
            "Kpi.TLabel",
            background=SURFACE_SOFT,
            foreground=INK_SOFT,
            font=(FONT_MONO, 9, "bold"),
            padding=(9, 5),
        )
        style.configure(
            "KpiLabel.TLabel",
            background=SURFACE_SOFT,
            foreground=MUTED_2,
            font=(FONT_MONO, 7),
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#ffffff",
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            focuscolor=ACCENT,
            padding=(12, 8),
            font=(FONT_SANS, 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DARK), ("disabled", "#9db9b3")],
            foreground=[("disabled", "#f0f5f4")],
        )
        style.configure(
            "Ghost.TButton",
            background=SURFACE,
            foreground=INK_SOFT,
            bordercolor=LINE_STRONG,
            lightcolor=LINE,
            darkcolor=LINE,
            padding=(10, 7),
            font=(FONT_SANS, 9),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", SURFACE_SOFT)],
            bordercolor=[("active", ACCENT)],
        )
        style.configure(
            "Card.TEntry",
            fieldbackground=SURFACE_SOFT,
            foreground=INK,
            bordercolor=LINE_STRONG,
            lightcolor=LINE_STRONG,
            darkcolor=LINE_STRONG,
            insertcolor=INK,
            padding=(7, 6),
            font=(FONT_MONO, 10),
        )
        style.configure(
            "Card.TCombobox",
            fieldbackground=SURFACE_SOFT,
            background=SURFACE,
            foreground=INK,
            bordercolor=LINE_STRONG,
            lightcolor=LINE_STRONG,
            darkcolor=LINE_STRONG,
            arrowcolor=ACCENT,
            padding=(7, 6),
            font=(FONT_MONO, 10),
        )

        style.configure("TNotebook", background=SURFACE, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab",
            background=SURFACE,
            foreground=MUTED,
            padding=(13, 7),
            font=(FONT_SANS, 9),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", SURFACE_TINT)],
            foreground=[("selected", ACCENT)],
        )
        style.configure(
            "TProgressbar",
            background=ACCENT,
            troughcolor=LINE,
            bordercolor=LINE,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )

    def _build_layout(self) -> None:
        self._build_header()

        body = ttk.Frame(self, style="App.TFrame")
        body.pack(fill="both", expand=True, padx=18, pady=(14, 8))
        body.columnconfigure(0, weight=1, minsize=0)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=3)
        body.rowconfigure(2, weight=2)
        self._body = body

        # --- Tarjeta del editor ------------------------------------------
        editor_card, _header, editor_body = self._card(
            body,
            icon="ƒ",
            title="Editor de la ecuación",
            subtitle="Escribe la EDO y define el problema de valor inicial.",
        )
        self._editor_card = editor_card
        self._editor_body = editor_body

        ttk.Label(editor_body, text="ECUACIÓN DIFERENCIAL", style="Field.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.equation = tk.StringVar(value=EXAMPLES[0])
        self.equation_entry = ttk.Combobox(
            editor_body,
            textvariable=self.equation,
            values=EXAMPLES,
            style="Card.TCombobox",
        )
        self.equation_entry.pack(fill="x", pady=(0, 4))
        self._equation_hint = ttk.Label(
            editor_body,
            text="Acepta y', dy/dx, M dx + N dy = 0, formas implícitas\ny LaTeX: \\frac{dy}{dx} = \\frac{x^2}{y}",
            style="Hint.TLabel",
        )
        self._equation_hint.pack(anchor="w", pady=(0, 8))

        if MathPreview is not None:
            preview_box = tk.Frame(
                editor_body,
                bg=SURFACE_SOFT,
                highlightbackground=LINE,
                highlightthickness=1,
                bd=0,
            )
            preview_box.pack(fill="x", pady=(0, 10))
            self._input_preview = MathPreview(
                preview_box,
                figsize=(4.2, 0.72),
                fontsize=12,
            )
            self._input_preview.figure.patch.set_facecolor(SURFACE_SOFT)
            self._input_preview.pack(fill="x", expand=True, padx=2, pady=2)

        conditions = tk.Frame(editor_body, bg=SURFACE)
        conditions.pack(fill="x", pady=(0, 12))
        ttk.Label(
            conditions,
            text="CONDICIONES INICIALES · opcional",
            style="Field.TLabel",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        self.x0 = tk.StringVar(value="0")
        self.y0 = tk.StringVar(value="1")
        self.x_min = tk.StringVar(value="-5")
        self.x_max = tk.StringVar(value="5")
        fields = (
            ("x₀", self.x0),
            ("y₀", self.y0),
            ("x mín", self.x_min),
            ("x máx", self.x_max),
        )
        for _index, (_label, variable) in enumerate(fields):
            row, column = divmod(_index, 2)
            ttk.Label(conditions, text=_label, style="Hint.TLabel").grid(
                row=row + 1,
                column=column * 2,
                sticky="e",
                padx=(0, 5),
                pady=3,
            )
            ttk.Entry(
                conditions,
                textvariable=variable,
                width=10,
                style="Card.TEntry",
            ).grid(row=row + 1, column=column * 2 + 1, sticky="w", padx=(0, 12), pady=3)
        conditions.columnconfigure(4, weight=1)

        for var in (self.equation, self.x0, self.y0):
            var.trace_add("write", self._programar_preview_entrada)

        actions = tk.Frame(editor_body, bg=SURFACE)
        actions.pack(fill="x", pady=(0, 10))
        self.solve_button = ttk.Button(
            actions,
            text="Resolver y verificar",
            style="Accent.TButton",
            command=self._start,
        )
        self.solve_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.clear_button = ttk.Button(
            actions,
            text="Limpiar",
            style="Ghost.TButton",
            command=self._reset_editor,
        )
        self.clear_button.pack(side="left")

        divider = tk.Frame(editor_body, bg=LINE, height=1)
        divider.pack(fill="x", pady=(6, 12))

        examples_header = tk.Frame(editor_body, bg=SURFACE)
        examples_header.pack(fill="x", pady=(0, 6))
        ttk.Label(
            examples_header, text="EJEMPLOS RÁPIDOS", style="Field.TLabel"
        ).pack(side="left")
        self._examples_toggle = ttk.Button(
            examples_header,
            text="Mostrar",
            style="Ghost.TButton",
            command=self._alternar_ejemplos,
        )
        self._examples_toggle.pack(side="right")
        quick = tk.Frame(editor_body, bg=SURFACE)
        self._quick_frame = quick
        for index, example in enumerate(EXAMPLES):
            label = example if len(example) <= 25 else example[:23] + "…"
            button = ttk.Button(
                quick,
                text=label,
                style="Ghost.TButton",
                command=lambda value=example: self._load_example(value),
            )
            button.pack(fill="x", pady=2)
        ttk.Button(
            quick,
            text="LaTeX: dy/dx = x²/y",
            style="Ghost.TButton",
            command=self._load_latex_example,
        ).pack(fill="x", pady=2)
        quick.pack_forget()

        tip = tk.Frame(editor_body, bg=SURFACE_TINT, highlightthickness=1, highlightbackground="#d9ece6")
        tip.pack(fill="x", pady=(14, 0))
        tk.Label(
            tip,
            text="  Atajos",
            bg=SURFACE_TINT,
            fg=ACCENT,
            font=(FONT_MONO, 8, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(7, 0))
        self._shortcut_hint = tk.Label(
            tip,
            text="  Ctrl + Enter resuelve · Ctrl + D inserta dy/dx\n  Puedes editar el ejemplo y pulsar Resolver.",
            bg=SURFACE_TINT,
            fg=MUTED,
            font=(FONT_SANS, 9),
            anchor="w",
            justify="left",
        )
        self._shortcut_hint.pack(fill="x", padx=2, pady=(1, 8))

        # --- Tarjeta del lienzo ------------------------------------------
        canvas_card, canvas_header, canvas_body = self._card(
            body,
            icon="∿",
            title="Lienzo interactivo",
            subtitle="Explora la solución, el campo de direcciones o la superficie.",
        )
        self._canvas_card = canvas_card
        self._card_action_button(
            canvas_header,
            "Exportar PNG",
            self._export_plot,
        )

        self.plot_panel: PlotPanel | None
        if PlotPanel is not None:
            self.plot_panel = PlotPanel(canvas_body)
            self.plot_panel.pack(fill="both", expand=True)
            self.plot_panel.figure.patch.set_facecolor(SURFACE)
        else:  # pragma: no cover - sólo sin el extra desktop
            self.plot_panel = None
            ttk.Label(
                canvas_body,
                text=(
                    "Las gráficas requieren el extra de escritorio:\n"
                    'pip install -e ".[desktop]"'
                ),
                style="Hint.TLabel",
            ).pack(anchor="w")

        # --- Tarjeta de salida -------------------------------------------
        output_card, output_header, output_body = self._card(
            body,
            icon="≡",
            title="Salida del motor",
            subtitle="Desplázate para ver resultado, métodos, pasos y advertencias.",
        )
        self._output_card = output_card
        self._build_kpis(output_header)

        self.output_scroll = _ScrollableFrame(output_body)
        self.output_scroll.pack(fill="both", expand=True)
        output_content = self.output_scroll.content

        self.summary = self._output_section(
            output_content,
            "Resultado",
            "Solución, verificación y dominio de la corrida.",
            height=10,
        )
        self._build_notacion_selector(self.summary._head)  # type: ignore[attr-defined]
        if MathPreview is not None:
            self._math_preview = MathPreview(self.summary.master.master)
            self._math_preview.pack(fill="x", before=self.summary.master, pady=(6, 0))
        self.methods = self._output_section(
            output_content,
            "Métodos",
            "Clasificaciones compatibles y método elegido.",
            height=6,
        )
        self.steps = self._output_section(
            output_content,
            "Pasos",
            "Explicación del procedimiento aplicado.",
            height=8,
        )
        self.warnings = self._output_section(
            output_content,
            "Advertencias",
            "Límites, supuestos y avisos del motor.",
            height=4,
        )
        self.explanation = self._output_section(
            output_content,
            "Explicación",
            "Lectura sencilla del resultado y su verificación.",
            height=6,
        )
        self.output_scroll.bind_wheel()

        # --- Barra de estado ---------------------------------------------
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=20, pady=(0, 10))
        self.status = ttk.Label(
            footer,
            text="Listo.",
            style="Status.TLabel",
        )
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(
            footer,
            mode="indeterminate",
            length=120,
        )
        self.progress.pack(side="right", padx=(10, 0))
        ttk.Label(
            footer,
            text="Motor odecalc · resultados verificados antes de mostrarse",
            style="Status.TLabel",
        ).pack(side="right")

        self._clear_outputs()
        if self.plot_panel is not None:
            self.plot_panel.show_waiting()

        self._body.bind("<Configure>", self._al_redimensionar)
        self._aplicar_responsive()
        self._vista.trace_add("write", lambda *_event: self._aplicar_layout())

    # ---------------------------------------------------------- responsive
    def _al_redimensionar(self, event: object) -> None:
        if getattr(event, "widget", None) is not self._body:
            return
        self._aplicar_responsive()

    def _ancho_disponible(self) -> int:
        ancho = int(self._body.winfo_width() or 0)
        if ancho > 1:
            return ancho
        try:
            return int(str(self.geometry()).split("x", 1)[0].split("+", 1)[0])
        except (ValueError, IndexError):  # pragma: no cover - defensa
            return 1024

    def _aplicar_responsive(self) -> None:
        ancho = self._ancho_disponible()
        if ancho <= 1:
            return
        compacto = ancho < 880
        if compacto != self._compacto:
            self._compacto = compacto
            self._nav_full.pack_forget()
            self._nav_compact.pack(side="left", padx=(2, 0), pady=17)
            if not compacto:
                self._nav_compact.pack_forget()
                self._nav_full.pack(side="left", pady=17)
        self._aplicar_layout(compacto)

        ancho_editor = max(280, ancho - 48) if compacto else min(
            360, max(280, int(ancho * 0.28))
        )
        self._fijar_wrap("ecuacion", self._equation_hint, ancho_editor)
        self._fijar_wrap("atajos", self._shortcut_hint, ancho_editor - 8)
        self._fijar_wrap("estado", self.status, max(260, ancho - 520))

    def _aplicar_layout(self, compacto: bool | None = None) -> None:
        """Coloca la vista activa para que ocupe todo el espacio disponible."""

        if compacto is None:
            compacto = bool(self._compacto)
        self._canvas_card.grid_forget()
        self._output_card.grid_forget()
        activa = (
            self._output_card if self._vista.get() == "Salida" else self._canvas_card
        )
        if compacto:
            self._body.columnconfigure(0, weight=1, minsize=0)
            self._body.columnconfigure(1, weight=0, minsize=0)
            self._body.rowconfigure(0, weight=0)
            self._body.rowconfigure(1, weight=1)
            self._body.rowconfigure(2, weight=0)
            self._editor_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            activa.grid(row=1, column=0, sticky="nsew")
        else:
            self._body.columnconfigure(0, weight=0, minsize=320)
            self._body.columnconfigure(1, weight=1)
            self._body.rowconfigure(0, weight=1)
            self._body.rowconfigure(1, weight=0)
            self._body.rowconfigure(2, weight=0)
            self._editor_card.grid(
                row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 14)
            )
            activa.grid(row=0, column=1, sticky="nsew")

    def _fijar_wrap(self, clave: str, etiqueta: tk.Misc, ancho: int) -> None:
        if self._wraplengths.get(clave) == ancho:
            return
        etiqueta.configure(wraplength=ancho)
        self._wraplengths[clave] = ancho

    def _alternar_ejemplos(self) -> None:
        self._ejemplos_visibles = not self._ejemplos_visibles
        if self._ejemplos_visibles:
            self._quick_frame.pack(fill="x")
            self._examples_toggle.configure(text="Ocultar")
        else:
            self._quick_frame.pack_forget()
            self._examples_toggle.configure(text="Mostrar")

    # ------------------------------------------------------------- header
    def _build_header(self) -> None:
        header = tk.Frame(self, bg=INK_BAR, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=INK_BAR)
        brand.pack(side="left", fill="y", padx=(20, 18))
        mark = tk.Label(
            brand,
            text="∿",
            bg=LIME,
            fg=INK_BAR,
            font=(FONT_SANS, 18, "bold"),
            width=2,
            height=1,
        )
        mark.pack(side="left", pady=17)
        titles = tk.Frame(brand, bg=INK_BAR)
        titles.pack(side="left", padx=(10, 0), pady=12)
        tk.Label(
            titles,
            text="ODE Calculator",
            bg=INK_BAR,
            fg="#f2f8f6",
            font=(FONT_SANS, 13, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="Ecuaciones diferenciales · workspace",
            bg=INK_BAR,
            fg="#91a8b6",
            font=(FONT_SANS, 8),
            anchor="w",
        ).pack(anchor="w")

        nav = tk.Frame(header, bg=INK_BAR)
        nav.pack(side="left", fill="y", pady=17)

        self._nav_full = tk.Frame(nav, bg=INK_BAR)
        self._nav_full.pack(side="left")
        self._nav_menu(self._nav_full, "Resolver", self._resolver_menu)
        self._nav_menu(self._nav_full, "Vista", self._vista_menu)
        self._nav_menu(self._nav_full, "Lienzo", self._canvas_menu)
        self._nav_menu(self._nav_full, "Ejercicios", self._exercises_menu)
        self._nav_menu(self._nav_full, "Ayuda", self._help_menu)

        self._nav_compact = tk.Menubutton(
            nav,
            text="Menú",
            bg=INK_BAR,
            fg="#d7e5e2",
            activebackground="#172b40",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            font=(FONT_SANS, 9),
            cursor="hand2",
        )
        compact_menu = tk.Menu(self._nav_compact, tearoff=False)
        for etiqueta, constructor in (
            ("Resolver", self._resolver_menu),
            ("Vista", self._vista_menu),
            ("Lienzo", self._canvas_menu),
            ("Ejercicios", self._exercises_menu),
            ("Ayuda", self._help_menu),
        ):
            submenu = tk.Menu(compact_menu, tearoff=False)
            constructor(submenu)
            compact_menu.add_cascade(label=etiqueta, menu=submenu)
        self._nav_compact.configure(menu=compact_menu)
        self._nav_compact.pack_forget()

        right = tk.Frame(header, bg=INK_BAR)
        right.pack(side="right", fill="y", padx=(0, 20), pady=17)
        self.header_plot_menu = tk.Menu(right, tearoff=False)
        self._canvas_menu(self.header_plot_menu)
        self.header_plot_button = self._header_button(
            right, "Gráficas", self._mostrar_graficas, destacado=True
        )
        self.header_exercise_button = self._header_button(
            right, "Ver ejercicio", self._ir_al_ejercicio
        )
        self.header_instructions_button = self._header_button(
            right, "Instrucciones", self._show_manual
        )

    def _header_button(
        self, parent: tk.Misc, text: str, command: Any, *, destacado: bool = False
    ) -> tk.Button:
        """Botón de la cabecera con estilo uniforme y sin desbordes."""

        boton = tk.Button(
            parent,
            text=text,
            command=command,
            bg=LIME if destacado else INK_BAR,
            fg=INK_BAR if destacado else "#d7e5e2",
            activebackground="#c6e45f" if destacado else "#172b40",
            activeforeground=INK_BAR if destacado else "#ffffff",
            relief="flat",
            bd=0,
            padx=12 if destacado else 10,
            pady=5,
            font=(FONT_SANS, 9, "bold" if destacado else "normal"),
            cursor="hand2",
        )
        boton.pack(side="left", padx=(0 if destacado else 6, 0))
        return boton

    def _nav_menu(self, parent: tk.Misc, label: str, builder: Any) -> None:
        button = tk.Menubutton(
            parent,
            text=label,
            bg=INK_BAR,
            fg="#d7e5e2",
            activebackground="#172b40",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            font=(FONT_SANS, 9),
            cursor="hand2",
        )
        menu = tk.Menu(button, tearoff=False)
        builder(menu)
        button.configure(menu=menu)
        button.pack(side="left", padx=1)

    def _card(
        self,
        parent: tk.Misc,
        *,
        icon: str,
        title: str,
        subtitle: str,
    ) -> tuple[tk.Frame, tk.Frame, tk.Frame]:
        outer = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=LINE,
            highlightthickness=1,
            bd=0,
        )
        header = tk.Frame(outer, bg=SURFACE)
        header.pack(fill="x", padx=16, pady=(14, 10))

        icon_label = tk.Label(
            header,
            text=icon,
            bg=ACCENT_SOFT,
            fg=ACCENT,
            font=(FONT_SANS, 12, "bold"),
            width=2,
            height=1,
        )
        icon_label.pack(side="left", padx=(0, 10))
        titles = tk.Frame(header, bg=SURFACE)
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(
            titles,
            text=title,
            bg=SURFACE,
            fg=INK,
            font=(FONT_SANS, 12, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            titles,
            text=subtitle,
            bg=SURFACE,
            fg=MUTED,
            font=(FONT_SANS, 8),
            anchor="w",
        ).pack(anchor="w")

        body = tk.Frame(outer, bg=SURFACE)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        return outer, header, body

    def _card_action_button(
        self,
        header: tk.Misc,
        text: str,
        command: Any,
    ) -> ttk.Button:
        button = ttk.Button(header, text=text, style="Ghost.TButton", command=command)
        button.pack(side="right")
        return button

    def _build_kpis(self, header: tk.Frame) -> None:
        container = tk.Frame(header, bg=SURFACE)
        container.pack(side="right")
        self.kpi_method = self._kpi(container, "MÉTODO")
        self.kpi_verification = self._kpi(container, "RESIDUO")
        self.kpi_time = self._kpi(container, "TIEMPO")

    def _kpi(self, parent: tk.Misc, label: str) -> tk.Label:
        card = tk.Frame(parent, bg=SURFACE_SOFT, highlightthickness=1, highlightbackground=LINE)
        card.pack(side="left", padx=(6, 0))
        tk.Label(
            card,
            text=label,
            bg=SURFACE_SOFT,
            fg=MUTED_2,
            font=(FONT_MONO, 7),
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(4, 0))
        value = tk.Label(
            card,
            text="—",
            bg=SURFACE_SOFT,
            fg=INK_SOFT,
            font=(FONT_MONO, 9, "bold"),
            anchor="w",
        )
        value.pack(anchor="w", padx=8, pady=(0, 4))
        return value

    def _output_section(
        self,
        parent: tk.Misc,
        title: str,
        subtitle: str,
        *,
        height: int,
    ) -> tk.Text:
        section = tk.Frame(parent, bg=SURFACE)
        section.pack(fill="x", padx=2, pady=(0, 10))

        head = tk.Frame(section, bg=SURFACE)
        head.pack(fill="x")
        tk.Label(
            head,
            text=title.upper(),
            bg=SURFACE,
            fg=INK,
            font=(FONT_MONO, 8, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            head,
            text=subtitle,
            bg=SURFACE,
            fg=MUTED,
            font=(FONT_SANS, 8),
            anchor="w",
        ).pack(side="left", padx=(8, 0))

        box = tk.Frame(
            section,
            bg=SURFACE_SOFT,
            highlightbackground=LINE,
            highlightthickness=1,
            bd=0,
        )
        box.pack(fill="x", pady=(5, 0))

        text = tk.Text(
            box,
            wrap="word",
            height=height,
            width=40,
            font=(FONT_SANS, 10),
            undo=False,
            bg=SURFACE_SOFT,
            fg=INK_SOFT,
            insertbackground=INK,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            spacing1=2,
            spacing3=2,
            selectbackground=ACCENT_SOFT,
            selectforeground=INK,
        )
        scroll = ttk.Scrollbar(box, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.configure(state="disabled")
        text._head = head  # type: ignore[attr-defined]
        return text

    # ------------------------------------------------------- nav menus
    def _resolver_menu(self, menu: tk.Menu) -> None:
        menu.add_command(
            label="Nueva ecuación",
            accelerator="Ctrl+N",
            command=self._reset_editor,
        )
        menu.add_command(label="Enfocar editor", command=self._focus_equation)
        menu.add_separator()
        menu.add_command(
            label="Insertar dy/dx",
            accelerator="Ctrl+D",
            command=lambda: self._insert_token("dy/dx"),
        )
        menu.add_command(
            label="Insertar exp()",
            accelerator="Ctrl+E",
            command=lambda: self._insert_token("exp()"),
        )
        menu.add_command(label="Insertar sqrt()", command=lambda: self._insert_token("sqrt()"))
        menu.add_command(
            label="Insertar pi",
            accelerator="Ctrl+P",
            command=lambda: self._insert_token("pi"),
        )
        menu.add_separator()
        menu.add_command(
            label="Resolver y verificar",
            accelerator="Ctrl+Enter",
            command=self._start,
        )
        menu.add_command(label="Limpiar salida", command=self._clear_outputs)
        menu.add_separator()
        menu.add_command(label="Salir", command=self.destroy)

    def _vista_menu(self, menu: tk.Menu) -> None:
        for opcion in ("Lienzo", "Salida"):
            menu.add_radiobutton(
                label=opcion,
                variable=self._vista,
                value=opcion,
                command=lambda valor=opcion: self._set_status(f"Vista: {valor}"),
            )

    def _canvas_menu(self, menu: tk.Menu) -> None:
        if PlotMode is None:
            menu.add_command(label="Gráficas no disponibles")
            return
        for mode in PlotMode:
            menu.add_command(
                label=mode.value,
                command=lambda value=mode.value: self._set_plot_mode(value),
            )
        menu.add_separator()
        menu.add_command(label="Exportar lienzo…", command=self._export_plot)

    def _exercises_menu(self, menu: tk.Menu) -> None:
        for example in EXAMPLES:
            menu.add_command(
                label=example,
                command=lambda value=example: self._load_example(value, solve_now=True),
            )
        menu.add_separator()
        menu.add_command(
            label="Ejemplo en LaTeX (fracción)",
            command=self._load_latex_example,
        )

    def _help_menu(self, menu: tk.Menu) -> None:
        menu.add_command(label="Manual de instrucciones", command=self._show_manual)
        menu.add_command(label="Atajos de teclado", command=self._show_shortcuts)
        menu.add_command(label="Abrir README", command=self._open_readme)
        menu.add_separator()
        menu.add_command(label="Acerca de", command=self._about)

    # -------------------------------------------------------------- helpers
    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _event: self._reset_editor())
        self.bind("<Control-Return>", lambda _event: self._start())
        self.bind("<Control-d>", lambda _event: self._insert_token("dy/dx"))
        self.bind("<Control-e>", lambda _event: self._insert_token("exp()"))
        self.bind("<Control-p>", lambda _event: self._insert_token("pi"))

    def _focus_equation(self) -> None:
        self.equation_entry.focus_set()

    def _insert_token(self, token: str) -> None:
        self.equation_entry.focus_set()
        current = self.equation.get()
        try:
            pos = self.equation_entry.index("insert")
            self.equation_entry.insert("insert", token)
            if token.endswith("()"):
                self.equation_entry.icursor(pos + len(token) - 1)
        except tk.TclError:  # pragma: no cover - combobox sin cursor
            self.equation.set(current + token)

    def _programar_preview_entrada(self, *_args: object) -> None:
        if self._input_preview is None:
            return
        if self._preview_after_id is not None:
            try:
                self.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
        self._preview_after_id = self.after(120, self._actualizar_preview_entrada)

    def _actualizar_preview_entrada(self) -> None:
        self._preview_after_id = None
        preview = self._input_preview
        if preview is None:
            return
        texto = self.equation.get().strip()
        if not texto:
            preview.show_placeholder()
            return
        cond = None
        x0_txt = self.x0.get().strip()
        y0_txt = self.y0.get().strip()
        if x0_txt and y0_txt:
            try:
                x0_val = float(x0_txt)
                y0_val = float(y0_txt)
                if math.isfinite(x0_val) and math.isfinite(y0_val):
                    cond = type("_PVI", (), {"x0": x0_val, "y0": y0_val})()
            except ValueError:
                cond = None
        parsed = parse_ode(texto)
        if parsed.error is None and parsed.latex_str:
            latex_expr = parsed.latex_str
        else:
            latex_expr = adaptar_latex_mathtext(codigo_a_latex(texto))
        if not latex_expr:
            preview.show_placeholder()
            return
        preview.render(latex_expr, cond)

    def _load_example(self, equation: str, *, solve_now: bool = False) -> None:
        self.equation.set(equation)
        self._focus_equation()
        if solve_now:
            self._start()
        else:
            self._set_status(f"Ejemplo cargado: {equation}")

    def _load_latex_example(self) -> None:
        self.equation.set(r"$$\frac{dy}{dx} = \frac{x^2}{y}$$")
        self.x0.set("0")
        self.y0.set("1")
        self.x_min.set("0")
        self.x_max.set("2")
        self._focus_equation()
        self._set_status("Ejemplo LaTeX cargado. Pulsa Resolver y verificar.")

    def _set_status(self, message: str, level: str = "info") -> None:
        style = {
            "info": "Status.TLabel",
            "ok": "StatusOk.TLabel",
            "error": "StatusFail.TLabel",
            "warning": "StatusFail.TLabel",
        }.get(level, "Status.TLabel")
        self.status.configure(text=message, style=style)

    def _build_notacion_selector(self, head: tk.Frame) -> None:
        """Selector compacto de notación, aplicable a resultados ya visibles."""

        contenedor = tk.Frame(head, bg=SURFACE)
        contenedor.pack(side="right")
        tk.Label(
            contenedor,
            text="Notación",
            bg=SURFACE,
            fg=MUTED,
            font=(FONT_SANS, 8),
        ).pack(side="left", padx=(0, 6))
        etiquetas = {"Algebraica": "Estándar"}
        for notacion in NOTACIONES:
            ttk.Radiobutton(
                contenedor,
                text=etiquetas.get(notacion, notacion),
                value=notacion,
                variable=self._notacion_salida,
                command=self._on_notacion_cambiada,
            ).pack(side="left", padx=(0, 4))

    def _on_notacion_cambiada(self) -> None:
        notacion = guardar_preferencia(self._notacion_salida.get())
        self._notacion_salida.set(notacion)
        if self._ultimo_resultado is not None:
            self._render_resultado_completo(self._ultimo_resultado)
        self._set_status(f"Notación: {notacion}")

    @staticmethod
    def _expr(latex: str, solucion: object, notacion: str) -> str:
        texto, es_latex = formatear(latex, solucion, notacion)
        return texto if texto else latex if es_latex else ""

    def _formula_en_linea(self, latex: str, solucion: object, notacion: str) -> str:
        """Devuelve la fórmula delimitada para renderizarla dentro del texto."""

        texto = self._expr(latex, solucion, notacion)
        if texto and normalizar(notacion) in ("Algebraica", NATURAL):
            return f"${texto}$"
        return texto

    def _set_preview(self, latex: str, visible: bool, conditions: Any = None) -> None:
        preview = self._math_preview
        if preview is None:
            return
        if not visible or not latex:
            preview.pack_forget()
            return
        if not preview.winfo_ismapped():
            preview.pack(fill="x", before=self.summary.master, pady=(6, 0))
        preview.render(adaptar_latex_mathtext(latex), conditions)

    def _imagen_latex(self, latex: str) -> tk.PhotoImage:
        """Renderiza una fórmula corta como imagen PNG para insertarla en el texto."""

        return tk.PhotoImage(data=_renderizar_png_latex(latex))

    def _insertar_formula(
        self, widget: tk.Text, latex: str, notacion: str = NATURAL
    ) -> None:
        try:
            imagen = self._imagen_latex(latex)
            self._math_images.append(imagen)
            etiqueta = tk.Label(
                widget,
                image=imagen,
                bg=widget.cget("bg"),
                highlightthickness=0,
                bd=0,
            )
            widget.window_create("end", window=etiqueta)
        except Exception:  # pragma: no cover - depende del backend gráfico
            fallback = (
                latex_a_natural(latex)
                if normalizar(notacion) == NATURAL
                else latex_a_infijo(latex)
            )
            widget.insert("end", fallback)

    def _set_text_formateado(
        self, widget: tk.Text, contenido: str, notacion: str
    ) -> None:
        """Escribe prosa y fórmulas mixtas con la notación elegida."""

        modo = normalizar(notacion)
        widget.configure(
            state="normal",
            font=(FONT_MONO, 9) if modo == "Infija" else (FONT_SANS, 10),
        )
        widget.delete("1.0", "end")
        try:
            if modo == "Infija":
                widget.insert("end", formatear_texto(contenido, notacion))
            else:
                for texto, es_latex in fragmentos(contenido, notacion):
                    if not texto:
                        continue
                    if es_latex:
                        self._insertar_formula(widget, texto, notacion)
                    else:
                        widget.insert("end", texto)
        finally:
            widget.configure(state="disabled")
            widget.yview_moveto(0.0)

    def _residuo_en_notacion(self, residual: object, notacion: str) -> str:
        texto = str(residual or "").strip()
        if not texto:
            return ""
        if normalizar(notacion) == "Infija":
            return texto
        allowed = {
            "x": X,
            "y": Y,
            "C": C,
            "Piecewise": sp.Piecewise,
            "Eq": sp.Eq,
            "Abs": sp.Abs,
            "sign": sp.sign,
            "nan": sp.nan,
            "oo": sp.oo,
            "True": sp.true,
            "False": sp.false,
            "EulerGamma": sp.EulerGamma,
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "exp": sp.exp,
            "log": sp.log,
            "sqrt": sp.sqrt,
            "Ci": sp.Ci,
            "Si": sp.Si,
            "Ei": sp.Ei,
            "erf": sp.erf,
            "erfi": sp.erfi,
        }
        try:
            expr = parse_expr(
                texto,
                local_dict=allowed,
                global_dict={"__builtins__": {}},
                evaluate=False,
            )
            latex_res = sp.latex(expr)
        except Exception:
            latex_res = codigo_a_latex(texto)
        return self._formula_en_linea(latex_res, None, notacion)

    def _render_salida(self, result: Any) -> None:
        """Actualiza la tarjeta «Resultado» con la notación elegida."""

        notacion = normalizar(self._notacion_salida.get())
        usar_preview = (
            notacion in ("Algebraica", NATURAL) and self._math_preview is not None
        )
        solucion = result.particular or result.general
        solucion_latex = getattr(solucion, "latex", "") or ""
        texto_preview, _es_latex = formatear(solucion_latex, solucion, notacion)
        if not texto_preview and getattr(result, "input_latex", ""):
            texto_preview = self._expr(result.input_latex, None, notacion)
        self._set_preview(texto_preview, usar_preview)

        lines: list[str] = []
        if result.error:
            lines.append(f"Error: {result.error}")
        input_latex = getattr(result, "input_latex", "") or ""
        if input_latex:
            ecuacion_fmt = self._formula_en_linea(input_latex, None, notacion)
            lines.append(f"Ecuación: {ecuacion_fmt}")
        if result.standard_form:
            if normalizar(notacion) == "Infija":
                lines.append(f"Forma estándar: {result.standard_form}")
            else:
                std_latex = codigo_a_latex(result.standard_form)
                if not input_latex or std_latex.replace(" ", "") != input_latex.replace(" ", ""):
                    lines.append(
                        f"Forma estándar: {self._formula_en_linea(std_latex, None, notacion)}"
                    )
        solicitud = getattr(self, "_ultima_solicitud", None)
        if solicitud is not None:
            x0 = solicitud[1].get("x0")
            y0 = solicitud[1].get("y0")
            if x0 is not None and y0 is not None:
                pvi_latex = rf"y({x0:g}) = {y0:g}"
                lines.append(
                    f"Condición inicial: {self._formula_en_linea(pvi_latex, None, notacion)}"
                )
        lines.append(f"Método elegido: {_etiqueta_metodo(result.chosen_method)}")
        if result.general:
            kind = "explícita" if result.general.is_explicit else "implícita"
            cuerpo = self._formula_en_linea(result.general.latex, result.general, notacion)
            lines.append(f"\nSolución general ({kind}):\n{cuerpo}")
            branch_note = getattr(result.general, "branch_note", None)
            if branch_note:
                lines.append(f"Nota de rama: {branch_note}")
        if result.particular:
            kind = "explícita" if result.particular.is_explicit else "implícita"
            cuerpo = self._formula_en_linea(result.particular.latex, result.particular, notacion)
            lines.append(f"\nSolución particular ({kind}):\n{cuerpo}")
            branch_note = getattr(result.particular, "branch_note", None)
            if branch_note:
                lines.append(f"Nota de rama: {branch_note}")
        if result.verification:
            lines.append(
                f"\nVerificación: {result.verification.status}\n"
                f"{result.verification.message}"
            )
            residuo = getattr(result.verification, "simplified_residual", None)
            if residuo is not None and str(residuo).strip():
                lines.append(
                    f"Residuo simbólico: {self._residuo_en_notacion(residuo, notacion)}"
                )
        if result.particular_verification:
            lines.append(
                f"\nVerificación del PVI: {result.particular_verification.status}\n"
                f"{result.particular_verification.message}"
            )
            residuo_pvi = getattr(result.particular_verification, "simplified_residual", None)
            if residuo_pvi is not None and str(residuo_pvi).strip():
                lines.append(
                    f"Residuo del PVI: {self._residuo_en_notacion(residuo_pvi, notacion)}"
                )
        if result.validity.domain:
            lines.append(f"\nDominio: {result.validity.domain}")
        if result.validity.interval:
            intervalo = (
                result.validity.interval
                if normalizar(notacion) == "Infija"
                else formatear_texto(result.validity.interval, notacion)
            )
            lines.append(f"Intervalo: {intervalo}")
        singular_points = getattr(result.validity, "singular_points", None) or ()
        if singular_points:
            pts = ", ".join(
                str(pt) if normalizar(notacion) == "Infija" else f"${codigo_a_latex(str(pt))}$"
                for pt in singular_points
            )
            lines.append(f"Puntos singulares: {pts}")
        validity_notes = getattr(result.validity, "notes", None) or ()
        for note in validity_notes:
            lines.append(f"• {note}")
        if result.numeric is not None:
            lines.append(f"\nRespaldo numérico: {result.numeric.message}")
            interval_num = getattr(result.numeric, "interval", None)
            if getattr(result.numeric, "success", False) and interval_num is not None:
                a_val, b_val = interval_num
                rango_latex = rf"x \in [{a_val:.6g}, {b_val:.6g}]"
                lines.append(
                    f"Intervalo numérico: {self._formula_en_linea(rango_latex, None, notacion)}"
                )
        if result.singular_solutions:
            lines.append("\nSoluciones singulares:")
            for item in result.singular_solutions:
                cuerpo_s = self._formula_en_linea(item.latex, item, notacion)
                nota_s = getattr(item, "branch_note", None)
                lines.append(f"  • {cuerpo_s}" + (f" ({nota_s})" if nota_s else ""))
        self._set_text_formateado(self.summary, "\n".join(lines), notacion)

    def _render_metodos(self, result: Any, notacion: str) -> None:
        lineas = [
            f"[{match.priority:3}] {match.name} ({match.method})\n"
            f"    {match.evidence}"
            for match in result.classifications
        ]
        self._set_text_formateado(
            self.methods,
            "\n\n".join(lineas) or "No hay métodos aplicables.",
            notacion,
        )

    def _render_pasos(self, result: Any, notacion: str) -> None:
        lineas: list[str] = []
        for paso in result.steps:
            lineas.append(f"{paso.number}. {paso.title}")
            if paso.latex:
                lineas.append(self._formula_en_linea(paso.latex, None, notacion))
            if paso.explanation:
                lineas.append(str(paso.explanation))
            lineas.append("")
        self._set_text_formateado(
            self.steps, "\n".join(lineas).strip() or "No hay pasos disponibles.", notacion
        )

    def _render_advertencias(self, result: Any, notacion: str) -> None:
        avisos = [str(aviso) for aviso in result.warnings if str(aviso).strip()]
        texto = (
            "\n".join(f"• {aviso}" for aviso in avisos)
            if avisos
            else "Sin advertencias."
        )
        self._set_text_formateado(self.warnings, texto, notacion)

    def _texto_explicacion(self, result: Any, notacion: str) -> str:
        partes: list[str] = []
        verificacion = getattr(result, "verification", None)
        if verificacion is not None:
            estados = {
                "ok": "La solución fue verificada simbólicamente: el residuo se anula.",
                "fail": "La solución no superó la verificación; revísala con cautela.",
                "unverified": "La solución no pudo verificarse con suficiente confianza.",
            }
            partes.append(estados.get(verificacion.status, verificacion.message))
        elif result.error:
            partes.append(f"El motor no pudo resolver la ecuación: {result.error}")
        if result.chosen_method:
            partes.append(f"Método elegido: {_etiqueta_metodo(result.chosen_method)}.")
        if result.general:
            cuerpo = self._formula_en_linea(result.general.latex, result.general, notacion)
            partes.append(f"Solución general:\n{cuerpo}")
        if result.particular:
            cuerpo = self._formula_en_linea(result.particular.latex, result.particular, notacion)
            partes.append(f"Solución particular:\n{cuerpo}")
        if result.validity.domain:
            partes.append(f"Dominio de validez: {result.validity.domain}.")
        if result.validity.interval:
            partes.append(f"Intervalo de validez: {result.validity.interval}.")
        if result.numeric is not None and result.numeric.message:
            partes.append(f"Respaldo numérico: {result.numeric.message}")
        if result.warnings:
            partes.append("Advertencias: " + " ".join(map(str, result.warnings)))
        return "\n\n".join(partes) or "No hay explicación disponible para este resultado."

    def _render_resultado_completo(self, result: Any) -> None:
        notacion = normalizar(self._notacion_salida.get())
        # Las fórmulas en línea se conservan mientras el texto sigue vivo; al
        # redibujar se liberan las imágenes de la renderización anterior.
        self._math_images.clear()
        self._render_salida(result)
        self._render_metodos(result, notacion)
        self._render_pasos(result, notacion)
        self._render_advertencias(result, notacion)
        self._set_text_formateado(
            self.explanation, self._texto_explicacion(result, notacion), notacion
        )

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")
        widget.yview_moveto(0.0)

    def _clear_outputs(self) -> None:
        self._ultimo_resultado = None
        self._set_preview("", False)
        for widget in (
            self.summary,
            self.methods,
            self.steps,
            self.warnings,
            self.explanation,
        ):
            self._set_text(widget, "")
        for kpi in (self.kpi_method, self.kpi_verification, self.kpi_time):
            kpi.configure(text="—", fg=INK_SOFT)
        self.output_scroll.reset()

    def _reset_editor(self) -> None:
        self.equation.set(EXAMPLES[0])
        self.x0.set("0")
        self.y0.set("1")
        self.x_min.set("-5")
        self.x_max.set("5")
        self._clear_outputs()
        if self.plot_panel is not None:
            self.plot_panel.show_waiting()
        self._set_status("Listo.")
        self._focus_equation()

    def _ir_al_ejercicio(self) -> None:
        """Vuelve a la vista donde se muestra el ejercicio resuelto."""

        self._vista.set("Salida")
        if self._ultimo_resultado is None:
            self._set_status("Resuelve una ecuación para ver el ejercicio.", "warning")
        else:
            self._set_status("Vista: Salida")

    def _mostrar_graficas(self) -> None:
        """Muestra el lienzo y despliega los modos bajo el botón de la cabecera."""

        # El botón debe surtir efecto con un solo clic, incluso si el despliegue
        # del menú falla en algún tema de Tk: primero abrimos el lienzo.
        self._vista.set("Lienzo")
        if self.plot_panel is not None:
            self.plot_panel._on_mode_selected()
            self._set_status(f"Gráfica: {self.plot_panel.mode_selector.get()}")
        else:
            self._set_status("Gráficas no disponibles", "warning")

        boton = self.header_plot_button
        boton.update_idletasks()
        self.after(
            0,
            lambda: self.header_plot_menu.tk_popup(
                boton.winfo_rootx(), boton.winfo_rooty() + boton.winfo_height()
            ),
        )

    def _set_plot_mode(self, mode_value: str) -> None:
        self._vista.set("Lienzo")
        if self.plot_panel is None:
            self._set_status(
                "Instala el extra de escritorio para ver las gráficas: "
                'pip install -e ".[desktop]"',
                "warning",
            )
            return
        self.plot_panel.mode_selector.set(mode_value)
        self.plot_panel._on_mode_selected()
        self._set_status(f"Gráfica: {mode_value}")

    def _export_plot(self) -> None:
        if self.plot_panel is None:
            messagebox.showinfo(
                "Exportar lienzo",
                'Instala el extra de escritorio con: pip install -e ".[desktop]"',
                parent=self,
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar lienzo",
            defaultextension=".png",
            filetypes=(("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")),
            initialfile="ode-calculator.png",
        )
        if not path:
            return
        try:
            self.plot_panel.figure.savefig(path, dpi=200, bbox_inches="tight")
        except Exception as exc:  # pragma: no cover - defensa de la UI
            messagebox.showerror("Exportar lienzo", str(exc), parent=self)
            return
        self._set_status(f"Lienzo exportado: {path}", "ok")

    def _show_manual(self) -> None:
        existing = getattr(self, "_manual_window", None)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_set()
            return

        manual = tk.Toplevel(self)
        manual.title("Manual de instrucciones · ODE Calculator")
        manual.geometry("820x700")
        manual.minsize(560, 420)
        manual.configure(bg=BG)
        manual.transient(self)
        self._manual_window = manual

        header = tk.Frame(manual, bg=INK_BAR, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="∿",
            bg=LIME,
            fg=INK_BAR,
            font=(FONT_SANS, 16, "bold"),
            width=2,
            height=1,
        ).pack(side="left", padx=(18, 12), pady=17)
        titles = tk.Frame(header, bg=INK_BAR)
        titles.pack(side="left", pady=12)
        tk.Label(
            titles,
            text="Manual de instrucciones",
            bg=INK_BAR,
            fg="#f2f8f6",
            font=(FONT_SANS, 13, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="ODE Calculator · guía de uso",
            bg=INK_BAR,
            fg="#91a8b6",
            font=(FONT_SANS, 8),
            anchor="w",
        ).pack(anchor="w")

        body = tk.Frame(
            manual,
            bg=SURFACE,
            highlightbackground=LINE,
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True, padx=16, pady=14)

        text = tk.Text(
            body,
            wrap="word",
            font=(FONT_SANS, 10),
            bg=SURFACE,
            fg=INK_SOFT,
            relief="flat",
            bd=0,
            padx=18,
            pady=14,
            selectbackground=ACCENT_SOFT,
            selectforeground=INK,
        )
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        text.tag_configure(
            "h1",
            font=(FONT_SANS, 16, "bold"),
            foreground=INK,
            spacing1=2,
            spacing3=8,
        )
        text.tag_configure(
            "h2",
            font=(FONT_SANS, 11, "bold"),
            foreground=ACCENT,
            spacing1=12,
            spacing3=4,
        )
        text.tag_configure(
            "body",
            font=(FONT_SANS, 10),
            foreground=INK_SOFT,
            spacing3=5,
            lmargin1=4,
            lmargin2=4,
        )
        text.tag_configure(
            "code",
            font=(FONT_MONO, 9),
            foreground=ACCENT_DARK,
            background=SURFACE_SOFT,
            lmargin1=18,
            lmargin2=18,
            spacing1=2,
            spacing3=2,
        )

        chunks = (
            ("MANUAL DE INSTRUCCIONES\n", "h1"),
            (
                "Guía rápida para resolver, verificar y entender una EDO de primer "
                "orden.\n\n",
                "body",
            ),
            ("1. Escribe la ecuación\n", "h2"),
            (
                "Usa y', dy/dx o pega una fórmula en LaTeX. También se admite la "
                "forma diferencial.\n",
                "body",
            ),
            (
                "y' = x + y\n"
                "dy/dx = x**2 / y\n"
                "$$\\frac{dy}{dx} = \\frac{x^2}{y}$$\n"
                "M(x,y) dx + N(x,y) dy = 0\n",
                "code",
            ),
            (
                "Puedes escribir multiplicación implícita (2x, 3y^2) y funciones "
                "como sin(x), cos(x), exp(x), ln(x) o sqrt(x).\n\n",
                "body",
            ),
            ("2. Define las condiciones iniciales\n", "h2"),
            (
                "x₀ e y₀ son opcionales, pero deben indicarse juntos. Si los dejas "
                "vacíos obtendrás la solución general o la familia de curvas. "
                "x mín y x máx solo controlan el intervalo del lienzo.\n\n",
                "body",
            ),
            ("3. Resuelve y verifica\n", "h2"),
            (
                "Pulsa «Resolver y verificar» o usa Ctrl+Enter. El cálculo corre en "
                "segundo plano y la barra de estado muestra el progreso. Antes de "
                "mostrar una solución, el motor la sustituye en la EDO y comprueba "
                "el residuo.\n\n",
                "body",
            ),
            ("4. Lee la salida del motor\n", "h2"),
            (
                "El menú Vista alterna entre Lienzo y Salida. Al resolver se abre "
                "automáticamente la salida, que reúne cinco bloques: Resultado, "
                "Métodos, Pasos, Advertencias y Explicación. Usa la barra de "
                "desplazamiento general de la tarjeta para recorrerlos todos; "
                "cada bloque tiene además su propio scroll si el texto es largo.\n\n"
                "• Resultado: método elegido, solución general y particular, "
                "verificación, dominio, intervalo y respaldo numérico.\n"
                "• Métodos: clasificaciones compatibles y el método finalmente "
                "elegido.\n"
                "• Pasos: explicación del procedimiento aplicado.\n"
                "• Advertencias: supuestos, límites y avisos del motor.\n"
                "• Explicación: lectura sencilla con la misma notación elegida.\n"
                "El selector Notación se aplica a todos los bloques. Los "
                "indicadores MÉTODO, RESIDUO y TIEMPO resumen la corrida.\n\n",
                "body",
            ),
            ("5. Explora el lienzo\n", "h2"),
            (
                "Elige el tipo de gráfica en el selector o en el menú Lienzo. La "
                "barra de Matplotlib permite hacer zoom, desplazar y guardar la "
                "vista. También puedes exportar el lienzo como PNG, PDF o SVG. Si "
                "un modo no aplica a la ecuación, verás un aviso en lugar de una "
                "gráfica vacía.\n\n",
                "body",
            ),
            ("6. Usa los ejercicios\n", "h2"),
            (
                "El menú Ejercicios carga ejemplos listos para resolver. El ejemplo "
                "en LaTeX demuestra el formato de fracciones y ajusta el intervalo "
                "para que la gráfica sea estable. Puedes editar cualquier ejemplo "
                "antes de resolverlo.\n\n",
                "body",
            ),
            ("7. Atajos de teclado\n", "h2"),
            (
                "Ctrl+N  Nueva ecuación\n"
                "Ctrl+Enter  Resolver y verificar\n"
                "Ctrl+D  Insertar dy/dx\n"
                "Ctrl+E  Insertar exp()\n"
                "Ctrl+P  Insertar pi\n\n",
                "code",
            ),
            ("8. Problemas frecuentes\n", "h2"),
            (
                "• «No se detectó una derivada»: escribe y' o dy/dx.\n"
                "• «Símbolos no permitidos»: usa solo x, y y funciones conocidas.\n"
                "• «PVI incompleto»: indica x₀ e y₀ juntos, o deja ambos vacíos.\n"
                "• «El cálculo excedió el tiempo límite»: simplifica la ecuación, "
                "ajusta el intervalo o revisa el respaldo numérico.\n"
                "• Las EDOs de orden superior a uno no están soportadas.\n\n",
                "body",
            ),
            (
                "Consejo: si una solución parece compleja, revisa primero los pasos "
                "y luego cambia a «Campo de direcciones» o «Familia de curvas» para "
                "ver el comportamiento global.",
                "body",
            ),
        )
        for chunk, tag in chunks:
            text.insert("end", chunk, tag)
        text.configure(state="disabled")
        text.yview_moveto(0.0)

        def scroll_wheel(event: tk.Event) -> str:
            if getattr(event, "num", None) == 4:
                text.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                text.yview_scroll(1, "units")
            else:
                text.yview_scroll(-1 if getattr(event, "delta", 0) > 0 else 1, "units")
            return "break"

        text.bind("<MouseWheel>", scroll_wheel)
        text.bind("<Button-4>", scroll_wheel)
        text.bind("<Button-5>", scroll_wheel)

        footer = tk.Frame(manual, bg=BG)
        footer.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Label(
            footer,
            text="El manual también está disponible en Ayuda → Manual de instrucciones.",
            style="Status.TLabel",
        ).pack(side="left")
        ttk.Button(
            footer,
            text="Cerrar",
            style="Accent.TButton",
            command=manual.destroy,
        ).pack(side="right")
        manual.protocol("WM_DELETE_WINDOW", manual.destroy)
        manual.after(60, manual.focus_set)

    def _show_shortcuts(self) -> None:
        messagebox.showinfo(
            "Atajos de teclado",
            "Ctrl+N  Nueva ecuación\n"
            "Ctrl+Enter  Resolver y verificar\n"
            "Ctrl+D  Insertar dy/dx\n"
            "Ctrl+E  Insertar exp()\n"
            "Ctrl+P  Insertar pi\n\n"
            "Los menús de la barra superior también permiten cambiar el tipo de "
            "gráfica, cargar ejemplos y exportar el lienzo.",
            parent=self,
        )

    def _open_readme(self) -> None:
        readme = Path(__file__).resolve().parents[2] / "README.md"
        if not readme.exists():
            messagebox.showinfo(
                "README",
                "Consulta el manual en Ayuda → Manual de instrucciones.",
                parent=self,
            )
            return
        try:
            webbrowser.open(readme.as_uri())
        except Exception:
            messagebox.showinfo("README", str(readme), parent=self)

    def _about(self) -> None:
        messagebox.showinfo(
            "Acerca de ODE Calculator",
            "ODE Calculator v2.0\n\n"
            "Resuelve EDOs de primer orden con métodos propios, verifica el "
            "residuo y explica el procedimiento paso a paso.\n\n"
            "Interfaz de escritorio construida con tkinter y matplotlib sobre "
            "el motor odecalc.",
            parent=self,
        )

    # -------------------------------------------------------------- solve
    def _start(self) -> None:
        if self._busy:
            self._set_status("Ya hay un cálculo en curso…", "warning")
            return
        equation = self.equation.get().strip()
        if not equation:
            messagebox.showerror("Entrada vacía", "Escribe una EDO de primer orden.", parent=self)
            return
        try:
            values = {
                "x0": float(self.x0.get()) if self.x0.get().strip() else None,
                "y0": float(self.y0.get()) if self.y0.get().strip() else None,
                "x_min": float(self.x_min.get() or -5),
                "x_max": float(self.x_max.get() or 5),
            }
        except ValueError:
            messagebox.showerror(
                "Datos inválidos",
                "Las condiciones e intervalos deben ser numéricos.",
                parent=self,
            )
            return
        if not all(
            math.isfinite(val) for val in values.values() if val is not None
        ):
            messagebox.showerror(
                "Datos inválidos",
                "Los valores numéricos no pueden ser NaN ni infinito.",
                parent=self,
            )
            return
        if values["x_min"] >= values["x_max"]:
            messagebox.showerror(
                "Intervalo inválido",
                "Se requiere x mín < x máx para graficar.",
                parent=self,
            )
            return
        if (values["x0"] is None) != (values["y0"] is None):
            messagebox.showerror(
                "PVI incompleto",
                "Indica x₀ e y₀ juntos, o deja ambos vacíos.",
                parent=self,
            )
            return

        self._plot_bounds = (values["x_min"], values["x_max"])
        self._started_at = time.monotonic()
        self._ultima_solicitud = (equation, values)
        self._reintentos_por_solicitud = 0
        self._launch_solve(30.0)

    def _launch_solve(self, timeout: float) -> None:
        """Ejecuta la última solicitud en segundo plano con un plazo dado."""

        solicitud = self._ultima_solicitud
        if solicitud is None:
            return
        equation, values = solicitud

        self._busy = True
        self.solve_button.configure(state="disabled")
        self.progress.start(12)
        self._set_status("Calculando…")
        self._clear_outputs()
        if self.plot_panel is not None:
            self.plot_panel.show_waiting()
        self.update_idletasks()

        def work() -> None:
            try:
                result = solve(equation, timeout=timeout, **values)
                self._queue.put(result)
            except TimeoutError as exc:
                self._queue.put(exc)
            except Exception as exc:  # pragma: no cover - defensa de la UI
                self._queue.put(exc)

        threading.Thread(target=work, daemon=True).start()

    def _confirmar_continuacion(self, mensaje: str) -> bool:
        """Pregunta al usuario si desea continuar tras un tiempo agotado."""

        dialog = tk.Toplevel(self)
        dialog.title("Tiempo límite alcanzado")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg=SURFACE)
        dialog.columnconfigure(0, weight=1)

        tarjeta = ttk.Frame(dialog, style="Card.TFrame", padding=18)
        tarjeta.grid(row=0, column=0, sticky="ew")
        tarjeta.columnconfigure(0, weight=1)

        ttk.Label(
            tarjeta,
            text=mensaje,
            style="Card.TLabel",
            wraplength=440,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            tarjeta,
            text="¿Continuar el cálculo con más tiempo o cancelar la operación?",
            style="CardTitle.TLabel",
            wraplength=440,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(14, 0))

        botones = ttk.Frame(tarjeta, style="Card.TFrame")
        botones.grid(row=2, column=0, sticky="e", pady=(18, 0))

        respuesta = {"continuar": False}

        def continuar() -> None:
            respuesta["continuar"] = True
            dialog.destroy()

        def cancelar() -> None:
            dialog.destroy()

        ttk.Button(
            botones,
            text="Continuar cálculo",
            style="Accent.TButton",
            command=continuar,
        ).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(
            botones,
            text="Cancelar",
            style="Ghost.TButton",
            command=cancelar,
        ).grid(row=0, column=0)

        dialog.protocol("WM_DELETE_WINDOW", cancelar)
        dialog.bind("<Escape>", lambda _event: cancelar())
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()
        dialog.focus_set()
        self.wait_window(dialog)
        return respuesta["continuar"]

    def _continuar_tras_timeout(self, payload: TimeoutError) -> bool:
        """Ofrece un único reintento con un plazo ampliado."""

        if self._ultima_solicitud is None or self._reintentos_por_solicitud >= 1:
            return False
        mensaje = f"No se puede graficar: {type(payload).__name__}: {payload}"
        if not self._confirmar_continuacion(mensaje):
            return False
        self._reintentos_por_solicitud += 1
        self._launch_solve(90.0)
        return True

    # ------------------------------------------------------------- polling
    def _schedule_poll(self) -> None:
        self._poll_id = self.after(100, self._poll)

    def _poll(self) -> None:
        try:
            payload = self._queue.get_nowait()
        except queue.Empty:
            self._schedule_poll()
            return

        if isinstance(payload, TimeoutError) and self._continuar_tras_timeout(payload):
            self._schedule_poll()
            return

        self._busy = False
        self.progress.stop()
        self.solve_button.configure(state="normal")

        if isinstance(payload, Exception):
            self._set_status("Error", "error")
            self._set_text(self.summary, f"{type(payload).__name__}: {payload}")
            if self.plot_panel is not None:
                self.plot_panel.show_error(f"{type(payload).__name__}: {payload}")
            self._schedule_poll()
            return

        result = payload
        self._ultimo_resultado = result
        if result.error:
            self._set_status("Sin solución", "error")
        elif result.verification is not None and result.verification.status == "ok":
            self._set_status("Solución verificada (residuo 0).", "ok")
        else:
            self._set_status("Resultado con advertencias.", "warning")

        self._vista.set("Salida")
        self._render_resultado_completo(result)

        self._update_kpis(result)
        if self.plot_panel is not None:
            self.plot_panel.show_result(
                result,
                x_min=self._plot_bounds[0],
                x_max=self._plot_bounds[1],
            )
        self._schedule_poll()

    def _update_kpis(self, result: Any) -> None:
        method = getattr(result, "chosen_method", None) or "—"
        self.kpi_method.configure(text=str(method)[:18], fg=ACCENT if method != "—" else INK_SOFT)

        verification = getattr(result, "verification", None)
        if getattr(result, "error", None):
            self.kpi_verification.configure(text="revisar", fg=ROSE)
        elif verification is not None and verification.status == "ok":
            self.kpi_verification.configure(text="residuo 0", fg=OK)
        elif verification is not None:
            self.kpi_verification.configure(text=verification.status, fg=AMBER)
        else:
            self.kpi_verification.configure(text="—", fg=INK_SOFT)

        timing = getattr(result, "timing_ms", None)
        if isinstance(timing, dict):
            timing = timing.get("total")
        if timing is None and self._started_at is not None:
            timing = (time.monotonic() - self._started_at) * 1000
        if isinstance(timing, (int, float)):
            self.kpi_time.configure(text=f"{float(timing):.0f} ms", fg=INK_SOFT)
        else:
            self.kpi_time.configure(text="—", fg=INK_SOFT)

    # ------------------------------------------------------------- lifecycle
    def destroy(self) -> None:
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:  # pragma: no cover - ventana ya destruida
                pass
            self._poll_id = None
        if self._preview_after_id is not None:
            try:
                self.after_cancel(self._preview_after_id)
            except tk.TclError:  # pragma: no cover - ventana ya destruida
                pass
            self._preview_after_id = None
        super().destroy()


def _renderizar_png_latex(
    latex: str,
    *,
    color: str = INK_SOFT,
    fontsize: int = 11,
    dpi: int = 115,
) -> bytes:
    """Genera los bytes PNG de una fórmula LaTeX adaptada a ``mathtext``."""

    if Figure is None:
        raise RuntimeError("Matplotlib no está disponible")
    adaptado = adaptar_latex_mathtext(latex)
    if not adaptado:
        raise ValueError("Fórmula LaTeX vacía")
    figura = Figure(figsize=(0.02, 0.02), dpi=dpi)
    figura.patch.set_alpha(0)
    figura.text(
        0,
        0,
        f"${adaptado}$",
        fontsize=fontsize,
        color=color,
        va="bottom",
    )
    buffer = io.BytesIO()
    figura.savefig(
        buffer,
        format="png",
        transparent=True,
        bbox_inches="tight",
        pad_inches=0.03,
    )
    return buffer.getvalue()


def main() -> None:
    app = ODEApp()
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["ODEApp", "_etiqueta_metodo", "_renderizar_png_latex", "main"]
