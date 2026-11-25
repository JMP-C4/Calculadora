# Plan de mejoras: ODE Calculator (nivel científico)

> Documento de traspaso para un agente de código (OpenCode). Léelo completo antes de tocar código.
> Repositorio: `JMP-C4/Calculadora` (Python, SymPy, SciPy, Matplotlib, tkinter).

---

## 1. Objetivo

Convertir el proyecto en una herramienta **profesional** que, dada **cualquier EDO de primer orden** (y después orden superior), entregue todo lo que un científico o ingeniero necesita:

- Clasificación completa (todos los métodos aplicables, no solo uno).
- Solución general y particular, **verificada automáticamente**.
- Procedimiento paso a paso con justificación.
- Condiciones de validez, soluciones singulares y dominio.
- Respaldo numérico cuando no exista forma cerrada.
- Gráficas (campo de direcciones, familia de curvas, solución particular).
- Dos interfaces sobre **un solo motor**: escritorio y web.

**Principio rector:** nunca devolver una respuesta no verificada como si fuera correcta.

---

## 2. Estado actual (auditoría)

### 2.1 Qué hay

- `math_engine/parser.py`: solo acepta `dy/dx = f(x,y)` y `y' = f(x,y)`.
- `math_engine/symbolic_solver.py`: llama a `sp.dsolve` y aplica condiciones iniciales.
- `math_engine/step_generator.py`: clasifica en un único tipo y genera pasos para separable, lineal, exacta, homogénea y Bernoulli.
- `math_engine/numeric_solver.py`: RK45 con `solve_ivp`.
- `ui/`: interfaz tkinter. `data/exercises.py`: 18 ejercicios. 31 pruebas del motor pasan.

### 2.2 Fallos reproducidos (casos de regresión obligatorios)

Todos se escriben como `y' = f(x,y)`.

| # | Ejercicio | Entrada | Problema observado |
|---|---|---|---|
| 1 | Exacta | `-(2*x*y+1)/(x**2+3*y**2)` | Clasifica bien, pero `dsolve` se cuelga más de 25 s y no da solución. Esperada: `x²y + x + y³ = C` (implícita). |
| 2 | Riccati | `y**2 - x*y + 1` | Sin solución ni método propio. |
| 3 | Sustitución `u = x+y` | `(x+y)**2` | Devuelve exponenciales complejas; se espera `y = tan(x + C) − x`. |
| 4 | Lineal con integral no elemental | `exp(-x**2)*y + 1` | **Respuesta incorrecta**: deja `Integral` con `y(x)` dentro. La verificación no da residuo 0. |
| 5 | Bernoulli `n = 1/2` | `y/x + sqrt(y)` | Clasificada como `otro`. Solo reconoce `n` entero mayor que 1. |
| 6 | No exacta, `μ(x)` | `-(x**2+y**2+x)/(x*y)` | Clasificada como `otro`, sin pasos. |
| 7 | No exacta, `μ(y)` | `-(y)/(2*x*y - exp(-2*y))` | Clasificada como `otro`, sin pasos. |
| 8 | Reducible a homogénea | `(x+y+1)/(x-y-3)` | Clasificada como `otro`, sin pasos. |
| 9 | Clairaut | `y = x*y' + y'**2` | El parser lo rechaza. |

### 2.3 Problemas estructurales

1. El motor **depende de `dsolve`** y los métodos propios solo sirven para explicar. Si `dsolve` falla, no hay plan B.
2. La clasificación es una cascada de `if` que devuelve **un solo tipo**.
3. **No hay verificación** de la solución.
4. **No hay tiempo límite**: los cálculos pueden colgarse.
5. El parser no acepta formas de libro: `y' + P(x)y = Q(x)`, `M dx + N dy = 0`, formas implícitas.
6. `sp.sympify` evalúa código: **riesgo de seguridad** si se expone en la web.
7. La interfaz tkinter está acoplada a la lógica; no se puede reutilizar en web.
8. Higiene del repo: ruta personal en el README, archivo `.config.kiro`, dependencias fijadas de forma muy rígida.

---

## 3. Arquitectura objetivo

```
ode-calculator/
├── odecalc/                    # paquete puro, SIN tkinter ni web
│   ├── parsing/                # parser seguro + formas de entrada
│   ├── classify/               # detector multi-método
│   ├── methods/                # un módulo por método (resuelve + pasos)
│   ├── verify/                 # verificación y análisis de validez
│   ├── numeric/                # respaldo numérico
│   ├── plotting/               # datos de gráficas (sin UI)
│   ├── api.py                  # función pública solve(...) -> SolveResult
│   └── models.py               # dataclasses de resultado
├── apps/
│   ├── desktop/                # interfaz tkinter (consume odecalc)
│   └── web/                    # FastAPI + frontend, o Pyodide
├── tests/
│   ├── unit/ · integration/ · regression/ · property/
│   └── bank/                   # banco de 100+ ejercicios con respuestas
└── docs/
```

**Regla:** `odecalc` no importa nada de `apps/`. Las dos interfaces solo llaman a `odecalc.api.solve`.

### 3.1 Contrato de salida (`SolveResult`)

```python
@dataclass
class SolveResult:
    input_latex: str
    standard_form: str            # y' = f(x,y) y/o M dx + N dy = 0
    classifications: list[Match]  # TODOS los métodos aplicables, con evidencia
    chosen_method: str
    general: Solution | None      # explícita o implícita (flag)
    particular: Solution | None
    steps: list[Step]             # LaTeX + justificación + ASCII
    verification: Verification   # residuo simbólico/numérico, estado ok/fail
    validity: Validity            # dominio, intervalo, divisiones por cero
    singular_solutions: list[Solution]
    numeric: NumericResult | None
    warnings: list[str]
    timing_ms: dict[str, float]
```

---

## 4. Tareas por fase

### Fase 0: Higiene (rápida)

- [ ] Quitar la ruta personal del README y el archivo `.config.kiro`.
- [ ] Añadir `LICENSE`, `.editorconfig`, `CONTRIBUTING.md`.
- [ ] Relajar versiones fijas a rangos (`sympy>=1.13,<1.15`, etc.) y añadir CI (GitHub Actions) que corra las pruebas del motor sin pantalla.
- [ ] Separar dependencias: núcleo, desktop, web, dev.

### Fase 1: Núcleo seguro y aislado

- [ ] Mover el motor a `odecalc/` sin dependencias de interfaz.
- [ ] **Parser seguro:** reemplazar `sympify` por `parse_expr` con lista blanca de nombres y transformaciones controladas (sin `eval` arbitrario). Probar con entradas maliciosas (`__import__`, `open`, atributos).
- [ ] Aceptar todas estas formas de entrada:
  - `y' = f(x,y)`, `dy/dx = f(x,y)`
  - `y' + P(x) y = Q(x)`
  - `M(x,y) dx + N(x,y) dy = 0`
  - Formas implícitas `F(x, y, y') = 0` (Clairaut, Lagrange)
  - Multiplicación implícita (`2x`, `3y^2`) y potencia con `^`
- [ ] Mensajes de error claros y en español.
- [ ] **Tiempo límite** configurable por etapa (proceso aparte con timeout; no solo hilos).

### Fase 2: Clasificador multi-método

Devolver **todos** los métodos aplicables con la evidencia (por qué aplica). Condiciones de detección:

| Método | Condición |
|---|---|
| Separable | `y' = g(x)h(y)` |
| Lineal | `y' + P(x)y = Q(x)` |
| Exacta | `∂M/∂y = ∂N/∂x` |
| Factor integrante `μ(x)` | `(M_y − N_x)/N` depende solo de `x` |
| Factor integrante `μ(y)` | `(N_x − M_y)/M` depende solo de `y` |
| Factor integrante `μ(xy)`, `μ(x+y)`, `μ(x²+y²)` | Reglas generales por sustitución |
| Homogénea (grado 0) | `f(tx,ty) = f(x,y)` |
| Reducible a homogénea | `(a₁x+b₁y+c₁)/(a₂x+b₂y+c₂)`, con rectas que se cortan o paralelas |
| Bernoulli | `y' + P y = Q yⁿ`, **cualquier `n` real** (incluye `n = 1/2`, negativo) |
| Riccati | `y' = q₀ + q₁y + q₂y²` (con solución particular conocida o buscada) |
| Sustitución `u = ax+by+c` | `y' = F(ax+by+c)` |
| Clairaut / Lagrange | `y = xy' + f(y')`, `y = xf(y') + g(y')` |
| Ecuaciones en `x = f(y, y')` | Intercambiar variables |
| Otros | Sustituciones comunes: `u = y/x`, `u = y^(1-n)`, `u = xy` |

- [ ] Prioridad configurable cuando varios métodos aplican; el usuario puede **elegir el método** y ver comparaciones.

### Fase 3: Solucionadores propios por método

Cada método es un módulo con `matches()`, `solve()` y `steps()`. **`dsolve` queda solo como respaldo**, y marcado como tal.

- [ ] Separable, lineal (factor integrante), exacta (con construcción de `F(x,y) = C`), `μ(x)`, `μ(y)`, homogénea, Bernoulli general, reducible a homogénea, `u = ax+by+c`, Riccati, Clairaut, Lagrange.
- [ ] Soluciones **implícitas** como ciudadano de primera clase: `F(x,y) = C` con flag, y despeje explícito solo cuando sea posible.
- [ ] **Integrales no elementales:** dejar `∫` explícita en `x` (nunca con `y(x)` dentro), o expresar con funciones especiales (`erf`, `Ei`, `Si`) cuando existan.
- [ ] Detección de **soluciones singulares y perdidas** al dividir (por ejemplo `y = 0` en separables y Bernoulli).
- [ ] **Condiciones iniciales:** resolver `C`, elegir la rama correcta cuando hay varias y reportar si el PVI no tiene solución o no es única.
- [ ] Pasos con LaTeX, justificación, y notas sobre cada simplificación.

### Fase 4: Verificación y validez (crítico)

- [ ] **Verificar siempre:** sustituir en la EDO, simplificar el residuo; si no es 0, verificar numéricamente en puntos aleatorios del dominio.
- [ ] Si falla la verificación: no presentar como correcta; mostrar advertencia y probar el siguiente método.
- [ ] Para soluciones implícitas, verificar por derivación implícita.
- [ ] **Intervalo de validez** de la solución del PVI (teorema de existencia y unicidad, puntos singulares, divisiones por cero, raíces cuadradas negativas).
- [ ] Reportar dominio, comportamiento asintótico y puntos de equilibrio.

### Fase 5: Respaldo numérico y análisis

- [ ] Cuando no hay forma cerrada: `solve_ivp` con `RK45`/`DOP853`/`LSODA` y tolerancias configurables.
- [ ] Detección de **rigidez** (stiff) y cambio automático a `Radau`/`BDF`.
- [ ] Detección de **explosión en tiempo finito** (blow-up) y reporte del intervalo máximo.
- [ ] Estimación de error y comparación contra la solución simbólica cuando existe.
- [ ] Análisis cualitativo: campo de direcciones, isoclinas, puntos de equilibrio y su estabilidad, líneas de fase para ecuaciones autónomas.

### Fase 6: Interfaces

**Escritorio (tkinter):**
- [ ] Adaptar la interfaz actual para consumir `odecalc.api.solve`.
- [ ] Cálculo en segundo plano con cancelación real.
- [ ] Mostrar todos los métodos aplicables, estado de verificación y advertencias.
- [ ] Historial de cálculos, exportar a PDF/LaTeX/PNG.

**Web:**
- [ ] Opción A: **FastAPI** con endpoint `POST /solve` (con límites de tiempo, tamaño y tasa por usuario).
- [ ] Opción B: **Pyodide** (SymPy en el navegador, sin servidor).
- [ ] Renderizado con KaTeX o MathJax, gráficas interactivas (Plotly o similar).
- [ ] Teclado matemático en pantalla y enlace compartible por ejercicio.
- [ ] Diseño responsivo y accesible.

### Fase 7: Más allá de primer orden (después de cerrar fases 1 a 6)

- [ ] Segundo orden: coeficientes constantes, coeficientes indeterminados, variación de parámetros, Cauchy-Euler, reducción de orden.
- [ ] Orden `n` lineal, series de potencias, transformada de Laplace.
- [ ] Sistemas lineales (valores propios, matriz exponencial) y análisis de fase 2D.
- [ ] Ecuaciones diferenciales exactas de orden superior y problemas de contorno.

---

## 5. Pruebas y calidad

- [ ] **Banco de 100 o más ejercicios** (libros clásicos: Zill, Boyce y DiPrima, Simmons, Kreyszig), en un archivo de datos con entrada, método esperado y solución esperada.
- [ ] Una prueba parametrizada que, para cada ejercicio, comprueba: clasificación, verificación de residuo 0 y solución particular con PVI.
- [ ] Todos los casos de la sección 2.2 como **pruebas de regresión**.
- [ ] Pruebas de propiedades con Hypothesis: soluciones generadas satisfacen la EDO.
- [ ] Pruebas de seguridad del parser (entradas maliciosas) y de rendimiento (nada tarda más del límite).
- [ ] Cobertura mínima del 85 % en `odecalc/`. CI obligatorio antes de fusionar.

## 6. Criterios de aceptación (definición de "terminado")

1. Los 9 casos de la tabla 2.2 se resuelven (o se reportan correctamente como no elementales con respaldo numérico) y **todos verifican residuo 0**.
2. Ningún cálculo bloquea la aplicación más allá del límite configurado.
3. El parser acepta las formas de libro de la Fase 1 y rechaza código malicioso.
4. Para cada ejercicio, el resultado indica **todos** los métodos aplicables, el elegido, los pasos, la verificación y el dominio de validez.
5. El mismo `odecalc` funciona desde escritorio y web sin cambios.
6. El banco de 100+ ejercicios pasa en CI.

## 7. Orden de trabajo sugerido para el agente

1. Fase 0 y mover el motor a `odecalc/` (sin cambiar comportamiento; pruebas verdes).
2. Parser seguro y nuevas formas de entrada.
3. **Verificación automática** (esto detecta los fallos de los demás pasos).
4. Clasificador multi-método y solucionadores propios, de uno en uno, cada uno con sus pruebas del banco.
5. Respaldo numérico y análisis cualitativo.
6. Interfaces (escritorio primero, luego web).
7. Orden superior.

> **Regla de oro para el agente:** cada método nuevo entra con sus pruebas, su verificación y sus pasos explicados. Nada se da por correcto sin residuo verificado.
