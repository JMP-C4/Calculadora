"""Núcleo matemático de EDO-Lab.

La capa ``core`` no importa nada de ``ui`` ni depende de internet.  Los
módulos pesados u opcionales (ajuste, incertidumbre, informes e IA) se cargan
de forma perezosa para que el paquete siga siendo utilizable en entornos
mínimos.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "1.0.0"

_EXPORTACIONES: dict[str, str] = {
    # Contratos
    "EstadoVerificacion": "core.tipos",
    "Certificado": "core.tipos",
    "Paso": "core.tipos",
    "ResultadoNumerico": "core.tipos",
    "InfoExistencia": "core.tipos",
    "Equilibrio": "core.tipos",
    "PuntoBifurcacion": "core.tipos",
    "FilaConvergencia": "core.tipos",
    "ResultadoConvergencia": "core.tipos",
    "BenchmarkItem": "core.tipos",
    "InfoRigidez": "core.tipos",
    "ResultadoSolucion": "core.tipos",
    "Ecuacion": "core.tipos",
    "EntradaInvalida": "core.tipos",
    "SolucionNoDisponible": "core.tipos",
    "TiempoAgotado": "core.tipos",
    "DatosInvalidos": "core.tipos",
    "IADesactivada": "core.tipos",
    # Entrada y solución
    "parsear": "core.parser",
    "parsear_con_parametros": "core.parser",
    "parsear_parametrizada": "core.parser",
    "rhs_de_texto": "core.parser",
    "clasificar": "core.clasificador",
    "tipo_principal": "core.clasificador",
    "resolver": "core.hibrido",
    "curva_solucion": "core.hibrido",
    "curva_desde_punto": "core.hibrido",
    "evaluar_solucion": "core.hibrido",
    # Verificación y análisis
    "certificar_motor": "core.verificador",
    "certificar_numerico": "core.verificador",
    "verificar_expresion": "core.verificador",
    "analizar_existencia": "core.existencia",
    "estimar_explosion": "core.existencia",
    "verificar_picard_lindelof": "core.existencia",
    "equilibrios": "core.cualitativo",
    "linea_fase": "core.cualitativo",
    "datos_isoclinas": "core.cualitativo",
    "bifurcacion": "core.cualitativo",
    "comportamiento_asintotico": "core.cualitativo",
    "resumen_cualitativo": "core.cualitativo",
    # Numérico
    "euler": "core.solver_numerico",
    "heun": "core.solver_numerico",
    "rk4": "core.solver_numerico",
    "resolver_metodo": "core.solver_numerico",
    "resolver_scipy": "core.solver_numerico",
    "comparar_metodos": "core.solver_numerico",
    "integrar_intervalo": "core.solver_numerico",
    "benchmark_metodos": "core.solver_numerico",
    "detectar_rigidez": "core.solver_numerico",
    "estudio_convergencia": "core.convergencia",
    "benchmark": "core.convergencia",
    "validar_orden": "core.convergencia",
    # Aprendizaje
    "pasos_para_tipo": "core.pasos",
    "generar_pasos": "core.pasos",
    "corregir": "core.corrector",
    "generar_ejercicio": "core.ejercicios",
    "recomendar_siguiente": "core.ejercicios",
    "cargar_perfil": "core.ejercicios",
    "guardar_perfil": "core.ejercicios",
    "TIPOS": "core.ejercicios",
    # Modelos aplicados
    "ModeloAplicado": "core.modelos",
    "ModeloInstanciado": "core.modelos",
    "ParametroModelo": "core.modelos",
    "MODELOS": "core.modelos",
    "listar_modelos": "core.modelos",
    "obtener_modelo": "core.modelos",
    "instanciar_modelo": "core.modelos",
    "resolver_modelo": "core.modelos",
    # Datos e incertidumbre
    "DatosAjuste": "core.ajuste",
    "ResultadoAjuste": "core.ajuste",
    "cargar_datos": "core.ajuste",
    "cargar_ejemplo": "core.ajuste",
    "ajustar": "core.ajuste",
    "seleccionar_mejor_modelo": "core.ajuste",
    "predecir": "core.ajuste",
    "Distribucion": "core.incertidumbre",
    "ResultadoMonteCarlo": "core.incertidumbre",
    "ResultadoSobol": "core.incertidumbre",
    "monte_carlo": "core.incertidumbre",
    "sobol_indices": "core.incertidumbre",
    "distribuciones_por_defecto": "core.incertidumbre",
    # Informes e IA
    "OpcionesInforme": "core.informes",
    "SeccionesInforme": "core.informes",
    "InformeGenerado": "core.informes",
    "generar_latex": "core.informes",
    "generar_pdf": "core.informes",
    "exportar_informe": "core.informes",
    "EstadoIA": "core.ia_opcional",
    "SugerenciaEcuacion": "core.ia_opcional",
    "estado_ia": "core.ia_opcional",
    "traducir_texto": "core.ia_opcional",
    "explicar_resultado": "core.ia_opcional",
}

__all__ = sorted(_EXPORTACIONES)


def __getattr__(nombre: str) -> Any:
    modulo = _EXPORTACIONES.get(nombre)
    if modulo is None:
        raise AttributeError(f"El módulo core no exporta «{nombre}».")
    valor = getattr(import_module(modulo), nombre)
    globals()[nombre] = valor
    return valor


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
