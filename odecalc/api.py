"""API pública del motor ``odecalc``.

Uso típico::

    from odecalc.api import solve
    resultado = solve("dy/dx = x + y", x0=0, y0=1)

La misma función alimenta la interfaz de escritorio, la web y los scripts.
"""

from __future__ import annotations

import time

import numpy as np
import sympy as sp

from odecalc.classify import classify
from odecalc.methods import solve_method, solve_with_dsolve
from odecalc.models import Attempt, Match, ParsedODE, SolveResult, Step
from odecalc.numeric import solve_numeric
from odecalc.parsing import parse_ode
from odecalc.timeout import TimeoutError, run_with_timeout
from odecalc.verify import apply_initial_conditions, verify_solution
from odecalc.verify.validity import analyze_validity
from odecalc.symbols import X, Y, lambdify_modules


def _numeric_steps(result: SolveResult) -> list[Step]:
    numeric = result.numeric
    if numeric is None:
        return []
    status = "exitosa" if numeric.success else "fallida"
    eq_latex = (result.input_latex or "").strip()
    if not eq_latex and result.standard_form:
        parsed_std = parse_ode(result.standard_form)
        eq_latex = parsed_std.latex_str or result.standard_form
    if not eq_latex:
        eq_latex = r"\frac{dy}{dx} = f(x, y)"
    steps = [
        Step(
            number=1,
            title="Respaldo numérico",
            latex=eq_latex,
            explanation=(
                "No se obtuvo una solución simbólica verificable; se integra "
                "la EDO numéricamente con SciPy."
            ),
            ascii=f"Solución numérica {status}: {numeric.message}",
        ),
        Step(
            number=2,
            title="Método y tolerancias",
            latex=rf"\mathrm{{Método:\ {numeric.method or 'auto'}}}",
            explanation=(
                "Se usan integradores adaptativos con tolerancias estrictas y "
                "cambio automático a un método implícito si se detecta rigidez."
            ),
            ascii=numeric.message,
        ),
    ]
    if numeric.success and numeric.interval is not None:
        steps.append(
            Step(
                number=3,
                title="Intervalo integrado",
                latex=(
                    rf"x \in [{numeric.interval[0]:.6g}, "
                    rf"{numeric.interval[1]:.6g}]"
                ),
                explanation=(
                    "La curva numérica cubre el intervalo donde el integrador "
                    "encontró una solución finita."
                ),
                ascii=f"x in [{numeric.interval[0]:.6g}, {numeric.interval[1]:.6g}]",
            )
        )
    if numeric.blow_up:
        steps.append(
            Step(
                number=len(steps) + 1,
                title="Posible explosión en tiempo finito",
                latex=r"\text{blow-up}",
                explanation=(
                    "El integrador se detuvo antes de cubrir todo el intervalo; "
                    "la solución puede tender a infinito en un punto finito."
                ),
                ascii="Posible blow-up detectado.",
            )
        )
    return steps


def _compare_numeric(result: SolveResult) -> None:
    numeric = result.numeric
    solution = result.particular
    if numeric is None or not numeric.success or solution is None or not solution.is_explicit:
        return
    if numeric.x_arr is None or numeric.y_arr is None:
        return
    try:
        function = sp.lambdify(X, solution.expr, modules=lambdify_modules())
        with np.errstate(all="ignore"):
            expected = function(numeric.x_arr)
        expected = np.asarray(expected, dtype=complex)
        actual = np.asarray(numeric.y_arr, dtype=complex)
        mask = (
            np.isfinite(expected.real)
            & np.isfinite(actual.real)
            & (np.abs(expected.imag) <= 1e-8)
        )
        if not np.any(mask):
            return
        error = float(np.max(np.abs(expected[mask].real - actual[mask].real)))
    except Exception:
        return
    numeric.error_estimate = error
    if error > 1e-3 * max(1.0, float(np.max(np.abs(numeric.y_arr)))):
        result.warnings.append(
            "La solución simbólica y la numérica difieren; revisa el dominio o "
            "la rama de la solución."
        )


def _solve_symbolic(
    equation: str,
    parsed: ParsedODE,
    x0: float | None,
    y0: float | None,
    method: str | None,
) -> tuple[SolveResult, bool]:
    result = SolveResult(
        input_text=equation,
        input_latex=parsed.latex_str or equation,
        standard_form=parsed.standard_form,
    )

    classify_start = time.perf_counter()
    matches = classify(parsed)
    result.classifications = matches
    result.timing_ms["classify"] = (time.perf_counter() - classify_start) * 1000

    candidates = matches
    if method is not None:
        candidates = [item for item in matches if item.method == method]
        if not candidates:
            result.warnings.append(
                f"El método solicitado ({method}) no figura entre los métodos "
                "aplicables; se intentarán los demás."
            )
            candidates = matches

    chosen = None
    for match in candidates:
        attempt_start = time.perf_counter()
        try:
            solution, steps, singular = solve_method(match.method, parsed, match)
        except Exception as exc:
            result.attempts.append(
                Attempt(
                    method=match.method,
                    success=False,
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
            result.warnings.append(
                f"El método {match.name} no produjo una solución utilizable: {exc}"
            )
            continue

        verification = verify_solution(
            solution,
            rhs=parsed.rhs,
            original_F=parsed.F,
            x0=x0,
        )
        result.attempts.append(
            Attempt(
                method=match.method,
                success=verification.status == "ok",
                verification_status=verification.status,
                message=verification.message,
            )
        )
        result.timing_ms[f"method:{match.method}"] = (
            time.perf_counter() - attempt_start
        ) * 1000

        if verification.status == "ok":
            chosen = (match, solution, steps, singular, verification)
            break
        result.warnings.append(
            f"El método {match.name} produjo una solución que no superó la "
            f"verificación: {verification.message}"
        )

    if chosen is None:
        fallback_start = time.perf_counter()
        try:
            solution, steps, singular = solve_with_dsolve(parsed)
            verification = verify_solution(
                solution,
                rhs=parsed.rhs,
                original_F=parsed.F,
                x0=x0,
            )
            result.attempts.append(
                Attempt(
                    method="dsolve",
                    success=verification.status == "ok",
                    verification_status=verification.status,
                    message=verification.message,
                )
            )
            if verification.status == "ok":
                match = Match(
                    method="dsolve",
                    name="Respaldo SymPy (dsolve)",
                    evidence="Solución obtenida por el resolvedor general de SymPy.",
                    priority=999,
                )
                chosen = (match, solution, steps, singular, verification)
                result.warnings.append(
                    "La solución se obtuvo con dsolve (respaldo), no con un "
                    "método propio; fue verificada antes de presentarse."
                )
            else:
                result.warnings.append(
                    "El respaldo dsolve no superó la verificación: "
                    + verification.message
                )
        except Exception as exc:
            result.attempts.append(
                Attempt(method="dsolve", success=False, message=str(exc))
            )
            result.warnings.append(f"El respaldo dsolve no fue aplicable: {exc}")
        result.timing_ms["dsolve"] = (time.perf_counter() - fallback_start) * 1000

    if chosen is not None:
        match, solution, steps, singular, verification = chosen
        result.chosen_method = match.method
        result.general = solution
        result.steps = steps
        result.singular_solutions = singular
        result.verification = verification

        if x0 is not None and y0 is not None:
            particular, warnings = apply_initial_conditions(
                solution,
                float(x0),
                float(y0),
                rhs=parsed.rhs,
                original_F=parsed.F,
            )
            if particular is None and singular:
                for candidate in singular:
                    sing_part, sing_warnings = apply_initial_conditions(
                        candidate,
                        float(x0),
                        float(y0),
                        rhs=parsed.rhs,
                        original_F=parsed.F,
                    )
                    if sing_part is not None:
                        particular = sing_part
                        warnings = [
                            "La condición inicial corresponde a una solución singular o de equilibrio.",
                            *sing_warnings,
                        ]
                        break
            result.particular = particular
            result.warnings.extend(warnings)
            if particular is not None:
                result.particular_verification = verify_solution(
                    particular,
                    rhs=parsed.rhs,
                    original_F=parsed.F,
                    x0=x0,
                )

        result.validity = analyze_validity(
            parsed.rhs,
            result.particular or result.general,
            x0=x0,
            y0=y0,
        )

    return result, chosen is not None


def _attach_numeric(
    result: SolveResult,
    parsed: ParsedODE,
    *,
    chosen_exists: bool,
    x0: float | None,
    y0: float | None,
    x_min: float,
    x_max: float,
    compute_numeric: bool | None,
) -> None:
    should_compute_numeric = compute_numeric
    if should_compute_numeric is None:
        should_compute_numeric = (not chosen_exists) or (
            x0 is not None and y0 is not None
        )

    if (
        should_compute_numeric
        and parsed.rhs is not None
        and x0 is not None
        and y0 is not None
        and x_min is not None
        and x_max is not None
    ):
        numeric_start = time.perf_counter()
        result.numeric = solve_numeric(
            parsed.rhs,
            float(x0),
            float(y0),
            float(x_min),
            float(x_max),
        )
        result.timing_ms["numeric"] = (time.perf_counter() - numeric_start) * 1000
        if not result.numeric.success:
            result.warnings.append(result.numeric.message)
        elif not chosen_exists:
            result.steps = _numeric_steps(result)
            result.chosen_method = "numeric"
            result.validity = analyze_validity(parsed.rhs, None, x0=x0, y0=y0)
        else:
            _compare_numeric(result)


def _solve_impl(
    equation: str,
    x0: float | None,
    y0: float | None,
    x_min: float,
    x_max: float,
    method: str | None,
    compute_numeric: bool | None,
    *,
    symbolic_timeout: float | None = None,
) -> SolveResult:
    start = time.perf_counter()

    parse_start = time.perf_counter()
    parsed = parse_ode(equation)
    parse_ms = (time.perf_counter() - parse_start) * 1000

    if parsed.error is not None:
        result = SolveResult(
            input_text=equation,
            input_latex=parsed.latex_str or equation,
            standard_form=parsed.standard_form,
            error=parsed.error,
        )
        result.timing_ms["parse"] = parse_ms
        result.timing_ms["total"] = (time.perf_counter() - start) * 1000
        return result

    chosen_exists = False
    if symbolic_timeout is not None:
        try:
            result, chosen_exists = run_with_timeout(
                _solve_symbolic,
                equation,
                parsed,
                x0,
                y0,
                method,
                timeout=symbolic_timeout,
            )
        except TimeoutError as exc:
            if (
                parsed.rhs is not None
                and x0 is not None
                and y0 is not None
                and compute_numeric is not False
            ):
                result = SolveResult(
                    input_text=equation,
                    input_latex=parsed.latex_str or equation,
                    standard_form=parsed.standard_form,
                )
                result.warnings.append(
                    f"El cálculo simbólico superó {symbolic_timeout:g} s ({exc}); "
                    "se utilizó el respaldo numérico."
                )
            else:
                raise
    else:
        result, chosen_exists = _solve_symbolic(equation, parsed, x0, y0, method)

    result.timing_ms["parse"] = parse_ms
    _attach_numeric(
        result,
        parsed,
        chosen_exists=chosen_exists,
        x0=x0,
        y0=y0,
        x_min=x_min,
        x_max=x_max,
        compute_numeric=compute_numeric,
    )

    if result.general is None and (result.numeric is None or not result.numeric.success):
        result.error = (
            "No se encontró una solución simbólica verificable ni una "
            "integración numérica exitosa."
        )

    # Advertencias únicas preservando el orden.
    result.warnings = list(dict.fromkeys(result.warnings))
    result.timing_ms["total"] = (time.perf_counter() - start) * 1000
    return result


def solve(
    equation: str,
    x0: float | None = None,
    y0: float | None = None,
    x_min: float = -5.0,
    x_max: float = 5.0,
    *,
    method: str | None = None,
    compute_numeric: bool | None = None,
    timeout: float | None = None,
) -> SolveResult:
    """Resuelve una EDO de primer orden y devuelve el contrato completo.

    Parameters
    ----------
    equation:
        Texto de la ecuación en cualquiera de las formas admitidas.
    x0, y0:
        Condición inicial opcional.
    x_min, x_max:
        Intervalo para el respaldo numérico.
    method:
        Fuerza un método del clasificador (por ejemplo ``"exact"``).
    compute_numeric:
        ``True``/``False`` fuerza o desactiva el respaldo numérico; ``None``
        lo calcula cuando no hay solución simbólica o cuando hay PVI.
    timeout:
        Si se indica, el cálculo simbólico se ejecuta en un proceso aparte y
        se interrumpe al superar ese número de segundos (degradando a numérico
        si hay PVI disponible).
    """

    return _solve_impl(
        equation,
        x0,
        y0,
        x_min,
        x_max,
        method,
        compute_numeric,
        symbolic_timeout=timeout,
    )


__all__ = ["solve"]
