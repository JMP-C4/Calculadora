"""Generación de informes PDF y LaTeX con certificado y tabla de errores."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape

from core.tipos import (
    ResultadoSolucion,
    SolucionNoDisponible,
)


@dataclass
class SeccionesInforme:
    """Secciones que se incluyen en el informe."""

    enunciado: bool = True
    metodo: bool = True
    pasos: bool = True
    graficas: bool = True
    errores: bool = True
    certificado: bool = True
    advertencias: bool = True


@dataclass
class OpcionesInforme:
    """Personalización básica del documento."""

    titulo: str = "Informe EDO-Lab"
    autor: str = ""
    secciones: SeccionesInforme = field(default_factory=SeccionesInforme)
    fecha: datetime | None = None


@dataclass
class InformeGenerado:
    """Documento listo para descargar."""

    contenido: bytes
    nombre_archivo: str
    formato: str
    mime: str

    @property
    def tamano_bytes(self) -> int:
        return len(self.contenido)


def _nombre_seguro(nombre: str) -> str:
    limpio = re.sub(r"[^0-9A-Za-z._-]+", "_", nombre).strip("._")
    return limpio or "informe_edolab"


def _numero(valor: Any) -> str:
    if valor is None:
        return "—"
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if abs(numero) >= 1e4 or (abs(numero) < 1e-3 and numero != 0):
        return f"{numero:.4e}"
    return f"{numero:.6g}"


def _estado_certificado(resultado: ResultadoSolucion) -> str:
    if resultado.certificado is None:
        return "Sin certificado"
    return resultado.certificado.etiqueta


def _filas_error(resultado: ResultadoSolucion, extra: Iterable[Any] | None) -> list[list[str]]:
    filas: list[list[str]] = []
    elementos: list[Any] = []
    if extra is not None:
        elementos.extend(extra)
    if resultado.numerico is not None:
        elementos.append(resultado.numerico)
    vistos: set[tuple[str, str, str]] = set()
    for elemento in elementos:
        metodo = str(getattr(elemento, "metodo", "—"))
        puntos = getattr(elemento, "puntos", None)
        if puntos is None:
            puntos = getattr(elemento, "pasos", None)
        error = getattr(elemento, "error_max", None)
        exito = getattr(elemento, "exito", None)
        if isinstance(elemento, dict):
            metodo = str(elemento.get("metodo", metodo))
            puntos = elemento.get("puntos", puntos)
            error = elemento.get("error_max", error)
            exito = elemento.get("exito", exito)
        estado = "Sí" if exito else ("No" if exito is False else "—")
        firma = (metodo, _numero(error), estado)
        if firma in vistos:
            continue
        vistos.add(firma)
        filas.append(
            [
                metodo,
                "—" if puntos is None else str(puntos),
                _numero(error),
                estado,
            ]
        )
    return filas


def _texto_latex(texto: str) -> str:
    reemplazos = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(reemplazos.get(caracter, caracter) for caracter in texto)


def generar_latex(
    resultado: ResultadoSolucion,
    opciones: OpcionesInforme | None = None,
    *,
    pasos: Iterable[Any] | None = None,
    tabla_errores: Iterable[Any] | None = None,
    figuras: Iterable[str | Path] | None = None,
) -> str:
    """Construye un documento LaTeX reproducible a partir del resultado."""

    opciones = opciones or OpcionesInforme()
    secciones = opciones.secciones
    pasos = list(pasos if pasos is not None else resultado.pasos)
    fecha = opciones.fecha or datetime.now()
    lineas: list[str] = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[spanish]{babel}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{booktabs}",
        r"\usepackage{graphicx}",
        r"\usepackage[margin=2.5cm]{geometry}",
        r"\usepackage{hyperref}",
        "",
        rf"\title{{{_texto_latex(opciones.titulo)}}}",
        rf"\author{{{_texto_latex(opciones.autor) or 'EDO-Lab'}}}",
        rf"\date{{{fecha.strftime('%d/%m/%Y')}}}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        rf"\section*{{Enunciado}}",
        r"\begin{center}",
        rf"\[ {resultado.ecuacion_latex} \]",
        r"\end{center}",
    ]
    if resultado.x0 is not None and resultado.y0 is not None:
        lineas.append(
            rf"Condición inicial: $y({resultado.x0:g}) = {resultado.y0:g}$."
        )
    if resultado.intervalo is not None:
        lineas.append(
            rf"Intervalo de estudio: $x \in [{resultado.intervalo[0]:g}, "
            rf"{resultado.intervalo[1]:g}]$."
        )
    lineas.extend(
        [
            "",
            rf"\section*{{Método y resultado}}",
            rf"Tipo detectado: {_texto_latex(resultado.tipo)}.\quad "
            rf"Camino: {_texto_latex(resultado.camino)}.",
            "",
            r"\begin{center}",
            rf"\[ {resultado.solucion_latex} \]",
            r"\end{center}",
        ]
    )
    if secciones.certificado:
        certificado = resultado.certificado
        lineas.extend([r"\section*{Certificado de verificación}", r"\begin{itemize}"])
        lineas.append(rf"\item Estado: {_texto_latex(_estado_certificado(resultado))}.")
        if certificado is not None:
            if certificado.residuo_max is not None:
                lineas.append(rf"\item Residuo máximo: {_numero(certificado.residuo_max)}.")
            if certificado.dominio_valido:
                lineas.append(
                    rf"\item Dominio declarado: {_texto_latex(certificado.dominio_valido)}."
                )
            if certificado.metodo:
                lineas.append(rf"\item Método: {_texto_latex(certificado.metodo)}.")
            for nota in certificado.notas:
                lineas.append(rf"\item {_texto_latex(nota)}")
        lineas.append(r"\end{itemize}")

    if secciones.pasos and pasos:
        lineas.append(r"\section*{Procedimiento}")
        for indice, paso in enumerate(pasos, start=1):
            titulo = _texto_latex(str(getattr(paso, "titulo", f"Paso {indice}")))
            explicacion = _texto_latex(str(getattr(paso, "explicacion", "")))
            latex = str(getattr(paso, "latex", "")).strip()
            lineas.extend(
                [
                    rf"\subsection*{{Paso {indice}. {titulo}}}",
                    explicacion,
                ]
            )
            if latex:
                lineas.extend([r"\[", latex, r"\]"])

    filas = _filas_error(resultado, tabla_errores) if secciones.errores else []
    if filas:
        lineas.extend(
            [
                r"\section*{Tabla de errores}",
                r"\begin{center}",
                r"\begin{tabular}{lrrl}",
                r"\toprule",
                r"Método & Puntos & Error máximo & Éxito \\",
                r"\midrule",
            ]
        )
        for fila in filas:
            lineas.append(" & ".join(_texto_latex(valor) for valor in fila) + r" \\")
        lineas.extend([r"\bottomrule", r"\end{tabular}", r"\end{center}"])

    if secciones.graficas and figuras:
        lineas.append(r"\section*{Gráficas}")
        for figura in figuras:
            ruta = str(figura)
            lineas.extend(
                [
                    r"\begin{center}",
                    rf"\includegraphics[width=0.85\textwidth]{{{ruta}}}",
                    r"\end{center}",
                ]
            )

    if secciones.advertencias and resultado.advertencias:
        lineas.append(r"\section*{Advertencias}")
        lineas.append(r"\begin{itemize}")
        for advertencia in resultado.advertencias:
            lineas.append(rf"\item {_texto_latex(advertencia)}")
        lineas.append(r"\end{itemize}")

    lineas.extend(["", r"\end{document}", ""])
    return "\n".join(lineas)


def _imagen_matematica(latex: str, *, ancho: float = 16.0) -> io.BytesIO | None:
    """Renderiza una fórmula con matplotlib (sin estado global pyplot) y devuelve PNG."""

    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        from core.notacion import adaptar_latex_mathtext
    except Exception:
        return None
    formula = adaptar_latex_mathtext(latex.strip().strip("$"))
    if not formula:
        return None
    try:
        figura = Figure(figsize=(ancho, 1.2), dpi=170)
        FigureCanvasAgg(figura)
        figura.patch.set_facecolor("white")
        figura.text(0.01, 0.5, f"${formula}$", fontsize=13, va="center", color="#1f2937")
        salida = io.BytesIO()
        figura.savefig(salida, format="png", bbox_inches="tight", facecolor="white")
        salida.seek(0)
        return salida
    except Exception:
        return None


def _grafica_resultado(resultado: ResultadoSolucion) -> io.BytesIO | None:
    """Dibuja la curva solución (analítica o numérica) para el informe sin usar pyplot."""

    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    except Exception:
        return None
    try:
        from core.hibrido import curva_solucion

        curva = curva_solucion(resultado, n_points=600)
    except Exception:
        curva = None
    if curva is None:
        return None
    xs, ys = curva
    if getattr(xs, "size", 0) < 2:
        return None
    try:
        figura = Figure(figsize=(7.2, 3.6), dpi=150)
        FigureCanvasAgg(figura)
        eje = figura.add_subplot(111)
        eje.plot(xs, ys, color="#2563eb", linewidth=2.0, label="solución")
        if resultado.x0 is not None and resultado.y0 is not None:
            eje.scatter(
                [resultado.x0],
                [resultado.y0],
                color="#dc2626",
                zorder=3,
                label="condición inicial",
            )
        eje.set_xlabel("$x$")
        eje.set_ylabel("$y$")
        eje.set_title("Curva solución")
        eje.grid(True, alpha=0.25)
        eje.legend(loc="best")
        figura.tight_layout()
        salida = io.BytesIO()
        figura.savefig(salida, format="png", bbox_inches="tight", facecolor="white")
        salida.seek(0)
        return salida
    except Exception:
        return None


def _leer_figura(fuente: Any) -> io.BytesIO | None:
    if isinstance(fuente, (bytes, bytearray)):
        return io.BytesIO(bytes(fuente))
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if ruta.exists():
            return io.BytesIO(ruta.read_bytes())
    return None


def generar_pdf(
    resultado: ResultadoSolucion,
    opciones: OpcionesInforme | None = None,
    *,
    pasos: Iterable[Any] | None = None,
    tabla_errores: Iterable[Any] | None = None,
    figuras: Iterable[Any] | None = None,
) -> InformeGenerado:
    """Genera un PDF con enunciado, método, pasos, gráfica y certificado."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception as exc:  # pragma: no cover - depende del entorno
        raise SolucionNoDisponible(
            "Para exportar PDF instala `reportlab` y `matplotlib`."
        ) from exc

    opciones = opciones or OpcionesInforme()
    secciones = opciones.secciones
    pasos = list(pasos if pasos is not None else resultado.pasos)
    fecha = opciones.fecha or datetime.now()
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "EdolabTitulo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    estilo_subtitulo = ParagraphStyle(
        "EdolabSubtitulo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    estilo_seccion = ParagraphStyle(
        "EdolabSeccion",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=14,
        spaceAfter=6,
    )
    estilo_cuerpo = ParagraphStyle(
        "EdolabCuerpo",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5,
    )
    estilo_paso = ParagraphStyle(
        "EdolabPaso",
        parent=estilo_cuerpo,
        leftIndent=8,
        borderPadding=4,
    )

    salida = io.BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=opciones.titulo,
        author=opciones.autor or "EDO-Lab",
    )
    historia: list[Any] = []
    historia.append(Paragraph(escape(opciones.titulo), estilo_titulo))
    historia.append(
        Paragraph(
            escape(
                f"EDO-Lab · {fecha.strftime('%d/%m/%Y %H:%M')} · "
                "La IA propone, el motor matemático comprueba."
            ),
            estilo_subtitulo,
        )
    )

    if secciones.enunciado:
        historia.append(Paragraph("1. Enunciado", estilo_seccion))
        imagen = _imagen_matematica(resultado.ecuacion_latex)
        if imagen is not None:
            historia.append(Image(imagen, width=15.0 * cm, height=2.2 * cm, kind="proportional"))
        else:
            historia.append(
                Paragraph(
                    f"<font name='Courier'>{escape(resultado.ecuacion_texto)}</font>",
                    estilo_cuerpo,
                )
            )
        datos: list[str] = [f"Tipo: {resultado.tipo}.", f"Camino: {resultado.camino}."]
        if resultado.x0 is not None and resultado.y0 is not None:
            datos.append(
                f"Condición inicial: y({resultado.x0:g}) = {resultado.y0:g}."
            )
        if resultado.intervalo is not None:
            datos.append(
                f"Intervalo: x ∈ [{resultado.intervalo[0]:g}, "
                f"{resultado.intervalo[1]:g}]."
            )
        historia.append(Paragraph(escape(" ".join(datos)), estilo_cuerpo))

    if secciones.metodo:
        historia.append(Paragraph("2. Método y solución", estilo_seccion))
        imagen = _imagen_matematica(resultado.solucion_latex)
        if imagen is not None:
            historia.append(Image(imagen, width=15.0 * cm, height=2.2 * cm, kind="proportional"))
        else:
            historia.append(
                Paragraph(
                    f"<font name='Courier'>{escape(resultado.solucion_latex)}</font>",
                    estilo_cuerpo,
                )
            )

    if secciones.certificado:
        historia.append(Paragraph("3. Certificado de verificación", estilo_seccion))
        certificado = resultado.certificado
        color_estado = {
            "verificada_simbolica": "#15803d",
            "verificada_numerica": "#b45309",
            "no_verificada": "#b91c1c",
        }.get(
            certificado.estado.value if certificado is not None else "",
            "#475569",
        )
        filas = [
            ["Estado", _estado_certificado(resultado)],
        ]
        if certificado is not None:
            filas.append(["Residuo máximo", _numero(certificado.residuo_max)])
            filas.append(["Dominio", certificado.dominio_valido or "—"])
            filas.append(["Método", certificado.metodo or "—"])
        tabla = Table(filas, colWidths=[4.0 * cm, 11.0 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor(color_estado)),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        historia.append(tabla)
        if certificado is not None and certificado.notas:
            for nota in certificado.notas:
                historia.append(Paragraph(escape(nota), estilo_cuerpo))

    if secciones.pasos and pasos:
        historia.append(Paragraph("4. Procedimiento", estilo_seccion))
        for indice, paso in enumerate(pasos, start=1):
            titulo = str(getattr(paso, "titulo", f"Paso {indice}"))
            explicacion = str(getattr(paso, "explicacion", ""))
            latex = str(getattr(paso, "latex", "")).strip()
            historia.append(
                Paragraph(
                    f"<b>Paso {indice}. {escape(titulo)}</b>",
                    estilo_cuerpo,
                )
            )
            if explicacion:
                historia.append(Paragraph(escape(explicacion), estilo_paso))
            if latex:
                imagen = _imagen_matematica(latex)
                if imagen is not None:
                    historia.append(Image(imagen, width=14.0 * cm, height=2.0 * cm, kind="proportional"))
                else:
                    historia.append(
                        Paragraph(
                            f"<font name='Courier'>{escape(latex)}</font>",
                            estilo_paso,
                        )
                    )

    if secciones.graficas:
        imagenes: list[Any] = []
        if figuras is not None:
            for fuente in figuras:
                leida = _leer_figura(fuente)
                if leida is not None:
                    imagenes.append(leida)
        if not imagenes:
            generada = _grafica_resultado(resultado)
            if generada is not None:
                imagenes.append(generada)
        if imagenes:
            historia.append(Paragraph("5. Gráfica de la solución", estilo_seccion))
            for imagen in imagenes:
                historia.append(Image(imagen, width=15.0 * cm, height=7.5 * cm))

    filas_error = _filas_error(resultado, tabla_errores) if secciones.errores else []
    if filas_error:
        historia.append(Paragraph("6. Tabla de errores", estilo_seccion))
        datos_tabla = [["Método", "Puntos", "Error máximo", "Éxito"]] + filas_error
        tabla = Table(datos_tabla, colWidths=[4.2 * cm, 2.6 * cm, 4.2 * cm, 2.0 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        historia.append(tabla)

    if secciones.advertencias and resultado.advertencias:
        historia.append(Paragraph("7. Advertencias", estilo_seccion))
        for advertencia in resultado.advertencias:
            historia.append(
                Paragraph("• " + escape(str(advertencia)), estilo_cuerpo)
            )

    def _pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(2.2 * cm, 1.2 * cm, "EDO-Lab · informe generado automáticamente")
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.2 * cm, f"Página {doc.page}")
        canvas.restoreState()

    try:
        documento.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    except Exception as exc:
        raise SolucionNoDisponible(
            "No se pudo componer el PDF. Revisa que reportlab y matplotlib "
            "estén instalados correctamente."
        ) from exc

    contenido = salida.getvalue()
    if not contenido:
        raise SolucionNoDisponible("El PDF generado está vacío.")
    nombre = _nombre_seguro(opciones.titulo.lower().replace(" ", "_")) + ".pdf"
    return InformeGenerado(
        contenido=contenido,
        nombre_archivo=nombre,
        formato="pdf",
        mime="application/pdf",
    )


def exportar_informe(
    resultado: ResultadoSolucion,
    ruta: str | Path,
    *,
    formato: str = "pdf",
    opciones: OpcionesInforme | None = None,
    pasos: Iterable[Any] | None = None,
    tabla_errores: Iterable[Any] | None = None,
    figuras: Iterable[Any] | None = None,
) -> Path:
    """Escribe el informe en disco y devuelve la ruta final."""

    destino = Path(ruta)
    formato = formato.lower().strip().lstrip(".")
    if formato in {"latex", "tex"}:
        contenido = generar_latex(
            resultado,
            opciones,
            pasos=pasos,
            tabla_errores=tabla_errores,
            figuras=figuras,
        ).encode("utf-8")
    elif formato == "pdf":
        contenido = generar_pdf(
            resultado,
            opciones,
            pasos=pasos,
            tabla_errores=tabla_errores,
            figuras=figuras,
        ).contenido
    else:
        raise SolucionNoDisponible(
            f"Formato de informe no soportado: {formato}. Usa PDF o LaTeX."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return destino


__all__ = [
    "SeccionesInforme",
    "OpcionesInforme",
    "InformeGenerado",
    "generar_latex",
    "generar_pdf",
    "exportar_informe",
]
