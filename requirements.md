# Requirements Document

## Introduction

Calculadora Inteligente para la Solución y Visualización Gráfica de Ecuaciones Diferenciales de Primer Orden. Es una herramienta de escritorio desarrollada en Python que permite a estudiantes e ingenieros ingresar, resolver (simbólica y numéricamente), previsualizar con formato matemático tipográfico y visualizar gráficamente ecuaciones diferenciales de primer orden. La interfaz es visual, amigable y ofrece atajos de teclado para insertar símbolos matemáticos, así como la capacidad de copiar y pegar ejercicios predefinidos.

---

## Glossary

- **ODE_Calculator**: La aplicación principal de escritorio desarrollada en Python.
- **EDO**: Ecuación Diferencial Ordinaria de primer orden (e.g., `dy/dx = f(x, y)`).
- **Equation_Input**: Campo de entrada donde el usuario escribe la ecuación diferencial.
- **Symbolic_Solver**: Componente que utiliza SymPy para obtener soluciones analíticas/simbólicas.
- **Numeric_Solver**: Componente que utiliza SciPy (`solve_ivp`) para obtener soluciones numéricas cuando la solución simbólica no existe o el usuario lo solicita.
- **Math_Preview**: Panel que muestra la ecuación con renderizado matemático tipográfico (fracciones apiladas, notación LaTeX visual).
- **Plot_View**: Panel que muestra la gráfica de la solución generada con Matplotlib.
- **Symbol_Toolbar**: Barra de herramientas con botones de símbolos matemáticos comunes.
- **Exercise_Library**: Colección de ejercicios predefinidos relacionados con EDOs de primer orden.
- **Condition_Panel**: Panel donde el usuario ingresa condiciones iniciales (valor de `x₀` e `y₀`).
- **Keyboard_Shortcut**: Combinación de teclas que inserta un símbolo matemático en el Equation_Input.
- **LaTeX_String**: Cadena de texto en formato LaTeX usada para renderizar ecuaciones tipográficamente.
- **Step_By_Step_Panel**: Panel que muestra el procedimiento completo de resolución de la EDO, desglosado en pasos atómicos con justificación matemática explícita para cada operación aritmética y algebraica.
- **Direction_Field**: Visualización 2D del campo de pendientes (slope field) de una EDO `dy/dx = f(x, y)`, formada por segmentos o flechas cortas en puntos de la cuadrícula del plano xy cuya inclinación indica el valor de `f(x, y)` en ese punto.
- **Surface_3D_View**: Visualización tridimensional de la superficie `z = f(x, y)`, que representa la función que define la derivada de la EDO, renderizada sobre el plano xy usando `mpl_toolkits.mplot3d`.

---

## Requirements

### Requirement 1: Ingreso de Ecuaciones Diferenciales

**User Story:** Como estudiante de ingeniería, quiero escribir una ecuación diferencial de primer orden en un campo de texto, para que la calculadora pueda procesarla.

#### Acceptance Criteria

1. THE Equation_Input SHALL aceptar ecuaciones diferenciales de primer orden expresadas en sintaxis estándar de Python/SymPy (e.g., `dy/dx = x + y`, `y' = sin(x)*y`).
2. WHEN el usuario escribe en el Equation_Input, THE Math_Preview SHALL actualizar el renderizado tipográfico de la ecuación en tiempo real.
3. IF el texto ingresado en el Equation_Input no representa una EDO de primer orden válida, THEN THE ODE_Calculator SHALL mostrar un mensaje de error descriptivo indicando el problema de sintaxis.
4. THE Equation_Input SHALL aceptar las funciones matemáticas estándar: `sin`, `cos`, `tan`, `exp`, `log`, `sqrt` y sus equivalentes en SymPy.

---

### Requirement 2: Previsualización Matemática con Formato Tipográfico

**User Story:** Como usuario, quiero ver la ecuación renderizada con notación matemática tipográfica (fracciones apiladas verticalmente, exponentes, símbolos), para que el ejercicio sea legible y visualmente claro antes de resolverlo.

#### Acceptance Criteria

1. THE Math_Preview SHALL renderizar la ecuación ingresada utilizando la librería `matplotlib.mathtext` o `sympy.printing.latex` combinada con Matplotlib para producir notación tipográfica con fracciones apiladas verticalmente.
2. WHEN el Equation_Input está vacío, THE Math_Preview SHALL mostrar un placeholder tipográfico que indique la sintaxis esperada (e.g., `dy/dx = f(x, y)`).
3. THE Math_Preview SHALL mostrar la ecuación en un tamaño de fuente mínimo de 14pt para garantizar legibilidad.
4. WHEN la ecuación contiene condiciones iniciales, THE Math_Preview SHALL mostrar tanto la ecuación como las condiciones iniciales formateadas tipográficamente.

---

### Requirement 3: Solución Simbólica

**User Story:** Como estudiante, quiero obtener la solución analítica exacta de la EDO cuando sea posible, para entender la forma cerrada de la respuesta.

#### Acceptance Criteria

1. WHEN el usuario solicita la solución simbólica, THE Symbolic_Solver SHALL utilizar `sympy.dsolve` para calcular la solución general de la EDO.
2. WHEN `sympy.dsolve` encuentra una solución, THE ODE_Calculator SHALL mostrar la solución general formateada tipográficamente en el Math_Preview.
3. WHEN se proporcionan condiciones iniciales en el Condition_Panel, THE Symbolic_Solver SHALL calcular la solución particular sustituyendo dichas condiciones.
4. IF `sympy.dsolve` no puede encontrar una solución simbólica, THEN THE ODE_Calculator SHALL informar al usuario y ofrecer automáticamente la solución numérica como alternativa.
5. THE Symbolic_Solver SHALL resolver los siguientes tipos de EDOs de primer orden: separables, lineales, exactas, homogéneas y Bernoulli.

---

### Requirement 4: Solución Numérica

**User Story:** Como usuario, quiero obtener una solución numérica cuando la solución simbólica no esté disponible o cuando necesite valores específicos, para poder analizar el comportamiento de la EDO.

#### Acceptance Criteria

1. WHEN el usuario solicita la solución numérica, THE Numeric_Solver SHALL utilizar `scipy.integrate.solve_ivp` para calcular la solución.
2. WHEN se ejecuta la solución numérica, THE Condition_Panel SHALL requerir al usuario ingresar los valores de `x₀`, `y₀`, `x_min` y `x_max` antes de calcular.
3. THE Numeric_Solver SHALL calcular la solución con un mínimo de 500 puntos en el intervalo especificado para garantizar suavidad en la gráfica.
4. IF `scipy.integrate.solve_ivp` devuelve un estado de falla (`success = False`), THEN THE ODE_Calculator SHALL mostrar el mensaje de error devuelto por el solver y sugerir ajustar el intervalo o las condiciones iniciales.

---

### Requirement 5: Visualización Gráfica

**User Story:** Como usuario, quiero ver distintas visualizaciones gráficas de la EDO y su solución, para analizar visualmente el comportamiento cualitativo y cuantitativo de la ecuación en el intervalo de interés.

#### Acceptance Criteria

1. WHEN una solución (simbólica o numérica) está disponible, THE Plot_View SHALL mostrar la gráfica de `y(x)` utilizando Matplotlib con ejes etiquetados (`x` e `y(x)`), título y cuadrícula visible.
2. THE Plot_View SHALL permitir al usuario especificar el intervalo de graficación `[x_min, x_max]` e `[y_min, y_max]` mediante campos en el Condition_Panel.
3. WHEN el usuario solicita la solución numérica con condiciones iniciales, THE Plot_View SHALL superponer la curva numérica sobre la gráfica existente con un color y etiqueta diferenciados.
4. THE Plot_View SHALL incluir controles interactivos nativos de Matplotlib (zoom, pan, guardar imagen) accesibles desde la interfaz.
5. WHERE la solución simbólica existe y el usuario proporciona múltiples condiciones iniciales, THE Plot_View SHALL renderizar una familia de curvas, una por cada condición inicial, en colores distintos.
6. THE Plot_View SHALL ofrecer un selector (pestañas o menú desplegable) que permita al usuario cambiar entre tres modos de visualización: gráfica de solución `y(x)`, Direction_Field y Surface_3D_View.
7. WHEN el usuario selecciona el modo Direction_Field, THE Plot_View SHALL calcular y renderizar el campo de pendientes de `dy/dx = f(x, y)` sobre una cuadrícula uniforme en el plano xy, representando la pendiente en cada punto mediante segmentos normalizados orientados según el valor de `f(x, y)`.
8. WHEN el Direction_Field está activo y existe una solución con condición inicial, THE Plot_View SHALL superponer la curva solución `y(x)` sobre el campo de pendientes para mostrar cómo la trayectoria sigue el campo vectorial.
9. IF el usuario activa el modo Direction_Field y el Condition_Panel no contiene valores de `x_min`, `x_max`, `y_min` e `y_max`, THEN THE Plot_View SHALL utilizar el intervalo por defecto `[-5, 5] × [-5, 5]` e informar al usuario de los valores utilizados.
10. WHEN el usuario selecciona el modo Surface_3D_View, THE Plot_View SHALL renderizar la superficie tridimensional `z = f(x, y)` sobre el plano xy utilizando `mpl_toolkits.mplot3d` con ejes etiquetados (`x`, `y`, `z = f(x,y)`), título y barra de color que indique la magnitud de `z`.
11. THE Plot_View SHALL generar el Surface_3D_View con una resolución de cuadrícula mínima de 50×50 puntos sobre el intervalo especificado en el Condition_Panel, para garantizar una superficie suave.
12. WHEN el Surface_3D_View está activo, THE Plot_View SHALL permitir al usuario rotar la superficie 3D interactivamente mediante arrastre del ratón, usando las capacidades nativas de rotación de `mpl_toolkits.mplot3d`.
13. THE Plot_View SHALL incluir botones de vista predefinida para el Surface_3D_View: vista frontal (elevación=0°, azimut=0°), vista lateral (elevación=0°, azimut=90°) y vista isométrica (elevación=30°, azimut=45°), accesibles desde la interfaz junto al selector de modo de visualización.

---

### Requirement 6: Solución Paso a Paso

**User Story:** Como estudiante, quiero ver el procedimiento completo de resolución de la EDO desglosado en pasos atómicos con justificación explícita de cada operación, para entender el proceso matemático y no solo el resultado final.

#### Acceptance Criteria

1. WHEN el usuario solicita la solución simbólica, THE Step_By_Step_Panel SHALL mostrar el procedimiento completo de resolución dividido en pasos numerados secuencialmente, donde cada paso muestra: la operación realizada, la expresión resultante en formato tipográfico y la justificación matemática de por qué se aplicó dicha operación.
2. THE Step_By_Step_Panel SHALL desglosar cada operación aritmética hasta el nivel más atómico posible, incluyendo:
   - Simplificaciones de signos (e.g., `(-1) × (-3) = +3`, `- × - = +`)
   - Cancelaciones de factores comunes en numeradores y denominadores
   - Distribución de factores y expansión de productos
   - Cambios de signo al transponer términos entre miembros de una ecuación
   - Integración de cada término por separado, mostrando la regla de integración aplicada
   - Sustitución de la constante de integración al aplicar condiciones iniciales
3. WHEN la EDO es separable, THE Step_By_Step_Panel SHALL mostrar explícitamente: (a) identificación del tipo, (b) separación de variables `f(y)dy = g(x)dx`, (c) integración de cada lado con la regla aplicada, (d) despeje de `y`, (e) aplicación de condiciones iniciales si las hay.
4. WHEN la EDO es lineal `dy/dx + P(x)y = Q(x)`, THE Step_By_Step_Panel SHALL mostrar explícitamente: (a) identificación y reescritura en forma estándar, (b) cálculo del factor integrante `μ(x) = e^(∫P(x)dx)` con cada sub-paso de la integral, (c) multiplicación de ambos lados por `μ(x)`, (d) reconocimiento del lado izquierdo como derivada de `μ(x)y`, (e) integración, (f) despeje y condiciones iniciales.
5. WHEN la EDO es de Bernoulli, THE Step_By_Step_Panel SHALL mostrar explícitamente la sustitución `v = y^(1-n)` con la transformación paso a paso que convierte la ecuación en una EDO lineal, seguida del procedimiento del criterio 4.
6. WHEN la EDO es exacta `M(x,y)dx + N(x,y)dy = 0`, THE Step_By_Step_Panel SHALL mostrar explícitamente: (a) verificación de exactitud `∂M/∂y = ∂N/∂x` con los cálculos de derivadas parciales, (b) integración de `M` respecto a `x`, (c) determinación de `g(y)` diferenciando respecto a `y`, (d) función potencial `F(x,y)`.
7. THE Step_By_Step_Panel SHALL renderizar cada paso con formato tipográfico matemático (usando `matplotlib.mathtext`) para que las expresiones sean legibles y visualmente claras.
8. THE Step_By_Step_Panel SHALL estar visible simultáneamente con el Math_Preview o accesible mediante una pestaña en el panel derecho, de modo que el usuario pueda ver el procedimiento y la gráfica en la misma sesión.
9. IF la solución simbólica no está disponible y se usa el Numeric_Solver, THEN THE Step_By_Step_Panel SHALL mostrar los pasos del método numérico empleado: discretización del intervalo, evaluación de `f(x, y)` en cada punto y avance del integrador.
10. THE Step_By_Step_Panel SHALL incluir un botón "Copiar pasos" que exporte el procedimiento completo como texto plano con notación ASCII matemática al portapapeles del sistema operativo.

---

### Requirement 7: Atajos de Teclado para Símbolos Matemáticos

**User Story:** Como usuario, quiero usar atajos de teclado para insertar símbolos matemáticos comunes, para agilizar la escritura de ecuaciones sin necesidad del ratón.

#### Acceptance Criteria

1. THE ODE_Calculator SHALL proveer atajos de teclado para insertar los siguientes tokens en el Equation_Input cuando el foco esté en dicho campo:
   - `Ctrl+D` → inserta `dy/dx`
   - `Ctrl+I` → inserta `∫` (integral, token `Integral`)
   - `Ctrl+Shift+I` → inserta `∞` (infinito, token `oo`)
   - `Ctrl+E` → inserta `exp()`
   - `Ctrl+Shift+S` → inserta `sqrt()`
   - `Ctrl+P` → inserta `pi`
2. WHEN se activa un atajo que inserta un token con paréntesis (e.g., `exp()`, `sqrt()`), THE Equation_Input SHALL posicionar el cursor dentro de los paréntesis.
3. THE Symbol_Toolbar SHALL mostrar los mismos símbolos del ítem 1 como botones clickeables visibles, como alternativa al atajo de teclado.
4. IF el foco no está en el Equation_Input cuando se activa un atajo de símbolo, THEN THE ODE_Calculator SHALL transferir el foco al Equation_Input e insertar el símbolo.

---

### Requirement 8: Biblioteca de Ejercicios Predefinidos

**User Story:** Como estudiante, quiero seleccionar ejercicios predefinidos de una biblioteca de EDOs, para practicar con ejemplos representativos y copiarlos al campo de entrada.

#### Acceptance Criteria

1. THE Exercise_Library SHALL contener un mínimo de 15 ejercicios predefinidos que cubran los siguientes tipos de EDOs de primer orden: separables (mínimo 3), lineales (mínimo 3), exactas (mínimo 2), homogéneas (mínimo 2), Bernoulli (mínimo 2) y con aplicaciones (crecimiento/decaimiento, mezcla, circuitos RC) (mínimo 3).
2. WHEN el usuario selecciona un ejercicio de la Exercise_Library, THE ODE_Calculator SHALL cargar la ecuación en el Equation_Input y las condiciones iniciales en el Condition_Panel.
3. THE Exercise_Library SHALL mostrar para cada ejercicio: el nombre del tipo de EDO, la ecuación formateada tipográficamente y una descripción breve de la aplicación.
4. THE Exercise_Library SHALL permitir al usuario copiar la ecuación del ejercicio como texto plano al portapapeles del sistema operativo.
5. WHEN el usuario carga un ejercicio desde la Exercise_Library, THE Math_Preview SHALL renderizar inmediatamente la ecuación cargada.

---

### Requirement 9: Interfaz Visual y Amigable

**User Story:** Como usuario, quiero una interfaz gráfica organizada y visualmente agradable, para que la herramienta sea cómoda de usar en sesiones de estudio.

#### Acceptance Criteria

1. THE ODE_Calculator SHALL implementar la interfaz gráfica utilizando `tkinter` estándar de Python con `ttk` y estilos `ttk.Style` para lograr una apariencia moderna sin dependencias externas de UI.
2. THE ODE_Calculator SHALL organizar la interfaz en un layout de paneles: panel izquierdo para entrada/controles y panel derecho para Math_Preview, Step_By_Step_Panel y Plot_View.
3. THE ODE_Calculator SHALL soportar redimensionamiento de ventana manteniendo proporciones legibles de todos los paneles, con un tamaño mínimo de ventana de 1024×768 píxeles.
4. THE ODE_Calculator SHALL mostrar indicadores de estado (e.g., "Calculando...", "Listo", "Error") en una barra de estado en la parte inferior de la ventana durante las operaciones de cálculo.
5. WHEN una operación de cálculo toma más de 2 segundos, THE ODE_Calculator SHALL mostrar un indicador visual de progreso (spinner o barra) para informar al usuario que el proceso está en curso.

---

### Requirement 10: Dependencias y Librerías

**User Story:** Como desarrollador, quiero que la herramienta use librerías Python bien establecidas y documentadas, para que el entorno sea reproducible y fácil de instalar.

#### Acceptance Criteria

1. THE ODE_Calculator SHALL utilizar las siguientes librerías principales: `sympy` (≥1.12) para solución simbólica, `scipy` (≥1.11) para solución numérica, `matplotlib` (≥3.8) para gráficas y renderizado matemático, `numpy` (≥1.26) para operaciones numéricas. La interfaz de usuario SHALL utilizar únicamente `tkinter` y `ttk` de la biblioteca estándar de Python, sin dependencias externas de UI.
2. THE ODE_Calculator SHALL incluir un archivo `requirements.txt` con las versiones exactas (pinned) de todas las dependencias.
3. THE ODE_Calculator SHALL ejecutarse correctamente en Python 3.10, 3.11 y 3.12 en los sistemas operativos Windows 10+, macOS 12+ y Ubuntu 22.04+.
4. IF una librería requerida no está instalada al iniciar la aplicación, THEN THE ODE_Calculator SHALL mostrar un mensaje de error indicando qué librería falta e instrucciones para instalarla.

---

### Requirement 11: Exportación de Gráficas *(Opcional)*

**User Story:** Como usuario, quiero exportar las gráficas generadas a un archivo de imagen o PDF, para incluirlas en reportes o documentos académicos.

> **Nota de integración**: Este requisito es opcional. Para implementarlo se necesitaría: `matplotlib.backends.backend_pdf` (incluido en matplotlib) para PDF, `Pillow` (≥10.0) para exportación PNG/JPEG de alta resolución, y un diálogo de guardado nativo del sistema operativo vía `tkinter.filedialog`. No requiere dependencias adicionales más allá de Pillow.

#### Acceptance Criteria

1. THE Plot_View SHOULD permitir al usuario exportar la gráfica activa (cualquier modo) a formato PNG, JPEG o PDF mediante un botón "Exportar" visible en la interfaz.
2. WHEN el usuario hace clic en "Exportar", THE ODE_Calculator SHOULD abrir un diálogo de guardado nativo del sistema operativo para que el usuario elija la ruta y el formato de archivo.
3. THE Plot_View SHOULD exportar las gráficas con una resolución mínima de 300 DPI para garantizar calidad de impresión.
4. WHEN la exportación se complete, THE ODE_Calculator SHOULD mostrar una notificación de éxito con la ruta del archivo guardado en la barra de estado.

