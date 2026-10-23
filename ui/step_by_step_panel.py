"""Panel con el procedimiento paso a paso y expresiones tipográficas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from math_engine.step_generator import SolutionStep


def _sanitize_latex(latex_str: str) -> str:
    """Adapta comandos LaTeX no soportados por ``mathtext``."""

    return (
        latex_str.replace(r"\Rightarrow", r"\rightarrow")
        .replace(r"\implies", r"\rightarrow")
        .replace(r"\dfrac", r"\frac")
        .replace(r"\left", "")
        .replace(r"\right", "")
    )


class StepByStepPanel(ttk.Frame):
    """Muestra los pasos con figuras Matplotlib embebidas en un ``tk.Text``."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.text = tk.Text(
            container,
            wrap="word",
            height=16,
            state="disabled",
            padx=10,
            pady=8,
            font=("DejaVu Sans", 11),
            relief="flat",
        )
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        self.text.tag_configure("step_title", font=("DejaVu Sans", 11, "bold"))
        self.text.tag_configure("justification", foreground="#444444")
        self.text.tag_configure("detail", foreground="#666666", font=("DejaVu Sans", 10, "italic"))

        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=(4, 0))
        self.copy_button = ttk.Button(
            footer,
            text="Copiar pasos",
            command=self.copy_to_clipboard,
        )
        self.copy_button.pack(side="right")

        self._embedded: list[tuple[FigureCanvasTkAgg, tk.Widget]] = []
        self._ascii_text = ""
        self._show_message(
            "Resuelve una EDO para ver aquí el procedimiento paso a paso."
        )

    def _show_message(self, message: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", message)
        self.text.configure(state="disabled")

    def _add_math(self, latex_str: str) -> None:
        figure = Figure(figsize=(5.2, 0.7), dpi=100)
        axes = figure.add_subplot(111)
        axes.set_axis_off()

        display = latex_str.strip()
        if not display.startswith("$"):
            display = f"${_sanitize_latex(display)}$"

        axes.text(
            0.02,
            0.5,
            display,
            ha="left",
            va="center",
            fontsize=14,
            transform=axes.transAxes,
        )

        canvas = FigureCanvasTkAgg(figure, master=self.text)
        widget = canvas.get_tk_widget()
        try:
            canvas.draw()
        except Exception:
            widget.destroy()
            self.text.insert("end", f"{latex_str}\n")
            return

        self.text.window_create("end", window=widget, padx=8, pady=3)
        self.text.insert("end", "\n")
        self._embedded.append((canvas, widget))

    def display_steps(
        self,
        steps: list[SolutionStep],
        ascii_text: str | None = None,
    ) -> None:
        """Renderiza la lista de pasos y prepara el texto ASCII para copiar."""

        self.clear()
        if ascii_text is None:
            ascii_text = self._build_ascii(steps)
        self._ascii_text = ascii_text

        self.text.configure(state="normal")
        if not steps:
            self.text.insert("end", "No hay pasos para mostrar.")
            self.text.configure(state="disabled")
            return

        for step in steps:
            self.text.insert(
                "end",
                f"Paso {step.number}: {step.operation}\n",
                "step_title",
            )
            self._add_math(step.latex_expr)
            self.text.insert("end", f"{step.justification}\n", "justification")
            if step.detail:
                self.text.insert("end", f"{step.detail}\n", "detail")
            self.text.insert("end", "\n")

        self.text.configure(state="disabled")

    @staticmethod
    def _build_ascii(steps: list[SolutionStep]) -> str:
        lines: list[str] = []
        for step in steps:
            lines.append(f"Paso {step.number}: {step.operation}")
            lines.append(f"  {step.ascii_expr or step.latex_expr}")
            lines.append(f"  Justificación: {step.justification}")
            if step.detail:
                lines.append(f"  Detalle: {step.detail}")
            lines.append("")
        return "\n".join(lines).strip()

    def clear(self) -> None:
        for _canvas, widget in self._embedded:
            widget.destroy()
        self._embedded.clear()
        self._ascii_text = ""

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def copy_to_clipboard(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._ascii_text)

    @property
    def ascii_text(self) -> str:
        return self._ascii_text


__all__ = ["StepByStepPanel"]
