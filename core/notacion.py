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
    "c",
    "k",
    "g",
    "m",
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


def leer_preferencia() -> str:
    """Preferencia guardada en disco para interfaces de escritorio."""

    try:
        return normalizar(_archivo_preferencia().read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        return NATURAL


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


def _codigo_a_latex(texto: str, *, funciones: bool = True) -> str:
    """Convierte notación de entrada o código matemático en LaTeX renderizable.

    Así ninguna vista tiene que mostrar ``*``, ``**`` o ``sqrt()``: todo pasa
    primero por una representación apta para KaTeX. Los textos que ya contienen
    comandos LaTeX se devuelven intactos. Con ``funciones=False`` se conservan
    las funciones escritas como texto, tal como espera la notación infija.
    """

    valor = _limpiar(str(texto))
    if not valor or "\\" in valor:
        return valor
    valor = re.sub(r"\bdy\s*/\s*dx\b", r"\\frac{dy}{dx}", valor)
    valor = valor.replace("**", "^")
    if funciones:
        valor = re.sub(r"\bsqrt\s*\(\s*([^()]*?)\s*\)", r"\\sqrt{\1}", valor)
        valor = re.sub(r"\bexp\s*\(\s*([^()]*?)\s*\)", r"e^{\1}", valor)
        for nombre in ("ln", "log", "sin", "cos", "tan", "asin", "acos", "atan"):
            valor = re.sub(rf"\b{nombre}\s*\(", r"\\" + nombre + "(", valor)
        valor = re.sub(r"\bpi\b", r"\\pi", valor)
        valor = re.sub(r"\boo\b", r"\\infty", valor)
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


def latex_a_infijo(texto: str) -> str:
    """Convierte un LaTeX simple a texto infijo cuando no hay objeto sympy."""

    if not texto:
        return ""
    convertido = _codigo_a_latex(texto, funciones=False)
    reemplazos = (
        (r"\\rightarrow", " -> "),
        (r"\\qquad", "  "),
        (r"\\quad", "  "),
        (r"\\to", " -> "),
        (r"\\left", ""),
        (r"\\right", ""),
        (r"\\infty", "∞"),
        (r"\\partial", "∂"),
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
        (r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)"),
        (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)"),
        (r"\\dfrac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)"),
        (r"\\cdot\s*", "*"),
        (r"\\times\s*", "*"),
        (r"_([0-9])", r"\1"),
        (r"\^\{([^{}]*)\}", r"^\1"),
        (r"_\{([^{}]*)\}", r"_\1"),
        (r"\\,", " "),
        (r"\\;", " "),
        (r"\\!", ""),
        (r"\$", ""),
    )
    for patron, sustitucion in reemplazos:
        convertido = re.sub(patron, sustitucion, convertido)
    # Segunda pasada para fracciones y raíces anidadas.
    for patron in (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\\sqrt\{([^{}]*)\}"):
        sustitucion = (
            r"(\1)/(\2)" if patron.startswith(r"\\frac") else r"sqrt(\1)"
        )
        convertido = re.sub(patron, sustitucion, convertido)
    convertido = convertido.replace("{", "").replace("}", "")
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
    # Derivadas primero: ``\frac{dy}{dx}`` debe leerse ``dy/dx``, no ``(dy)/(dx)``.
    derivadas = (
        (r"\\(?:dfrac|tfrac|frac)\{\s*d\s*y\s*\}\{\s*d\s*x\s*\}", "dy/dx"),
        (r"\\(?:dfrac|tfrac|frac)\{\s*d\s*([A-Za-z])\s*\}\{\s*d\s*([A-Za-z])\s*\}", r"d\1/d\2"),
    )
    for patron, sustitucion in derivadas:
        convertido = re.sub(patron, sustitucion, convertido)
    reemplazos = (
        (r"\\(?:dfrac|tfrac|frac)\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2"),
        (r"\\sqrt\{([^{}]*)\}", r"√(\1)"),
        (r"\\left", ""),
        (r"\\right", ""),
        (r"\\mathrm\{([^{}]*)\}", r"\1"),
        (r"\\operatorname\{([^{}]*)\}", r"\1"),
        (r"\\text\{([^{}]*)\}", r"\1"),
        (r"\\rightarrow", "→"),
        (r"\\Rightarrow", "⇒"),
        (r"\\to", "→"),
        (r"\\infty", "∞"),
        (r"\\partial", "∂"),
        (r"\\mu", "μ"),
        (r"\\nu", "ν"),
        (r"\\pi", "π"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\delta", "δ"),
        (r"\\theta", "θ"),
        (r"\\lambda", "λ"),
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
    # Segunda pasada para fracciones y raíces anidadas.
    for patron, sustitucion in (
        (r"\\(?:dfrac|tfrac|frac)\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2"),
        (r"\\sqrt\{([^{}]*)\}", r"√(\1)"),
    ):
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
        contenido = _codigo_a_latex(contenido.strip())
        return f"${contenido}$" if contenido else ""

    return _DELIMITADOS.sub(reemplazar, texto)


def _fin_fragmento(texto: str, inicio: int) -> int:
    """Extiende un comando LaTeX hasta un separador razonable de prosa."""

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
    """Marca comandos LaTeX sueltos para que la UI los renderice como fórmula."""

    resultado: list[str] = []
    ultimo = 0
    cursor = 0
    while (encontrado := _COMANDO.search(texto, cursor)) is not None:
        cursor = encontrado.end()
        inicio = encontrado.start()
        if inicio < ultimo or _dentro_de_matematicas(texto, inicio):
            continue
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
        "aparte", "bien", "mal", "y", "o", "u", "además", "deriva", "sigue",
        "llega", "permite", "explica", "representa",
    }
)
_FUNCION_LLAMADA = re.compile(
    r"\b(?:sqrt|exp|ln|log|sin|cos|tan|asin|acos|atan)\s*\([^()]*\)"
)
_INICIO_ECUACION = re.compile(
    r"(?<![\w$])(dy\s*/\s*dx|y\s*'\s*(?:\(\s*x\s*\))?|[A-Za-z_]\w*(?:\([^()]*\))?)\s*="
)


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
            if caracter in "\n;:":
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
                if palabra and palabra.group(0).lower() in _PROSA_STOP:
                    break
                if siguiente < len(texto) and texto[siguiente] == "$":
                    break
        indice += 1
    while indice > inicio and texto[indice - 1].isspace():
        indice -= 1
    return max(indice, inicio)


def _envolver_en_prosa(texto: str) -> str:
    """Delimita las fórmulas escritas en prosa sin necesidad de ``$``."""

    # Si el texto ya trae delimitadores o comandos, la lógica existente se
    # encarga de él; envolverlo de nuevo alteraría fragmentos ya marcados.
    if "$" in texto or "\\" in texto:
        return texto
    resultado: list[str] = []
    ultimo = 0
    for encontrado in _INICIO_ECUACION.finditer(texto):
        inicio = encontrado.start()
        if inicio < ultimo or _dentro_de_matematicas(texto, inicio):
            continue
        fin = _fin_expresion(texto, inicio)
        if fin <= encontrado.end():
            continue
        fragmento = texto[inicio:fin].strip()
        marcas = ("+", "-", "*", "/", "^", "(", ")", "·", "√")
        if not any(marca in fragmento for marca in marcas) and not any(
            caracter.isdigit() for caracter in fragmento
        ):
            continue
        resultado.append(texto[ultimo:inicio])
        resultado.append(f"${fragmento}$")
        ultimo = fin
    resultado.append(texto[ultimo:])
    preparado = "".join(resultado)

    resultado = []
    ultimo = 0
    for encontrado in _FUNCION_LLAMADA.finditer(preparado):
        inicio = encontrado.start()
        if inicio < ultimo or _dentro_de_matematicas(preparado, inicio):
            continue
        resultado.append(preparado[ultimo:inicio])
        resultado.append(f"${encontrado.group(0)}$")
        ultimo = encontrado.end()
    resultado.append(preparado[ultimo:])
    return "".join(resultado)


def formatear_texto(texto: object, notacion: str, *, markdown: bool = True) -> str:
    """Formatea prosa con fragmentos matemáticos incrustados.

    En notaciones renderizadas los fragmentos se devuelven entre ``$`` para que
    Streamlit los renderice y Tk pueda convertirlos en imágenes. La notación
    natural usa Pretty Print con derivadas ``dy/dx`` y ``y′``; la infija usa
    texto tradicional. La prosa se conserva en ambos casos.
    """

    if texto is None:
        return ""
    valor = _envolver_en_prosa(str(texto))
    if not valor.strip():
        return ""
    modo = normalizar(notacion)
    if modo == "Infija":
        if _DELIMITADOS.search(valor) or _COMANDO.search(valor) or _parece_formula(valor):
            return latex_a_infijo(valor)
        return _limpiar_parrafos(valor)

    if _DELIMITADOS.search(valor) or _COMANDO.search(valor):
        preparado = _envolver_comandos(_normalizar_delimitadores(valor))
    elif _parece_formula(valor):
        preparado = f"${_codigo_a_latex(valor.strip())}$"
    else:
        preparado = _limpiar_parrafos(valor)
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
