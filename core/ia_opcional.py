"""Capa opcional de IA: traduce texto y explica resultados ya verificados.

La IA **nunca** calcula ni modifica soluciones.  Su única misión es proponer
una ecuación a partir de lenguaje natural (que luego valida el parser) o
redactar en lenguaje sencillo un resultado que ya pasó por el motor y su
certificado.  Si no hay configuración, todo el laboratorio sigue funcionando
con reglas locales.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from core.parser import parsear
from core.tipos import EntradaInvalida, IADesactivada, ResultadoSolucion

_URL_ANTHROPIC = "https://api.anthropic.com/v1/messages"
_MODELO_POR_DEFECTO = "claude-sonnet-4-5"
_PROMPT_SISTEMA = (
    "Eres un asistente docente de ecuaciones diferenciales. No resuelvas la "
    "EDO ni inventes resultados: el motor matemático ya calculó y verificó la "
    "solución. Limítate a traducir o explicar de forma clara y breve."
)


@dataclass(frozen=True)
class EstadoIA:
    """Disponibilidad de la capa opcional de IA."""

    activa: bool
    configurada: bool
    modelo: str
    motivo: str = ""
    proveedor: str = "anthropic"


@dataclass
class SugerenciaEcuacion:
    """Ecuación propuesta a partir de lenguaje natural."""

    texto: str
    explicacion: str
    confianza: float
    origen: str
    advertencias: list[str] = field(default_factory=list)


def _variable_activa() -> bool:
    valor = os.environ.get("EDO_LAB_IA_ACTIVA", "").strip().lower()
    return valor in {"1", "true", "si", "sí", "yes", "on"}


def estado_ia() -> EstadoIA:
    """Indica si la IA está configurada y activada explícitamente."""

    clave = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    modelo = os.environ.get("EDO_LAB_IA_MODELO", _MODELO_POR_DEFECTO).strip()
    activa = _variable_activa()
    if not key_valida(clave):
        return EstadoIA(
            activa=False,
            configurada=False,
            modelo=modelo,
            motivo=(
                "La IA está desactivada. Define ANTHROPIC_API_KEY y "
                "EDO_LAB_IA_ACTIVA=1 para habilitarla; el resto de la app "
                "funciona sin ella."
            ),
        )
    if not activa:
        return EstadoIA(
            activa=False,
            configurada=True,
            modelo=modelo,
            motivo=(
                "Hay una clave configurada, pero la IA está apagada. "
                "Actívala con EDO_LAB_IA_ACTIVA=1."
            ),
        )
    return EstadoIA(
        activa=True,
        configurada=True,
        modelo=modelo,
        motivo="Capa de IA opcional activada.",
    )


def key_valida(clave: str) -> bool:
    """Comprobación mínima para no intentar llamadas con una clave vacía."""

    return bool(clave and len(clave) >= 20)


def _sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in normalizado if not unicodedata.combining(caracter))


def _limpiar_lenguaje(texto: str) -> str:
    limpio = texto.strip()
    reemplazos = (
        (r"\bmas\b", "+"),
        (r"\bmás\b", "+"),
        (r"\bpor\b", "*"),
        (r"\bmultiplicado por\b", "*"),
        (r"\bdividido entre\b", "/"),
        (r"\bdividido por\b", "/"),
        (r"\bal cuadrado\b", "^2"),
        (r"\bal cubo\b", "^3"),
        (r"\belevado a\b", "^"),
        (r"\bmenos\b", "-"),
    )
    for patron, valor in reemplazos:
        limpio = re.sub(patron, valor, limpio, flags=re.IGNORECASE)
    limpio = limpio.replace("−", "-").replace("×", "*").replace("÷", "/")
    return limpio.strip(" .,;")


def _candidata_desde_igualdad(texto: str) -> str | None:
    if "=" not in texto:
        return None
    izquierda, derecha = texto.split("=", 1)
    if "y'" not in izquierda.lower() and "dy/dx" not in izquierda.lower():
        return None
    candidata = f"y' = {_limpiar_lenguaje(derecha)}"
    try:
        parsear(candidata)
    except EntradaInvalida:
        return None
    return candidata


def _traducir_con_reglas(texto: str) -> SugerenciaEcuacion:
    original = texto.strip()
    normalizado = _sin_acentos(original.lower())

    candidata = _candidata_desde_igualdad(original)
    if candidata is not None:
        return SugerenciaEcuacion(
            texto=candidata,
            explicacion="Se tomó la igualdad escrita y se normalizó la sintaxis.",
            confianza=0.95,
            origen="reglas",
        )

    modelos = (
        (
            ("poblacion", "logistic", "crecimiento", "capacidad de carga"),
            "y' = r*y*(1 - y/K)",
            "Crecimiento logístico con tasa r y capacidad de carga K.",
            0.9,
        ),
        (
            ("enfriamiento", "newton", "temperatura", "cafe", "café"),
            "y' = -k*(y - Tenv)",
            "Ley de enfriamiento de Newton con constante k y ambiente Tenv.",
            0.9,
        ),
        (
            ("circuito", "inductancia", "bobina", "rl"),
            "y' = (V - R*y)/L",
            "Circuito RL: corriente gobernada por V, R y L.",
            0.88,
        ),
        (
            ("mezcla", "tanque", "salmuera", "concentracion"),
            "y' = (q/V)*(C_in - y)",
            "Mezcla en un tanque bien agitado con caudal q y volumen V.",
            0.88,
        ),
        (
            ("radiactiv", "decaimiento", "desintegracion"),
            "y' = -lambda*y",
            "Decaimiento proporcional a la cantidad presente.",
            0.9,
        ),
        (
            ("resistencia del aire", "caida", "caída", "arrastre"),
            "y' = g - (c/m)*y^2",
            "Caída vertical con resistencia cuadrática del aire.",
            0.86,
        ),
        (
            ("crecimiento exponencial", "interes compuesto", "interés compuesto"),
            "y' = k*y",
            "Cambio proporcional al valor actual.",
            0.85,
        ),
    )
    for palabras, ecuacion, explicacion, confianza in modelos:
        if any(palabra in normalizado for palabra in palabras):
            return SugerenciaEcuacion(
                texto=ecuacion,
                explicacion=explicacion,
                confianza=confianza,
                origen="reglas",
                advertencias=[
                    "Se usaron reglas locales. La ecuación contiene parámetros "
                    "simbólicos: sustitúyelos por valores numéricos antes de "
                    "resolver (o carga el modelo aplicado correspondiente)."
                ],
            )

    if "y'" in normalizado or "dy/dx" in normalizado:
        desde = min(
            posicion
            for posicion in (
                normalizado.find("y'"),
                normalizado.find("dy/dx"),
            )
            if posicion >= 0
        )
        fragmento = _limpiar_lenguaje(original[desde:])
        if "=" in fragmento:
            try:
                parsear(fragmento)
            except EntradaInvalida:
                pass
            else:
                return SugerenciaEcuacion(
                    texto=fragmento,
                    explicacion="Se extrajo la expresión que sigue a y'.",
                    confianza=0.7,
                    origen="reglas",
                )

    raise EntradaInvalida(
        "No se reconoció una ecuación en el texto. Prueba a escribirla "
        "directamente, por ejemplo `y' = x*y + sin(x)`, o menciona un modelo "
        "conocido (población, enfriamiento, circuito RL, mezcla, decaimiento, "
        "caída con aire)."
    )


def _llamar_anthropic(prompt: str, *, timeout: float = 20.0) -> str:
    estado = estado_ia()
    if not estado.activa:
        raise IADesactivada(estado.motivo or "La capa de IA está desactivada.")
    cuerpo = {
        "model": estado.modelo,
        "max_tokens": 600,
        "system": _PROMPT_SISTEMA,
        "messages": [{"role": "user", "content": prompt}],
    }
    solicitud = urllib.request.Request(
        _URL_ANTHROPIC,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", "").strip(),
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise IADesactivada(
            "No se pudo contactar con el servicio de IA; se usará el "
            "explicador local."
        ) from exc
    bloques = datos.get("content", [])
    textos = [
        bloque.get("text", "")
        for bloque in bloques
        if isinstance(bloque, dict) and bloque.get("type") == "text"
    ]
    respuesta = "\n".join(texto for texto in textos if texto).strip()
    if not respuesta:
        raise IADesactivada("La IA no devolvió una explicación utilizable.")
    return respuesta


def traducir_texto(
    texto: str,
    *,
    usar_ia: bool = False,
) -> SugerenciaEcuacion:
    """Convierte una descripción en español en una ecuación validada.

    Con ``usar_ia=True`` intenta la API opcional; si falla, cae en las reglas
    locales.  La ecuación propuesta siempre se valida con :func:`core.parser.parsear`.
    """

    if not isinstance(texto, str) or not texto.strip():
        raise EntradaInvalida("Escribe una descripción o una ecuación.")

    if usar_ia:
        estado = estado_ia()
        if estado.activa:
            prompt = (
                "Convierte el siguiente enunciado en una EDO explícita de "
                "primer orden en notación `y' = f(x, y)`. Responde sólo con la "
                "ecuación, sin explicaciones ni delimitadores.\n\n"
                f"Enunciado: {texto.strip()}"
            )
            try:
                candidata = _llamar_anthropic(prompt)
            except IADesactivada:
                candidata = ""
            candidata = candidata.strip().strip("`").strip()
            if candidata:
                if not candidata.lower().startswith("y'"):
                    candidata = "y' = " + candidata.split("=", 1)[-1].strip()
                try:
                    parsear(candidata)
                except EntradaInvalida:
                    pass
                else:
                    return SugerenciaEcuacion(
                        texto=candidata,
                        explicacion="Propuesta por la capa de IA y validada por el parser.",
                        confianza=0.75,
                        origen="ia",
                        advertencias=[
                            "Revisa que la ecuación propuesta represente el "
                            "enunciado completo antes de resolver."
                        ],
                    )

    return _traducir_con_reglas(texto)


def _explicacion_determinista(resultado: ResultadoSolucion) -> str:
    partes: list[str] = []
    if resultado.certificado is not None:
        certificado = resultado.certificado
        if certificado.estado.value == "verificada_simbolica":
            partes.append(
                "La solución fue verificada simbólicamente: al sustituirla en "
                "la ecuación, el residuo se anula de forma exacta."
            )
        elif certificado.estado.value == "verificada_numerica":
            partes.append(
                "La solución fue verificada numéricamente: se evaluó la "
                "ecuación en varios puntos del dominio y el residuo es muy "
                "pequeño."
            )
        else:
            partes.append(
                "La solución no pudo verificarse con suficiente confianza; "
                "trátala como una propuesta y revisa las advertencias."
            )
        if certificado.dominio_valido:
            partes.append(f"Dominio de validez: {certificado.dominio_valido}.")
    else:
        partes.append("Este resultado no incluye certificado de verificación.")

    if resultado.camino == "analitica":
        partes.append(
            f"Se encontró una forma cerrada de tipo {resultado.tipo.lower()}."
        )
    else:
        partes.append(
            "No se encontró una forma cerrada verificable, así que se usó "
            "integración numérica."
        )

    if resultado.x0 is not None and resultado.y0 is not None:
        partes.append(
            f"La condición inicial es y({resultado.x0:g}) = {resultado.y0:g}."
        )

    if resultado.existencia is not None:
        info = resultado.existencia
        if info.no_unicidad:
            partes.append(
                "Atención: en el punto inicial no se cumple la condición de "
                "Lipschitz, por lo que la solución podría no ser única."
            )
        if info.explota:
            tiempo = (
                f" alrededor de x = {info.tiempo_explosion:g}"
                if info.tiempo_explosion is not None
                else ""
            )
            partes.append(
                f"La solución parece explotar en tiempo finito{tiempo}."
            )
        if info.puntos_singularidad:
            partes.append(
                "Hay posibles singularidades en: "
                + "; ".join(info.puntos_singularidad[:4])
                + "."
            )

    if resultado.advertencias:
        partes.append("Advertencias: " + " ".join(resultado.advertencias))
    return " ".join(partes)


def explicar_resultado(
    resultado: ResultadoSolucion,
    *,
    usar_ia: bool = False,
) -> str:
    """Explica un resultado ya verificado en lenguaje sencillo.

    La explicación local siempre está disponible.  La IA sólo reescribe el
    texto; no recibe permiso para calcular ni corregir la solución.
    """

    base = _explicacion_determinista(resultado)
    if not usar_ia:
        return base
    estado = estado_ia()
    if not estado.activa:
        return base
    resumen = (
        f"Ecuación: {resultado.ecuacion_texto}\n"
        f"Tipo: {resultado.tipo}\n"
        f"Camino: {resultado.camino}\n"
        f"Solución mostrada: {resultado.solucion_latex}\n"
        f"Certificado: "
        f"{resultado.certificado.etiqueta if resultado.certificado else 'sin certificado'}\n"
        f"Explicación técnica: {base}\n"
    )
    prompt = (
        "Reescribe la siguiente explicación para un estudiante de primer "
        "curso, en español, en dos o tres párrafos. No cambies la solución, "
        "no calcules nada nuevo y no contradigas el certificado.\n\n"
        + resumen
    )
    try:
        return _llamar_anthropic(prompt)
    except IADesactivada:
        return base


__all__ = [
    "EstadoIA",
    "SugerenciaEcuacion",
    "estado_ia",
    "traducir_texto",
    "explicar_resultado",
]
