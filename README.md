# ODE Calculator

[![Tests](https://github.com/JMP-C4/Calculadora/actions/workflows/tests.yml/badge.svg)](https://github.com/JMP-C4/Calculadora/actions/workflows/tests.yml)

Calculadora científica de ecuaciones diferenciales ordinarias de primer orden.
Clasifica cada ecuación con **todos** los métodos aplicables, resuelve con
métodos propios, **verifica el residuo** antes de presentar una respuesta y
ofrece respaldo numérico cuando no existe forma cerrada.

El proyecto separa por completo el motor matemático (`odecalc`) de las
interfaces. Escritorio, web y scripts consumen la misma función:
`odecalc.api.solve`.

---

## 🧪 EDO-Lab: laboratorio Streamlit

Sobre el mismo motor verificado se añade **EDO-Lab**, un laboratorio docente con
siete pestañas: resolver, análisis cualitativo, análisis numérico, ajuste de
datos, incertidumbre, aprendizaje e informes. Toda solución mostrada lleva un
**certificado de verificación** (`VERIFICADA_SIMBOLICA`, `VERIFICADA_NUMERICA` o
`NO_VERIFICADA`).

### Instalación y ejecución

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

La aplicación abre en `http://localhost:8501`. No necesita internet ni clave de
IA para funcionar. `app.py` detecta el runtime de Streamlit; si se ejecuta con
Python normal conserva la interfaz Tk clásica.

### Qué incluye

| Pestaña | Contenido |
| --- | --- |
| **Resolver** | Entrada flexible, PVI, solución analítica o numérica, certificado, pasos, campo de direcciones con clic para trazar una curva, modelos aplicados y explicación local. |
| **Cualitativo** | Equilibrios, estabilidad, línea de fase, isóclinas, comportamiento asintótico y diagrama de bifurcación con parámetro `mu`. |
| **Numérico** | Euler, Heun, RK4, RK45, DOP853, BDF y Radau; comparación, error frente a `h`, orden empírico, benchmark y detección de rigidez. |
| **Datos** | CSV/Excel con detección de columnas, modelos exponencial, logístico, Gompertz y Newton, selección AIC/BIC, intervalos de confianza, sensibilidad y predicción con banda. |
| **Incertidumbre** | Monte Carlo reproducible sobre parámetros y `y₀`, bandas de predicción e índices de Sobol con SALib. |
| **Aprender** | Ejercicios generados y verificados por el motor, corrector línea a línea con pista del primer error y perfil de progreso persistente. |
| **Informes** | PDF y LaTeX con enunciado, método, pasos, gráfica, tabla de errores y certificado. |

### Ejemplos rápidos

Prueba en la barra lateral:

```text
y' = y*(1-y)                 # logística: equilibrios 0 (inestable) y 1 (estable)
y' = x*y + sin(x)            # sin forma cerrada: respaldo numérico verificado
y' = y^2                     # explosión en x ≈ 1 para y(0)=1
y' = y^(1/3)                 # pérdida de unicidad en y(0)=0
2*x*y + (x^2+1)*y' = 0       # exacta
```

En **Datos** puedes cargar `data/ejemplos/logistico.csv`,
`enfriamiento.csv`, `crecimiento.csv` o `decaimiento.csv`; el ajuste logístico
recupera `r` y `K` con menos de 5 % de error y el AIC prefiere el modelo
correcto.

### Capa de IA opcional

La IA **nunca** calcula soluciones. Sólo puede proponer una ecuación (validada
después por el parser) o reescribir una explicación de un resultado ya
certificado. Está apagada por defecto:

```bash
export ANTHROPIC_API_KEY="..."
export EDO_LAB_IA_ACTIVA=1
export EDO_LAB_IA_MODELO="claude-sonnet-4-5"   # opcional
```

Sin esas variables, todas las pestañas funcionan con reglas y explicaciones
locales.

### Pruebas de EDO-Lab

```bash
python3 -m pytest tests/edolab -q
python3 -m pytest tests/edolab -q -m "not slow"
```

Las pruebas cubren los contratos, el parser, la solución híbrida, los
certificados, explosión y no unicidad, equilibrios, orden empírico de RK4,
ajuste con datos sintéticos, Monte Carlo determinista, Sobol, corrector,
informes, modelos y la importación de la interfaz.

### Estructura nueva

```text
core/                    # lógica matemática pura, sin UI
├── tipos.py             # dataclasses y excepciones propias
├── parser.py · clasificador.py · solver_simbolico.py · solver_numerico.py
├── hibrido.py · verificador.py · existencia.py · pasos.py
├── cualitativo.py · convergencia.py · ajuste.py · incertidumbre.py
├── corrector.py · ejercicios.py · modelos.py · informes.py · ia_opcional.py
ui/
├── streamlit_app.py     # entrada de EDO-Lab
├── estilos.py · componentes.py · graficas.py
└── pagina_*.py          # una pestaña por archivo
data/
├── ejemplos/*.csv
└── perfil_estudiante.json
tests/edolab/            # pruebas del laboratorio
```

---

## Principios

- **Nada se presenta como correcto sin verificar.** Cada solución se sustituye
  en la EDO y se comprueba simbólica y numéricamente. Si el residuo no es cero,
  se marca como fallida y se prueba el siguiente método.
- **Clasificación multi-método.** El resultado incluye todas las coincidencias
  con su evidencia, la prioridad y el método finalmente elegido.
- **Soluciones implícitas de primera clase.** Se conservan como `F(x, y) = C`
  cuando no conviene (o no es posible) despejar `y`.
- **Integrales no elementales correctas.** Se dejan como `∫` explícita en `x`,
  nunca con `y(x)` dentro de la integral.
- **Parser seguro.** Lista blanca de nombres y `parse_expr` con
  `__builtins__` vacío; no se evalúa código arbitrario.
- **Tiempo límite real.** El cálculo puede ejecutarse en un proceso hijo y
  cancelarse al superar el límite configurado.

## Formas de entrada admitidas

```text
y' = f(x, y)
dy/dx = f(x, y)
y' + P(x)*y = Q(x)
M(x, y) dx + N(x, y) dy = 0
F(x, y, y') = 0          # por ejemplo, Clairaut y = x*y' + y'**2
```

También se acepta multiplicación implícita (`2x`, `3y^2`), el operador `^`
como potencia y funciones habituales (`sin`, `cos`, `exp`, `log`, `sqrt`,
`tan`, `atan`, `erf`, `Integral`, etc.).

Además, puedes pegar fórmulas en LaTeX copiadas de un libro o editor:

```text
$$\frac{dy}{dx} = \frac{x^2}{y}$$
$\frac{dy}{dx} = \sqrt{x} + \sin(x)$
\frac{\mathrm{d}y}{\mathrm{d}x} = x^{2} + 3y^{2}
```

Se reconocen fracciones (`\frac`, `\dfrac`), raíces (`\sqrt`, `\sqrt[n]`),
potencias (`x^{2}`), funciones (`\sin`, `\cos`, `\ln`, `\exp`...), `\cdot`,
`\times`, `\left`/`\right` y delimitadores `$$...$$`, `$...$` o `\[...\]`.
La conversión no relaja la validación: el texto resultante sigue pasando por
la lista blanca del parser.

## Métodos implementados

| Familia | Métodos |
| --- | --- |
| Básicos | Separable, lineal de primer orden, exacta |
| Factores integrantes | `μ(x)`, `μ(y)`, `μ(xy)`, `μ(x+y)`, `μ(x²+y²)` |
| Cambios de variable | Homogénea, reducible a homogénea, `u = ax+by+c` |
| No lineales | Bernoulli para cualquier `n` real, Riccati |
| Implícitas | Clairaut y Lagrange |
| Respaldo | `sympy.dsolve`, marcado como tal y siempre verificado |

## Instalación

Requisitos: Python 3.10–3.12.

Núcleo matemático (sin interfaz gráfica):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Interfaz de escritorio (añade Matplotlib y Pillow; requiere Tk del sistema):

```bash
pip install -e ".[desktop]"
# Ubuntu/Debian: sudo apt-get install -y python3-tk python3-pil.imagetk
# El Pillow de pip ya incluye ImageTk; el paquete del sistema necesita
# python3-pil.imagetk para el backend Tk de Matplotlib.
python3 -c "import tkinter; from PIL import ImageTk; print(tkinter.TkVersion)"
```

Desarrollo y pruebas:

```bash
pip install -e ".[dev]"
```

Si prefieres no instalar el paquete, define `PYTHONPATH=.` al ejecutar desde la
raíz del repositorio.

## Uso rápido

### Python

```python
from odecalc.api import solve

resultado = solve("y' = x + y", x0=0, y0=1, timeout=20)

print(resultado.chosen_method)
print(resultado.general.latex)
print(resultado.particular.latex)
print(resultado.verification.status)          # "ok"
print(resultado.particular_verification.status)
print([m.method for m in resultado.classifications])
```

`SolveResult` incluye, entre otros campos:

| Campo | Contenido |
| --- | --- |
| `input_latex`, `standard_form` | Entrada normalizada y forma estándar |
| `classifications` | Todos los métodos aplicables con evidencia |
| `chosen_method` | Método usado para la solución presentada |
| `general`, `particular` | Soluciones explícitas o implícitas |
| `steps` | Pasos con LaTeX, justificación y texto ASCII |
| `verification`, `particular_verification` | Estado del residuo |
| `validity` | Dominio, intervalo y puntos singulares |
| `singular_solutions` | Soluciones singulares detectadas |
| `numeric` | Respaldo numérico (`RK45`, `DOP853`, `Radau`, `BDF`, `LSODA`) |
| `warnings`, `timing_ms`, `attempts` | Advertencias, tiempos y métodos intentados |

Para forzar un método concreto:

```python
resultado = solve("dy/dx = x + y", method="linear")
```

### Escritorio

```bash
python -m apps.desktop.app
# o, tras instalar con el extra desktop:
ode-calculator
```

La ventana usa una cabecera única con menús desplegables (**Resolver**,
**Lienzo**, **Ejercicios** y **Ayuda**) y un tablero en estilo *bento*: editor de
la EDO, lienzo interactivo y la tarjeta **Salida del motor**. Las acciones
(escribir, insertar símbolos, resolver, limpiar y salir) viven solo en
**Resolver**; los tipos de gráfica y la exportación, solo en **Lienzo**; los
ejemplos, solo en **Ejercicios**. Incluye atajos de teclado. El cálculo se
ejecuta en segundo plano y el tiempo límite se aplica en el motor.

La tarjeta **Salida del motor** apila **Resultado**, **Métodos**, **Pasos** y
**Advertencias** dentro de un área con scroll general, de modo que siempre se
puede llegar a todos los bloques; cada bloque conserva además su propio scroll
para textos largos. Los menús **Ayuda → Manual de instrucciones** abren una guía
de uso completa (formatos de entrada, condiciones iniciales, lectura de la
salida, lienzo, ejercicios, atajos y solución de problemas).

El selector del lienzo incluye todos los tipos disponibles:

| Gráfica | Cuándo está disponible |
| --- | --- |
| Solución `y(x)` | Solución particular explícita o curva numérica |
| Campo de direcciones | Cualquier EDO con `y' = f(x, y)` despejable |
| Isoclinas | Se calculan las curvas `f(x, y) = k` para `k = -1, 0, 1` |
| Familia de curvas | Solución general explícita o despejable con una constante |
| Línea de fase | EDOs autónomas `y' = f(y)` |
| Puntos de equilibrio | EDOs autónomas con raíces reales de `f(y) = 0` |
| Superficie 3D | Superficie `z = f(x, y)` del campo de pendientes |

Si la ecuación no permite el tipo de gráfica seleccionado, el lienzo muestra
un aviso visible en lugar de una figura vacía. Por ejemplo, la línea de fase
avisa cuando la EDO no es autónoma.

### Web

```bash
python -m apps.web.server --host 127.0.0.1 --port 8000
# o, tras instalar:
ode-calculator-web --port 8000
```

Abre `http://127.0.0.1:8000` y usa el workspace: portada de producto, navegación
con desplegables, editor, lienzo Plotly con anotaciones, exportación PNG y una
biblioteca de 12 ejercicios guiados. Si el puerto 8000 ya está en uso, indica
otro, por ejemplo `--port 8001`. También puedes llamar directamente a la API:

```bash
curl -s http://127.0.0.1:8000/solve \
  -H 'Content-Type: application/json' \
  -d '{"equation": "y'"'"' = x + y", "x0": 0, "y0": 1}'
```

La página incluye la misma sección **Gráfica** que el escritorio: un menú
desplegable con los 7 tipos (los mismos del selector de Tk) dibujados con
Plotly (CDN). Los tipos y avisos son los de la tabla anterior: si un modo no
aplica (por ejemplo la línea de fase con una EDO no autónoma), la sección
muestra el aviso en lugar de la figura.

#### Diseños de la interfaz

El engranaje de la barra superior abre **Configuración de diseño**, con tres
estilos inspirados en las propuestas de Figma:

| Diseño | Estilo |
| --- | --- |
| **Estudio 3 paneles** | Predeterminado: biblioteca, lienzo e inspector con acento naranja. |
| **Cuaderno** | Papel cálido, serif y margen de notas. |
| **Lienzo flotante** | Cuadrícula lila, acento índigo y tarjetas flotantes. |

El diseño elegido se conserva en la cookie `ode-design` (`path=/`,
`SameSite=Lax`, 365 días) y se restaura al recargar la página. El interruptor
de claro/oscuro funciona de forma independiente y recuerda la preferencia por
diseño en `localStorage` con la clave `ode-theme:<diseño>`; también respeta la
preferencia `ode-theme` de versiones anteriores.

Los datos los calcula el endpoint `POST /plot`, que acepta el mismo cuerpo
que `/solve` más `"mode"` (`solution`, `direction_field`, `isoclines`,
`family`, `phase_line`, `equilibria`, `surface`):

```bash
curl -s http://127.0.0.1:8000/plot \
  -H 'Content-Type: application/json' \
  -d '{"equation": "y'"'"' = x + y", "x0": 0, "y0": 1, "mode": "solution"}'
```

La respuesta trae `available`, `notice` y `figure`; si la gráfica no es
posible, `available` es `false` y `notice` explica el motivo. El servidor
limita el tamaño del cuerpo, el tiempo de cálculo y la tasa de
peticiones. No usa FastAPI ni dependencias externas (Plotly solo se carga
desde el navegador).

### Simbología y serialización

```python
from odecalc.serialization import result_to_dict

datos = result_to_dict(resultado)   # apto para JSON
```

## Pruebas

Suite del motor (rápida, sin Tk):

```bash
python3 -m pytest tests/unit tests/regression tests/integration tests/property -q
```

Banco de 105 ejercicios clásicos con PVI (más lento):

```bash
python3 -m pytest tests/bank -q -m bank
```

Cobertura mínima del 85 % en `odecalc/`:

```bash
python3 -m pytest tests/unit tests/regression tests/integration tests/property tests/bank \
  -q --cov=odecalc --cov-report=term-missing --cov-fail-under=85
```

Suite completa, incluida la interfaz legacy (requiere Tk y, en servidores sin
pantalla, Xvfb):

```bash
xvfb-run -a python3 -m pytest tests/ -q
```

Marcadores disponibles: `bank` (banco de ejercicios), `legacy` (suite antigua)
y `slow` (pruebas largas). Si Tk o Pillow con `ImageTk` no están disponibles,
los tests que los importan se omiten automáticamente durante la recolección.

## Estructura

```text
.
├── odecalc/                 # Motor puro: sin tkinter ni frameworks web
│   ├── parsing/             # Parser seguro y formas de entrada
│   ├── classify/            # Clasificador multi-método
│   ├── methods/             # Un módulo por método
│   ├── verify/              # Verificación, PVI y validez
│   ├── numeric/             # Respaldo numérico y rigidez
│   ├── plotting/            # Datos de gráficas sin UI
│   ├── api.py               # solve(...) -> SolveResult
│   ├── models.py            # Contrato de datos
│   └── serialization.py     # Conversión a JSON
├── apps/
│   ├── desktop/             # Interfaz tkinter (app.py + plot_panel.py)
│   └── web/                 # Servidor HTTP, endpoint /plot y frontend Plotly
│       └── static/          # index.html, styles.css y app.js (diseños y temas)
├── tests/
│   ├── unit/ · regression/ · integration/ · property/
│   └── bank/                # 105 ejercicios con PVI
├── math_engine/, ui/, app.py  # Implementación legacy (compatibilidad)
├── pyproject.toml
├── CONTRIBUTING.md
└── LICENSE
```

## Seguridad

- El parser rechaza `__import__`, `open`, atributos, guiones bajos y cualquier
  nombre fuera de la lista blanca.
- Las expresiones se construyen con `sympy.parse_expr` y un diccionario de
  símbolos y funciones permitidas.
- La API web valida tipos, tamaño, rangos y tiempo máximo antes de resolver.
- Ninguna interfaz contiene lógica matemática propia.

## Alcance y limitaciones

- El alcance actual es **primer orden**. Las fases de orden superior están
  planificadas en `PLAN_MEJORAS_ODE_CALCULATOR.md`.
- Cuando no hay forma cerrada, se devuelve el respaldo numérico y se indica
  explícitamente que la solución simbólica no está disponible.
- Algunas integrales muy costosas pueden agotar el tiempo límite; en ese caso
  el resultado reporta el error en lugar de bloquear la aplicación.

## Contribuir

Consulta `CONTRIBUTING.md`. Cada método nuevo debe entrar con sus pruebas, su
verificación de residuo y sus pasos explicados.

## Licencia

MIT. Consulta `LICENSE`.
