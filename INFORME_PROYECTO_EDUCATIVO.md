# Documento Base para Informe de Proyecto Educacional: ODE Calculator / EDO-Lab

> **Propósito de este documento:** Recopilar de forma rigurosa las capacidades reales, fundamentos pedagógicos, arquitectura técnica, estado de madurez y limitaciones actuales del sistema **ODE Calculator / EDO-Lab** (en desarrollo activo, versión de referencia `2.0.0`), con el fin de servir como insumo directo para redactar el **planteamiento del problema, justificación, objetivos, marco conceptual, alcance, metodología y conclusiones** de un informe académico o proyecto educacional.

---

## 1. Ficha General del Proyecto

| Elemento | Descripción |
| :--- | :--- |
| **Nombre del sistema** | **ODE Calculator / EDO-Lab** (Laboratorio Inteligente de Ecuaciones Diferenciales Ordinarias de Primer Orden) |
| **Estado del proyecto** | **En desarrollo activo** (núcleo funcional y laboratorio docente operativos; en fase de consolidación arquitectónica y corrección de hallazgos de auditoría técnica) |
| **Público objetivo** | Estudiantes universitarios de ingeniería, ciencias y matemáticas; docentes de ecuaciones diferenciales y modelado matemático |
| **Alcance matemático actual** | Ecuaciones diferenciales ordinarias (EDOs) de **primer orden** (simbólicas, numéricas, cualitativas, ajuste a datos e incertidumbre) |
| **Principio rector** | *«Nada se presenta como correcto sin verificar»* / *«La IA propone, el motor matemático comprueba»* |
| **Tecnologías principales** | Python (3.10–3.12), SymPy, SciPy, NumPy, Matplotlib, Plotly, Pandas, Streamlit, SALib, ReportLab, Tkinter |
| **Conectividad requerida** | **Ninguna** para el núcleo y las 7 pestañas de EDO-Lab (funciona 100 % local sin internet ni API de IA; la capa de IA es opcional y está desactivada por defecto) |
| **Licencia** | MIT |

---

## 2. Planteamiento del Problema

### 2.1 Contexto educativo
El estudio de las Ecuaciones Diferenciales Ordinarias (EDOs) de primer orden constituye uno de los pilares formativos en carreras de ingeniería, física, biología y economía, ya que permite modelar fenómenos dinámicos como crecimiento poblacional, enfriamiento térmico, circuitos eléctricos, mezclas químicas y decaimiento radiactivo. Sin embargo, su enseñanza y aprendizaje suelen enfrentar una fuerte fragmentación entre el cálculo algebraico manual, la interpretación geométrica y la simulación computacional.

### 2.2 Problemática identificada
En el entorno académico actual se observan cuatro brechas principales que dificultan el aprendizaje significativo de las EDOs:

1. **Enfoque centrado en respuestas finales sin verificación ni justificación:**
   Muchas calculadoras simbólicas y sistemas basados en modelos de lenguaje (IA generativa) entregan una fórmula final sin mostrar los pasos intermedios ni comprobar matemáticamente si la expresión satisface la ecuación diferencial original o las condiciones iniciales. Esto fomenta la memorización mecánica y expone al estudiante a aceptar resultados erróneos o incompletos (por ejemplo, soluciones que omiten ramas, constantes o restricciones de dominio).
2. **Desconexión entre lo simbólico, lo cualitativo y lo numérico:**
   En clase, los estudiantes suelen ver por separado la resolución analítica (separables, lineales, exactas, Bernoulli), el análisis cualitativo (campos de direcciones, isóclinas, puntos de equilibrio, estabilidad, bifurcaciones) y los métodos numéricos (Euler, Heun, Runge-Kutta, rigidez). Las herramientas tradicionales rara vez integran estas tres perspectivas sobre un mismo problema y una misma interfaz didáctica.
3. **Brecha entre la teoría idealizada y los datos experimentales reales:**
   Los cursos introductorios trabajan principalmente con ecuaciones ya formuladas, pero los futuros ingenieros y científicos necesitan ajustar modelos diferenciales a series de datos experimentales (CSV/Excel), comparar modelos mediante criterios estadísticos (AIC/BIC) y cuantificar cómo la incertidumbre en parámetros o condiciones iniciales afecta las predicciones (Monte Carlo y sensibilidad).
4. **Falta de retroalimentación formativa paso a paso:**
   Cuando un estudiante resuelve una EDO a mano y comete un error algebraico o de integración en un paso intermedio, las plataformas convencionales suelen calificar únicamente el resultado final como «correcto» o «incorrecto», sin identificar exactamente en qué línea ocurrió la desviación ni ofrecer una pista pedagógica sin revelar la respuesta.

### 2.3 Formulación del problema (preguntas guía para el informe)
* **Pregunta general:** ¿Cómo diseñar e implementar un entorno computacional educativo abierto y verificable que integre resolución simbólica multi-método, análisis cualitativo, simulación numérica, ajuste de datos reales y retroalimentación paso a paso para fortalecer el aprendizaje de las ecuaciones diferenciales ordinarias de primer orden?
* **Preguntas específicas:**
  1. ¿De qué manera se puede garantizar que toda solución presentada al estudiante sea verificada automáticamente mediante residuo simbólico o numérico antes de mostrarse?
  2. ¿Cómo unificar en un flujo didáctico comprensible las dimensiones analítica, geométrica/cualitativa, numérica y de modelado empírico de las EDOs?
  3. ¿Cómo proporcionar práctica autónoma y corrección procedimental línea por línea sin depender de servicios externos de pago ni delegar el cálculo matemático a modelos de IA generativa?

---

## 3. Justificación del Proyecto

El desarrollo de **ODE Calculator / EDO-Lab** se justifica desde cuatro dimensiones complementarias:

### 3.1 Justificación pedagógica y didáctica
* **Aprendizaje activo y comprensivo:** Al desglosar los procedimientos en pasos justificados en notación matemática (LaTeX), permitir trazar curvas solución haciendo clic sobre campos de direcciones y visualizar equilibrios, estabilidad y orden de convergencia numérico, el estudiante pasa de ser un consumidor pasivo de respuestas a un explorador del comportamiento dinámico de las ecuaciones.
* **Retroalimentación formativa sin *spoilers*:** El módulo corrector revisa línea por línea el desarrollo del estudiante comprobando equivalencia simbólica/diferencial, señala la primera línea con error y entrega una pista orientada al concepto fallido, imitando la tutoría docente.
* **Adaptación progresiva:** El generador determinista de ejercicios (dificultad 1 a 5) y el registro del perfil de progreso por tipo de EDO permiten focalizar la práctica en las áreas donde el estudiante presenta mayores dificultades.

### 3.2 Justificación científica y matemática
* **Rigor mediante verificación obligatoria:** A diferencia de calculadoras basadas en un único intento simbólico, el sistema clasifica todos los métodos aplicables, intenta resoluciones propias por método antes de usar respaldos generales y somete toda respuesta a una prueba de residuo y análisis de dominio, emitiendo un **Certificado de Verificación** explícito (`VERIFICADA_SIMBOLICA`, `VERIFICADA_NUMERICA` o `NO_VERIFICADA`).
* **Cobertura realista de limitaciones analíticas:** Muchas EDOs relevantes carecen de solución cerrada elemental. El sistema integra respaldo numérico adaptativo, detección de rigidez (*stiffness*), análisis de existencia y unicidad (Picard-Lindelöf), detección de pérdida de unicidad (ej. $y' = y^{1/3}$) y estimación de explosión en tiempo finito (*blow-up*, ej. $y' = y^2$).

### 3.3 Justificación tecnológica y de seguridad
* **Desacoplamiento y reutilización:** El motor matemático (`odecalc` y `core`) está separado de las interfaces de usuario (`ui/` en Streamlit, `apps/desktop/` en Tkinter y `apps/web/` con API HTTP + Plotly), lo que permite mantener una única fuente de verdad matemática consumible desde escritorio, navegador web o scripts académicos.
* **Seguridad en entornos educativos multiusuario:** El parser moderno emplea una lista blanca estricta de símbolos y funciones matemáticas junto con `sympy.parse_expr` con `__builtins__` vacío, evitando la ejecución arbitraria de código en entradas web o compartidas, además de usar límites reales de tiempo (*timeout*) para evitar bloqueos por integrales costosas.
* **Soberanía tecnológica y operación *offline*:** Toda la lógica matemática, la generación de ejercicios, la corrección y las explicaciones funcionan sin conexión a internet y sin claves de IA; la IA opcional únicamente traduce lenguaje natural o redacta explicaciones sobre resultados ya certificados.

### 3.4 Justificación práctica
* **Generación de evidencias académicas:** Permite exportar resultados, gráficas, tablas de error y certificados de verificación directamente a informes en **PDF** y **LaTeX**, facilitando la entrega de prácticas de laboratorio, talleres y reportes estudiantiles reproducibles.

---

## 4. Objetivos del Proyecto

### 4.1 Objetivo general
Desarrollar una plataforma computacional educativa modular, verificable y multi-interfaz (**ODE Calculator / EDO-Lab**) para la resolución, visualización, análisis cualitativo, simulación numérica, calibración con datos y práctica guiada de ecuaciones diferenciales ordinarias de primer orden.

### 4.2 Objetivos específicos
1. **Construir un motor simbólico-numérico seguro y verificado (`odecalc` / `core`):** capaz de parsear múltiples notaciones (incluyendo LaTeX y multiplicación implícita), clasificar de forma multi-método una EDO de primer orden, resolverla mediante métodos analíticos propios o respaldo numérico, y emitir un certificado basado en la comprobación del residuo.
2. **Implementar herramientas de análisis cualitativo y de existencia/unicidad:** para identificar equilibrios, estabilidad, líneas de fase, isóclinas, comportamiento asintótico, bifurcaciones paramétricas, singularidades y explosiones en tiempo finito.
3. **Proveer un laboratorio numérico y de modelado científico:** que permita comparar métodos didácticos de paso fijo (`Euler`, `Heun`, `RK4`) frente a integradores adaptativos e implícitos (`RK45`, `DOP853`, `BDF`, `Radau`), medir el orden empírico de convergencia, ajustar modelos a datos experimentales (CSV/Excel) con criterios AIC/BIC y cuantificar incertidumbre mediante Monte Carlo e índices de Sobol.
4. **Incorporar módulos pedagógicos de aprendizaje activo y generación de informes:** incluyendo explicación paso a paso, biblioteca de modelos físicos/aplicados, generador de ejercicios certificados, corrector automático de procedimientos línea por línea y exportación reproducible a PDF y LaTeX.
5. **Ofrecer interfaces accesibles y desacopladas:** mediante un laboratorio docente interactivo en **Streamlit** (`EDO-Lab`), una aplicación de escritorio en **Tkinter** y una interfaz **Web** ligera con gráficas interactivas en Plotly, garantizando la calidad mediante pruebas automatizadas y auditoría técnica continua.

---

## 5. Capacidades Actuales del Programa

Las capacidades descritas a continuación han sido verificadas directamente sobre el código fuente actual del repositorio.

### 5.1 Núcleo Matemático (`odecalc/` y `core/`)

#### A. Entrada flexible y parser seguro (`odecalc/parsing/`, `core/parser.py`)
* **Formas admitidas:**
  * Explícitas: `y' = f(x, y)`, `dy/dx = f(x, y)`
  * Lineales estándar: `y' + P(x)*y = Q(x)`
  * Diferenciales: `M(x, y) dx + N(x, y) dy = 0`
  * Implícitas de primer orden: `F(x, y, y') = 0` (ej. Clairaut y Lagrange)
* **Notación natural y LaTeX:** Soporta multiplicación implícita (`2x`, `3y^2`), potencia con `^`, funciones estándar y especiales (`sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `atan`, `erf`, `erfi`, `Ei`, `Si`, `Ci`, `Integral`, etc.), así como pegado directo de expresiones LaTeX (`\frac{dy}{dx}`, `\dfrac`, `\sqrt`, `\ln`, `\cdot`, `\times`, delimitadores `$...$`, `$$...$$`, `\[...\]`).
* **Seguridad:** Validación por lista blanca de identificadores y rechazo de palabras peligrosas (`__import__`, `open`, acceso a atributos, guiones bajos) sin recurrir a `eval` abierto en el motor principal.

#### B. Clasificación multi-método y resolución simbólica (`odecalc/classify/`, `odecalc/methods/`)
En lugar de devolver una única etiqueta, el clasificador evalúa **todos los métodos aplicables** con su evidencia matemática y prioridad. Los métodos implementados incluyen:
* **Básicos:** Separable (`separable`), Lineal de primer orden (`linear`), Exacta (`exact`).
* **Factores integrantes:** $\mu(x)$, $\mu(y)$, $\mu(xy)$, $\mu(x+y)$, $\mu(x^2+y^2)$ (`integrating_factor`).
* **Sustituciones y cambios de variable:** Homogénea de grado 0 (`homogeneous`), Reducible a homogénea (`reducible_homogeneous`), Sustitución lineal `u = a*x + b*y + c` (`substitution`).
* **No lineales e implícitas:** Bernoulli para cualquier exponente real $n$ (`bernoulli`), Riccati (`riccati`), Clairaut (`clairaut`), Lagrange (`lagrange`).
* **Respaldo controlado:** `sympy.dsolve` (`dsolve_fallback`), marcado explícitamente como respaldo y sujeto al mismo proceso de verificación.
* **Tratamiento matemático riguroso:** Manejo de soluciones implícitas $F(x, y) = C$ como ciudadanos de primera clase, conservación de integrales no elementales en forma explícita en $x$ (sin `y(x)` dentro de la integral), detección de soluciones singulares o perdidas y resolución de problemas de valor inicial (PVI) con selección de rama.

#### C. Verificación matemática y certificado de confianza (`odecalc/verify/`, `core/verificador.py`)
* Toda solución se sustituye en la EDO original (y para soluciones implícitas mediante derivación implícita) para comprobar si el residuo se anula.
* Si la simplificación simbólica no es concluyente, se evalúa el residuo numéricamente sobre una muestra determinista de puntos del dominio (200 puntos en `core/verificador.py`).
* **Estados del certificado:**
  * `VERIFICADA_SIMBOLICA`: residuo simbólico idénticamente cero.
  * `VERIFICADA_NUMERICA`: residuo verificado numéricamente dentro de tolerancia o respaldo numérico exitoso con estimación de error.
  * `NO_VERIFICADA`: solución no concluyente o con advertencia explícita (el motor descarta el método fallido y prueba el siguiente candidato antes de mostrar resultados).

#### D. Análisis de existencia, unicidad y validez (`odecalc/verify/validity.py`, `core/existencia.py`)
* Comprobación didáctica del **Teorema de Picard-Lindelöf** (continuidad de $f(x, y)$ y $\partial f/\partial y$ en un entorno de $(x_0, y_0)$).
* Detección de puntos singulares (denominadores que se anulan) y notas de restricción de dominio (logaritmos, raíces cuadradas).
* Detección de **pérdida de unicidad** por potencias fraccionarias (ej. $y' = y^{1/3}$ en $y_0 = 0$).
* Detección y estimación de **explosión en tiempo finito (*blow-up*)** (ej. $y' = y^2$ con $y(0) = 1 \Rightarrow x_{\text{exp}} \approx 1$).

#### E. Control de tiempo límite y orquestación híbrida (`odecalc/timeout.py`, `core/hibrido.py`)
* Ejecución con *timeout* configurable en subproceso independiente para evitar que integrales simbólicas costosas congelen la interfaz.
* Degradación automática al respaldo numérico cuando no existe forma cerrada elemental o el método simbólico falla/agota tiempo.

---

### 5.2 Capacidades de EDO-Lab: Laboratorio Docente en Streamlit (`ui/streamlit_app.py`, `ui/pagina_*.py`)

El laboratorio integra **7 pestañas especializadas** sobre un estado de sesión persistente, tema claro/oscuro, diseño *responsive* e historial lateral:

1. **Resolver (`pagina_resolver.py`):**
   * Editor de ecuación, selección de ejemplos precargados (8 casos representativos: logística, lineal, separable, exacta, explosión, sin unicidad, sin forma cerrada, enfriamiento), condiciones iniciales $(x_0, y_0)$ e intervalo $[x_{\min}, x_{\max}]$.
   * Muestra solución general y particular, certificado de verificación, análisis de existencia/unicidad, pasos detallados con LaTeX y justificación, campo de direcciones interactivo (con clic sobre el gráfico para trazar curvas) y selección de **6 modelos aplicados** (`core/modelos.py`): crecimiento poblacional logístico, enfriamiento de Newton, circuito RL en serie, mezcla en un tanque, decaimiento radiactivo y caída con resistencia del aire.
   * Explicación en lenguaje sencillo (local por defecto, o enriquecida mediante IA opcional).
2. **Cualitativo (`pagina_cualitativo.py`, `core/cualitativo.py`):**
   * Detección de ecuaciones autónomas $y' = f(y)$, cálculo de puntos de equilibrio $f(y^*) = 0$ y clasificación de estabilidad (`estable/atractor`, `inestable/repulsor`, `semiestable`, `indeterminada`) vía $f'(y^*)$ y análisis de signo lateral.
   * Diagrama de línea de fase 1D, curvas isóclinas, comportamiento asintótico ($x \to \infty$) y **diagrama de bifurcación** interactivo con parámetro $\mu$.
3. **Numérico (`pagina_numerico.py`, `core/solver_numerico.py`, `core/convergencia.py`):**
   * Integración y comparación de **7 métodos**: 3 implementaciones didácticas de paso fijo (`Euler`, `Heun`, `RK4`) y 4 integradores adaptativos/implícitos de SciPy (`RK45`, `DOP853`, `BDF`, `Radau`).
   * **Estudio de convergencia:** gráfica log-log de error frente al paso $h$ y cálculo del **orden empírico** por regresión lineal (verificando p. ej. $\approx 1$ para Euler, $\approx 2$ para Heun y $\approx 4$ para RK4).
   * **Benchmark en vivo** (tiempo, evaluaciones de $f$, error máximo) y **detección automática de rigidez (*stiffness*)** con recomendación/cambio a métodos implícitos (`BDF`/`Radau`).
4. **Datos (`pagina_datos.py`, `core/ajuste.py`):**
   * Carga de archivos **CSV y Excel** (`.xlsx`), detección automática de columnas de tiempo y variable, limpieza de `NaN` y 4 conjuntos de datos de ejemplo incluidos (`crecimiento.csv`, `decaimiento.csv`, `enfriamiento.csv`, `logistico.csv`).
   * Calibración de parámetros por mínimos cuadrados no lineales integrando la EDO en cada iteración para **4 modelos candidatos**: exponencial, logístico, Gompertz y enfriamiento de Newton.
   * Comparación automática mediante **AIC, BIC, RMSE y $R^2$**, intervalos de confianza de parámetros, análisis de sensibilidad local y proyección a futuro con banda de confianza.
5. **Incertidumbre (`pagina_incertidumbre.py`, `core/incertidumbre.py`):**
   * Simulación **Monte Carlo** determinista (semilla configurable) sobre parámetros y condiciones iniciales con distribuciones `normal`, `uniforme` o `fija`, generando bandas de predicción (por ejemplo 5–95 %).
   * Análisis de sensibilidad global mediante **índices de Sobol** de primer orden ($S_1$) y totales ($S_T$) usando `SALib`.
6. **Aprender (`pagina_aprendizaje.py`, `core/ejercicios.py`, `core/corrector.py`):**
   * **Generador determinista de ejercicios** en 5 categorías (`separable`, `lineal`, `exacta`, `bernoulli`, `logistica`) con niveles de dificultad del 1 al 5, previamente verificados por el motor antes de mostrarse.
   * **Corrector de procedimiento:** recibe el desarrollo paso a paso del estudiante (una línea por paso, en texto o LaTeX básico), valida la equivalencia algebraica/diferencial contra la EDO y la línea previa, localiza la **primera línea errónea** y ofrece una pista pedagógica sin revelar la solución.
   * **Perfil del estudiante** persistente (`data/perfil_estudiante.json`) con conteo de aciertos/errores por tipo y recomendación adaptativa del siguiente ejercicio.
7. **Informes (`pagina_informes.py`, `core/informes.py`):**
   * Vista previa y exportación de documentos académicos reproducibles en formato **PDF** (con ReportLab y figuras Matplotlib incrustadas) y **LaTeX** (`.tex`), configurando secciones (enunciado, método y resultado, pasos, gráficas, tabla de errores, certificado y advertencias).

---

### 5.3 Interfaces Complementarias: Escritorio, Web y Capa Legacy

Además de EDO-Lab en Streamlit, el repositorio cuenta con interfaces adicionales conectadas al motor `odecalc`:

* **Interfaz de Escritorio (`apps/desktop/app.py`, `apps/desktop/plot_panel.py`):**
  * Aplicación Tkinter/ttk en diseño *bento* con barra de menús (**Resolver**, **Lienzo**, **Ejercicios**, **Ayuda**), manual integrado, barra de símbolos, atajos de teclado, cálculo en segundo plano y **7 modos de visualización**: solución $y(x)$, campo de direcciones, isoclinas, familia de curvas, línea de fase, puntos de equilibrio y superficie 3D $z = f(x, y)$.
* **Aplicación Web y API REST (`apps/web/server.py`, `apps/web/static/`):**
  * Servidor HTTP basado en `ThreadingHTTPServer` (sin dependencias externas de frameworks web), con límites de tamaño de petición, tasa de solicitudes (*rate limiting*) y *timeout*.
  * Endpoints `POST /solve` y `POST /plot` que serializan `SolveResult` a JSON (`odecalc/serialization.py`).
  * Interfaz web responsiva con renderizado matemático MathJax, gráficas interactivas con Plotly (los mismos 7 modos), anotaciones sobre canvas, biblioteca de ejercicios guiados y exportación PNG.
* **Interfaz Legacy (`app.py`, `math_engine/`):**
  * Conservada por compatibilidad al ejecutar `python app.py` directamente (con catálogo de 18 ejercicios clásicos en `data/exercises.py`); cuando se ejecuta `streamlit run app.py`, delega automáticamente en **EDO-Lab**.

---

## 6. Metodología de Desarrollo y Aseguramiento de Calidad

Para el apartado metodológico del informe educativo, el proyecto sigue prácticas de ingeniería de software científico reproducibles:

1. **Arquitectura modular en capas:** Separación estricta entre lógica matemática pura (`odecalc/`, `core/`) e interfaces de presentación (`ui/`, `apps/`), utilizando `dataclass` tipados como contratos de datos (`SolveResult`, `ResultadoSolucion`, `Certificado`, `ResultadoAjuste`, etc.).
2. **Estrategia de pruebas multinivel (`tests/`):**
   * El proyecto registra **517 pruebas recolectadas** distribuidas en pruebas unitarias (`tests/unit/`), pruebas de regresión (`tests/regression/`), pruebas de integración (`tests/integration/`), pruebas del laboratorio docente (`tests/edolab/`), pruebas basadas en propiedades con **Hypothesis** (`tests/property/`, `tests/test_properties.py`) y un **banco de 105 ejercicios clásicos** con PVI de referencia (`tests/bank/`).
   * Regla de cobertura objetivo del **85 %** sobre `odecalc/` configurada en `pyproject.toml`.
3. **Auditoría técnica continua:** Documentada en `REPORTE_AUDITORIA_TECNICA.md` (última revisión: 25 de noviembre de 2026, con `475 passed` registrados en la ejecución verificada), lo cual evidencia un proceso honesto de control de calidad previo a una versión final estable.

---

## 7. Estado Actual: Alcance y Limitaciones del Proyecto en Desarrollo

Dado que el proyecto **aún se encuentra en desarrollo**, es fundamental presentar con transparencia en el informe qué está consolidado y qué limitaciones o defectos conocidos siguen en proceso de corrección (extraídos de `REPORTE_AUDITORIA_TECNICA.md` y `PLAN_MEJORAS_ODE_CALCULATOR.md`):

### 7.1 Limitaciones matemáticas y funcionales de alcance
* **Solo EDOs de primer orden:** El soporte actual no resuelve todavía EDOs de segundo orden o orden $n$, sistemas de ecuaciones diferenciales ni transformada de Laplace (previstos en fases futuras).
* **Casos analíticos complejos:** Algunas integrales costosas pueden agotar el *timeout*, activando el respaldo numérico en lugar de una fórmula cerrada.
* **Análisis cualitativo en funciones trascendentes:** El cálculo de diagramas de bifurcación y raíces de equilibrio depende principalmente de resolución simbólica/polinomial (`sp.solve`/`sp.nroots`), por lo que ecuaciones trascendentes como $y' = \mu y - \sin(y)$ pueden devolver diagramas vacíos hasta incorporar búsqueda numérica por muestreo/bisección.

### 7.2 Hallazgos técnicos vigentes por estado "en desarrollo"
La auditoría técnica interna identificó **34 hallazgos** (26 vigentes, 7 parcialmente corregidos y 1 reclasificado), entre los que destacan como relevantes para documentar en el estado actual:
1. **Coexistencia de tres capas de código:** Conviven `odecalc/` (motor principal), `core/` (lógica pedagógica de EDO-Lab) y `math_engine/` (motor legacy de la interfaz Tk antigua), lo que genera cierta duplicación de utilidades (`lambdify`, parseo, gráficas).
2. **Casos borde en el parser:** Exponentes negativos sin llaves en texto plano (ej. `y' = x^-2`) y comandos de funciones LaTeX sin delimitadores (ej. `\sin 2x`) presentan defectos de preprocesamiento identificados y pendientes de parche.
3. **Ajuste de datos en series de decaimiento:** El modelo `exponencial` en `core/ajuste.py` restringe actualmente el parámetro $k > 0$, por lo que falla en series de decaimiento (como `decaimiento.csv`) hasta permitir $k < 0$; asimismo faltan validaciones ante series no positivas en modelos logístico/Gompertz.
4. **Respaldo numérico y timeouts:** La cascada de integradores numéricos ante explosiones en tiempo finito y la separación del *timeout* simbólico respecto al respaldo numérico requieren refinamiento para no agotar el tiempo global en casos extremos.
5. **Seguridad y concurrencia en rutas heredadas/web:** El parser legacy (`math_engine/parser.py`) aún usa `sp.sympify` sin aislamiento completo (a diferencia del parser seguro de `odecalc`), y el mecanismo de *timeout* basado en `fork` en Linux requiere migración a `spawn` para evitar riesgos en procesos multi-hilo.
6. **Detalles de interfaz, corrector e informes:** El corrector tiene limitaciones cuando pasos intermedios implícitos conservan la constante libre $C$; la exportación PDF usa tamaños fijos de imagen para fórmulas; la persistencia del perfil estudiantil escribe dentro del árbol del proyecto (`data/perfil_estudiante.json`); y el servidor web/frontend aún depende de CDN para MathJax/Plotly y requiere ajustes menores en validación y CORS.

---

## 8. Impacto Educativo y Casos de Uso en el Aula

| Actor | Escenario de uso concreto | Beneficio pedagógico |
| :--- | :--- | :--- |
| **Estudiante (autoaprendizaje)** | Resuelve ejercicios en *Aprender*, introduce su procedimiento paso a paso y recibe pistas en la primera línea errónea. | Corrige errores conceptuales (signos, constantes, factor integrante) de forma inmediata sin depender de ver la solución completa. |
| **Estudiante (laboratorio / tareas)** | Modela un problema en *Resolver* o *Datos*, analiza convergencia de Euler/RK4 en *Numérico* y exporta el PDF/LaTeX en *Informes*. | Entrega reportes con gráficas, tablas de error y certificado de verificación, conectando teoría y práctica. |
| **Docente (clase magistral)** | Proyecta campos de direcciones y diagramas de fase/bifurcación en *Cualitativo* haciendo clic para mostrar familias de trayectorias, o contrasta casos patológicos ($y'=y^2$, $y'=y^{1/3}$). | Ilustra visualmente existencia, unicidad, estabilidad y explosión en tiempo finito en tiempo real. |
| **Cursos de modelado / simulación** | Carga un CSV experimental, compara exponencial vs. logístico vs. Gompertz por AIC/BIC y ejecuta Monte Carlo / Sobol en *Incertidumbre*. | Introduce cultura estadística, selección de modelos y sensibilidad paramétrica desde cursos iniciales. |

---

## 9. Hoja de Ruta y Trabajo Futuro

Para la sección de **Conclusiones y Trabajo Futuro** del informe, las líneas de evolución proyectadas del proyecto son:

1. **Corto plazo — Estabilización y cierre de auditoría:**
   * Corregir los hallazgos críticos y altos documentados en `REPORTE_AUDITORIA_TECNICA.md` (parser de exponentes negativos y funciones LaTeX, ajuste exponencial decreciente, aislamiento de *timeouts* con `spawn`, validación estricta de intervalos y seguridad del parser legacy).
   * Deprecar formalmente la capa legacy (`math_engine/` y `app.py` clásico) y consolidar el empaquetado de datos (`data/ejemplos/*.csv`) en el distribuidor Python.
2. **Mediano plazo — Robustez pedagógica y offline:**
   * Mejorar el corrector paso a paso para despejar constantes arbitrarias en derivación implícita, añadir búsqueda numérica de raíces en bifurcaciones trascendentes y ofrecer respaldo local sin CDN para la interfaz web.
   * Migrar el perfil del estudiante a almacenamiento por usuario/sesión.
3. **Largo plazo — Expansión matemática (Fase 7 del plan):**
   * Extender el motor verificado hacia **EDOs de segundo orden y orden $n$** (coeficientes constantes, indeterminados, variación de parámetros, Cauchy-Euler, reducción de orden).
   * Incorporar **transformada de Laplace**, **series de potencias**, **sistemas lineales de EDOs** (valores propios, matriz exponencial) y **planos de fase 2D**.

---

## 10. Guía Rápida para Armar el Informe Final

Si necesitas trasladar este insumo directamente a la estructura estándar de un informe académico, puedes mapear sus secciones así:

* **Capítulo I: El Problema** $\rightarrow$ Usar **Sección 2** (Planteamiento y Formulación), **Sección 3** (Justificación) y **Sección 4** (Objetivos).
* **Capítulo II: Marco Teórico / Referencial** $\rightarrow$ Combinar las bases matemáticas listadas en la **Sección 5.1 y 5.2** (clasificación de EDOs, Picard-Lindelöf, métodos numéricos y convergencia, análisis cualitativo, AIC/BIC, Monte Carlo y Sobol, evaluación formativa).
* **Capítulo III: Marco Metodológico y Diseño del Sistema** $\rightarrow$ Usar **Sección 5** (Capacidades y arquitectura modular) y **Sección 6** (Metodología, contratos de datos y pruebas automatizadas).
* **Capítulo IV: Resultados / Estado del Prototipo** $\rightarrow$ Presentar los 7 módulos de **EDO-Lab** (**Sección 5.2**), los casos de prueba/batería de 105 ejercicios y los resultados honestos de la auditoría (**Sección 7**).
* **Capítulo V: Conclusiones y Recomendaciones (Trabajo Futuro)** $\rightarrow$ Usar **Sección 8** (Impacto educativo) y **Sección 9** (Hoja de ruta).
