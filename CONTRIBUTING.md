# Contribuir a ODE Calculator

Gracias por ayudar a mejorar la calculadora. El proyecto separa el motor
matemático puro (`odecalc/`) de las interfaces (`apps/`, `ui/`). Ninguna
interfaz debe importar lógica de otra: todas consumen `odecalc.api.solve`.

## Entorno de desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
# Sólo si vas a trabajar en la interfaz tkinter:
sudo apt-get install -y python3-tk python3-pil.imagetk
python -c "import tkinter; from PIL import ImageTk; print(tkinter.TkVersion)"
```

## Reglas para cambios matemáticos

1. Cada método nuevo entra con pruebas, pasos explicados y verificación.
2. Nunca se presenta como correcta una solución con residuo distinto de cero:
   si la verificación simbólica no basta, se exige comprobación numérica.
3. Los casos de regresión en `tests/regression/test_plan_cases.py` son
   intocables: cualquier cambio debe mantenerlos verdes.
4. Las soluciones implícitas son de primera clase; no se fuerza un despeje
   que introduzca ramas incorrectas.
5. Las integrales no elementales se dejan indicadas en `x`, nunca con `y(x)`
   dentro del integrando.

## Pruebas

```bash
# Núcleo rápido (sin tkinter ni pantalla)
python -m pytest tests/unit tests/regression tests/integration tests/property -q

# Banco completo de 100+ ejercicios
python -m pytest tests/bank -q

# Cobertura del motor
python -m pytest tests/unit tests/regression tests/integration tests/property tests/bank \
  --cov=odecalc --cov-report=term-missing
```

La suite heredada de la interfaz tkinter se ejecuta con `xvfb-run` cuando el
entorno tiene Tk y Pillow con `ImageTk` instalados. En servidores sin esas
dependencias, `tests/conftest.py` las omite automáticamente.

## Estilo

- Python 3.10+ con `from __future__ import annotations`.
- Español para mensajes de usuario y documentación; nombres de código en
  inglés cuando sean API pública.
- Cuatro espacios, líneas de hasta 100 caracteres y sin dependencias nuevas
  en el núcleo sin discutirlo antes.
- No incluir rutas personales, credenciales ni archivos de configuración de
  asistentes en el repositorio.

## Seguridad

El parser rechaza atributos, guiones bajos, cadenas, corchetes, palabras
reservadas e importaciones. Cualquier cambio en `odecalc/parsing/` debe añadir
pruebas con entradas maliciosas y ejecutar toda la suite de seguridad.
