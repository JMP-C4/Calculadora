# Plan de Implementación: ODE Calculator

## Resumen

Implementación incremental de la calculadora de EDOs de primer orden en Python con tkinter/ttk. El orden sigue la cadena de dependencias: infraestructura base → math engine (parser → solvers → step generator) → componentes de UI → integración en el controlador principal → tests de propiedades.

## Tareas

- [x] 1. Infraestructura base del proyecto
  - Crear la estructura de directorios: `math_engine/`, `ui/`, `data/`, `tests/` con sus archivos `__init__.py`.
  - Crear `requirements.txt` con las versiones exactas: `sympy==1.13.1`, `scipy==1.13.1`, `matplotlib==3.9.2`, `numpy==1.26.4`, `hypothesis==6.112.0`, `pytest==8.3.3`.
  - Crear `tests/conftest.py` con las estrategias Hypothesis compartidas: `valid_ode_texts`, `invalid_ode_texts`, `solvable_odes`, `numeric_odes`, `valid_rhs_exprs` y el `SHORTCUT_MAP`.
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 2. Parser y validador de ecuaciones
  - [x] 2.1 Implementar `math_engine/parser.py`
    - Definir el dataclass `ParseResult` con campos `rhs`, `latex_str` y `error`.
    - Implementar `parse_ode(text: str) -> ParseResult` con normalización de `y'` y `dy/dx`, separación por `=`, llamada a `sp.sympify` y captura de `SympifyError`, `TypeError` y `ValueError`.
    - Soportar las funciones estándar: `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`.
    - _Requirements: 1.1, 1.3, 1.4_

  - [x]* 2.2 Escribir tests unitarios para el parser
    - Verificar que `dy/dx = x + y` retorna `rhs = x + y(x)` y `error = None`.
    - Verificar que `y' = sin(x)` se parsea sin error.
    - Verificar que cadena vacía retorna `error ≠ None`.
    - Verificar que expresión sin `=` retorna `error ≠ None`.
    - Verificar que EDO de segundo orden retorna `error ≠ None`.
    - Verificar que todas las funciones estándar se parsean sin error.
    - _Requirements: 1.1, 1.3, 1.4_

- [x] 3. Solver simbólico con pasos detallados
  - [x] 3.1 Implementar `math_engine/symbolic_solver.py`
    - Definir los dataclasses `StepByStepResult`, `SymbolicResult`.
    - Implementar `solve_symbolic(rhs, conditions=None) -> SymbolicResult` usando `sympy.dsolve`.
    - Calcular la solución particular aplicando `sympy.solve` sobre `C1` cuando se proporcionan condiciones iniciales.
    - Capturar `NotImplementedError` de `dsolve` y poblar `SymbolicResult.error`.
    - Detectar el tipo de EDO (`ode_type`): separable, lineal, exacta, homogénea, Bernoulli.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x]* 3.2 Escribir tests unitarios para el solver simbólico
    - `dy/dx = y` tiene solución general `y = C1 * exp(x)`.
    - `dy/dx = x` tiene solución general `y = x**2/2 + C1`.
    - Con condiciones iniciales `(0, 1)` en `dy/dx = y`, la particular es `y = exp(x)`.
    - EDO no resoluble retorna `SymbolicResult.error ≠ None`.
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 4. Generador de pasos paso a paso
  - [x] 4.1 Implementar `math_engine/step_generator.py`
    - Definir el dataclass `SolutionStep` con campos `number`, `operation`, `latex_expr`, `justification`, `detail`.
    - Implementar `generate_steps(rhs, symbolic_result) -> StepByStepResult` que desglose la resolución según el tipo de EDO detectado.
    - Para EDOs separables: identificación, separación `f(y)dy = g(x)dx`, integración de cada lado, despeje de `y`, aplicación de condiciones.
    - Para EDOs lineales: reescritura en forma estándar, cálculo del factor integrante `μ(x)`, multiplicación, reconocimiento de derivada de producto, integración, despeje.
    - Para EDOs de Bernoulli: mostrar sustitución `v = y^(1-n)`, transformación a EDO lineal, luego seguir el flujo lineal.
    - Para EDOs exactas: verificación `∂M/∂y = ∂N/∂x`, integración de `M` respecto a `x`, determinación de `g(y)`, función potencial.
    - Generar `ascii_text` para exportar al portapapeles.
    - Para el caso numérico (sin solución simbólica): generar pasos del método numérico (discretización, evaluación de `f(x,y)`, avance del integrador).
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.9_

  - [x]* 4.2 Escribir tests unitarios para el generador de pasos
    - `generate_steps` de `dy/dx = y` (separable) retorna lista no vacía con el paso de identificación de tipo.
    - `generate_steps` de EDO lineal incluye paso de factor integrante.
    - Todos los pasos tienen `latex_expr` no vacío y `justification` no vacío.
    - `ascii_text` no está vacío y contiene los números de paso.
    - _Requirements: 6.1, 6.2, 6.7_

- [x] 5. Solver numérico
  - [x] 5.1 Implementar `math_engine/numeric_solver.py`
    - Definir el dataclass `NumericResult` con `x_arr`, `y_arr`, `success`, `message`.
    - Implementar `solve_numeric(rhs, conditions, n_points=500) -> NumericResult` usando `sympy.lambdify` y `scipy.integrate.solve_ivp`.
    - Devolver `success=False` si `solve_ivp.success` es `False`, con el mensaje de error del solver.
    - Validar que `x_min < x_max` antes de llamar al solver; si no, devolver `success=False`.
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 Escribir tests unitarios para el solver numérico
    - Solución de `dy/dx = y` con `(0, 1)` en `[0, 2]` aproxima `exp(x)` con error < 1e-4.
    - `x_arr` tiene ≥ 500 puntos.
    - Intervalo inválido (`x_min > x_max`) retorna `success=False`.
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 6. Checkpoint — verificar math engine completo
  - Ejecutar `pytest tests/test_parser.py tests/test_symbolic_solver.py tests/test_numeric_solver.py tests/test_step_generator.py` y asegurarse de que todos los tests pasen. Preguntar al usuario si surgen dudas.

- [x] 7. Catálogo de ejercicios predefinidos
  - [x] 7.1 Implementar `data/exercises.py`
    - Definir el dataclass `Exercise` con campos `id`, `ode_type`, `name`, `equation_text`, `latex_str`, `description`, `initial_conditions`.
    - Implementar `load_exercises() -> list[Exercise]` con ≥ 15 ejercicios: separables (≥3), lineales (≥3), exactas (≥2), homogéneas (≥2), Bernoulli (≥2), aplicaciones (crecimiento/decaimiento, mezcla, circuito RC) (≥3).
    - Cada ejercicio debe incluir `equation_text` en sintaxis Python/SymPy válida y `latex_str` para renderizado.
    - _Requirements: 8.1, 8.3_

  - [x]* 7.2 Escribir tests unitarios para los ejercicios
    - El catálogo contiene ≥ 15 ejercicios.
    - Cada tipo requerido tiene el número mínimo de ejercicios.
    - Cada `Exercise.equation_text` es parseable sin error por `parse_ode`.
    - _Requirements: 8.1_

- [x] 8. Componentes de UI: entrada y barra de símbolos
  - [x] 8.1 Implementar `ui/equation_input.py`
    - Crear `EquationInput(ttk.Frame)` con un `tk.Text` de una línea.
    - Implementar `insert_token(token, place_cursor_inside=False)`: inserta el token en la posición del cursor y, si `place_cursor_inside=True`, posiciona el cursor dentro de los paréntesis.
    - Implementar `get_text() -> str` y `set_text(text: str) -> None`.
    - Exponer el callback `on_change: Callable[[str], None]` que se dispara en cada pulsación de tecla.
    - Ligar los atajos de teclado (`Ctrl+D`, `Ctrl+I`, `Ctrl+Shift+I`, `Ctrl+E`, `Ctrl+Shift+S`, `Ctrl+P`) al método `insert_token` cuando el widget tiene foco.
    - _Requirements: 1.1, 7.1, 7.2, 7.4_

  - [x] 8.2 Implementar `ui/symbol_toolbar.py`
    - Crear `SymbolToolbar(ttk.Frame)` con botones `ttk.Button` para cada símbolo del Requirement 7.1.
    - Al hacer clic en un botón, llamar a `EquationInput.insert_token(...)`.
    - _Requirements: 7.3_

- [x] 9. Componente de UI: panel de condiciones
  - Implementar `ui/condition_panel.py`
  - Crear `ConditionPanel(ttk.LabelFrame)` con campos `ttk.Entry` para `x₀`, `y₀`, `x_min`, `x_max`, `y_min`, `y_max`.
  - Implementar `get_conditions() -> SolverConditions` y `set_conditions(cond: SolverConditions) -> None`.
  - Incluir valores por defecto `x_min=-5.0`, `x_max=5.0` visibles en los campos.
  - _Requirements: 4.2, 5.2_

- [x] 10. Componente de UI: previsualización matemática
  - Implementar `ui/math_preview.py`
  - Crear `MathPreview(ttk.Frame)` que incruste una figura Matplotlib (`FigureCanvasTkAgg`) de tamaño fijo.
  - Implementar `render(latex_str: str) -> None` que use `matplotlib.mathtext` para renderizar la cadena LaTeX con fuente mínima de 14pt.
  - Implementar `show_placeholder() -> None` que muestre el placeholder tipográfico `dy/dx = f(x, y)`.
  - Cuando `Equation_Input` está vacío, llamar automáticamente a `show_placeholder()`.
  - Cuando hay condiciones iniciales disponibles, renderizar ecuación y condiciones juntas.
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 11. Componente de UI: panel paso a paso
  - Implementar `ui/step_by_step_panel.py`
  - Crear `StepByStepPanel(ttk.Frame)` con un `tk.Text` de solo lectura con scroll vertical.
  - Implementar `display_steps(steps: list[SolutionStep]) -> None` que renderice cada paso con: número de paso, figura Matplotlib incrustada con la expresión LaTeX (`mathtext`), justificación textual y sub-detalle atómico si existe.
  - Implementar `clear() -> None` para borrar el contenido.
  - Implementar `copy_to_clipboard() -> None` que exporte `ascii_text` al portapapeles del sistema operativo usando `tk.clipboard_clear()` + `tk.clipboard_append()`.
  - Agregar botón "Copiar pasos" que llame a `copy_to_clipboard()`.
  - _Requirements: 6.1, 6.7, 6.8, 6.10_

- [x] 12. Componente de UI: vista de gráficas
  - [x] 12.1 Implementar `ui/plot_view.py` — modo solución `y(x)`
    - Crear `PlotMode(str, Enum)` con valores `SOLUTION`, `DIRECTION_FIELD`, `SURFACE_3D`.
    - Crear `PlotView(ttk.Frame)` con `FigureCanvasTkAgg` de tamaño completo y selector de modo (`ttk.Notebook` o `ttk.Combobox`).
    - Implementar `plot_solution(symbolic, numeric, conditions)`: graficar `y(x)` con ejes etiquetados, título y cuadrícula. Superponer curva numérica con color y etiqueta diferenciados. Renderizar familia de curvas si hay múltiples condiciones iniciales.
    - Incluir la barra de herramientas nativa de Matplotlib (zoom, pan, guardar).
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 12.2 Implementar el modo Direction Field en `PlotView`
    - Implementar `plot_direction_field(rhs, conditions, solution_curve=None)`: calcular y renderizar el campo de pendientes sobre cuadrícula uniforme usando segmentos normalizados.
    - Usar el intervalo `[-5, 5] × [-5, 5]` por defecto si `conditions` no tiene valores explícitos; registrar los valores usados en la `StatusBar`.
    - Si `solution_curve` está disponible, superponer la curva `y(x)` sobre el campo.
    - Implementar la función auxiliar `compute_direction_field_bounds(rhs, conditions)` que retorne la tupla `(x_min, x_max, y_min, y_max)`.
    - _Requirements: 5.6, 5.7, 5.8, 5.9_

  - [x] 12.3 Implementar el modo Surface 3D en `PlotView`
    - Implementar `plot_surface_3d(rhs, conditions)`: renderizar `z = f(x, y)` con `mpl_toolkits.mplot3d` sobre cuadrícula de mínimo 50×50 puntos, ejes etiquetados `x`, `y`, `z = f(x,y)` y barra de color.
    - Implementar `set_3d_view(elev, azim)` para las vistas predefinidas.
    - Agregar tres botones de vista predefinida: Frontal (0°, 0°), Lateral (0°, 90°), Isométrica (30°, 45°).
    - Habilitar rotación interactiva mediante arrastre del ratón (nativa de `mpl_toolkits.mplot3d`).
    - _Requirements: 5.6, 5.10, 5.11, 5.12, 5.13_

- [x] 13. Componente de UI: biblioteca de ejercicios
  - Implementar `ui/exercise_library.py`
  - Crear `ExerciseLibrary(ttk.Frame)` con `ttk.Treeview` o `tk.Listbox` con scroll para listar los ejercicios.
  - Mostrar para cada ejercicio: nombre del tipo, ecuación formateada tipográficamente y descripción breve.
  - Al seleccionar un ejercicio, disparar el callback `on_select(exercise: Exercise)` hacia el controlador.
  - Agregar botón "Copiar ecuación" que copie `exercise.equation_text` al portapapeles.
  - _Requirements: 8.2, 8.3, 8.4, 8.5_

- [x] 14. Componente de UI: barra de estado
  - Implementar `ui/status_bar.py`
  - Crear `StatusBar(ttk.Frame)` en la parte inferior de la ventana.
  - Implementar `set_status(message, level="info")` con estilos diferenciados para `info`, `error` y `warning`.
  - Implementar `show_spinner() -> None` y `hide_spinner() -> None` para el indicador de progreso visual.
  - _Requirements: 9.4, 9.5_

- [x] 15. Checkpoint — verificar UI components
  - Verificar que todos los módulos de `ui/` y `data/` importan sin error ejecutando `python -c "from ui import *; from data.exercises import load_exercises"`. Preguntar al usuario si surgen dudas.

- [x] 16. Controlador principal e integración
  - [x] 16.1 Implementar `app.py` — esqueleto del controlador
    - Definir el dataclass `AppState` con campos `current_equation_text`, `last_parse_result`, `symbolic_result`, `numeric_result`, `conditions`, `plot_mode`, `step_by_step_visible`.
    - Crear `App(tk.Tk)` con el layout raíz usando `ttk.PanedWindow` horizontal: panel izquierdo (`SymbolToolbar`, `EquationInput`, `ConditionPanel`, botones Resolver, `ExerciseLibrary`) y panel derecho (`MathPreview`, `StepByStepPanel`, `PlotView`).
    - Implementar `_configure_styles()` con `ttk.Style` para definir colores, fuentes y apariencia de todos los widgets.
    - Configurar tamaño mínimo de ventana 1024×768.
    - Implementar el bloque `try/except ImportError` al inicio para verificar las dependencias críticas y mostrar `tkinter.messagebox.showerror` si falta alguna.
    - _Requirements: 9.1, 9.2, 9.3, 10.4_

  - [x] 16.2 Implementar el flujo de cambio de ecuación en `app.py`
    - Implementar `_on_equation_changed(text: str)`: llamar a `parse_ode`, actualizar `AppState`, actualizar `MathPreview` (render o placeholder) y mostrar errores en `StatusBar`.
    - Conectar el callback `EquationInput.on_change` a `_on_equation_changed`.
    - _Requirements: 1.2, 1.3, 2.1, 2.2_

  - [x] 16.3 Implementar el flujo de resolución simbólica en `app.py`
    - Implementar `_on_solve_symbolic()`: ejecutar `solve_symbolic` en hilo secundario (`threading.Thread`), activar `StatusBar.show_spinner()` y, al completarse, actualizar `MathPreview`, `StepByStepPanel` y `PlotView` en el hilo principal con `app.after(0, callback)`.
    - Si `SymbolicResult.error` está poblado, mostrar el error y ofrecer automáticamente la solución numérica.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.1, 9.4, 9.5_

  - [x] 16.4 Implementar el flujo de resolución numérica en `app.py`
    - Implementar `_on_solve_numeric()`: validar que `ConditionPanel` tiene `x₀`, `y₀`, `x_min`, `x_max`; ejecutar `solve_numeric` en hilo secundario; al completarse, actualizar `PlotView` y `StatusBar`.
    - Si `NumericResult.success` es `False`, mostrar el mensaje y sugerir ajustar el intervalo o las condiciones iniciales.
    - _Requirements: 4.1, 4.2, 4.4, 9.4, 9.5_

  - [x] 16.5 Implementar el flujo de cambio de modo de visualización en `app.py`
    - Implementar `_on_mode_changed(mode: PlotMode)`: según el modo seleccionado, llamar a `PlotView.plot_solution`, `PlotView.plot_direction_field` o `PlotView.plot_surface_3d` con los datos del `AppState` actual.
    - _Requirements: 5.6, 5.7, 5.9, 5.10_

  - [x] 16.6 Implementar la carga de ejercicios desde `ExerciseLibrary` en `app.py`
    - Conectar `ExerciseLibrary.on_select` al controlador: cargar `exercise.equation_text` en `EquationInput`, cargar `exercise.initial_conditions` en `ConditionPanel` si existen, y disparar `_on_equation_changed`.
    - _Requirements: 8.2, 8.5_

  - [x] 16.7 Implementar los atajos de teclado globales en `app.py`
    - Implementar `_bind_shortcuts()`: ligar `Ctrl+D`, `Ctrl+I`, `Ctrl+Shift+I`, `Ctrl+E`, `Ctrl+Shift+S`, `Ctrl+P` a nivel de ventana para que, si el foco no está en `EquationInput`, se transfiera el foco e inserte el token.
    - _Requirements: 7.1, 7.4_

- [x] 17. Checkpoint — integración completa
  - Ejecutar `pytest tests/` (excluyendo `test_properties.py`) y verificar que todos los tests unitarios pasen. Lanzar la aplicación con `python app.py` y probar manualmente la carga de un ejercicio, la resolución simbólica y la visualización en los tres modos. Preguntar al usuario si surgen dudas.

- [x] 18. Tests de propiedades (Hypothesis)
  - [x] 18.1 Implementar la Propiedad 1 en `tests/test_properties.py`
    - **Property 1: Round-trip de parsing y renderizado LaTeX**
    - Para cualquier ecuación válida en `valid_ode_texts`, `parse_ode` debe retornar `rhs ≠ None` y `latex_str` no vacío.
    - **Validates: Requirements 1.1, 1.4, 2.1**

  - [x]* 18.2 Ejecutar test de Propiedad 1
    - Correr `pytest tests/test_properties.py::test_property_1_parse_roundtrip` con `max_examples=100`.

  - [x] 18.3 Implementar la Propiedad 2 en `tests/test_properties.py`
    - **Property 2: Rechazo de entradas inválidas**
    - Para cualquier texto en `invalid_ode_texts`, `parse_ode` debe retornar `rhs = None` y `error ≠ None`.
    - **Validates: Requirements 1.3**

  - [x]* 18.4 Ejecutar test de Propiedad 2
    - Correr `pytest tests/test_properties.py::test_property_2_invalid_input_rejected` con `max_examples=100`.

  - [x] 18.5 Implementar la Propiedad 3 en `tests/test_properties.py`
    - **Property 3: Solución simbólica satisface la EDO original**
    - Para cualquier `(rhs, tipo)` en `solvable_odes`, la solución general de `solve_symbolic` debe satisfacer la EDO original al sustituir y simplificar con SymPy (resultado idénticamente cero).
    - **Validates: Requirements 3.1, 3.2, 3.5**

  - [x]* 18.6 Ejecutar test de Propiedad 3
    - Correr `pytest tests/test_properties.py::test_property_3_symbolic_solution_satisfies_ode` con `max_examples=100`.

  - [x] 18.7 Implementar la Propiedad 4 en `tests/test_properties.py`
    - **Property 4: Solución particular satisface condiciones iniciales**
    - Para cualquier `(rhs, tipo)` en `solvable_odes` y par `(x0, y0)` flotantes en `[-3, 3]`, la solución particular al evaluarse en `x=x0` debe dar `y0` con tolerancia ε < 1e-6.
    - **Validates: Requirements 3.3**

  - [x]* 18.8 Ejecutar test de Propiedad 4
    - Correr `pytest tests/test_properties.py::test_property_4_particular_solution_satisfies_ic` con `max_examples=100`.

  - [x] 18.9 Implementar la Propiedad 5 en `tests/test_properties.py`
    - **Property 5: Solución numérica y cobertura mínima de puntos**
    - Para cualquier entrada en `numeric_odes`, `solve_numeric` exitoso debe tener `len(x_arr) >= 500`, `|x_arr[0] - x0| < 1e-9` e `|y_arr[0] - y0| < 1e-6`.
    - **Validates: Requirements 4.1, 4.3**

  - [x]* 18.10 Ejecutar test de Propiedad 5
    - Correr `pytest tests/test_properties.py::test_property_5_numeric_solution_coverage_and_ic` con `max_examples=100`.

  - [x] 18.11 Implementar la Propiedad 6 en `tests/test_properties.py`
    - **Property 6: Integridad del catálogo de ejercicios**
    - Para cualquier ejercicio muestreado de `load_exercises()`: el catálogo total ≥ 15, cada ejercicio tiene `name`, `latex_str` y `description` no vacíos, y `equation_text` es parseable sin error.
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.5**

  - [x]* 18.12 Ejecutar test de Propiedad 6
    - Correr `pytest tests/test_properties.py::test_property_6_exercise_catalog_integrity` con `max_examples=100`.

  - [x] 18.13 Implementar la Propiedad 7 en `tests/test_properties.py`
    - **Property 7: Inserción de tokens mediante atajos de teclado**
    - Para cualquier `(key, (token, cursor_inside))` en `SHORTCUT_MAP`, `EquationInput.insert_token` debe insertar el token y, si `cursor_inside=True`, posicionar el cursor entre los paréntesis.
    - **Validates: Requirements 7.1, 7.2**

  - [x]* 18.14 Ejecutar test de Propiedad 7
    - Correr `pytest tests/test_properties.py::test_property_7_shortcut_inserts_token` con `max_examples=100`.

  - [x] 18.15 Implementar la Propiedad 8 en `tests/test_properties.py`
    - **Property 8: Direction Field usa intervalo por defecto cuando faltan condiciones**
    - Para cualquier `rhs` en `valid_rhs_exprs`, `compute_direction_field_bounds(rhs, SolverConditions())` debe retornar exactamente `(-5.0, 5.0, -5.0, 5.0)`.
    - **Validates: Requirements 5.9**

  - [x]* 18.16 Ejecutar test de Propiedad 8
    - Correr `pytest tests/test_properties.py::test_property_8_direction_field_default_interval` con `max_examples=100`.

  - [x] 18.17 Implementar la Propiedad 9 en `tests/test_properties.py`
    - **Property 9: Resolución mínima y etiquetas en visualizaciones**
    - Para cualquier llamada válida a `plot_surface_3d`: cuadrícula ≥ 50×50 puntos y ejes con etiquetas no vacías `x`, `y`, `z = f(x,y)`. Para `plot_solution` y `plot_direction_field`: ejes 2D con `xlabel` e `ylabel` no vacíos.
    - **Validates: Requirements 5.1, 5.10, 5.11**

  - [x]* 18.18 Ejecutar test de Propiedad 9
    - Correr `pytest tests/test_properties.py::test_property_9_surface_3d_resolution_and_labels` con `max_examples=100`.

- [x] 19. Exportación de gráficas *(Opcional — Requirement 11)*
  - [x]* 19.1 Implementar `ui/export_manager.py`
    - Implementar `export_figure(fig: Figure) -> None` que abra `tkinter.filedialog.asksaveasfilename` con filtros PNG/JPEG/PDF.
    - Usar `matplotlib.backends.backend_pdf.PdfPages` para exportar a PDF y `figure.savefig(..., dpi=300)` para imágenes.
    - Si `Pillow` no está instalado, mostrar un error descriptivo con instrucciones de instalación en lugar de abortar.
    - Agregar botón "Exportar" al `PlotView` que llame a `export_figure` con la figura activa.
    - Al completarse, llamar a `StatusBar.set_status` con la ruta del archivo guardado.
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 20. Checkpoint final — suite completa de tests
  - Ejecutar `pytest tests/` con todos los tests unitarios y de propiedades y asegurarse de que todos pasen. Preguntar al usuario si surgen dudas.

## Tramo de hardening y release (21-25)

- [x] 21. Documentación y empaquetado
  - [x] 21.1 Reescribir `README.md`
    - Incluir descripción, características, requisitos, instalación, ejecución, pruebas, estructura del proyecto, atajos y uso de la exportación.
    - Documentar la necesidad de Tk y el uso de Xvfb en entornos sin display.
    - _Requirements: 10.1, 10.3_

  - [x] 21.2 Crear `pyproject.toml`
    - Metadatos del proyecto, versión 1.0.0, `requires-python >=3.10`, dependencias fijadas y entry point `ode-calculator = "app:main"`.
    - Configurar pytest: `testpaths`, `pythonpath` y filtrado de avisos de Pyparsing.
    - _Requirements: 10.1, 10.2_

  - [x] 21.3 Fijar versiones exactas en `requirements.txt`
    - Reemplazar el rango de Pillow por una versión exacta compatible con Python 3.10-3.12.
    - _Requirements: 10.2_

- [x] 22. Robustez del arranque
  - [x] 22.1 Crear `dependencies.py`
    - Función `missing_dependencies()` sin importar librerías de terceros.
    - _Requirements: 10.4_

  - [x] 22.2 Verificar dependencias antes de los imports de SymPy/SciPy/Matplotlib/NumPy en `app.py`
    - Mostrar un mensaje descriptivo con instrucciones de instalación y abortar el arranque si falta alguna.
    - _Requirements: 10.4_

  - [x] 22.3 Añadir tests del verificador de dependencias
    - Cubrir caso completo y caso con dependencias faltantes mediante monkeypatch.
    - _Requirements: 10.4_

- [x] 23. Spinner diferido
  - [x] 23.1 Mostrar el spinner solo cuando la operación supere 2 segundos
    - Programar el spinner con `after(2000, ...)` y cancelarlo al terminar.
    - Mantener el mensaje de estado inmediato.
    - _Requirements: 9.4, 9.5_

  - [x] 23.2 Añadir test del comportamiento diferido
    - Verificar que no se muestra al iniciar y que se muestra al vencer el temporizador simulado.
    - _Requirements: 9.5_

- [x] 24. Integración continua
  - [x] 24.1 Crear `.github/workflows/tests.yml`
    - Matriz Python 3.10, 3.11 y 3.12 ejecutando la suite con `pytest`.
    - Job adicional con Tk y Xvfb para ejecutar también los tests de UI en Python 3.12.
    - _Requirements: 10.3_

- [ ] 25. Checkpoint de release
  - [x] 25.1 Ejecutar la suite completa y el smoke test de la aplicación.
  - [x] 25.2 Fusionar `feature/hardening` en `develop` y `develop` en `main`.
  - [x] 25.3 Crear y publicar la etiqueta `v1.1.0`.
  - _Requirements: 10.2, 10.3_

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido.
- La tarea 19 (exportación) y sus sub-tareas son opcionales en su totalidad (Requirement 11 es opcional).
- Cada tarea referencia requisitos específicos para trazabilidad completa.
- Los checkpoints en las tareas 6, 15, 17 y 20 aseguran validación incremental.
- Los tests de propiedades (tarea 18) se ubican al final pero sus sub-tareas de ejecución están marcadas como opcionales; las sub-tareas de implementación del test sí deben ejecutarse.
- La barra de herramientas nativa de Matplotlib (zoom, pan, guardar) cubre los controles interactivos del Requirement 5.4 sin código adicional.
- El hilo secundario en los solvers (tarea 16.3 y 16.4) es esencial para mostrar el spinner cuando el cálculo supera 2 segundos (Requirement 9.5).
