"""ODE Calculator: controlador principal e integración de la interfaz."""

from __future__ import annotations

import importlib
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

from data.exercises import Exercise, load_exercises
from math_engine.numeric_solver import NumericResult, solve_numeric
from math_engine.parser import ParseResult, parse_ode
from math_engine.symbolic_solver import SymbolicResult, solve_symbolic
from ui.condition_panel import ConditionPanel, SolverConditions
from ui.equation_input import SHORTCUTS, EquationInput
from ui.exercise_library import ExerciseLibrary
from ui.math_preview import MathPreview
from ui.plot_view import PlotMode, PlotView
from ui.status_bar import StatusBar
from ui.step_by_step_panel import StepByStepPanel
from ui.symbol_toolbar import SymbolToolbar


@dataclass
class AppState:
    """Estado compartido de una sesión de trabajo."""

    current_equation_text: str = ""
    last_parse_result: ParseResult | None = None
    symbolic_result: SymbolicResult | None = None
    numeric_result: NumericResult | None = None
    conditions: SolverConditions | None = None
    plot_mode: PlotMode = PlotMode.SOLUTION
    step_by_step_visible: bool = True


class App(tk.Tk):
    """Ventana principal de la calculadora."""

    def __init__(self) -> None:
        super().__init__()
        self.title("ODE Calculator — Ecuaciones diferenciales de primer orden")
        self.geometry("1280x820")
        self.minsize(1024, 768)

        self.state = AppState()
        self._busy = False
        self._result_queue: queue.Queue = queue.Queue()

        self._configure_styles()
        self._build_layout()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.after(100, self.equation_input.focus_input)
        self.after(50, self._poll_results)

    # ------------------------------------------------------------------ UI
    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        base_font = ("DejaVu Sans", 10)
        style.configure(".", font=base_font)
        style.configure("TButton", padding=(8, 5), font=base_font)
        style.configure("Accent.TButton", font=("DejaVu Sans", 10, "bold"))
        style.configure("Title.TLabel", font=("DejaVu Sans", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#5f6368")
        style.configure("TLabelframe.Label", font=("DejaVu Sans", 10, "bold"))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.PanedWindow(self, orient="horizontal")
        main.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        left = ttk.Frame(main, padding=6)
        right = ttk.Frame(main, padding=6)
        main.add(left, weight=0)
        main.add(right, weight=1)
        self._main_pane = main

        ttk.Label(left, text="ODE Calculator", style="Title.TLabel").pack(
            anchor="w", pady=(0, 2)
        )
        ttk.Label(
            left,
            text="Ecuaciones diferenciales de primer orden",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.equation_input = EquationInput(left, on_change=self._on_equation_changed)
        self.equation_input.pack(fill="x", pady=(0, 6))

        self.symbol_toolbar = SymbolToolbar(left, self.equation_input)
        self.symbol_toolbar.pack(fill="x", pady=(0, 8))

        self.condition_panel = ConditionPanel(left)
        self.condition_panel.pack(fill="x", pady=(0, 8))

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(0, 8))
        self.symbolic_button = ttk.Button(
            actions,
            text="Resolver simbólico",
            style="Accent.TButton",
            command=self._on_solve_symbolic,
        )
        self.symbolic_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.numeric_button = ttk.Button(
            actions,
            text="Resolver numérico",
            command=self._on_solve_numeric,
        )
        self.numeric_button.pack(side="left", fill="x", expand=True)

        ttk.Label(left, text="Biblioteca de ejercicios", style="TLabelframe.Label").pack(
            anchor="w", pady=(4, 2)
        )
        self.exercise_library = ExerciseLibrary(
            left,
            exercises=load_exercises(),
            on_select=self._on_exercise_selected,
        )
        self.exercise_library.pack(fill="both", expand=True)

        self.math_preview = MathPreview(right)
        self.math_preview.pack(fill="x", pady=(0, 6))

        vertical = ttk.PanedWindow(right, orient="vertical")
        vertical.pack(fill="both", expand=True)

        self.step_panel = StepByStepPanel(vertical)
        self.plot_view = PlotView(vertical)
        vertical.add(self.step_panel, weight=1)
        vertical.add(self.plot_view, weight=2)
        self._vertical_pane = vertical

        self.plot_view.on_mode_change = self._on_mode_changed
        self.state.plot_mode = self.plot_view.current_mode

        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))
        self.status_bar.set_status("Listo. Escribe una EDO o elige un ejercicio.")
        self.plot_view.on_export_status = self.status_bar.set_status

    # -------------------------------------------------------------- helpers
    def _poll_results(self) -> None:
        try:
            while True:
                callback = self._result_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(50, self._poll_results)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.symbolic_button.configure(state=state)
        self.numeric_button.configure(state=state)
        if busy:
            self.status_bar.set_status(message or "Procesando…")
            self.status_bar.show_spinner()
        else:
            self.status_bar.hide_spinner()

    def _conditions(self) -> SolverConditions:
        return self.condition_panel.get_conditions()

    def _parsed_rhs(self):
        result = self.state.last_parse_result
        if result is None or result.rhs is None or result.error is not None:
            return None
        return result.rhs

    def _refresh_plot(self) -> None:
        rhs = self._parsed_rhs()
        if rhs is None:
            return
        conditions = self._conditions()
        mode = self.state.plot_mode

        if mode == PlotMode.SOLUTION:
            self.plot_view.plot_solution(
                self.state.symbolic_result,
                self.state.numeric_result,
                conditions,
            )
        elif mode == PlotMode.DIRECTION_FIELD:
            self.plot_view.plot_direction_field(
                rhs,
                conditions,
                solution_curve=self.state.numeric_result,
            )
        else:
            self.plot_view.plot_surface_3d(rhs, conditions)

    # ---------------------------------------------------------- callbacks
    def _on_equation_changed(self, text: str) -> None:
        self.state.current_equation_text = text
        self.state.symbolic_result = None
        self.state.numeric_result = None
        conditions = self._conditions()

        if not text.strip():
            self.state.last_parse_result = None
            self.math_preview.show_placeholder()
            self.step_panel.clear()
            self.status_bar.set_status(
                "Escribe una EDO de primer orden, por ejemplo: dy/dx = x + y"
            )
            return

        result = parse_ode(text)
        self.state.last_parse_result = result
        if result.error is not None:
            self.math_preview.show_placeholder()
            self.status_bar.set_status(result.error, "error")
            return

        self.math_preview.render(result.latex_str, conditions)
        self.status_bar.set_status("Ecuación válida. Elige un método de resolución.")

    def _on_exercise_selected(self, exercise: Exercise) -> None:
        self.equation_input.set_text(exercise.equation_text)
        if exercise.initial_conditions is not None:
            self.condition_panel.set_conditions(exercise.initial_conditions)
            result = self.state.last_parse_result
            if result is not None and result.rhs is not None:
                self.math_preview.render(result.latex_str, self._conditions())
        self.status_bar.set_status(f"Ejercicio cargado: {exercise.name}")

    def _on_solve_symbolic(self) -> None:
        if self._busy:
            return
        result = parse_ode(self.state.current_equation_text)
        self.state.last_parse_result = result
        if result.error is not None or result.rhs is None:
            self.status_bar.set_status(result.error or "Ecuación inválida.", "error")
            return

        rhs = result.rhs
        conditions = self._conditions()
        self.state.conditions = conditions
        self._set_busy(True, "Resolviendo simbólicamente…")

        def worker() -> None:
            try:
                symbolic = solve_symbolic(rhs, conditions)
            except Exception as exc:  # pragma: no cover - defensa adicional
                symbolic = SymbolicResult(
                    general_solution=None,
                    particular_solution=None,
                    latex_general="",
                    latex_particular="",
                    error=f"Error inesperado del solver simbólico: {exc}",
                    ode_type=None,
                    step_by_step=None,
                )
            self._result_queue.put(lambda: self._on_symbolic_done(symbolic))

        threading.Thread(target=worker, daemon=True).start()

    def _on_symbolic_done(self, symbolic: SymbolicResult) -> None:
        self._set_busy(False)
        self.state.symbolic_result = symbolic

        if symbolic.error is not None:
            self.status_bar.set_status(symbolic.error, "error")
            if symbolic.step_by_step is not None:
                self.step_panel.display_steps(
                    symbolic.step_by_step.steps,
                    symbolic.step_by_step.ascii_text,
                )
            self._on_solve_numeric()
            return

        conditions = self._conditions()
        latex = symbolic.latex_particular or symbolic.latex_general
        if latex:
            self.math_preview.render(latex, conditions)
        if symbolic.step_by_step is not None:
            self.step_panel.display_steps(
                symbolic.step_by_step.steps,
                symbolic.step_by_step.ascii_text,
            )
        self._refresh_plot()
        kind = symbolic.ode_type or "desconocido"
        self.status_bar.set_status(f"Solución simbólica encontrada (EDO {kind}).")

    def _on_solve_numeric(self) -> None:
        if self._busy:
            return
        result = parse_ode(self.state.current_equation_text)
        self.state.last_parse_result = result
        if result.error is not None or result.rhs is None:
            self.status_bar.set_status(result.error or "Ecuación inválida.", "error")
            return

        conditions = self._conditions()
        if conditions.x0 is None or conditions.y0 is None:
            self.status_bar.set_status(
                "Ingresa x₀ y y₀ para la solución numérica.", "error"
            )
            return
        if conditions.x_min >= conditions.x_max:
            self.status_bar.set_status(
                "El intervalo no es válido: x mín debe ser menor que x máx.", "error"
            )
            return

        rhs = result.rhs
        self.state.conditions = conditions
        self._set_busy(True, "Integrando numéricamente…")

        def worker() -> None:
            numeric = solve_numeric(rhs, conditions)
            self._result_queue.put(lambda: self._on_numeric_done(numeric))

        threading.Thread(target=worker, daemon=True).start()

    def _on_numeric_done(self, numeric: NumericResult) -> None:
        self._set_busy(False)
        self.state.numeric_result = numeric

        if not numeric.success:
            self.status_bar.set_status(numeric.message, "error")
            return

        self._refresh_plot()
        self.status_bar.set_status(numeric.message)

    def _on_mode_changed(self, mode: PlotMode) -> None:
        self.state.plot_mode = mode
        self._refresh_plot()

    def _insert_global(self, token: str, cursor_inside: bool) -> None:
        self.equation_input.focus_input()
        self.equation_input.insert_token(token, place_cursor_inside=cursor_inside)

    def _bind_shortcuts(self) -> None:
        for sequence, (token, cursor_inside) in SHORTCUTS.items():
            self.bind_all(
                sequence,
                lambda _event, t=token, inside=cursor_inside: (
                    self._insert_global(t, inside),
                    "break",
                )[1],
            )

    # ------------------------------------------------------------- lifecycle
    def _wait_idle(self, timeout: float = 0.0) -> None:
        """Procesa eventos pendientes (útil para tests y scripts)."""

        del timeout
        self.update()


def _check_dependencies() -> list[str]:
    missing: list[str] = []
    for module in ("sympy", "scipy", "matplotlib", "numpy"):
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    return missing


def main() -> None:
    missing = _check_dependencies()
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Dependencias faltantes",
            "Faltan las siguientes dependencias: "
            + ", ".join(missing)
            + ".\n\nInstálalas con:\n  pip install -r requirements.txt",
        )
        root.destroy()
        return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()


__all__ = ["App", "AppState", "main"]
