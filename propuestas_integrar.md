# EDO-Lab: Laboratorio Inteligente de Ecuaciones Diferenciales de Primer Orden

> **Instrucciones para el agente (OpenCode):** este archivo es la especificación del proyecto.
> Impleméntalo **por fases, en orden**. Al terminar cada fase: ejecuta las pruebas, marca las casillas `[x]`, haz commit y solo entonces pasa a la siguiente. No avances si los criterios de aceptación de la fase actual no se cumplen.
> Lema del proyecto: **"La IA propone, el motor matemático comprueba."**

---

## 0. Reglas generales para el agente

1. **Lenguaje:** Python 3.10+. Código y comentarios en español; nombres de funciones en `snake_case`.
2. **Stack:** `sympy`, `numpy`, `scipy`, `pandas`, `plotly`, `matplotlib`, `streamlit`, `lmfit`, `SALib`, `pytest`, `reportlab` o `pylatex` (informes).
3. **Determinismo:** toda aleatoriedad debe usar semilla fija configurable (`seed=42` por defecto).
4. **Nunca congelar la UI:** `dsolve` y cualquier cálculo pesado se ejecutan con *timeout* (por defecto 10 s) en un proceso aparte (`multiprocessing`) y degradan a método numérico.
5. **Separación estricta:** la lógica matemática (`core/`) **no importa** nada de `ui/`. La UI solo llama funciones de `core/`.
6. **Errores claros:** nunca mostrar trazas crudas al usuario; usar excepciones propias (`EntradaInvalida`, `SolucionNoDisponible`, `TiempoAgotado`) con mensajes en lenguaje sencillo.
7. **Tipado y docstrings** en todas las funciones públicas. Resultados devueltos como `dataclass` (no diccionarios sueltos).
8. **Pruebas primero:** cada módulo nuevo trae sus pruebas en `tests/` con ecuaciones de solución conocida.
9. **Sin dependencia de internet** en el núcleo. La IA (API de Claude) es **opcional** y solo se usa para traducir texto a ecuación y explicar resultados ya verificados.

---

## 1. Estructura del proyecto

```
edo-lab/
├── AGENTS.md                  # (copia de este archivo)
├── README.md
├── requirements.txt
├── pyproject.toml
├── app.py                     # punto de entrada Streamlit
├── core/
│   ├── parser.py              # entrada flexible -> expresión SymPy
│   ├── clasificador.py        # tipo de EDO (separable, lineal, exacta, Bernoulli...)
│   ├── solver_simbolico.py    # dsolve + PVI + constante C
│   ├── solver_numerico.py     # Euler, Heun, RK4, RK45, BDF, Radau
│   ├── hibrido.py             # orquestador: analítico -> numérico
│   ├── verificador.py         # residuo, certificado de confianza
│   ├── existencia.py          # Picard-Lindelöf, singularidades, explosión
│   ├── convergencia.py        # error vs h, orden empírico, benchmark
│   ├── cualitativo.py         # equilibrios, estabilidad, isóclinas, bifurcaciones
│   ├── ajuste.py              # ajuste con datos, AIC/BIC, IC, predicción
│   ├── incertidumbre.py       # Monte Carlo, Sobol
│   ├── pasos.py               # explicación paso a paso (LaTeX)
│   ├── corrector.py           # corrector de procedimiento del estudiante
│   ├── ejercicios.py          # generador de ejercicios con solución verificada
│   ├── modelos.py             # biblioteca de modelos aplicados
│   ├── informes.py            # exportación PDF/LaTeX
│   ├── tipos.py               # dataclasses y excepciones
│   └── ia_opcional.py         # capa opcional con API de Claude
├── ui/
│   ├── estilos.py             # CSS global (espaciado, scroll, responsive)
│   ├── componentes.py         # tarjetas, badges, bloques reutilizables
│   ├── pagina_resolver.py
│   ├── pagina_cualitativo.py
│   ├── pagina_numerico.py
│   ├── pagina_datos.py
│   ├── pagina_incertidumbre.py
│   ├── pagina_aprendizaje.py
│   └── pagina_informes.py
├── data/
│   ├── ejemplos/              # CSV de ejemplo (enfriamiento, población...)
│   └── perfil_estudiante.json
└── tests/
    ├── test_parser.py
    ├── test_clasificador.py
    ├── test_solvers.py
    ├── test_verificador.py
    ├── test_existencia.py
    ├── test_cualitativo.py
    ├── test_ajuste.py
    ├── test_corrector.py
    └── bateria_edos.py        # ecuaciones con solución conocida
```

---

## 2. Hoja de ruta por fases

### Fase 1 — Núcleo híbrido (base de todo)
- [x] `parser.py`: aceptar `y' = x*y + sin(x)`, `dy/dx = ...`, `y'=...`, `^` como potencia, multiplicación implícita (`2x` → `2*x`). Validar símbolos permitidos (lista blanca, **sin `eval` inseguro**).
- [x] `clasificador.py`: usar `sympy.classify_ode` y traducir a etiquetas amigables (separable, lineal 1.er orden, exacta, homogénea, Bernoulli, Riccati, autónoma).
- [x] `solver_simbolico.py`: `dsolve` con y sin condición inicial; calcular la constante `C`.
- [x] `solver_numerico.py`: Euler, Heun, RK4 (implementación propia) + `solve_ivp` (RK45, BDF, Radau).
- [x] `hibrido.py`: intentar analítico con timeout; si falla, caer a numérico; devolver `ResultadoSolucion` indicando qué camino se usó.
- **Aceptación:** pasa `bateria_edos.py` (mínimo 15 EDO: separables, lineales, exactas, Bernoulli, una sin solución cerrada).

### Fase 2 — Verificación matemática (diferenciador principal)
- [x] `verificador.py`: sustituir la solución en la EDO y simplificar; el residuo debe ser 0 simbólicamente. Si no se puede simplificar, verificación numérica en 200 puntos del dominio.
- [x] **Certificado de confianza** (`dataclass`): método usado, residuo máximo, condiciones de validez, estado (`VERIFICADA_SIMBOLICA`, `VERIFICADA_NUMERICA`, `NO_VERIFICADA`).
- [x] `existencia.py`: comprobar continuidad de `f` y `∂f/∂y` (Picard-Lindelöf), detectar puntos de singularidad, solución no única (ej. `y' = y^(1/3)`) y explosión en tiempo finito (ej. `y' = y²`) estimando el tiempo de explosión.
- **Aceptación:** cualquier solución mostrada en la UI lleva su certificado; `y' = y²` reporta explosión en `x = 1/y0`.

### Fase 3 — Visualización y análisis cualitativo
- [x] Campo de direcciones con curvas solución para varias condiciones iniciales (Plotly).
- [x] **Clic en el gráfico → traza la curva solución** que pasa por ese punto.
- [x] `cualitativo.py`: equilibrios de EDO autónomas (`f(y)=0`), estabilidad por signo de `f'(y*)`, diagrama de fase 1D, isóclinas.
- [x] Diagrama de bifurcación con parámetro `μ` controlado por deslizador.
- [x] Comportamiento asintótico (límite cuando `x → ∞`) con `sympy.limit` y respaldo numérico.
- **Aceptación:** para `y' = y(1-y)` identifica `y=0` inestable y `y=1` estable.

### Fase 4 — Análisis numérico riguroso
- [x] Estimación de error local y global; control adaptativo del paso.
- [x] **Detección de rigidez** (stiffness) y cambio automático a BDF/Radau, avisando al usuario.
- [x] Estudio de convergencia: gráfica log-log error vs `h`, con **orden empírico** calculado por regresión (Euler ≈ 1, Heun ≈ 2, RK4 ≈ 4).
- [x] Benchmark en vivo: tiempo, evaluaciones de `f`, error máximo por método.
- **Aceptación:** el orden empírico de RK4 está entre 3.8 y 4.2 en una EDO de prueba.

### Fase 5 — Ajuste con datos reales
- [x] Cargar CSV/Excel (detectar columnas tiempo/valor, manejar NaN, validar mínimo de puntos).
- [x] Ajuste de parámetros con `lmfit`/`scipy.optimize` integrando la EDO en cada iteración.
- [x] Modelos candidatos: exponencial, logístico, Gompertz, enfriamiento de Newton.
- [x] Selección por **AIC/BIC**; recomendar el mejor y explicar por qué.
- [x] Intervalos de confianza de parámetros, predicción a futuro con banda.
- [x] Análisis de sensibilidad local de los parámetros.
- **Aceptación:** con datos sintéticos de un logístico con ruido, el ajuste recupera `r` y `K` con error < 5 % y el AIC prefiere logístico.

### Fase 6 — Incertidumbre
- [x] Monte Carlo sobre condiciones iniciales y parámetros (distribución configurable), bandas de predicción 5–95 %.
- [x] Índices de Sobol con `SALib` (primer orden y total).
- **Aceptación:** reproducible con la misma semilla; gráfico de bandas y barras de sensibilidad.

### Fase 7 — Modo paso a paso y aprendizaje adaptativo
- [x] `pasos.py`: para separable, lineal, exacta y Bernoulli, devolver lista de pasos (`titulo`, `explicacion`, `latex`).
- [x] `corrector.py`: recibir el desarrollo del estudiante (una línea por paso), comprobar **equivalencia** entre pasos consecutivos con SymPy y señalar la **primera línea con error** con una pista (sin dar la respuesta completa).
- [x] `ejercicios.py`: generar ejercicios por tipo y dificultad (1–5) con solución verificada por el motor.
- [x] Perfil del estudiante (`data/perfil_estudiante.json`): aciertos/errores por tipo de EDO y recomendación del siguiente ejercicio.
- **Aceptación:** el corrector detecta un error de signo introducido a propósito en la línea correcta.

### Fase 8 — Modelos aplicados, informes y capa de IA opcional
- [x] `modelos.py`: crecimiento poblacional, Newton, circuito RL, mezclas, decaimiento radiactivo, caída con resistencia del aire (cada uno con descripción, parámetros y valores por defecto).
- [x] `informes.py`: exportar PDF/LaTeX con enunciado, método, pasos, gráficas, tabla de errores y certificado.
- [x] `ia_opcional.py`: (1) texto natural → ecuación, (2) explicar en lenguaje sencillo un resultado **ya verificado**. Desactivable; la app debe funcionar completa sin ella. Nunca usar la IA para calcular la solución.
- **Aceptación:** informe PDF generado sin errores; con la IA desactivada nada falla.

---

## 3. Diseño de la interfaz (UI/UX)

### 3.1 Principios
- **Cómoda e intuitiva:** una tarea por pestaña, flujo de izquierda a derecha y de arriba abajo.
- **Espacios generosos:** el contenido respira; nada pegado a los bordes.
- **Scroll controlado:** el scroll vertical de la página es natural; las áreas largas (pasos, tablas, historial, registros) van en **contenedores con altura máxima y barra de scroll propia**, para que la página no se haga interminable.
- **Responsive:** funciona en móvil, tableta y escritorio sin scroll horizontal de la página.
- **Legible:** tipografía mínima de 16 px, interlineado 1.6, buen contraste, ancho de línea cómodo (60–80 caracteres para texto).
- **Accesible:** no depender solo del color (usar iconos y texto para estados), etiquetas claras, foco visible.

### 3.2 Esqueleto de pantalla (escritorio)

```
┌──────────────────────────────────────────────────────────────────────┐
│  ENCABEZADO: EDO-Lab · lema · selector de tema claro/oscuro          │
├───────────────┬──────────────────────────────────────────────────────┤
│  BARRA LATERAL│  PESTAÑAS:                                           │
│  (scroll propio)│ Resolver | Cualitativo | Numérico | Datos |        │
│               │ Incertidumbre | Aprender | Informes                  │
│  1. Ecuación  │ ┌──────────────────────────────────────────────────┐ │
│  [campo]      │ │ TARJETA: Resultado + Certificado de verificación │ │
│  ejemplos ▾   │ └──────────────────────────────────────────────────┘ │
│               │ ┌───────────────────────┬──────────────────────────┐ │
│  2. Condición │ │ GRÁFICA (Plotly)      │ PASO A PASO              │ │
│  inicial      │ │ ajusta al ancho       │ (contenedor con scroll)  │ │
│  x0, y0       │ └───────────────────────┴──────────────────────────┘ │
│               │ ┌──────────────────────────────────────────────────┐ │
│  3. Intervalo │ │ Detalles técnicos (expanders colapsables)        │ │
│  4. Método    │ └──────────────────────────────────────────────────┘ │
│  [RESOLVER]   │                                                      │
└───────────────┴──────────────────────────────────────────────────────┘
```

### 3.3 Comportamiento responsive
| Ancho | Diseño |
|---|---|
| ≥ 1100 px (escritorio) | Barra lateral fija + contenido en 2 columnas (gráfica + pasos) |
| 700–1099 px (tableta) | Barra lateral colapsable; gráfica y pasos apilados |
| < 700 px (móvil) | Una sola columna; entrada de ecuación arriba; pestañas con scroll horizontal; gráfica con altura reducida |

Reglas:
- Usar `st.columns` (Streamlit las apila solo en pantallas pequeñas) y `use_container_width=True` en todas las gráficas.
- Altura de gráficas con `clamp()` o proporcional, nunca valores fijos grandes en píxeles.
- Tablas anchas dentro de contenedores con `overflow-x: auto`.

### 3.4 Contenido de cada pestaña
1. **Resolver:** entrada de ecuación, PVI, resultado analítico/numérico, certificado, paso a paso, campo de direcciones con curvas.
2. **Cualitativo:** equilibrios y estabilidad, diagrama de fase 1D, isóclinas, deslizador de parámetro y bifurcación, clic en gráfico para trazar curvas.
3. **Numérico:** comparación de métodos, convergencia (log-log), benchmark, aviso de rigidez.
4. **Datos:** cargar CSV/Excel, vista previa (con scroll), elegir modelos, ajuste, AIC/BIC, predicción con bandas.
5. **Incertidumbre:** Monte Carlo y Sobol con controles simples.
6. **Aprender:** generador de ejercicios, corrector de procedimiento, panel de progreso.
7. **Informes:** vista previa, selección de secciones, exportar PDF/LaTeX.

### 3.5 Componentes reutilizables (`ui/componentes.py`)
- `tarjeta(titulo, contenido)`: bloque con borde suave, radio 12 px y padding generoso.
- `badge_estado(estado)`: ícono + texto (✅ Verificada, ⚠️ Verificación numérica, ❌ No verificada).
- `bloque_scroll(altura_max)`: contenedor con barra de scroll para listas largas.
- `mensaje_error(msg)`: mensaje amable con sugerencia de corrección.
- `teclado_ayuda()`: expander con sintaxis aceptada (`sin(x)`, `exp(x)`, `x^2`, `y'`).

### 3.6 CSS base (`ui/estilos.py`)

```python
CSS = """
<style>
:root{
  --espacio: clamp(0.75rem, 1.5vw, 1.5rem);
  --radio: 12px;
  --max-ancho: 1400px;
}

/* Contenedor principal con respiro y ancho máximo */
.block-container{
  padding: var(--espacio) clamp(1rem, 4vw, 3rem) 4rem;
  max-width: var(--max-ancho);
}

/* Tipografía legible */
html, body, [class*="css"]{
  font-size: 16px;
  line-height: 1.6;
}
h1{font-size: clamp(1.5rem, 3vw, 2.2rem);}
h2{font-size: clamp(1.25rem, 2.2vw, 1.7rem); margin-top: 1.5rem;}
p, li{max-width: 80ch;}

/* Tarjetas */
.edo-tarjeta{
  border: 1px solid rgba(128,128,128,.25);
  border-radius: var(--radio);
  padding: var(--espacio);
  margin-bottom: var(--espacio);
}

/* Áreas con scroll propio (pasos, tablas, historial) */
.edo-scroll{
  max-height: min(60vh, 520px);
  overflow-y: auto;
  overflow-x: auto;
  padding-right: .5rem;
  scrollbar-width: thin;
}
.edo-scroll::-webkit-scrollbar{width: 8px; height: 8px;}
.edo-scroll::-webkit-scrollbar-thumb{
  background: rgba(128,128,128,.45);
  border-radius: 8px;
}

/* Fórmulas largas nunca rompen el diseño */
.katex-display{overflow-x: auto; overflow-y: hidden; padding: .5rem 0;}

/* Pestañas con scroll horizontal en pantallas pequeñas */
.stTabs [data-baseweb="tab-list"]{
  overflow-x: auto;
  gap: .25rem;
  scrollbar-width: thin;
}

/* Gráficas y tablas se ajustan al ancho */
.js-plotly-plot, .stDataFrame{max-width: 100%;}

/* Móvil */
@media (max-width: 700px){
  .block-container{padding: .75rem 1rem 3rem;}
  .edo-scroll{max-height: 50vh;}
}
</style>
"""
```

Uso en `app.py`:

```python
import streamlit as st
from ui.estilos import CSS

st.set_page_config(page_title="EDO-Lab", page_icon="🧪", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)
```

Para contenedores con scroll nativo de Streamlit también se puede usar:

```python
with st.container(height=480, border=True):
    for paso in pasos:
        st.markdown(f"**{paso.titulo}**")
        st.write(paso.explicacion)
        st.latex(paso.latex)
```

### 3.7 Experiencia de usuario
- Botón **Resolver** siempre visible en la barra lateral; indicador de progreso (`st.spinner`) en cálculos largos.
- Ejemplos precargados desplegables (separable, lineal, logística, Newton) para empezar con un clic.
- Resultados persistentes con `st.session_state` (cambiar de pestaña no borra nada).
- Historial de ecuaciones resueltas en un bloque con scroll en la barra lateral.
- Mensajes de error con sugerencia concreta (por ejemplo: "Parece que falta un `*`: ¿quisiste escribir `2*x`?").
- Opción de tema claro/oscuro; los gráficos de Plotly adaptan colores al tema.

---

## 4. Contratos de datos (`core/tipos.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class EstadoVerificacion(str, Enum):
    SIMBOLICA = "verificada_simbolica"
    NUMERICA = "verificada_numerica"
    NO_VERIFICADA = "no_verificada"

@dataclass
class Certificado:
    estado: EstadoVerificacion
    residuo_max: float | None
    dominio_valido: str
    notas: list[str] = field(default_factory=list)

@dataclass
class ResultadoSolucion:
    ecuacion_latex: str
    tipo: str                    # separable, lineal, ...
    camino: str                  # "analitica" | "numerica"
    solucion: Any                # expresión SymPy o objeto de solve_ivp
    certificado: Certificado
    advertencias: list[str] = field(default_factory=list)

@dataclass
class Paso:
    titulo: str
    explicacion: str
    latex: str

class EntradaInvalida(Exception): ...
class SolucionNoDisponible(Exception): ...
class TiempoAgotado(Exception): ...
```

---

## 5. Batería mínima de pruebas (`tests/bateria_edos.py`)

| EDO | Tipo | Solución esperada |
|---|---|---|
| `y' = y` , `y(0)=1` | separable/lineal | `exp(x)` |
| `y' = -2*y` , `y(0)=3` | lineal | `3*exp(-2*x)` |
| `y' + y = x` | lineal | `x - 1 + C*exp(-x)` |
| `y' = x*y` | separable | `C*exp(x**2/2)` |
| `y' = y*(1-y)` | logística | equilibrios 0 (inestable) y 1 (estable) |
| `y' = y**2` , `y(0)=1` | explosión | explota en `x = 1` |
| `y' = y**(1/3)` , `y(0)=0` | no unicidad | detectar y avisar |
| `2*x*y + (x**2+1)*y' = 0` | exacta | `y = C/(x**2+1)` |
| `y' + y = y**2` | Bernoulli | verificada |
| `y' = x*y + sin(x)` | sin forma simple | camino numérico verificado |

Criterios globales de prueba:
- `pytest` en verde en todas las fases.
- Cobertura mínima del 80 % en `core/`.
- Ninguna prueba depende de internet ni de la capa de IA.

---

## 6. Criterios de calidad final (definición de "terminado")

- [x] Las 8 fases completas y con pruebas en verde.
- [x] Toda solución mostrada incluye certificado de verificación.
- [x] La app funciona sin internet y sin la capa de IA.
- [ ] La interfaz se ve bien en 360 px, 768 px y 1440 px de ancho, sin scroll horizontal de página. *(CSS responsive implementado; falta revisión visual en esos tres anchos.)*
- [x] Las áreas largas tienen scroll propio y los espacios son cómodos.
- [x] Misma entrada y misma semilla producen siempre el mismo resultado.
- [ ] `README.md` con instalación (`pip install -r requirements.txt`), ejecución (`streamlit run app.py`), capturas y ejemplos. *(Instalación, ejecución y ejemplos documentados; faltan capturas.)*
- [x] Informe PDF exportable con enunciado, procedimiento, gráficas y certificado.

---

## 7. Orden de trabajo sugerido para el agente

1. Crear estructura de carpetas, `requirements.txt` y `pyproject.toml`.
2. Implementar Fase 1 con sus pruebas y una UI mínima (`app.py` con la pestaña **Resolver**).
3. Implementar la Fase 2 y mostrar el certificado en la UI.
4. Aplicar el CSS de la sección 3.6 desde el inicio para que todas las pestañas nuevas hereden el diseño.
5. Agregar una pestaña por fase, siguiendo la sección 3.4.
6. Cerrar con README, informes y revisión responsive.

> Al finalizar cada fase, actualiza este archivo marcando las casillas completadas y anota en una sección `## Registro de avance` qué se hizo y qué quedó pendiente.

## Registro de avance

**Estado:** fases 1–8 implementadas sobre el motor `odecalc` existente, sin
duplicar la lógica matemática ni romper las interfaces Tk/web anteriores.

### Qué se hizo

1. **Núcleo (`core/`).** Contratos tipados y `dataclass` en `tipos.py`; parser
   flexible con lista blanca; clasificador; solucionador simbólico y numérico
   (Euler, Heun, RK4 propios y RK45/DOP853/BDF/Radau de SciPy); orquestador
   híbrido con timeout real de 10 s en proceso aparte y degradación a numérico;
   verificador con residuo simbólico/numérico y certificado; análisis de
   existencia, unicidad, explosión y singularidades.
2. **Análisis.** Campo de direcciones con clic → traza, equilibrios,
   estabilidad, fase, isóclinas, bifurcación y comportamiento asintótico;
   convergencia con orden empírico, benchmark y detección de rigidez con cambio
   automático a BDF/Radau; ajuste de exponencial/logístico/Gompertz/Newton con
   AIC/BIC, intervalos de confianza, sensibilidad local y predicción con banda;
   Monte Carlo y Sobol deterministas con semilla configurable (42 por defecto).
3. **Aprendizaje y entrega.** Pasos en LaTeX para los cuatro tipos principales,
   corrector línea a línea con pistas, generador de ejercicios verificados,
   perfil persistente, seis modelos aplicados, exportación PDF/LaTeX y capa de
   IA opcional que **nunca** calcula soluciones.
4. **Interfaz.** `ui/streamlit_app.py` con siete pestañas, CSS responsive,
   espaciado generoso, contenedores con scroll propio, tema claro/oscuro,
   persistencia por `session_state` y mensajes de error sin trazas crudas.
   `app.py` enruta a Streamlit sólo cuando está disponible su runtime; si no,
   conserva la interfaz Tk clásica. Las ecuaciones con parámetros se dirigen a
   **Incertidumbre**/**Cualitativo** con un aviso en lugar de un error críptico.
5. **Correcciones de compatibilidad.** `y^(2)` y `(y)^(1/3)` ahora se parsean
   correctamente (arreglo en `odecalc/parsing/parser.py`); las ecuaciones
   parametrizadas se aceptan sólo donde tienen sentido mediante
   `parsear_con_parametros`; la extracción de ramas implícitas corre con timeout
   de 2 s y degrada a la solución implícita verificada.
6. **Pruebas.** `tests/edolab/` cubre contratos, parser, híbrido, certificados,
   explosión (`y' = y²`, x ≈ 1), no unicidad (`y' = y^(1/3)`), equilibrios
   logísticos, orden empírico de RK4 (≈ 3.96), recuperación de parámetros
   logísticos, Monte Carlo reproducible, Sobol, corrector, informes, modelos e
   importación de UI. Resultado: **27 pruebas en verde**; la suite completa del
   repositorio (incluida la batería heredada de 105 ecuaciones) terminó con
   **470 pruebas en verde**. Pruebas de humo con
   `AppTest`: render inicial, resolver, comparación, convergencia, carga y
   ajuste de datos, generación de ejercicio, PDF, Monte Carlo (300/300
   trayectorias) y Sobol sin errores de página.

### Pendiente o no verificado

- Capturas de pantalla para el README y revisión visual real a 360/768/1440 px
  (el CSS responsive está implementado, pero no se comprobó en navegador).
- Medición formal de cobertura del 80 % en `core/`.
- Avisos de deprecación de `use_container_width` con Streamlit 1.67 (sigue
  funcionando; conviene migrar a `width='stretch'` al actualizar el mínimo de
  versión).
- Se creó un commit únicamente con los archivos de EDO-Lab. Quedan fuera, a la
  espera de una decisión, el paquete `odecalc/` (del que depende `core/`) y el
  resto de cambios previos del árbol.