"""Biblioteca de ejercicios predefinidos."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from data.exercises import Exercise, load_exercises


class ExerciseLibrary(ttk.Frame):
    """Lista de ejercicios con selección y copiado de la ecuación."""

    def __init__(
        self,
        master: tk.Misc | None = None,
        exercises: list[Exercise] | None = None,
        on_select: Callable[[Exercise], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_select = on_select
        self._exercises = exercises if exercises is not None else load_exercises()
        self._by_id = {exercise.id: exercise for exercise in self._exercises}

        self.tree = ttk.Treeview(
            self,
            columns=("type", "equation", "description"),
            show="headings",
            height=10,
            selectmode="browse",
        )
        self.tree.heading("type", text="Tipo")
        self.tree.heading("equation", text="Ecuación")
        self.tree.heading("description", text="Descripción")
        self.tree.column("type", width=90, stretch=False)
        self.tree.column("equation", width=210, stretch=True)
        self.tree.column("description", width=260, stretch=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        for exercise in self._exercises:
            self.tree.insert(
                "",
                "end",
                iid=exercise.id,
                values=(
                    exercise.ode_type,
                    exercise.latex_str.strip("$"),
                    exercise.description,
                ),
            )

        self.tree.bind("<<TreeviewSelect>>", self._on_selection)

        self.copy_button = ttk.Button(
            self,
            text="Copiar ecuación",
            command=self.copy_selected_equation,
        )
        self.copy_button.pack(side="bottom", anchor="e", pady=(4, 0))

    def _on_selection(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        exercise = self._by_id.get(selection[0])
        if exercise is not None and self.on_select is not None:
            self.on_select(exercise)

    def selected_exercise(self) -> Exercise | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._by_id.get(selection[0])

    def select_exercise(self, exercise_id: str) -> None:
        if exercise_id in self._by_id:
            self.tree.selection_set(exercise_id)
            self.tree.focus(exercise_id)
            self.tree.see(exercise_id)

    def copy_selected_equation(self) -> bool:
        exercise = self.selected_exercise()
        if exercise is None:
            return False
        self.clipboard_clear()
        self.clipboard_append(exercise.equation_text)
        return True


__all__ = ["ExerciseLibrary"]
