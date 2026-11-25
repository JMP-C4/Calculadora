# Reporte de Auditoría Técnica — ODE Calculator / EDO-Lab

**Fecha:** 2026-11-25  
**Alcance:** Auditoría integral del motor matemático (`odecalc/`, `core/`, `math_engine/`), interfaces gráficas (`apps/desktop/`, `apps/web/`, `ui/`), datos (`data/`), dependencias y empaquetado (`pyproject.toml`, `dependencies.py`, `app.py`).  

> [!NOTE]
> Este documento fue revisado contra el estado actual del árbol de trabajo, después de la refactorización de `ui/`, `apps/desktop/`, `core/` y `app.py`. Las referencias `file:line` y el estado de cada hallazgo se actualizaron. La verificación ejecutó la suite completa: `475 passed, 49 warnings` en `.venv`. Las soluciones recomendadas **no** fueron implementadas; esta corrección es documental.

---

## Resumen cuantitativo

| Severidad histórica | Hallazgos | Vigentes | Parcialmente corregidos | Reclasificados |
| --- | ---: | ---: | ---: | ---: |
| **Crítico** | 7 | 7 | 0 | 0 |
| **Alto** | 11 | 8 | 2 | 1 |
| **Medio** | 11 | 7 | 4 | 0 |
| **Bajo / Mejora** | 5 | 4 | 1 | 0 |
| **Total** | **34** | **26** | **7** | **1** |

A-05 se mantiene en el listado por trazabilidad, pero su impacto observable quedó reducido a robustez interna: el parser actual reescribe el ejemplo como ecuación explícita y el clasificador sí lo etiqueta.

---

## Hallazgos Críticos

### C-01. Exponentes negativos sin llaves fallan en el parser principal
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/parsing/parser.py:227-242`, `odecalc/parsing/parser.py:306-309`, `odecalc/parsing/parser.py:524-527`.
- **Descripción del error o punto a corregir:** `parse_ode` aplica `_latex_to_plain` a toda entrada, incluso texto plano. Al procesar `^`, `_latex_to_plain` llama a `_read_latex_group(source, position + 1)`. Si el exponente no lleva `{...}` ni `(...)` —por ejemplo, `y' = x^-2` o `y' = e^-x`—, `_read_latex_group` devuelve un único carácter (`"-"` en `:242`), transformando `x^-2` en `x**(-)2` y produciendo un `SyntaxError` en `parse_expr`.
- **Impacto en la aplicación:** Rechaza ecuaciones cotidianas escritas con exponente negativo sin llaves en el motor `odecalc`, escritorio, web y EDO-Lab.
- **Solución recomendada:** En `_read_latex_group` (o en la rama `^` de `_latex_to_plain`), consumir el signo unario `+`/`-` junto con el número, símbolo o grupo siguiente cuando no haya delimitadores, o evitar la reescritura de `^` si la entrada no contiene comandos LaTeX.

### C-02. Comandos de funciones LaTeX sin delimitadores alteran silenciosamente la ecuación
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/parsing/parser.py:370-396`, especialmente `:386-388`.
- **Descripción del error o punto a corregir:** Al encontrar un comando de `_LATEX_FUNCTIONS` (`\sin`, `\cos`, `\ln`, `\exp`, etc.) sin `{...}` ni `(...)` después, la rama `elif cursor < len(source) and source[cursor] in "xyz0123456789":` toma un único carácter como argumento. `$$\frac{dy}{dx} = \sin 2x$$` se convierte en `dy/dx = sin(2)x` y `\ln xy` en `dy/dx = ln(x)y`.
- **Impacto en la aplicación:** Se resuelve y verifica como correcta (`verification.status == "ok"`) una EDO distinta de la introducida, sin advertencia.
- **Solución recomendada:** Consumir el término completo tras la función o emitir un error/advertencia explícita cuando el argumento compuesto carezca de paréntesis o llaves.

### C-03. Bloqueo por reintentos numéricos y pérdida del respaldo ante timeout
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/numeric/solver.py:111`, `odecalc/numeric/solver.py:117-137`, `odecalc/numeric/solver.py:155-156`, `odecalc/api.py:273-301`, `odecalc/api.py:346-358`.
- **Descripción del error o punto a corregir:**
  1. `solve_numeric` itera secuencialmente `("RK45", "LSODA", "Radau", "BDF", "DOP853")`. Ante una explosión en tiempo finito (`y' = y^2`, `y(0) = 1`, `[-1, 2]`) o un límite de dominio real, la cascada no terminó en más de 30 s en la verificación.
  2. `timeout` envuelve todo `_solve_impl` (simbólico y numérico) en un único `run_with_timeout`; se reproduce `TimeoutError` incluso con `compute_numeric=True` en `y' = x*y + sin(x)`. La capa web lo traduce a HTTP 504 (`apps/web/server.py:256-257`).
  3. `blow_up` solo se evalúa cuando fallan todos los segmentos (`if not segments:`, `:131-137`). Si un sentido integra bien y el otro explota, se devuelve `False`.
- **Impacto en la aplicación:** Timeouts en API web y escritorio para EDOs válidas, y omisión de la bandera `blow_up` en intervalos bilaterales.
- **Solución recomendada:** Abortar la cascada al detectar `overflow`/valores no finitos, marcar `blow_up=True` si cualquier segmento falla por explosión y aplicar `timeout` solo a la fase simbólica con degradación automática a `solve_numeric`.

### C-04. Ajuste de datos: decaimiento prohibido, valores no positivos y validación antes de deduplicar
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `core/ajuste.py:259-263`, `core/ajuste.py:287-295`, `core/ajuste.py:303-308`, `core/ajuste.py:356-365`.
- **Descripción del error o punto a corregir:**
  1. `_valoraciones_iniciales` impone `limites = ([1e-6], [10.0])` para `exponencial`, forzando `k > 0`. Con `data/ejemplos/decaimiento.csv` (`k ≈ -0.15`) el optimizador queda en `k = 1e-6` (`R² = -6.276`, `AIC = 352.53`).
  2. En `logistico` y `gompertz`, si `max_y <= 0` la cota inferior excede la superior y `least_squares` lanza `ValueError`.
  3. `len(subconjunto) < 5` se comprueba antes de `drop_duplicates("x")` (`:263`), por lo que una tabla con menos de 5 valores de `x` distintos pasa el filtro.
- **Impacto en la aplicación:** El modelo exponencial falla en series de decaimiento, incluido el ejemplo oficial, y el ajuste falla con series observadas no positivas.
- **Solución recomendada:** Permitir `k < 0` con estimación inicial log-lineal, validar `max_y > 0` antes de fijar cotas de `K` y contar puntos después de deduplicar por `x`.

### C-05. División por cero en `resistencia_aire` y `lambda` bloqueado en la ruta de texto
- **Estado:** Vigente, matizado.
- **Ruta del archivo y línea(s) afectada(s):** `core/modelos.py:217-220`, `core/modelos.py:244`, `core/modelos.py:313-317`, `core/modelos.py:347-353`, `core/ia_opcional.py:177-182`, `odecalc/parsing/parser.py:151-155`, `core/parser.py:139-141`.
- **Descripción del error o punto a corregir:**
  1. `c` tiene `minimo=0.0` (`:244`), valor aceptado por `instanciar_modelo` (`:313-317`), pero `:349` calcula `math.sqrt(m*g/c)` sin exigir `c > 0`: se reproduce `ZeroDivisionError`.
  2. `instanciar_modelo("decaimiento")` **sí funciona** porque sustituye `lambda` por un número (`:335-338`). El bloqueo afecta a la ruta de texto literal: la regla local de `core/ia_opcional.py:179` y la pestaña *Incertidumbre* usan `"y' = -lambda*y"`, rechazado por `_DANGEROUS_WORDS` y por `parsear_con_parametros`.
- **Impacto en la aplicación:** Excepción no controlada al probar `c = 0` en *Resolver* y rechazo de la ecuación de decaimiento en Monte Carlo/Sobol.
- **Solución recomendada:** Condicionar la velocidad terminal cuando `c == 0` o exigir `minimo > 0`; usar un identificador seguro como `lam` en reglas y texto.

### C-06. Uso de `fork` desde procesos multi-hilo
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/timeout.py:38-45`, `apps/web/server.py:101-109`, `apps/web/server.py:272`, `apps/desktop/app.py:1492`, `apps/desktop/app.py:1499`, `core/resultado.py:37-42`.
- **Descripción del error o punto a corregir:** `run_with_timeout` selecciona `mp.get_context("fork")` en Linux, pero se invoca desde hilos secundarios del servidor web, del hilo de cálculo de escritorio y de Streamlit. En Python 3.12 se reproduce el `DeprecationWarning: This process is multi-threaded, use of fork() may lead to deadlocks in the child`. La referencia anterior `apps/desktop/app.py:1256` quedó desactualizada; hoy es `:1499`.
- **Impacto en la aplicación:** Posibles interbloqueos aleatorios de workers bajo carga concurrente.
- **Solución recomendada:** Usar `spawn` o mantener un pool de procesos `spawn` inicializado en el hilo principal al arrancar la aplicación.

### C-07. Evaluación insegura mediante `sp.sympify` en el parser legacy
- **Estado:** Vigente, matizado.
- **Ruta del archivo y línea(s) afectada(s):** `math_engine/parser.py:15`, `math_engine/parser.py:97`, `math_engine/parser.py:128-131`, `math_engine/parser.py:133-142`, `app.py:340`, `app.py:362`, `app.py:420`.
- **Descripción del error o punto a corregir:** La refactorización delegó solo `latex_to_plain` (`:15`, `:97`), sin aplicar `_security_check` ni aislar `__builtins__`. `sp.sympify(rhs_text, locals=_ALLOWED_LOCALS)` (`:129`) ejecuta construcciones Python antes de la validación posterior débil: se reproduce ejecución de `__import__('os').system('echo PWNED')` y aceptación de `lambda t: t` como `sp.Lambda`.
- **Impacto en la aplicación:** Exposición a evaluación arbitraria y denegación de servicio en la ruta legacy (`python app.py`, no `streamlit run app.py`).
- **Solución recomendada:** Delegar en `odecalc.parsing.parse_ode` o usar `parse_expr` con `global_dict={"__builtins__": {}}` y `_security_check`, como en `odecalc/parsing/parser.py:445-478`.

---

## Hallazgos Altos

### A-01. `_compare_numeric` ignora la parte imaginaria y puede producir `NaN` en JSON
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/api.py:88-111` (`mask` en `:100`, `error` en `:103`, asignación en `:106`, comparación en `:107`), `odecalc/serialization.py:18-36`, `odecalc/serialization.py:88`.
- **Descripción del error o punto a corregir:** `mask = np.isfinite(expected.real) & np.isfinite(actual.real)` ignora `.imag`. Con parte imaginaria `NaN`, `error_estimate` queda como `nan` y no se emite advertencia; `serialization.py:88` lo serializa como `NaN` literal.
- **Impacto en la aplicación:** Oculta discrepancias complejas y emite JSON no estándar en `/solve`.
- **Solución recomendada:** Comprobar finitud de `.real` y `.imag`, advertir si hay parte imaginaria significativa y guardar `None` cuando el error no sea finito.

### A-02. Paso numérico corrupto con `sp.latex(str)`
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/api.py:29-85`, línea exacta `:38`.
- **Descripción del error o punto a corregir:** `_numeric_steps` construye `latex=r"\frac{dy}{dx} = " + sp.latex(result.standard_form or "")`. Como `standard_form` es un `str`, el resultado verificado es `\frac{dy}{dx} = \mathtt{\text{dy/dx = x + y}}`.
- **Impacto en la aplicación:** El primer paso del respaldo numérico aparece duplicado/corrupto en web, escritorio y EDO-Lab.
- **Solución recomendada:** Usar `result.input_latex or sp.latex(...)` sin prefijar `\frac{dy}{dx} = ` sobre `standard_form`.

### A-03. `analyze_validity` omite restricciones de raíces pares y funciones inversas
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/verify/validity.py:30-49`, `odecalc/verify/validity.py:52-124`, rama por defecto en `:108-113`.
- **Descripción del error o punto a corregir:** Solo se inspeccionan denominadores y ceros de `sp.log`. Para `y = sqrt(1 - x**2)` con `x0 = 2`, se devuelve `interval='(-∞, ∞) en ausencia de otras singularidades'`.
- **Impacto en la aplicación:** Intervalos de validez inexistentes con raíces, potencias fraccionarias pares, `asin` o `acos`.
- **Solución recomendada:** Extraer argumentos de potencias con denominador par y de `asin`/`acos`, resolver sus fronteras reales y comprobar que `x0` pertenezca a la región válida.

### A-04. `dsolve_fallback` descarta el miembro derecho
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/methods/dsolve_fallback.py:17-63`, bloque `:50-62`.
- **Descripción del error o punto a corregir:** Si `sp.dsolve` devuelve `Eq(y(x)**2, C1 + x)`, el código toma `potential = lhs.subs(y_func, Y)` e ignora `rhs`, produciendo `y**2 = C`.
- **Impacto en la aplicación:** Falsos fallos del respaldo `dsolve` en soluciones implícitas con términos en `x` junto a la constante.
- **Solución recomendada:** Resolver `lhs - rhs = 0` respecto a la constante o reorganizar `F(x, y) = C1` conservando todos los términos.

### A-05. `clairaut_or_lagrange` rechaza `psi` constante
- **Estado:** Reclasificado a mejora de bajo impacto.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/classify/classifier.py:286-311`, condición en `:309`.
- **Descripción del error o punto a corregir:** La condición `if psi.has(DY)` sigue devolviendo `None` cuando `psi = 1`. Sin embargo, `parse_ode("y = 2*x*y' + 1")` reescribe la ecuación como `explicit` (`rhs = (y - 1)/(2*x)`) y `classify` la etiqueta como lineal. Con `y = 2*x*y' + y'**2 + 1` (`psi` no constante) sí se clasifica como `lagrange`.
- **Impacto en la aplicación:** Robustez interna del detector; ya no deja el ejemplo sin clasificar en la interfaz.
- **Solución recomendada:** Aceptar `lagrange` cuando `phi.has(DY)`, aunque `psi` no contenga `DY`, manteniendo la validación de dependencias.

### A-06. `PlotPanel` ignora los límites en curvas y no sanea `Inf` en superficies 3D
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `apps/desktop/plot_panel.py:136-154`, `:238-240`, `:256-258`, `:288-319`, `:519-550`; `ui/plot_view.py:268-305`, `:360-392`; `odecalc/plotting/data.py:55-86`.
- **Descripción del error o punto a corregir:**
  1. `solution_curve(result)` se llama sin `x_min/x_max` en `plot_panel.py:258` y `:319`, por lo que se usan los valores por defecto `-5..5` (`data.py:58-59`). Verificado: con límites `[0, 2]` la curva sigue en `[-5, 5]`.
  2. En 3D no se sustituye `±Inf` por `NaN`. `PlotPanel` ya descarta el caso “todo no finito” en `:539`, pero `PlotView.plot_surface_3d` (`:380-387`) no filtra. Con Matplotlib 3.11.2 `plot_surface` tolera `Inf`, por lo que el impacto es de robustez visual, no de error de renderizado confirmado.
- **Impacto en la aplicación:** La curva escritorio ignora el intervalo elegido; las superficies con polos pueden renderizarse de forma engañosa.
- **Solución recomendada:** Pasar `x_min` y `x_max` a `solution_curve` en `PlotPanel` y reemplazar valores no finitos por `np.nan` antes de `plot_surface`.

### A-07. Servidor HTTP web: race condition, CORS y validación incompleta
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `apps/web/server.py:55-98`, `:143-160`, `:169-176`, `:225-268`, `:272`.
- **Descripción del error o punto a corregir:**
  1. `_RateLimiter` modifica un `defaultdict(deque)` desde hilos de `ThreadingHTTPServer` sin `threading.Lock` y no elimina claves inactivas.
  2. `_validated` acepta `NaN`/`Infinity` y no valida `x_min < x_max` ni `x_min <= x0 <= x_max`; verificado con `nan`, `-inf/inf` e intervalo invertido.
  3. `:174` anuncia `Access-Control-Allow-Origin: *`, pero no existe `do_OPTIONS`, y `:243-248` devuelve `413` para cuerpo vacío.
- **Impacto en la aplicación:** Condición de carrera, fuga de memoria, fallos de preflight CORS y entrada no finita no filtrada.
- **Solución recomendada:** Sincronizar el limitador con `Lock` y limpieza por ventana; exigir `math.isfinite` y orden de intervalo; añadir `do_OPTIONS`; responder `400` si `length <= 0`.

### A-08. Frontend web: scroll automático y fallo fatal sin `localStorage`
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `apps/web/static/app.js:311-315`, `:544-550`, `:1165-1178`; contraste `apps/web/static/index.html:10-18`.
- **Descripción del error o punto a corregir:** `init()` programa `startDemo()` a los 420 ms (`:1176`) y `startDemo()` llama a `loadExercise(demo, { solveNow: true, scroll: true })` (`:546`). `applyTheme` (`:314`) e `init` (`:1166`) acceden a `localStorage` sin `try/catch`, a diferencia de `index.html`.
- **Impacto en la aplicación:** Desplazamiento involuntario al cargar e inoperatividad total si el almacenamiento está bloqueado.
- **Solución recomendada:** Usar `scroll: false` en el arranque y encapsular `localStorage` en helpers con `try/catch`.

### A-09. Escritorio: hilos concurrentes y validación aún débil de intervalos
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `apps/desktop/app.py:918-950`, `:984-989`, `:1002-1006`, `:1453-1499`, `:1505-1515`, `:1586-1593`.
- **Descripción del error o punto a corregir:** `_start()` deshabilita botones en `:1482-1483`, pero no hay flag `_busy`: se reproducen 2 llamadas concurrentes a `solve()` mediante atajo (`:986`), menú (`:946`) o carga de ejemplo (`:1006`). La validación ya usa `.strip()` para `x0/y0` (`:1460-1461`) y captura `ValueError` (`:1465-1471`), pero `:1462-1463` mantiene `float(get() or -5/5)` y no comprueba `isfinite`, `x_min < x_max` ni `x0` dentro del intervalo. `destroy()` (`:1586-1593`) ya cancela `_poll_id`; no existe `_spinner_job` (el spinner es `ttk.Progressbar`).
- **Impacto en la aplicación:** Desincronización de spinner, cronómetro y cola de resultados; aceptación de `nan`, `inf` e intervalos invertidos.
- **Solución recomendada:** Añadir `_busy`, validar finitud y orden del intervalo, y seguir cancelando los trabajos `after` al cerrar.

### A-10. Corrector: símbolo libre `C` en derivación implícita
- **Estado:** Vigente, matizado.
- **Ruta del archivo y línea(s) afectada(s):** `core/corrector.py:186-213`, `:216-294`, `:392-415`.
- **Descripción del error o punto a corregir:** `y - C*exp(x) = 0` y `C*exp(x) = y` pasan a la rama implícita (`:261-294`), donde `-f_x/f_y` conserva `C`; fallan la igualdad simbólica y la lambdificación `(X, Y)`. Verificado para `y' = y`. El `None` de `_equivalente` (`:196`) es intencionado y el llamador (`:392-415`) solo actúa sobre `False`; no causa el falso negativo.
- **Impacto en la aplicación:** Pasos algebraicamente válidos se marcan como erróneos en *Aprender*.
- **Solución recomendada:** Despejar `Y` o la constante desde la propia relación antes de evaluar el residuo frente a la EDO.

### A-11. Isoclinas constantes y bifurcaciones trascendentes
- **Estado:** Vigente, matizado.
- **Ruta del archivo y línea(s) afectada(s):** `core/cualitativo.py:56-78`, `:145-162`, `:165-221`, `:224-247`; `ui/graficas.py:266-283`.
- **Descripción del error o punto a corregir:** `datos_isoclinas` deja `zz` como arreglo 0-D cuando `rhs` es constante; verificado `shape ()` para `y' = 2`, frente al `np.broadcast_to` que sí se aplica en `linea_fase` (`:161`). `_raices_reales` ya tiene respaldo `sp.nroots` para polinomios (`:62-67`), pero `y' = μ*y - sin(y)` sigue devolviendo `[]` y `bifurcacion` queda vacía.
- **Impacto en la aplicación:** Contorno degenerado en isoclinas constantes y diagramas vacíos en familias trascendentes.
- **Solución recomendada:** Aplicar `np.broadcast_to(zz, xx.shape)` y añadir búsqueda numérica por muestreo/bisección en `_raices_reales`.

---

## Hallazgos Medios

### M-01. Inconsistencia entre parser y `lambdify` para funciones especiales y valores complejos
- **Estado:** Vigente; superficie ampliada tras la refactorización.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/parsing/parser.py:46`, `:65-69`; inyector único en `odecalc/verify/verifier.py:62-78`; `lambdify` con `numpy` en `odecalc/numeric/solver.py:26`, `odecalc/plotting/data.py:15,79,112,145`, `odecalc/api.py:96`, `apps/web/plotting.py:496`, `apps/desktop/plot_panel.py:532`, `core/solver_numerico.py:39,67,536,543`, `core/verificador.py:46,155`, `core/cualitativo.py:156,181,200`, `core/hibrido.py:220`, `core/corrector.py:281-282`, `ui/graficas.py:52,216`, `ui/pagina_numerico.py:66`, `ui/plot_view.py:217,229,238,324,371`.
- **Descripción del error o punto a corregir:** El parser admite `erf`, `erfi`, `Ei`, `Si`, `Ci` y `acot`, pero solo `verifier.py` inyecta `scipy.special`; los puntos enumerados fallan con `NameError` para `erfi`, `Ei`, `Si` o `Ci`. Además, `np.asarray(..., dtype=float)` descarta partes imaginarias con `ComplexWarning`.
- **Impacto en la aplicación:** Fallos de integración/graficación con funciones admitidas y trazado espurio de la parte real de resultados complejos.
- **Solución recomendada:** Centralizar `lambdify` en un helper que inyecte `scipy.special` y enmascare con `NaN` cualquier resultado con parte imaginaria significativa.

### M-02. Comparación exacta con cero de parte imaginaria en `equilibrium_points`
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/plotting/data.py:179`.
- **Descripción del error o punto a corregir:** `if sp.im(sp.N(root)) != 0: continue` descarta raíces reales con residuo imaginario numérico del orden `1e-20`. Verificado: `y³ - 3y + 1` devuelve `[]`; con tolerancia `1e-9` devuelve tres raíces.
- **Impacto en la aplicación:** Desaparición de puntos de equilibrio válidos.
- **Solución recomendada:** Comparar con tolerancia, como en `core/cualitativo.py:73`.

### M-03. Singularidades, potencias fraccionarias y dirección de explosión en `core/existencia.py`
- **Estado:** Vigente, matizado.
- **Ruta del archivo y línea(s) afectada(s):** `core/existencia.py:82-94`, `:97-112`, `:139`.
- **Descripción del error o punto a corregir:** Los `break` en `:88` y `:93` ocultan una de las dos notas cuando aparecen `log` y `sqrt`. `_tiene_potencia_fraccionaria` sustituye solo `Y` (`:108`) y usa `float(sp.N(...))` sin tolerar exponentes complejos. `estimar_explosion` elige `sp.oo`/`-sp.oo` según `y0`, no según `f(y0)`: con `y' = y² + 1, y0 = -1` detecta solo el escape hacia atrás y omite el hacia delante.
- **Impacto en la aplicación:** Advertencias incompletas de dominio, unicidad y explosión.
- **Solución recomendada:** Reemplazar `break` por banderas, sustituir `{X: x0, Y: y0}` y analizar ambos sentidos según `f(y0)`.

### M-04. `curva_solucion` ignora los límites cuando existe curva numérica previa
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `core/hibrido.py:194-229`, retorno anticipado en `:203-207`, límites aplicados recién en `:214-221`.
- **Descripción del error o punto a corregir:** Si `resultado.numerico` es exitoso, se devuelven sus arreglos sin comparar `x_min`/`x_max` solicitados con `resultado.intervalo`. Verificado: pedir `[1, 2]` sobre un numérico en `[0, 5]` devuelve `[0, 5]`.
- **Impacto en la aplicación:** Gráficas desactualizadas respecto al rango pedido.
- **Solución recomendada:** Reevaluar la solución simbólica explícita o reintegrar cuando los límites difieran.

### M-05. PDF: estado global de `pyplot` y distorsión fija de fórmulas
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `core/informes.py:260-267`, `:281`, `:294-301`, `:334`, `:465`, `:489`, `:558`.
- **Descripción del error o punto a corregir:** `_imagen_matematica` y `_grafica_resultado` siguen usando `matplotlib.pyplot` global con `bbox_inches="tight"`, mientras el PDF incrusta imágenes con tamaños fijos `15×2 cm` (`14×1.9 cm` en pasos).
- **Impacto en la aplicación:** Fórmulas estiradas o aplastadas y riesgo de colisiones de estado entre sesiones concurrentes.
- **Solución recomendada:** Usar `Figure` + `FigureCanvasAgg` y calcular dimensiones proporcionales al PNG generado.

### M-06. Perfil del estudiante en ruta interna del paquete y sin escritura atómica
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `core/ejercicios.py:232-235`, `:261-272`.
- **Descripción del error o punto a corregir:** `_ruta_perfil` escribe en `Path(__file__).resolve().parent.parent / "data" / "perfil_estudiante.json"` (`:235`) y `guardar_perfil` usa `write_text` directo (`:268-271`).
- **Impacto en la aplicación:** Fallo por permisos en `site-packages`, corrupción concurrente y mezcla de historiales entre usuarios.
- **Solución recomendada:** Usar el directorio de datos del usuario o sesión y escritura atómica vía archivo temporal.

### M-07. Web: CDN sin SRI/fallback, PNG sin anotaciones y canvas
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `apps/web/static/index.html:26-27`, `:260-264`; `apps/web/static/app.js:279-292`, `:554-566`, `:1048-1054`, `:1086-1090`, `:1110-1127`.
- **Descripción del error o punto a corregir:** Los CDNs siguen sin SRI ni respaldo local. Ya se espera `mathJax.startup.promise` (`:279-292`) y se coloca el cursor tras `(` (`:561-564`), pero `Plotly.downloadImage` (`:1119`) omite `#annotation-canvas`, `pointFromEvent` no protege `rect.width/height == 0` (`:1048-1054`), `pointerleave` corta trazos con captura activa (`:1086-1090`) y los tokens `sqrt(`/`exp(` no insertan el `)` de cierre.
- **Impacto en la aplicación:** Dependencia de red, exportaciones incompletas y trazos que se cortan en bordes.
- **Solución recomendada:** Combinar `Plotly.toImage` con `#annotation-canvas`, validar `rect > 0`, ignorar `pointerleave` con captura y cerrar paréntesis.

### M-08. Escritorio Tk: longitud de texto, README y tamaño base de figura
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `apps/desktop/app.py:150`, `:615`, `:1434-1439`; `apps/desktop/plot_panel.py:87`, `:110-119`.
- **Descripción del error o punto a corregir:** Ya no existe `minsize(1040, 700)` ni `wraplength=760`: `minsize` es `720×520` (`:150`), la columna tiene `minsize=320` (`:615`) y `PlotPanel` ajusta `wraplength` dinámicamente con `<Configure>` (`:110-119`). Permanece `Figure(figsize=(8.0, 5.0))` (`:87`) como tamaño base de un canvas redimensionable y la ruta `parents[2] / "README.md"` (`:1435`), ausente en instalaciones `site-packages`.
- **Impacto en la aplicación:** Enlace roto al README empaquetado; el tamaño base de la figura es menos crítico que antes.
- **Solución recomendada:** Abrir documentación con `importlib.resources` o desde el manual integrado y, si se desea, reducir el `figsize` inicial.

### M-09. EDO-Lab: CSS frágil y exportación incompleta de `aviso_parametros`
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `ui/streamlit_app.py:330`; `ui/estilos.py:103-110`; `ui/componentes.py:6`, `:52`, `:64-69`, `:143`, `:173-190`, `:378`, `:408-426`.
- **Descripción del error o punto a corregir:** Se corrigió la doble inyección de CSS y el escape HTML de `tarjeta`, `chip` y `titulo_pagina` (`from html import escape` en `:6`). Quedan las reglas con `height: var(--altura-scroll)!important` sobre selectores internos de Streamlit (`estilos.py:103-110`), que conviven con `st.container(height=...)` (`componentes.py:64-69`), y la omisión de `aviso_parametros` (`:173-190`) en `__all__` (`:408-426`).
- **Impacto en la aplicación:** Acoplamiento frágil ante cambios del DOM de Streamlit y API incompleta del módulo.
- **Solución recomendada:** Confiar en `st.container(height=...)` sin `!important` y exportar `aviso_parametros`.

### M-10. Desincronización de validaciones y retornos tempranos en EDO-Lab
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `ui/pagina_datos.py:53-57`; `core/ajuste.py:259-263`; `ui/pagina_cualitativo.py:175-179`, `:219-220`; `ui/pagina_numerico.py:152-157`; `ui/pagina_incertidumbre.py:58-75`; `core/incertidumbre.py:34`.
- **Descripción del error o punto a corregir:** El aviso dice “al menos cuatro filas numéricas”, pero `cargar_datos` exige 5 antes de deduplicar; `pagina_cualitativo` retorna en `:177-179` antes de `_seccion_bifurcacion()` (`:219-220`); `pagina_numerico` retorna en `:152-157` si `x_fin <= x0`; `pagina_incertidumbre` no valida `minimo < maximo` en uniformes.
- **Impacto en la aplicación:** Mensajes contradictorios y ocultamiento de resultados cacheados.
- **Solución recomendada:** Corregir el texto a 5 filas, renderizar siempre la bifurcación, evitar retornos tempranos y validar rangos uniformes.

### M-11. Legacy Tk: mensaje sobrescrito y trabajos `after`
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `app.py:106`, `:261-262`, `:276-291`, `:395`, `:401`, `:440`; `ui/plot_view.py:33-52`, `:285-287`, `:316`, `:364`, `:380-387`.
- **Descripción del error o punto a corregir:** `_poll_results` ya comprueba `winfo_exists()` antes de reprogramarse (`:261-262`), pero `_on_solve_numeric` sobrescribe el error simbórico (`:395`, `:401`, `:440`) y `_spinner_job` no se cancela en el ciclo de cierre (`:276-291`). `compute_direction_field_bounds` (`plot_view.py:33-52`) sigue sin validar `x_min < x_max` ni `y_min < y_max`, a diferencia de `plot_solution` (`:285-287`).
- **Impacto en la aplicación:** Error simbólico oculto, posibles `TclError` al cerrar y límites inválidos en campo/superficie.
- **Solución recomendada:** Anexar el motivo simbólico al estado numérico, cancelar trabajos `after` y validar límites en todos los métodos de `PlotView`.

---

## Hallazgos Bajos / Mejora

### B-01. Empaquetado incompleto de datos y coexistencia de tres arquitecturas
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `pyproject.toml:62-70`, `dependencies.py:7`, `core/ajuste.py:598-604`.
- **Descripción del error o punto a corregir:** `package-data` solo declara `"apps.web" = ["static/*"]` (`:69-70`); los CSV de `data/ejemplos` no entran en el wheel y `cargar_ejemplo()` (`:601-603`) falla. `REQUIRED_MODULES` en `dependencies.py:7` tampoco comprueba `PIL.ImageTk`.
- **Impacto en la aplicación:** Ejemplos de *Datos* ausentes en instalaciones wheel; responsabilidades duplicadas entre `odecalc`, `core` y `math_engine`.
- **Solución recomendada:** Declarar `"data" = ["ejemplos/*.csv"]` o usar `importlib.resources`, y deprecar formalmente la capa legacy.

### B-02. Verificación numérica limitada ante integrales e implícitas particulares
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/verify/verifier.py:94-95`, `:160-182`, `:232-241`.
- **Descripción del error o punto a corregir:** `_numeric_check_explicit` devuelve `False` ante cualquier `sp.Integral`; las soluciones implícitas se muestrean en una rejilla `(x, y)` fija, no sobre la curva `F(x, y) = value`.
- **Impacto en la aplicación:** Falsos rechazos de soluciones verificables.
- **Solución recomendada:** Evaluar integrales por cuadratura y muestrear puntos sobre la curva de nivel.

### B-03. Isoclinas indisponibles cuando no puede despejarse `y(x)`
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `odecalc/plotting/data.py:125-161` (resolución en `:140`); `apps/web/plotting.py:317-335`; `apps/desktop/plot_panel.py:335-353`.
- **Descripción del error o punto a corregir:** `isoclines` depende solo de `sp.solve(rhs - k, Y)`. Con `y' = sin(x*y)` devuelve `[]` y web/escritorio muestran indisponibilidad, mientras `core/cualitativo.datos_isoclinas` sí genera malla 2D.
- **Impacto en la aplicación:** Inconsistencia funcional entre EDO-Lab y web/escritorio.
- **Solución recomendada:** Añadir respaldo por curvas de nivel sobre malla 2D.

### B-04. Falta de guarda ante covarianza mal condicionada en `predecir`
- **Estado:** Vigente.
- **Ruta del archivo y línea(s) afectada(s):** `core/ajuste.py:565-572`, `:581-582`.
- **Descripción del error o punto a corregir:** `rng.multivariate_normal` se invoca sin comprobar finitud ni capturar `LinAlgError`; se reproduce `LinAlgError: SVD did not converge` con una covarianza con `NaN`. El único fallback existente (`:581-582`) actúa si quedan menos de 10 trayectorias.
- **Impacto en la aplicación:** Fallo de predicción con bandas de confianza en datos degenerados.
- **Solución recomendada:** Verificar `np.all(np.isfinite(covarianza))` y degradar a `[media]` ante errores de álgebra lineal.

### B-05. Ergonomía y código muerto en UI
- **Estado:** Parcialmente corregido.
- **Ruta del archivo y línea(s) afectada(s):** `apps/web/static/styles.css:1598-1607`; `apps/desktop/app.py:994-1000`; `app.py:467-475`; `ui/pagina_resolver.py:19-34`, `:96`, `:260`.
- **Descripción del error o punto a corregir:** Ya no están los imports muertos de `badge_estado`/`tema_oscuro` en `pagina_resolver.py` (`:19-34`). Quedan `text-overflow: ellipsis` en `.method__body small` sin expansión, `_insert_token` sin mover el cursor dentro de `exp()`/`sqrt()` (`:994-1000`), `bind_all` en `app.py:469` y los `parsear(...)` repetidos en `pagina_resolver.py:96,260`.
- **Impacto en la aplicación:** Pequeñas fricciones visuales/ergonómicas y trabajo redundante en reruns.
- **Solución recomendada:** Permitir multilínea, colocar el cursor dentro de los paréntesis, limitar atajos al campo de entrada y cachear el parseo.
