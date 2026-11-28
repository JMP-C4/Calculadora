"""Ejecución de cálculos con tiempo límite real (proceso separado).

Los hilos no pueden interrumpir de forma segura una llamada a SymPy.  Para
garantizar que la interfaz nunca se bloquee, ``run_with_timeout`` ejecuta el
trabajo en un proceso hijo y lo termina si excede el presupuesto.
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import threading
from typing import Any, Callable

_CTX_LOCK = threading.Lock()
_FORKSERVER_PRELOADED = False


def _mp_context() -> mp.context.BaseContext:
    """Selecciona un contexto seguro sin ``fork`` desde procesos multi-hilo."""

    global _FORKSERVER_PRELOADED
    methods = mp.get_all_start_methods()
    if "forkserver" in methods:
        context = mp.get_context("forkserver")
        with _CTX_LOCK:
            if not _FORKSERVER_PRELOADED:
                try:
                    context.set_forkserver_preload(["odecalc.api"])
                except Exception:  # pragma: no cover - si el servidor ya arrancó
                    pass
                _FORKSERVER_PRELOADED = True
        return context
    if "spawn" in methods:  # pragma: no cover - Windows/macOS
        return mp.get_context("spawn")
    return mp.get_context()  # pragma: no cover


class TimeoutError(RuntimeError):
    """El cálculo excedió el tiempo límite configurado."""


def _worker(func: Callable[..., Any], args: tuple, kwargs: dict, output_queue) -> None:
    try:
        output_queue.put(("ok", func(*args, **kwargs)))
    except BaseException as exc:  # pragma: no cover - se propaga al padre
        output_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def run_with_timeout(
    func: Callable[..., Any],
    *args: Any,
    timeout: float,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """Ejecuta ``func`` en un proceso hijo y devuelve su resultado."""

    if timeout <= 0:
        raise ValueError("El tiempo límite debe ser positivo.")

    kwargs = kwargs or {}
    context = _mp_context()
    output_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_worker,
        args=(func, args, kwargs, output_queue),
        daemon=True,
    )
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(1.0)
        if process.is_alive():  # pragma: no cover
            process.kill()
            process.join(1.0)
        output_queue.close()
        raise TimeoutError(
            f"El cálculo excedió el tiempo límite de {timeout:g} s. "
            "Se recomienda simplificar la ecuación o usar el respaldo numérico."
        )

    try:
        status, payload = output_queue.get_nowait()
    except queue.Empty:
        output_queue.close()
        raise TimeoutError(
            "El proceso de cálculo terminó sin devolver un resultado."
        ) from None
    output_queue.close()

    if status == "error":
        raise RuntimeError(payload)
    return payload


__all__ = ["TimeoutError", "run_with_timeout"]
