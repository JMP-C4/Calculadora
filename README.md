# ODE Calculator

Calculadora de escritorio para resolver, explicar y visualizar ecuaciones diferenciales ordinarias de primer orden. Está pensada para estudiantes de ingeniería y profesionales que necesitan obtener soluciones simbólicas o numéricas, revisar el procedimiento paso a paso y analizar el comportamiento de la ecuación mediante gráficas 2D y 3D.

## Características

- Entrada de EDOs en sintaxis Python/SymPy (`dy/dx = x + y`, `y' = sin(x)*y`).
- Solución simbólica con SymPy para EDOs separables, lineales, exactas, homogéneas y Bernoulli.
- Solución numérica con `scipy.integrate.solve_ivp` (Runge-Kutta RK45), con al menos 500 puntos.
- Condiciones iniciales y aplicación automática de la solución particular.
- Previsualización matemática tipográfica con Matplotlib.
- Procedimiento paso a paso con justificación matemática y copiado en texto ASCII.
- Tres modos de visualización: solución `y(x)`, campo de direcciones y superficie 3D.
- Familia de curvas para soluciones simbólicas.
- Biblioteca de 18 ejercicios con condiciones iniciales.
- Exportación de la gráfica activa a PNG, JPEG o PDF a 300 DPI.
- Atajos de teclado para insertar símbolos matemáticos.
- Interfaz tkinter/ttk con barra de estado, indicador de progreso y cálculo en segundo plano.

## Requisitos

- Python 3.10, 3.11 o 3.12.
- Tkinter (incluido en las distribuciones oficiales de Python; en Ubuntu puede requerir `python3-tk`).
- Linux, macOS o Windows con entorno gráfico.

En Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk
```

## Instalación

```bash
cd /home/juan_parada/Escritorio/Programas/Proyectos/ode-calculator

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

También puedes instalar el proyecto como paquete editable:

```bash
pip install -e ".[dev]"
```

## Ejecución

Con el entorno virtual activo:

```bash
python app.py
```

Si instalaste el paquete editable, también puedes usar:

```bash
ode-calculator
```

## Uso

1. Escribe una EDO en el campo de entrada o selecciona un ejercicio de la biblioteca.
2. Revisa la previsualización matemática.
3. Introduce condiciones iniciales e intervalos en el panel de condiciones.
4. Pulsa **Resolver simbólico** o **Resolver numérico**.
5. Consulta los pasos, cambia el modo de gráfica y exporta el resultado si lo necesitas.

### Atajos de teclado

| Atajo | Token insertado |
| --- | --- |
| `Ctrl+D` | `dy/dx` |
| `Ctrl+I` | `Integral` |
| `Ctrl+Shift+I` | `oo` |
| `Ctrl+E` | `exp()` |
| `Ctrl+Shift+S` | `sqrt()` |
| `Ctrl+P` | `pi` |

Los atajos funcionan aunque el foco no esté en el campo de ecuación: la aplicación lo transfiere automáticamente.

## Pruebas

Ejecutar toda la suite:

```bash
python -m pytest tests/ -q
```

En un servidor sin pantalla, usa Xvfb para que también se ejecuten los tests de interfaz:

```bash
xvfb-run -a python -m pytest tests/ -q
```

Los tests unitarios cubren parser, solver simbólico, solver numérico, generador de pasos, componentes de UI, integración de la aplicación, exportación y propiedades con Hypothesis.

## Estructura del proyecto

```text
ode-calculator/
├── app.py                  # Ventana principal, estado y flujos asíncronos
├── dependencies.py         # Verificación de dependencias al arrancar
├── data/
│   └── exercises.py        # Catálogo de ejercicios
├── math_engine/
│   ├── parser.py           # Parsing y validación de EDOs
│   ├── symbolic_solver.py  # Solución simbólica y condiciones iniciales
│   ├── numeric_solver.py   # Integración numérica RK45
│   └── step_generator.py   # Clasificación y pasos justificados
├── ui/
│   ├── equation_input.py
│   ├── symbol_toolbar.py
│   ├── condition_panel.py
│   ├── math_preview.py
│   ├── step_by_step_panel.py
│   ├── plot_view.py
│   ├── exercise_library.py
│   ├── export_manager.py
│   └── status_bar.py
├── tests/
├── requirements.txt
├── pyproject.toml
├── requirements.md
├── design.md
└── tasks.md
```

## Exportación

El botón **Exportar** del panel de gráficas abre un diálogo nativo con filtros PNG, JPEG y PDF. Las imágenes se guardan a 300 DPI y el PDF se genera con `matplotlib.backends.backend_pdf.PdfPages`. La ruta final se muestra en la barra de estado.

La exportación de imágenes requiere Pillow, incluida en `requirements.txt`.

## Documentación de diseño

- `requirements.md`: requisitos funcionales y criterios de aceptación.
- `design.md`: arquitectura, modelos de datos, propiedades e interfaz.
- `tasks.md`: plan de implementación y estado de las tareas.
