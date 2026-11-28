"""Servidor HTTP sin dependencias externas para la calculadora de EDOs.

Uso::

    python -m apps.web.server --port 8000

Expone ``POST /solve`` con un cuerpo JSON::

    {"equation": "y' = x + y", "x0": 0, "y0": 1, "x_min": 0, "x_max": 1}

y ``POST /plot`` con el mismo cuerpo más ``"mode"`` (una de las claves de
``apps.web.plotting.PLOT_MODES``) para obtener los datos de una gráfica.

La lógica matemática vive exclusivamente en ``odecalc.api.solve``; este
archivo sólo valida tamaño/tiempo y serializa la respuesta.
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from odecalc.api import solve
from odecalc.models import SolveResult
from odecalc.serialization import result_to_dict
from odecalc.timeout import TimeoutError

from apps.web.plotting import PLOT_MODES, build_plot

MAX_REQUEST_BYTES = 16_384
DEFAULT_TIMEOUT = 20.0
MAX_TIMEOUT = 60.0
RATE_LIMIT = 30
RATE_WINDOW = 60.0

_STATIC = Path(__file__).with_name("static")
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _validated(payload: dict[str, Any]) -> dict[str, Any]:
    """Valida y normaliza un payload de resolución."""

    if not isinstance(payload, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    equation = payload.get("equation")
    if not isinstance(equation, str) or not equation.strip():
        raise ValueError("Falta el campo 'equation'.")
    if len(equation) > 2000:
        raise ValueError("La ecuación es demasiado larga (máximo 2000 caracteres).")

    def optional_float(name: str) -> float | None:
        value = payload.get(name)
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"El campo '{name}' debe ser numérico.") from exc
        if not math.isfinite(number):
            raise ValueError(f"El campo '{name}' debe ser un número finito.")
        return number

    x0 = optional_float("x0")
    y0 = optional_float("y0")
    x_min_value = optional_float("x_min")
    x_max_value = optional_float("x_max")
    timeout_value = optional_float("timeout")
    x_min = -5.0 if x_min_value is None else x_min_value
    x_max = 5.0 if x_max_value is None else x_max_value
    if x_min >= x_max:
        raise ValueError("El intervalo no es válido: x_min debe ser menor que x_max.")
    timeout = min(
        max(DEFAULT_TIMEOUT if timeout_value is None else timeout_value, 0.1),
        MAX_TIMEOUT,
    )

    if (x0 is None) != (y0 is None):
        raise ValueError("x0 e y0 deben indicarse juntos.")

    return {
        "equation": equation,
        "x0": x0,
        "y0": y0,
        "x_min": x_min,
        "x_max": x_max,
        "timeout": timeout,
    }


def _solve_values(values: dict[str, Any]) -> SolveResult:
    return solve(
        values["equation"],
        x0=values["x0"],
        y0=values["y0"],
        x_min=values["x_min"],
        x_max=values["x_max"],
        timeout=values["timeout"],
    )


def solve_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Valida un payload y resuelve la EDO devolviendo un diccionario."""

    return result_to_dict(_solve_values(_validated(payload)))


def plot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Resuelve la EDO y devuelve los datos de la gráfica solicitada.

    El campo ``mode`` es obligatorio y debe ser una de las claves de
    ``PLOT_MODES``.  La respuesta incluye ``available``/``notice`` para que
    el cliente muestre un aviso cuando la gráfica no sea posible.
    """

    values = _validated(payload)
    mode = payload.get("mode", "solution")
    if not isinstance(mode, str) or mode not in PLOT_MODES:
        raise ValueError(
            "Modo de gráfica inválido. Usa uno de: "
            + ", ".join(sorted(PLOT_MODES))
            + "."
        )
    result = _solve_values(values)
    return build_plot(
        result,
        mode,
        x_min=values["x_min"],
        x_max=values["x_max"],
    )


class _RateLimiter:
    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW) -> None:
        self.limit = limit
        self.window = window
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._events) > 1024:
                stale = [
                    k for k, q in self._events.items() if not q or now - q[-1] > self.window
                ]
                for k in stale:
                    del self._events[k]
            events = self._events[key]
            while events and now - events[0] > self.window:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


_LIMITER = _RateLimiter()


class ODEHandler(BaseHTTPRequestHandler):
    server_version = "ODECalculator/2.0"

    def log_message(self, format: str, *args: object) -> None:  # pragma: no cover
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Recurso no encontrado."})
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, route: str) -> bool:
        """Sirve un archivo de ``static`` sin permitir rutas fuera de él."""

        relative = route.removeprefix("/static/").strip("/")
        if not relative:
            return False
        candidate = (_STATIC / relative).resolve()
        try:
            candidate.relative_to(_STATIC.resolve())
        except ValueError:
            return False
        content_type = _CONTENT_TYPES.get(candidate.suffix.lower())
        if content_type is None:
            return False
        self._send_file(candidate, content_type)
        return True

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route in ("/", "/index.html"):
            self._send_file(_STATIC / "index.html", "text/html; charset=utf-8")
            return
        if route.startswith("/static/"):
            if self._send_static(route):
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Recurso no encontrado."})
            return
        if route == "/favicon.ico":
            self._send_json(HTTPStatus.NO_CONTENT, {})
            return
        if route == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        handlers = {"/solve": solve_payload, "/plot": plot_payload}
        handler = handlers.get(route)
        if handler is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
            return
        client = self.client_address[0]
        if not _LIMITER.allow(client):
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "Demasiadas solicitudes; inténtalo más tarde."},
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Cuerpo vacío."},
            )
            return
        if length > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "Cuerpo demasiado grande."},
            )
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            response = handler(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON inválido."})
            return
        except TimeoutError as exc:
            self._send_json(HTTPStatus.GATEWAY_TIMEOUT, {"error": str(exc)})
            return
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - protección del servidor
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Error interno: {type(exc).__name__}"},
            )
            return
        self._send_json(HTTPStatus.OK, response)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), ODEHandler)
    print(f"ODE Calculator escuchando en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web de ODE Calculator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    serve(arguments.host, arguments.port)


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["solve_payload", "plot_payload", "serve", "ODEHandler", "main"]
