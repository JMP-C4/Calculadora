"""Formateo compartido de la notación de salida del motor.

Todas las interfaces muestran la misma representación algebraica o infija
tradicional; la elección se guarda en ``CLAVE_NOTACION`` para que cada
interface recuerde la preferencia del usuario.

Además de soluciones completas, el módulo formatea texto mixto (explicaciones,
métodos, pasos y advertencias) sin alterar la prosa: sólo transforma los
fragmentos que realmente parecen fórmulas.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import sympy as sp

from odecalc.models import Solution

#: Clave usada por web y escritorio para persistir la preferencia.
CLAVE_NOTACION = "edo_notacion_salida"
NATURAL = "Natural / Leibniz"
NOTACIONES = ("Algebraica", "Infija", NATURAL)

#: Alias aceptados al cargar preferencias o enlaces antiguos.
_ALIAS_NOTACION = {
    "natural": NATURAL,
    "pretty": NATURAL,
    "pretty print": NATURAL,
    "natural display": NATURAL,
    "2d math": NATURAL,
    "leibniz": NATURAL,
    "lagrange": NATURAL,
    "natural / pretty print": NATURAL,
    "natural / leibniz-lagrange": NATURAL,
}

_DELIMITADOS = re.compile(
    r"\$\$([\s\S]*?)\$\$|\$([^$\n]*)\$|\\\(([\s\S]*?)\\\)|\\\[([\s\S]*?)\\\]"
)
_COMANDO = re.compile(r"\\[A-Za-z]+")
_MATEO_EN_LINEA = re.compile(r"\$([^$\n]+)\$")
_TOKENS_MATEMATICOS = {
    "e",
    "i",
    "x",
    "y",
    "u",
    "v",
    "t",
    "c",
    "k",
    "g",
    "h",
    "m",
    "n",
    "p",
    "q",
    "dx",
    "dy",
    "du",
    "dv",
    "dz",
    "dt",
    "dr",
    "mu",
    "nu",
    "pi",
    "lam",
    "lambda",
    "exp",
    "log",
    "ln",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "erf",
    "erfi",
    "ci",
    "si",
    "ei",
    "acot",
    "abs",
    "piecewise",
    "sqrt",
    "frac",
    "dfrac",
    "tfrac",
    "text",
    "mathrm",
    "operatorname",
    "left",
    "right",
    "cdot",
    "times",
    "quad",
    "qquad",
    "rightarrow",
    "to",
    "infty",
    "partial",
    "int",
    "sum",
    "lim",
    "alpha",
    "beta",
    "gamma",
    "delta",
    "theta",
}


def normalizar(valor: str | None) -> str:
    """Devuelve una notación válida; cualquier valor desconocido es algebraica."""

    if valor in NOTACIONES:
        return valor  # type: ignore[return-value]
    if isinstance(valor, str):
        alias = _ALIAS_NOTACION.get(valor.strip().lower())
        if alias is not None:
            return alias
    return NATURAL


def _archivo_preferencia() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "odecalc" / "notacion.txt"


def leer_preferencia(*, default: str | None = None) -> str:
    """Preferencia guardada en disco para interfaces de escritorio."""

    try:
        return normalizar(_archivo_preferencia().read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        return normalizar(default) if default is not None else NATURAL


def guardar_preferencia(notacion: str) -> str:
    """Guarda la notación elegida y devuelve el valor normalizado."""

    valor = normalizar(notacion)
    try:
        ruta = _archivo_preferencia()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(valor, encoding="utf-8")
    except OSError:  # pragma: no cover - sistema de solo lectura
        pass
    return valor


def _limpiar(texto: str) -> str:
    return " ".join(texto.split())


def _limpiar_parrafos(texto: str) -> str:
    """Conserva saltos de línea, pero no espacios sobrantes al final."""

    return "\n".join(linea.rstrip() for linea in str(texto).splitlines()).strip()


_GRIEGAS_UNICODE = {
    "μ": r"\mu",
    "ν": r"\nu",
    "π": r"\pi",
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "θ": r"\theta",
    "λ": r"\lambda",
    "φ": r"\varphi",
    "ψ": r"\psi",
}
_SUBINDICES_UNICODE = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERINDICES_UNICODE = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ", "0123456789n")


def _reemplazar_potencia_parentesis(texto: str) -> str:
    """Convierte ``^(...)`` (incluyendo paréntesis anidados) en ``^{...}``."""

    if "^(" not in texto and "^ (" not in texto:
        return texto
    resultado: list[str] = []
    pos = 0
    patron = re.compile(r"\^\s*\(")
    while (encontrado := patron.search(texto, pos)) is not None:
        par_idx = texto.find("(", encontrado.start())
        bloque = _leer_bloque(texto, par_idx, "(", ")")
        if bloque is None:
            break
        contenido, fin = bloque
        resultado.append(texto[pos : encontrado.start()])
        resultado.append(f"^{{{_reemplazar_potencia_parentesis(contenido.strip())}}}")
        pos = fin
    resultado.append(texto[pos:])
    return "".join(resultado)


def _unicode_sqrt_a_latex(texto: str) -> str:
    """Convierte ``√(...)`` o ``√x`` en ``\\sqrt{...}`` para ``mathtext``."""

    if "√" not in texto:
        return texto
    salida: list[str] = []
    i = 0
    n = len(texto)
    while i < n:
        if texto[i] == "√":
            j = i + 1
            while j < n and texto[j].isspace():
                j += 1
            if j < n and texto[j] == "(":
                bloque = _leer_bloque(texto, j, "(", ")")
                if bloque is not None:
                    contenido, fin = bloque
                    salida.append(rf"\sqrt{{{_unicode_sqrt_a_latex(contenido.strip())}}}")
                    i = fin
                    continue
            if j < n:
                k = j
                while k < n and (texto[k].isalnum() or texto[k] in ("_", "\\")):
                    k += 1
                token = texto[j:k] if k > j else texto[j]
                salida.append(rf"\sqrt{{{token}}}")
                i = k if k > j else j + 1
                continue
        salida.append(texto[i])
        i += 1
    return "".join(salida)


def _leer_bloque(texto: str, inicio: int, abrir: str, cerrar: str) -> tuple[str, int] | None:
    """Extrae el contenido de un bloque ``{...}`` o ``(...)`` respetando anidación."""

    if inicio >= len(texto) or texto[inicio] != abrir:
        return None
    profundidad = 0
    indice = inicio
    while indice < len(texto):
        caracter = texto[indice]
        if caracter == "\\" and abrir == "{":
            indice += 2
            continue
        if caracter == abrir:
            profundidad += 1
        elif caracter == cerrar:
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio + 1 : indice], indice + 1
        indice += 1
    return None


def _reemplazar_funcion_parentesis(texto: str, nombre: str, plantilla: str) -> str:
    """Reemplaza llamadas ``nombre(...)`` respetando paréntesis anidados."""

    patron = re.compile(rf"\b{re.escape(nombre)}\s*\(")
    resultado: list[str] = []
    posicion = 0
    while (encontrado := patron.search(texto, posicion)) is not None:
        bloque = _leer_bloque(texto, encontrado.end() - 1, "(", ")")
        if bloque is None:
            break
        contenido, fin = bloque
        resultado.append(texto[posicion : encontrado.start()])
        resultado.append(plantilla.format(contenido.strip()))
        posicion = fin
    resultado.append(texto[posicion:])
    return "".join(resultado)


def _necesita_parentesis_frac(texto: str) -> bool:
    """Indica si un operando de ``a/b`` requiere paréntesis al aplanarse."""

    valor = texto.strip()
    if not valor or re.fullmatch(r"[A-Za-z0-9_^{}.]+", valor):
        return False
    if valor.startswith("(") and valor.endswith(")"):
        bloque = _leer_bloque(valor, 0, "(", ")")
        if bloque is not None and bloque[1] == len(valor):
            return False
    profundidad = 0
    for idx, car in enumerate(valor):
        if car in "({[":
            profundidad += 1
        elif car in ")}]":
            profundidad = max(0, profundidad - 1)
        elif profundidad == 0:
            if idx > 0 and car in "+-*/":
                return True
            if car.isspace():
                return True
    return False


def _simplificar_argumentos_latex(texto: str) -> str:
    """Convierte agrupaciones SymPy ``f{\\left(x\\right)}`` en ``f(x)`` sin llaves extra."""

    patron_fn = re.compile(
        r"(?:\\(?:ln|log|exp|sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|erf|erfi|Ci|Si|Ei|acot)|\\operatorname\{[^{}]+\})\s*\{"
    )
    resultado = texto
    pos = 0
    salida: list[str] = []
    while (encontrado := patron_fn.search(resultado, pos)) is not None:
        llave_idx = encontrado.end() - 1
        bloque = _leer_bloque(resultado, llave_idx, "{", "}")
        if bloque is None:
            break
        contenido, fin = bloque
        salida.append(resultado[pos:llave_idx])
        c_strip = contenido.strip()
        if c_strip.startswith(r"\left(") and c_strip.endswith(r"\right)"):
            salida.append("(" + c_strip[6:-7].strip() + ")")
        else:
            salida.append(contenido if c_strip.startswith("(") else "{" + contenido + "}")
        pos = fin
    salida.append(resultado[pos:])
    limpio = "".join(salida)
    limpio = re.sub(r"\\left([|(])", r"\1", limpio)
    limpio = re.sub(r"\\right([|)])", r"\1", limpio)
    limpio = re.sub(r"\\left(?![A-Za-z])", "", limpio)
    limpio = re.sub(r"\\right(?![A-Za-z])", "", limpio)
    return limpio


def _aplanar_comandos_anidados(
    texto: str,
    *,
    estilo: str,
) -> str:
    """Aplana ``\\frac``, ``\\dfrac``, ``\\tfrac``, ``\\sqrt`` y ``cases`` con anidación."""

    def _transformar_cases(cuerpo: str) -> str:
        filas = [f.strip() for f in re.split(r"\\\\", cuerpo) if f.strip()]
        partes: list[str] = []
        for fila in filas:
            if "&" in fila:
                expr, cond = (trozo.strip() for trozo in fila.split("&", 1))
                cond = re.sub(r"\\text\{([^{}]*)\}(?:\\:|\s)*", r"\1 ", cond).strip()
                cond = re.sub(r"^\bfor\b\s*", "si ", cond)
                if cond == "otherwise":
                    partes.append(f"{_aplanar(expr)} (en otro caso)")
                else:
                    partes.append(f"{_aplanar(expr)} ({_aplanar(cond)})")
            else:
                partes.append(_aplanar(fila))
        return "{" + "; ".join(partes) + "}"

    def _aplanar(valor: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(valor):
            if valor.startswith(r"\begin{cases}", i):
                fin = valor.find(r"\end{cases}", i)
                if fin != -1:
                    out.append(_transformar_cases(valor[i + 13 : fin]))
                    i = fin + 11
                    continue
            for cmd in (r"\dfrac{", r"\tfrac{", r"\frac{"):
                if valor.startswith(cmd, i):
                    b1 = _leer_bloque(valor, i + len(cmd) - 1, "{", "}")
                    if b1 is not None:
                        sig = b1[1]
                        while sig < len(valor) and valor[sig].isspace():
                            sig += 1
                        b2 = _leer_bloque(valor, sig, "{", "}")
                        if b2 is not None:
                            num = _aplanar(b1[0])
                            den = _aplanar(b2[0])
                            num_c = num.replace(" ", "")
                            den_c = den.replace(" ", "")
                            num_nat = re.sub(r"\\partial", "∂", num_c)
                            den_nat = re.sub(r"\\partial", "∂", den_c)
                            if (
                                estilo == "natural"
                                and re.fullmatch(r"(?:d|∂)\^?\d*[A-Za-z]+", num_nat)
                                and re.fullmatch(r"(?:d|∂)[A-Za-z]+\^?\d*", den_nat)
                            ):
                                out.append(f"{num_nat}/{den_nat}")
                            elif estilo == "natural":
                                n_txt = f"({num})" if _necesita_parentesis_frac(num) else num
                                d_txt = f"({den})" if _necesita_parentesis_frac(den) else den
                                out.append(f"{n_txt}/{d_txt}")
                            else:
                                out.append(f"({num})/({den})")
                            i = b2[1]
                            break
            else:
                if valor.startswith(r"\sqrt{", i):
                    b1 = _leer_bloque(valor, i + 5, "{", "}")
                    if b1 is not None:
                        inner = _aplanar(b1[0])
                        prefix = "√" if estilo == "natural" else "sqrt"
                        out.append(f"{prefix}({inner})")
                        i = b1[1]
                        continue
                out.append(valor[i])
                i += 1
                continue
            continue
        return "".join(out)

    return _aplanar(texto)


def adaptar_latex_mathtext(latex: str) -> str:
    """Adapta expresiones LaTeX para evitar errores de sintaxis en Matplotlib ``mathtext``."""

    if not latex:
        return ""
    valor = str(latex).strip()
    if len(valor) >= 2 and valor.startswith("$") and valor.endswith("$"):
        valor = valor[1:-1].strip()

    def _transformar_cuerpo_cases(cuerpo: str) -> str:
        filas = [f.strip() for f in re.split(r"\\\\", cuerpo) if f.strip()]
        ramas: list[str] = []
        for fila in filas:
            if "&" in fila:
                expr_r, cond_r = (p.strip() for p in fila.split("&", 1))
                cond_r = re.sub(r"\\text\{for\}(?:\\:|\s)*", r"\\mathrm{si}\\ ", cond_r)
                cond_r = re.sub(r"\\text\{otherwise\}", r"\\mathrm{en\\ otro\\ caso}", cond_r)
                ramas.append(rf"{expr_r}\ ({cond_r})")
            else:
                ramas.append(fila)
        unido = r"\ ;\ ".join(ramas)
        return rf"\left\{{\ {unido}\right."

    def _convertir_cases(texto: str) -> str:
        salida: list[str] = []
        pos = 0
        while pos < len(texto):
            ini_env = texto.find(r"\begin{cases}", pos)
            ini_cmd = texto.find(r"\cases{", pos)
            candidatos = [p for p in (ini_env, ini_cmd) if p != -1]
            if not candidatos:
                break
            ini = min(candidatos)
            if ini == ini_env:
                fin = texto.find(r"\end{cases}", ini)
                if fin == -1:
                    break
                salida.append(texto[pos:ini])
                salida.append(_transformar_cuerpo_cases(texto[ini + 13 : fin]))
                pos = fin + 11
            else:
                bloque = _leer_bloque(texto, ini + 6, "{", "}")
                if bloque is None:
                    break
                salida.append(texto[pos:ini])
                salida.append(_transformar_cuerpo_cases(bloque[0]))
                pos = bloque[1]
        salida.append(texto[pos:])
        return "".join(salida)

    valor = _convertir_cases(valor)
    reemplazos = (
        (r"\implies", r"\Longrightarrow"),
        (r"\iff", r"\Leftrightarrow"),
        (r"\tfrac", r"\frac"),
        (r"\displaystyle", ""),
        (r"\limits", ""),
        (r"\:", r"\,"),
    )
    for origen, destino in reemplazos:
        valor = valor.replace(origen, destino)
    valor = re.sub(r"\\le(?![A-Za-z])", r"\\leq", valor)
    valor = re.sub(r"\\ge(?![A-Za-z])", r"\\geq", valor)
    valor = re.sub(r"\\text\{([^{}]*)\}", lambda m: r"\mathrm{" + m.group(1) + "}", valor)
    valor = _unicode_sqrt_a_latex(valor)
    valor = _reemplazar_potencia_parentesis(valor)
    valor = re.sub(
        r"([A-Za-z0-9\)\]])\s*([⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ]+)",
        lambda m: f"{m.group(1)}^{{{m.group(2).translate(_SUPERINDICES_UNICODE)}}}",
        valor,
    )
    reemplazos_unicode = (
        ("−", "-"),
        ("·", r"\cdot "),
        ("×", r"\times "),
        ("÷", r"\div "),
        ("≤", r"\leq "),
        ("≥", r"\geq "),
        ("≠", r"\neq "),
        ("±", r"\pm "),
        ("∞", r"\infty "),
        ("∂", r"\partial "),
        ("∫", r"\int "),
        ("Σ", r"\sum "),
        ("∈", r"\in "),
        ("→", r"\rightarrow "),
        ("⇒", r"\Longrightarrow "),
        ("⇔", r"\Leftrightarrow "),
        ("′", "'"),
        ("″", "''"),
    )
    for u_char, tex_cmd in reemplazos_unicode:
        valor = valor.replace(u_char, tex_cmd)
    for g_char, g_cmd in _GRIEGAS_UNICODE.items():
        valor = valor.replace(g_char, g_cmd + " ")
    valor = re.sub(r"([A-Za-z0-9])\s*([₀₁₂₃₄₅₆₇₈₉]+)", lambda m: f"{m.group(1)}_{{{m.group(2).translate(_SUBINDICES_UNICODE)}}}", valor)
    valor = valor.replace("$", "")
    return _limpiar(valor)


def _codigo_a_latex(texto: str, *, funciones: bool = True) -> str:
    """Convierte notación de entrada o código matemático en LaTeX renderizable.

    Así ninguna vista tiene que mostrar ``*``, ``**`` o ``sqrt()``: todo pasa
    primero por una representación apta para KaTeX y ``mathtext``. Los textos
    que ya contienen comandos LaTeX se devuelven intactos. Con ``funciones=False``
    se conservan las funciones escritas como texto, tal como espera la notación infija.
    """

    valor = _limpiar(str(texto))
    if not valor or "\\" in valor:
        return valor
    for g_char, g_cmd in _GRIEGAS_UNICODE.items():
        if funciones:
            valor = valor.replace(g_char, g_cmd)
    valor = (
        valor.replace("−", "-")
        .replace("′", "'")
        .replace("″", "''")
        .replace("·", "*")
        .replace("≤", r"\leq " if funciones else "<=")
        .replace("≥", r"\geq " if funciones else ">=")
        .replace("≠", r"\neq " if funciones else "!=")
    )
    if funciones:
        valor = valor.replace("±", r"\pm ").replace("∫", r"\int ").replace("∂", r"\partial ")
        valor = re.sub(r"\\partial\s*([A-Za-z])\s*/\s*\\partial\s*([A-Za-z])", r"\\frac{\\partial \1}{\\partial \2}", valor)
        valor = re.sub(r"([A-Za-z0-9\)\]])\s*([⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ]+)", lambda m: f"{m.group(1)}^{{{m.group(2).translate(_SUPERINDICES_UNICODE)}}}", valor)
    valor = re.sub(
        r"([A-Za-z])([₀₁₂₃₄₅₆₇₈₉]+)",
        lambda m: f"{m.group(1)}_{m.group(2).translate(_SUBINDICES_UNICODE)}",
        valor,
    )
    if funciones:
        valor = re.sub(r"\bDy\b", "y'", valor)
    valor = re.sub(r"\bdy\s*/\s*dx\b", r"\\frac{dy}{dx}", valor)
    valor = _reemplazar_potencia_parentesis(valor.replace("**", "^"))
    if funciones:
        valor = _unicode_sqrt_a_latex(valor)
        valor = _reemplazar_funcion_parentesis(valor, "sqrt", r"\sqrt{{{}}}")
        valor = _reemplazar_funcion_parentesis(valor, "exp", r"e^{{{}}}")
        valor = _reemplazar_funcion_parentesis(valor, "Abs", r"\left|{{{}}}\right|")
        for nombre in ("ln", "log", "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh"):
            valor = re.sub(rf"\b{nombre}\s*\(", r"\\" + nombre + "(", valor)
        for esp in ("erf", "erfi", "Ci", "Si", "Ei", "acot"):
            valor = re.sub(rf"\b{esp}\s*\(", rf"\\operatorname{{{esp}}}(", valor)
        valor = re.sub(r"\bpi\b", r"\\pi", valor)
        valor = re.sub(r"\boo\b|∞", r"\\infty", valor)
    valor = re.sub(r"\b([A-Za-z])([0-9])\b", r"\1_\2", valor)
    punto = r"\cdot " if funciones else r"\cdot"
    # ``y^*`` es un comodín matemático, no un producto: no debe volverse ``y^\cdot``.
    return _limpiar(re.sub(r"(?<![\^*])\*", lambda _match: punto, valor))


def _leer_solucion(solucion: object | None) -> str:
    if not isinstance(solucion, Solution):
        return ""
    def texto(expr: object) -> str:
        return re.sub(r"\bI\b", "i", sp.sstr(expr).replace("**", "^"))

    if solucion.is_explicit:
        return _limpiar(f"y = {texto(solucion.expr)}")
    expresion = texto(solucion.expr)
    if solucion.value is None:
        return _limpiar(expresion)
    return _limpiar(f"{expresion} = {texto(solucion.value)}")


_EXPONENTE_INFIJO_APERTURA = "\ue000"
_EXPONENTE_INFIJO_CIERRE = "\ue001"


def _exponente_infijo(contenido: str) -> str:
    """Conserva la agrupación de exponentes compuestos al pasar a notación infija."""

    if re.fullmatch(r"[A-Za-z0-9]+", contenido):
        return f"^{contenido}"
    return f"^{_EXPONENTE_INFIJO_APERTURA}{contenido}{_EXPONENTE_INFIJO_CIERRE}"


def latex_a_infijo(texto: str) -> str:
    """Convierte un LaTeX simple a texto infijo cuando no hay objeto sympy."""

    if not texto:
        return ""
    convertido = _codigo_a_latex(texto, funciones=False)
    convertido = _simplificar_argumentos_latex(convertido)
    convertido = _aplanar_comandos_anidados(convertido, estilo="infijo")
    reemplazos = (
        (r"\\Longrightarrow", " => "),
        (r"\\Rightarrow", " => "),
        (r"\\Leftrightarrow", " <=> "),
        (r"\\rightarrow", " -> "),
        (r"\\qquad", "  "),
        (r"\\quad", "  "),
        (r"\\to", " -> "),
        (r"\\infty", "∞"),
        (r"\\partial", "∂"),
        (r"\\leq", "<="),
        (r"\\le(?![A-Za-z])", "<="),
        (r"\\geq", ">="),
        (r"\\ge(?![A-Za-z])", ">="),
        (r"\\neq", "!="),
        (r"\\mathrm\{e\}", "e"),
        (r"\\mathrm\{([^{}]*)\}", r"\1"),
        (r"\\operatorname\{([^{}]*)\}", r"\1"),
        (r"\\text\{([^{}]*)\}", r"\1"),
        (r"\\exp", "exp"),
        (r"\\ln", "ln"),
        (r"\\log", "log"),
        (r"\\sin", "sin"),
        (r"\\cos", "cos"),
        (r"\\tan", "tan"),
        (r"\\asin", "asin"),
        (r"\\acos", "acos"),
        (r"\\atan", "atan"),
        (r"\\cdot\s*", "*"),
        (r"\\times\s*", "*"),
        (r"_([0-9])", r"\1"),
        (r"\^\{([^{}]*)\}", lambda m: _exponente_infijo(m.group(1))),
        (r"_\{([^{}]*)\}", r"_\1"),
        (r"\\,", " "),
        (r"\\;", " "),
        (r"\\!", ""),
        (r"\$", ""),
    )
    for patron, sustitucion in reemplazos:
        convertido = re.sub(patron, sustitucion, convertido)
    convertido = convertido.replace("{", "").replace("}", "")
    convertido = convertido.replace(_EXPONENTE_INFIJO_APERTURA, "(").replace(
        _EXPONENTE_INFIJO_CIERRE, ")"
    )
    convertido = convertido.replace("**", "^").replace("\\", "")
    return _limpiar(convertido)


def latex_a_natural(texto: str) -> str:
    """Convierte LaTeX en notación natural con derivadas de Leibniz/y′.

    El resultado sigue siendo válido para MathJax y Matplotlib: se eliminan
    los comandos visibles, se usan símbolos Unicode y las derivadas se escriben
    como ``dy/dx`` o ``y′`` en lugar de ``y'``.
    """

    if not texto:
        return ""
    convertido = _codigo_a_latex(texto)
    convertido = _simplificar_argumentos_latex(convertido)
    convertido = re.sub(r"\^\{([A-Za-z0-9])\}", r"^\1", convertido)
    convertido = _aplanar_comandos_anidados(convertido, estilo="natural")
    reemplazos = (
        (r"\\mathrm\{([^{}]*)\}", r"\1"),
        (r"\\operatorname\{([^{}]*)\}", r"\1"),
        (r"\\text\{([^{}]*)\}", r"\1"),
        (r"\\Longrightarrow", "⇒"),
        (r"\\Rightarrow", "⇒"),
        (r"\\Leftrightarrow", "⇔"),
        (r"\\rightarrow", "→"),
        (r"\\to", "→"),
        (r"\\infty", "∞"),
        (r"\\partial", "∂"),
        (r"\\leq", "≤"),
        (r"\\le(?![A-Za-z])", "≤"),
        (r"\\geq", "≥"),
        (r"\\ge(?![A-Za-z])", "≥"),
        (r"\\neq", "≠"),
        (r"\\pm", "±"),
        (r"\\mu", "μ"),
        (r"\\nu", "ν"),
        (r"\\pi", "π"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\delta", "δ"),
        (r"\\theta", "θ"),
        (r"\\lambda", "λ"),
        (r"\\varphi", "φ"),
        (r"\\psi", "ψ"),
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\int", "∫"),
        (r"\\sum", "Σ"),
        (r"\\prime", "′"),
        (r"\\ln", "ln"),
        (r"\\log", "log"),
        (r"\\exp", "exp"),
        (r"\\sin", "sin"),
        (r"\\cos", "cos"),
        (r"\\tan", "tan"),
        (r"\\asin", "asin"),
        (r"\\acos", "acos"),
        (r"\\atan", "atan"),
        (r"\\qquad", "  "),
        (r"\\quad", "  "),
        (r"\\,", " "),
        (r"\\;", " "),
        (r"\\:", " "),
        (r"\\!", ""),
        (r"\$", ""),
    )
    for patron, sustitucion in reemplazos:
        convertido = re.sub(patron, sustitucion, convertido)
    convertido = re.sub(r"([A-Za-z])''", r"\1″", convertido)
    convertido = re.sub(r"([A-Za-z])'", r"\1′", convertido)
    convertido = re.sub(r"\^\{([A-Za-z0-9])\}", r"^\1", convertido)
    for indice, subindice in enumerate("₀₁₂₃₄₅₆₇₈₉"):
        convertido = convertido.replace(f"_{indice}", subindice)
    convertido = convertido.replace("\\", "")
    convertido = re.sub(r"(?<![\^*])\*", "·", convertido)
    return _limpiar(convertido)


def natural(latex: str, solucion: object | None = None) -> str:
    """Representación natural (Pretty Print + Leibniz/Lagrange) de una solución."""

    texto = latex_a_natural(latex)
    if texto:
        return texto
    origen = _leer_solucion(solucion)
    return latex_a_natural(origen) if origen else ""


def infijo(latex: str, solucion: object | None = None) -> str:
    """Texto infijo legible de una solución, con operadores explícitos."""

    texto = _leer_solucion(solucion)
    return texto or latex_a_infijo(latex)


def formatear(
    latex: str, solucion: object | None, notacion: str
) -> tuple[str, bool]:
    """Devuelve ``(texto, es_latex)`` según la notación solicitada."""

    modo = normalizar(notacion)
    if modo == "Infija":
        return infijo(latex, solucion), False
    if modo == NATURAL:
        return natural(latex, solucion), True
    return _codigo_a_latex(latex), True


def _normalizar_delimitadores(texto: str) -> str:
    """Unifica ``$``, ``$$``, ``\\(`` y ``\\[`` a matemática en línea."""

    def reemplazar(encontrado: re.Match[str]) -> str:
        contenido = next(grupo for grupo in encontrado.groups() if grupo is not None)
        contenido = _codigo_a_latex(" ".join(contenido.splitlines()).strip())
        return f"${contenido}$" if contenido else ""

    return _DELIMITADOS.sub(reemplazar, texto)


def _inicio_fragmento(texto: str, inicio_cmd: int) -> int:
    """Retrocede desde un comando LaTeX para no partir prefijos como ``y = v^{``."""

    indice = inicio_cmd
    profundidad_llave = 0
    profundidad_par = 0
    while indice > 0:
        car = texto[indice - 1]
        if car == "}":
            profundidad_llave += 1
        elif car == "{":
            if profundidad_llave:
                profundidad_llave -= 1
            else:
                indice -= 1
                continue
        elif car == ")":
            profundidad_par += 1
        elif car == "(":
            if profundidad_par:
                profundidad_par -= 1
            else:
                break
        elif profundidad_llave == 0 and profundidad_par == 0:
            if car in "$\n":
                break
            if car in ".;:," and (indice >= len(texto) or not texto[indice].isdigit()):
                break
            if car.isspace():
                pos = indice - 1
                while pos > 0 and texto[pos - 1].isspace():
                    pos -= 1
                palabra_m = re.search(r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)$", texto[:pos])
                if palabra_m:
                    palabra = palabra_m.group(1)
                    siguiente = texto[indice:].lstrip()
                    es_lhs_ecuacion = siguiente.startswith("=")
                    if palabra.lower() in _PROSA_STOP and not (
                        palabra.lower() == "y" and es_lhs_ecuacion
                    ):
                        break
                    if len(palabra) >= 3 and palabra.lower() not in _TOKENS_MATEMATICOS:
                        break
        indice -= 1
    while indice < inicio_cmd and texto[indice].isspace():
        indice += 1
    return indice


def _fin_fragmento(texto: str, inicio: int) -> int:
    """Extiende un comando LaTeX respetando llaves y paréntesis balanceados."""

    profundidad = 0
    indice = inicio
    while indice < len(texto):
        caracter = texto[indice]
        if caracter == "{":
            profundidad += 1
        elif caracter == "}" and profundidad:
            profundidad -= 1
        elif profundidad == 0:
            if caracter in "$\n":
                break
            if caracter in ".;:" and (
                indice + 1 == len(texto) or texto[indice + 1].isspace()
            ):
                break
        indice += 1
    while indice > inicio and texto[indice - 1].isspace():
        indice -= 1
    return max(indice, inicio)


def _dentro_de_matematicas(texto: str, posicion: int) -> bool:
    return texto[:posicion].count("$") % 2 == 1


def _envolver_comandos(texto: str) -> str:
    """Marca comandos LaTeX sueltos con su expresión completa para la UI."""

    resultado: list[str] = []
    ultimo = 0
    cursor = 0
    while (encontrado := _COMANDO.search(texto, cursor)) is not None:
        cursor = encontrado.end()
        if encontrado.start() < ultimo or _dentro_de_matematicas(texto, encontrado.start()):
            continue
        inicio = max(ultimo, _inicio_fragmento(texto, encontrado.start()))
        fin = _fin_fragmento(texto, inicio)
        if fin <= encontrado.end():
            continue
        fragmento = texto[inicio:fin].strip()
        resultado.append(texto[ultimo:inicio])
        resultado.append(f"${fragmento}$")
        ultimo = fin
    resultado.append(texto[ultimo:])
    return "".join(resultado)


def _parece_formula(texto: str) -> bool:
    """Detecta fórmulas cortas sin comandos, como ``y = C e^{x} - x - 1``."""

    valor = texto.strip()
    if not valor or "\n" in valor or "$" in valor or _COMANDO.search(valor):
        return False
    if not any(marca in valor for marca in ("=", "^", "_")):
        return False
    tokens = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]+", valor)
    return all(
        len(token) <= 2 or token.lower() in _TOKENS_MATEMATICOS for token in tokens
    )


def _naturalizar_prosa(texto: str) -> str:
    """Derivadas en notación de Lagrange dentro de la prosa (``y′``)."""

    valor = re.sub(r"([A-Za-z])''", r"\1″", texto)
    return re.sub(r"([A-Za-z])'", r"\1′", valor)


def _naturalizar_fragmentos(texto: str) -> str:
    """Aplica la notación natural sólo dentro de los fragmentos ``$...$``."""

    def reemplazar(encontrado: re.Match[str]) -> str:
        contenido = latex_a_natural(encontrado.group(1))
        return f"${contenido}$" if contenido else ""

    return _MATEO_EN_LINEA.sub(reemplazar, texto)


_PROSA_STOP = frozenset(
    {
        "se", "escribe", "escriben", "como", "donde", "para", "cuando", "con",
        "que", "de", "del", "la", "el", "los", "las", "por", "sin", "usa",
        "usar", "esto", "esta", "este", "eso", "su", "sus", "un", "una", "no",
        "sí", "si", "ya", "más", "pero", "porque", "así", "también",
        "finalmente", "primero", "después", "luego", "entonces", "ni", "hay",
        "tiene", "puede", "pueden", "debe", "deben", "entre", "sobre", "según",
        "aparte", "bien", "mal", "y", "o", "u", "e", "a", "en", "es", "son",
        "al", "lo", "le", "además", "deriva", "sigue", "llega", "permite",
        "explica", "representa", "implica", "equivale", "da", "hace", "vale",
        "queda", "cumple", "verifica", "anula", "resulta", "obtiene",
        "sustituir", "derivar", "integrar", "despejar", "separa", "igualamos",
        "multiplica", "divide", "resta", "suma", "cambia", "pasa", "cancela",
        "evalúa", "evalua", "tomando", "usando", "aplicando",
    }
)
_PROSA_CONJUNCIONES = frozenset({"y", "o", "u", "e", "a"})
_FUNCION_LLAMADA = re.compile(
    r"(?:\b(?:sqrt|exp|ln|log|sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|Abs|erf|erfi|Ci|Si|Ei|acot)\s*\([^()\n]+\)"
    r"|(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])(?:[μνφψ]|[fghPMNFG])\([^()\n]+\))"
)
_INTERVALO_PROSA = re.compile(
    r"(?:(?<=\s)|^)(?:"
    r"[\[(]\s*[^()\[\]\n]*?(?:∞|-∞|\boo\b)[^()\[\]\n]*?,\s*[^()\[\]\n]+?[\])]"
    r"|[\[(]\s*[^()\[\]\n]+?,\s*[^()\[\]\n]*?(?:∞|-∞|\boo\b)[^()\[\]\n]*?[\])]"
    r")"
)
_INTEGRAL_PROSA = re.compile(r"∫\s*[^\n.;:]+?\s*d[xyuvXt]\b")
_DERIV_PROSA = re.compile(r"(?:∂\s*[A-Za-z]\s*/\s*∂\s*[A-Za-z]|(?<![A-Za-z])d[yuv]\s*/\s*d[xXt](?![A-Za-z]))")
_INICIO_ECUACION = re.compile(
    r"(?<![\w$])("
    r"∂\s*[A-Za-z]\s*/\s*∂\s*[A-Za-z]"
    r"|d[yuv]\s*/\s*d[xXt]"
    r"|y\s*'{1,2}\s*(?:\(\s*x\s*\))?"
    r"|\([^()\n]+\)"
    r"|[A-Za-zμνπαβγδθλφψ_][A-Za-z0-9_₀₁₂₃₄₅₆₇₈₉']*(?:\([^()]*\))?"
    r")\s*(?:=|!=|≠|<=|>=|≤|≥|[<>])"
)


def _inicio_expresion_en_prosa(texto: str, pos_match: int) -> int:
    """Extiende hacia la izquierda si la ecuación tiene varios términos, ej. ``y' + P(x)y =``."""

    indice = pos_match
    profundidad_par = 0
    vio_operador = False
    while indice > 0:
        car = texto[indice - 1]
        if car == ")":
            profundidad_par += 1
        elif car == "(":
            if profundidad_par:
                profundidad_par -= 1
            else:
                break
        elif profundidad_par == 0:
            if car in "\n.;:$":
                break
            if car in "+-*/^·−":
                vio_operador = True
            elif car.isspace():
                pos = indice - 1
                while pos > 0 and texto[pos - 1].isspace():
                    pos -= 1
                palabra_m = re.search(r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)$", texto[:pos])
                if palabra_m:
                    palabra = palabra_m.group(1)
                    if palabra.lower() in _PROSA_STOP:
                        break
                    if len(palabra) >= 3 and palabra.lower() not in _TOKENS_MATEMATICOS:
                        break
        indice -= 1
    while indice < pos_match and texto[indice].isspace():
        indice += 1
    return indice if vio_operador else pos_match


def _es_stopword_en_contexto(texto: str, inicio_palabra: int, palabra: str) -> bool:
    lower = palabra.lower()
    if lower not in _PROSA_STOP:
        return False
    if lower not in _PROSA_CONJUNCIONES:
        return True
    resto = texto[inicio_palabra + len(palabra) :].lstrip()
    if not resto or resto[0] in ".;:,\n)$":
        prev_no_space = texto[:inicio_palabra].rstrip()
        if lower == "y" and prev_no_space and prev_no_space[-1].isalpha():
            return False
    if re.match(r"^[A-Za-zμνπαβγδθλφψ_][A-Za-z0-9_']*\s*=", resto):
        return True
    siguiente = re.match(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]+", resto)
    if siguiente is not None:
        sig_palabra = siguiente.group(0)
        if sig_palabra.lower() in _PROSA_STOP or (
            len(sig_palabra) >= 2 and sig_palabra.lower() not in _TOKENS_MATEMATICOS
        ):
            return True
    return False


def _fin_expresion(texto: str, inicio: int) -> int:
    """Extiende una ecuación en prosa hasta una pausa razonable."""

    profundidad = 0
    indice = inicio
    while indice < len(texto):
        caracter = texto[indice]
        if caracter in "({[":
            profundidad += 1
        elif caracter in ")}]":
            if profundidad:
                profundidad -= 1
            else:
                break
        elif profundidad == 0:
            if caracter in "\n;:,":
                break
            if caracter == "." and (
                indice + 1 == len(texto) or not texto[indice + 1].isdigit()
            ):
                break
            if caracter.isspace():
                siguiente = indice + 1
                while siguiente < len(texto) and texto[siguiente].isspace():
                    siguiente += 1
                palabra = re.match(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]+", texto[siguiente:])
                if palabra is not None:
                    word = palabra.group(0)
                    despues = texto[siguiente + len(word) :]
                    if not despues.startswith(("(", "'")):
                        if _es_stopword_en_contexto(texto, siguiente, word):
                            break
                        if len(word) >= 3 and word.lower() not in _TOKENS_MATEMATICOS:
                            break
                if siguiente < len(texto) and texto[siguiente] == "$":
                    break
        indice += 1
    while indice > inicio and texto[indice - 1].isspace():
        indice -= 1
    return max(indice, inicio)


def _envolver_solo_prosa(texto: str, *, latexify: bool = True) -> str:
    """Detecta fórmulas sueltas en un segmento libre de ``$`` y comandos LaTeX."""

    if not texto or "\\" in texto:
        return texto
    resultado: list[str] = []
    ultimo = 0
    # Una integral puede preceder al signo "=" que dispara la detección de
    # ecuaciones (p. ej. "Integramos ∫ f(x) dx = 1.").  Se añade como punto de
    # partida para envolver toda la expresión de una sola vez y no partir una
    # fórmula ya delimitada en dos fragmentos.
    candidatos = [
        (encontrado.start(), 0, encontrado) for encontrado in _INICIO_ECUACION.finditer(texto)
    ] + [
        (encontrado.start(), 1, encontrado) for encontrado in _INTEGRAL_PROSA.finditer(texto)
    ]
    for posicion, es_integral, encontrado in sorted(candidatos, key=lambda item: item[:2]):
        if posicion < ultimo:
            continue
        inicio = (
            posicion
            if es_integral
            else max(ultimo, _inicio_expresion_en_prosa(texto, posicion))
        )
        fin = _fin_expresion(texto, inicio)
        if fin <= max(encontrado.end(), inicio):
            continue
        fragmento = texto[inicio:fin].strip()
        marcas = ("+", "-", "−", "*", "/", "^", "(", ")", "·", "√", "_", "'", "≠", "≤", "≥", "<", ">", "!")
        es_par_corto = bool(
            re.fullmatch(
                r"[A-Za-zμνπαβγδθλφψ][0-9₀-₉']*\s*=\s*[+-]?[A-Za-z0-9μνπαβγδθλφψ]+",
                fragmento,
            )
        )
        if (
            not es_par_corto
            and not any(marca in fragmento for marca in marcas)
            and not any(caracter.isdigit() for caracter in fragmento)
        ):
            continue
        envuelto = _codigo_a_latex(fragmento) if latexify else fragmento
        resultado.append(texto[ultimo:inicio])
        resultado.append(f"${envuelto}$")
        ultimo = fin
    resultado.append(texto[ultimo:])
    preparado = "".join(resultado)

    for patron in (_INTEGRAL_PROSA, _FUNCION_LLAMADA, _INTERVALO_PROSA, _DERIV_PROSA):
        resultado = []
        ultimo = 0
        for encontrado in patron.finditer(preparado):
            inicio = encontrado.start()
            # La comprobación en el inicio no basta: un patrón puede empezar en
            # prosa y terminar dentro de una fórmula ya delimitada.
            if (
                inicio < ultimo
                or _dentro_de_matematicas(preparado, inicio)
                or preparado[: encontrado.end()].count("$") % 2 == 1
            ):
                continue
            fragmento = encontrado.group(0).strip()
            envuelto = _codigo_a_latex(fragmento) if latexify else fragmento
            resultado.append(preparado[ultimo:inicio])
            resultado.append(f"${envuelto}$")
            ultimo = encontrado.end()
        resultado.append(preparado[ultimo:])
        preparado = "".join(resultado)
    return preparado


def _envolver_en_prosa(texto: str, *, latexify: bool = True) -> str:
    """Delimita las fórmulas escritas en prosa respetando los fragmentos ya delimitados."""

    partes: list[str] = []
    posicion = 0
    for encontrado in _MATEO_EN_LINEA.finditer(texto):
        partes.append(_envolver_solo_prosa(texto[posicion : encontrado.start()], latexify=latexify))
        partes.append(encontrado.group(0))
        posicion = encontrado.end()
    partes.append(_envolver_solo_prosa(texto[posicion:], latexify=latexify))
    return "".join(partes)


def formatear_texto(texto: object, notacion: str, *, markdown: bool = True) -> str:
    """Formatea prosa con fragmentos matemáticos incrustados.

    En notaciones renderizadas los fragmentos se devuelven entre ``$`` para que
    Streamlit los renderice y Tk pueda convertirlos en imágenes. La notación
    natural usa Pretty Print con derivadas ``dy/dx`` y ``y′``; la infija usa
    texto tradicional. La prosa se conserva en ambos casos.
    """

    if texto is None:
        return ""
    raw = str(texto)
    if not raw.strip():
        return ""
    modo = normalizar(notacion)
    if modo == "Infija":
        valor = _envolver_en_prosa(raw, latexify=False)
        if _DELIMITADOS.search(valor) or _COMANDO.search(valor) or _parece_formula(valor):
            return latex_a_infijo(valor)
        return _limpiar_parrafos(valor)

    if _DELIMITADOS.search(raw) or _COMANDO.search(raw):
        con_comandos = _envolver_comandos(_normalizar_delimitadores(raw))
        preparado = _envolver_en_prosa(con_comandos, latexify=True)
    elif _parece_formula(raw):
        preparado = f"${_codigo_a_latex(raw.strip())}$"
    else:
        valor = _envolver_en_prosa(raw, latexify=True)
        preparado = _limpiar_parrafos(valor) if not _DELIMITADOS.search(valor) else valor
    if modo == NATURAL:
        # La prosa se respeta; sólo se naturalizan las derivadas sueltas y los
        # fragmentos matemáticos delimitados.
        partes: list[str] = []
        posicion = 0
        for encontrado in _MATEO_EN_LINEA.finditer(preparado):
            partes.append(_naturalizar_prosa(preparado[posicion : encontrado.start()]))
            partes.append(_naturalizar_fragmentos(encontrado.group(0)))
            posicion = encontrado.end()
        partes.append(_naturalizar_prosa(preparado[posicion:]))
        preparado = "".join(partes)
    return preparado if markdown else preparado


codigo_a_latex = _codigo_a_latex


def fragmentos(texto: str, notacion: str = NATURAL) -> list[tuple[str, bool]]:
    """Divide texto en ``(contenido, es_latex)`` para renderizado mixto."""

    preparado = formatear_texto(texto, notacion, markdown=True)
    if not preparado:
        return []
    partes: list[tuple[str, bool]] = []
    posicion = 0
    for encontrado in _MATEO_EN_LINEA.finditer(preparado):
        if encontrado.start() > posicion:
            partes.append((preparado[posicion : encontrado.start()], False))
        partes.append((encontrado.group(1), True))
        posicion = encontrado.end()
    if posicion < len(preparado):
        partes.append((preparado[posicion:], False))
    return partes


__all__ = [
    "CLAVE_NOTACION",
    "NATURAL",
    "NOTACIONES",
    "adaptar_latex_mathtext",
    "codigo_a_latex",
    "formatear",
    "formatear_texto",
    "fragmentos",
    "guardar_preferencia",
    "infijo",
    "latex_a_infijo",
    "latex_a_natural",
    "leer_preferencia",
    "natural",
    "normalizar",
]
