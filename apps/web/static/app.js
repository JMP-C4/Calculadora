/* ==========================================================================
   ODE Calculator — web workspace behaviour
   Vanilla JS: no build step, no framework.
   ========================================================================== */

(() => {
  "use strict";

  /* ------------------------------------------------------------------ data */

  const EXERCISES = [
    {
      id: "sep-01",
      type: "separable",
      typeLabel: "Separable",
      name: "Crecimiento exponencial",
      equation: "dy/dx = y",
      conditions: { x0: 0, y0: 1, x_min: -2, x_max: 2 },
      description:
        "La tasa de cambio es proporcional a la cantidad presente. El modelo más limpio de crecimiento sin restricciones.",
      note:
        "La solución particular pasa por (0, 1). Cambia y₀ para desplazar la curva sin cambiar su forma.",
    },
    {
      id: "sep-02",
      type: "separable",
      typeLabel: "Separable",
      name: "Decaimiento exponencial",
      equation: "dy/dx = -2*y",
      conditions: { x0: 0, y0: 100, x_min: 0, x_max: 5 },
      description:
        "La cantidad disminuye a una tasa proporcional a su valor actual, como en el decaimiento radiactivo.",
      note:
        "Observa cómo la curva se aplana: la velocidad de caída depende de cuánto queda, no del tiempo.",
    },
    {
      id: "sep-03",
      type: "separable",
      typeLabel: "Separable",
      name: "Separable con seno",
      equation: "dy/dx = sin(x)*y",
      conditions: { x0: 0, y0: 1, x_min: -3, x_max: 3 },
      description:
        "Variables separables con un factor periódico en x; el signo del seno alterna el crecimiento y el decaimiento.",
      note:
        "Busca los intervalos donde y crece y donde decrece. El signo de sin(x) lo explica sin resolver nada.",
    },
    {
      id: "lin-01",
      type: "linear",
      typeLabel: "Lineal",
      name: "Crecimiento con forzamiento",
      equation: "y' = x + y",
      conditions: { x0: 0, y0: 1, x_min: 0, x_max: 2 },
      description:
        "EDO lineal de primer orden con término independiente. El factor integrante convierte el lado izquierdo en la derivada de un producto.",
      note:
        "La solución particular pasa por (0, 1); la general añade la familia con la constante C.",
    },
    {
      id: "lin-02",
      type: "linear",
      typeLabel: "Lineal",
      name: "Forzada por exponencial",
      equation: "dy/dx = exp(x) - y",
      conditions: { x0: 0, y0: 0, x_min: -3, x_max: 3 },
      description:
        "La incógnita aparece linealmente y el término forzante es una exponencial.",
      note:
        "El signo del término -y frena el crecimiento. Prueba el campo de direcciones para ver el equilibrio.",
    },
    {
      id: "lin-03",
      type: "linear",
      typeLabel: "Lineal",
      name: "Forzada por coseno",
      equation: "dy/dx = cos(x) + y",
      conditions: { x0: 0, y0: 1, x_min: -3, x_max: 3 },
      description:
        "EDO lineal con coeficiente unitario y forzamiento oscilatorio; ideal para practicar el factor integrante.",
      note:
        "La respuesta combina una oscilación con una tendencia. Compara la curva simbólica con la numérica.",
    },
    {
      id: "exa-01",
      type: "exact",
      typeLabel: "Exacta",
      name: "Exacta racional",
      equation: "dy/dx = -(2*x + y)/(x + 2*y)",
      conditions: { x0: 1, y0: 1, x_min: -3, x_max: 3 },
      description:
        "La EDO es exacta porque ∂M/∂y = ∂N/∂x; se resuelve encontrando una función potencial F(x, y).",
      note:
        "Las isoclinas revelan la simetría de la familia de curvas solución.",
    },
    {
      id: "aut-01",
      type: "autonomous",
      typeLabel: "Autónoma",
      name: "Logística",
      equation: "y' = y*(1-y)",
      conditions: { x0: 0, y0: 0.5, x_min: 0, x_max: 5 },
      description:
        "Un crecimiento limitado por capacidad de carga. Tiene dos puntos de equilibrio y una dinámica muy rica.",
      note:
        "Prueba la línea de fase y los puntos de equilibrio: y = 0 es inestable, y = 1 es estable.",
    },
    {
      id: "aut-02",
      type: "autonomous",
      typeLabel: "Autónoma",
      name: "Umbral de Allee",
      equation: "y' = y*(y-1)*(2-y)",
      conditions: { x0: 0, y0: 0.5, x_min: 0, x_max: 6 },
      description:
        "Tres equilibrios con estabilidad alternada. Un cambio pequeño en la condición inicial cambia el destino.",
      note:
        "Prueba y₀ = 0.5 y y₀ = 1.5. La línea de fase explica por qué el destino no es el mismo.",
    },
    {
      id: "non-01",
      type: "nonlinear",
      typeLabel: "No lineal",
      name: "Riccati cuadrática",
      equation: "dy/dx = x*y**2",
      conditions: { x0: 0, y0: 1, x_min: -2, x_max: 2 },
      description:
        "Variables separables donde el lado derecho es producto de una función de x y una función cuadrática de y.",
      note:
        "La solución puede explotar en un intervalo finito. Acota x máx y observa el comportamiento.",
    },
    {
      id: "non-02",
      type: "nonlinear",
      typeLabel: "No lineal",
      name: "Homogénea racional",
      equation: "y' = (x + y)/(x - y)",
      conditions: { x0: 1, y0: 1, x_min: -3, x_max: 3 },
      description:
        "El cambio u = y/x reduce la ecuación a una separable. La recta y = x marca una singularidad.",
      note:
        "La recta x = y divide el plano: las soluciones no la cruzan. La gráfica lo hace visible.",
    },
    {
      id: "non-03",
      type: "nonlinear",
      typeLabel: "Implícita",
      name: "Clairaut",
      equation: "y = x*y' + y'**2",
      conditions: null,
      description:
        "Forma implícita clásica. Tiene una familia de rectas y, además, una solución singular envolvente.",
      note:
        "Elige «Familia de curvas» y «Campo de direcciones»: la envolvente es la solución singular.",
    },
  ];

  const PLOT_LABELS = {
    solution: "Solución y(x)",
    direction_field: "Campo de direcciones",
    isoclines: "Isoclinas",
    family: "Familia de curvas",
    phase_line: "Línea de fase",
    equilibria: "Puntos de equilibrio",
    surface: "Superficie 3D z = f(x,y)",
  };

  const TYPE_LABELS = {
    all: "Todos",
    separable: "Separables",
    linear: "Lineales",
    exact: "Exactas",
    autonomous: "Autónomas",
    nonlinear: "No lineales",
  };

  /* ------------------------------------------------------------------- dom */

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const form = $("#form");
  const equationInput = $("#equation");
  const submitButton = $("#submit");
  const clearButton = $("#clear-button");
  const plotDiv = $("#plot");
  const plotNotice = $("#plot-notice");
  const plotMode = $("#plot_mode");
  const plotRefresh = $("#plot_refresh");
  const canvasStage = $("#canvas-stage");
  const canvasEmpty = $("#canvas-empty");
  const annotateCanvas = $("#annotation-canvas");
  const penColor = $("#pen_color");
  const canvasCard = $("#canvas-card");
  const canvasModeLabel = $("#canvas-mode-label");
  const canvasHint = $("#canvas-hint");
  const engineStatus = $("#engine-status");
  const engineStatusWrap = $("#engine-status-wrap");
  const solutionContent = $("#solution-content");
  const solutionEmpty = $("#solution-empty");
  const solutionChip = $("#solution-chip");
  const resultMethod = $("#result-method");
  const generalBlock = $("#general-block");
  const particularBlock = $("#particular-block");
  const resultGeneral = $("#result-general");
  const resultParticular = $("#result-particular");
  const verifyStatus = $("#verify-status");
  const resultDomain = $("#result-domain");
  const resultInterval = $("#result-interval");
  const methodList = $("#method-list");
  const methodCount = $("#method-count");
  const stepList = $("#step-list");
  const warningList = $("#warning-list");
  const exerciseGrid = $("#exercise-grid");
  const exerciseFilters = $("#exercise-filters");
  const exerciseCount = $("#exercise-count");
  const guideContent = $("#guide-content");
  const guideChip = $("#guide-chip");
  const toast = $("#toast");

  const state = {
    lastPayload: null,
    lastFigure: null,
    plotRequest: 0,
    busy: false,
    selectedExercise: EXERCISES.find((item) => item.id === "lin-01"),
    filter: "all",
    annotating: false,
    strokes: [],
    currentStroke: null,
    theme: document.documentElement.dataset.theme || "light",
  };

  let toastTimer = null;

  /* ------------------------------------------------------------- utilities */

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));

  const showToast = (message, variant = "") => {
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.className = `toast is-visible${variant === "error" ? " is-error" : ""}`;
    toastTimer = window.setTimeout(() => {
      toast.className = "toast";
    }, 3600);
  };

  const setEngineStatus = (message, mode = "") => {
    if (engineStatus) engineStatus.textContent = message;
    if (engineStatusWrap) {
      engineStatusWrap.classList.toggle("is-busy", mode === "busy");
      engineStatusWrap.classList.toggle("is-ok", mode === "ok");
      engineStatusWrap.classList.toggle("is-error", mode === "error");
    }
  };

  const setBusy = (busy) => {
    state.busy = busy;
    if (submitButton) {
      submitButton.disabled = busy;
      submitButton.textContent = busy ? "Resolviendo…" : "Resolver y verificar";
    }
    if (plotRefresh) plotRefresh.disabled = busy;
    ["#solution", "#methods", "#steps"].forEach((selector) => {
      const card = $(selector);
      if (card) card.classList.toggle("is-loading", busy);
    });
  };

  const typeset = (nodes) => {
    const mathJax = window.MathJax;
    if (!mathJax) return;
    const run = () => {
      if (typeof mathJax.typesetPromise === "function") {
        mathJax.typesetPromise(nodes).catch(() => {});
      }
    };
    if (mathJax.startup && mathJax.startup.promise) {
      mathJax.startup.promise.then(run).catch(() => {});
    } else {
      run();
    }
  };

  const setMath = (element, latex) => {
    if (!element) return;
    element.textContent = latex ? `$$${latex}$$` : "";
  };

  const valueOrEmpty = (id) => {
    const input = document.getElementById(id);
    return input ? input.value.trim() : "";
  };

  const setValue = (id, value) => {
    const input = document.getElementById(id);
    if (input) input.value = value === null || value === undefined ? "" : String(value);
  };

  /* -------------------------------------------------------------- theme/nav */

  const applyTheme = (theme) => {
    state.theme = theme;
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("ode-theme", theme);
    const toggle = $("#theme-toggle");
    if (toggle) {
      toggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      toggle.setAttribute(
        "aria-label",
        theme === "dark" ? "Activar tema claro" : "Activar tema oscuro",
      );
      toggle.innerHTML =
        theme === "dark"
          ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>'
          : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8Z"/></svg>';
    }
    if (state.lastFigure) drawFigure(state.lastFigure);
  };

  const closeMenus = () => {
    $$(".nav__group").forEach((group) => {
      group.classList.remove("is-open");
      const trigger = $(".nav__link", group);
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  };

  const closeMobileNav = () => {
    const nav = $("#nav");
    const button = $("#menu-toggle");
    if (nav) nav.classList.remove("is-open");
    if (button) {
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", "Abrir menú");
    }
  };

  $$(".nav__group").forEach((group) => {
    const trigger = $(".nav__link", group);
    if (!trigger) return;
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = group.classList.contains("is-open");
      closeMenus();
      if (!isOpen) {
        group.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
      }
    });
    $(".dropdown", group)?.addEventListener("click", (event) => {
      if (event.target.closest("a, button")) {
        closeMenus();
        closeMobileNav();
      }
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".nav__group")) closeMenus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenus();
      closeMobileNav();
    }
  });

  $("#menu-toggle")?.addEventListener("click", () => {
    const nav = $("#nav");
    const button = $("#menu-toggle");
    if (!nav || !button) return;
    const isOpen = nav.classList.toggle("is-open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
    button.setAttribute("aria-label", isOpen ? "Cerrar menú" : "Abrir menú");
    if (!isOpen) closeMenus();
  });

  $$(".nav a[href^='#']").forEach((link) => {
    link.addEventListener("click", () => {
      closeMenus();
      closeMobileNav();
    });
  });

  $("#theme-toggle")?.addEventListener("click", () => {
    applyTheme(state.theme === "dark" ? "light" : "dark");
  });

  $$("[data-select-plot]").forEach((button) => {
    button.addEventListener("click", () => {
      const mode = button.dataset.selectPlot;
      if (!mode) return;
      plotMode.value = mode;
      updateCanvasModeLabel();
      document.getElementById("canvas-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
      if (state.lastPayload) {
        loadPlot();
      } else {
        setPlotNotice("Resuelve una ecuación para ver esta visualización.");
        showToast(`Vista preparada: ${PLOT_LABELS[mode] || mode}`);
      }
    });
  });

  /* --------------------------------------------------------------- exercises */

  const renderFilters = () => {
    if (!exerciseFilters) return;
    exerciseFilters.innerHTML = "";
    Object.entries(TYPE_LABELS).forEach(([key, label]) => {
      const count = key === "all"
        ? EXERCISES.length
        : EXERCISES.filter((exercise) => exercise.type === key).length;
      if (key !== "all" && count === 0) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `filter${state.filter === key ? " is-active" : ""}`;
      button.dataset.filter = key;
      button.textContent = `${label} ${count}`;
      button.setAttribute("aria-pressed", state.filter === key ? "true" : "false");
      exerciseFilters.appendChild(button);
    });
  };

  const renderExerciseGrid = () => {
    if (!exerciseGrid) return;
    exerciseGrid.innerHTML = "";
    const visible = EXERCISES.filter(
      (exercise) => state.filter === "all" || exercise.type === state.filter,
    );
    visible.forEach((exercise) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `exercise${state.selectedExercise?.id === exercise.id ? " is-active" : ""}`;
      button.dataset.exercise = exercise.id;
      button.setAttribute("aria-pressed", state.selectedExercise?.id === exercise.id ? "true" : "false");

      const type = document.createElement("span");
      type.className = "exercise__type";
      type.textContent = exercise.typeLabel;

      const name = document.createElement("span");
      name.className = "exercise__name";
      name.textContent = exercise.name;

      const eq = document.createElement("span");
      eq.className = "exercise__eq";
      eq.textContent = exercise.equation;

      button.append(type, name, eq);
      exerciseGrid.appendChild(button);
    });
    if (exerciseCount) {
      exerciseCount.textContent = String(visible.length);
    }
  };

  const renderGuide = (exercise) => {
    if (!guideContent || !exercise) return;
    if (guideChip) guideChip.textContent = exercise.typeLabel;
    const conditions = exercise.conditions
      ? `· x₀ = ${exercise.conditions.x0}, y₀ = ${exercise.conditions.y0}`
      : "· sin PVI";
    guideContent.innerHTML = `
      <div class="guide__top">
        <div>
          <span class="guide__type">${escapeHtml(exercise.typeLabel)}</span>
          <h4>${escapeHtml(exercise.name)}</h4>
        </div>
      </div>
      <p>${escapeHtml(exercise.description)}</p>
      <div class="guide__equation">${escapeHtml(exercise.equation)} &nbsp;${escapeHtml(conditions)}</div>
      <div class="guide__note"><span>✦</span><span><strong>Qué observar:</strong> ${escapeHtml(exercise.note)}</span></div>
      <div class="guide__actions">
        <button class="btn btn--small btn--primary" type="button" id="guide-load">Cargar y resolver</button>
        <button class="btn btn--small btn--ghost" type="button" id="guide-random">Otro reto</button>
      </div>
    `;
  };

  const loadExercise = (exercise, { solveNow = true, scroll = false } = {}) => {
    if (!exercise) return;
    state.selectedExercise = exercise;
    setValue("equation", exercise.equation);
    if (exercise.conditions) {
      setValue("x0", exercise.conditions.x0);
      setValue("y0", exercise.conditions.y0);
      setValue("x_min", exercise.conditions.x_min);
      setValue("x_max", exercise.conditions.x_max);
    } else {
      ["x0", "y0"].forEach((id) => setValue(id, ""));
      setValue("x_min", -3);
      setValue("x_max", 3);
    }
    renderFilters();
    renderExerciseGrid();
    renderGuide(exercise);
    if (scroll) {
      document.getElementById("editor")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (solveNow) solve();
  };

  exerciseFilters?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    state.filter = button.dataset.filter;
    renderFilters();
    renderExerciseGrid();
  });

  exerciseGrid?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-exercise]");
    if (!button) return;
    const exercise = EXERCISES.find((item) => item.id === button.dataset.exercise);
    if (!exercise) return;
    loadExercise(exercise, { solveNow: true });
    showToast(`Ejercicio cargado: ${exercise.name}`);
  });

  guideContent?.addEventListener("click", (event) => {
    if (event.target.closest("#guide-load")) {
      loadExercise(state.selectedExercise, { solveNow: true, scroll: true });
      return;
    }
    if (event.target.closest("#guide-random")) {
      const pool = EXERCISES.filter((exercise) => exercise.id !== state.selectedExercise?.id);
      const next = pool[Math.floor(Math.random() * pool.length)];
      loadExercise(next, { solveNow: true, scroll: true });
    }
  });

  const startDemo = () => {
    const demo = EXERCISES.find((exercise) => exercise.id === "lin-01");
    loadExercise(demo, { solveNow: true, scroll: true });
  };

  $("#demo-button")?.addEventListener("click", startDemo);
  $("#nav-demo")?.addEventListener("click", startDemo);

  /* --------------------------------------------------------------- editor */

  $$("[data-token]").forEach((button) => {
    button.addEventListener("click", () => {
      const token = button.dataset.token || "";
      const start = equationInput.selectionStart ?? equationInput.value.length;
      const end = equationInput.selectionEnd ?? start;
      equationInput.setRangeText(token, start, end, "end");
      equationInput.focus();
      if (token.endsWith("(")) {
        const position = start + token.length;
        equationInput.setSelectionRange(position, position);
      }
    });
  });

  $("#latex-example")?.addEventListener("click", () => {
    setValue("equation", String.raw`$$\frac{dy}{dx} = \frac{x^2}{y}$$`);
    setValue("x0", 0);
    setValue("y0", 1);
    setValue("x_min", 0);
    setValue("x_max", 2);
    equationInput?.focus();
    showToast("Ejemplo LaTeX cargado · pulsa Resolver y verificar");
  });

  clearButton?.addEventListener("click", () => {
    setValue("equation", "y' = x + y");
    ["x0", "y0"].forEach((id) => setValue(id, ""));
    setValue("x_min", 0);
    setValue("x_max", 2);
    state.lastPayload = null;
    state.lastFigure = null;
    clearPlot();
    setPlotNotice("Escribe una ecuación y pulsa «Resolver y verificar».");
    setEngineStatus("Listo para resolver");
    equationInput.focus();
    showToast("Editor reiniciado");
  });

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      solve();
    }
  });

  /* ------------------------------------------------------------------ solve */

  const renderSolution = (data) => {
    if (!solutionContent || !solutionEmpty) return;
    const hasSolution = Boolean(data.general || data.particular);
    solutionEmpty.hidden = hasSolution;
    solutionContent.hidden = !hasSolution;

    if (!hasSolution) {
      solutionChip.textContent = data.error ? "Error" : "Pendiente";
      return;
    }

    solutionChip.textContent = data.particular ? "Con PVI" : "General";
    resultMethod.textContent = data.chosen_method || "—";

    generalBlock.hidden = !data.general;
    particularBlock.hidden = !data.particular;
    if (data.general) setMath(resultGeneral, data.general.latex);
    if (data.particular) setMath(resultParticular, data.particular.latex);
    typeset([resultGeneral, resultParticular]);
  };

  const renderVerification = (data) => {
    if (!verifyStatus) return;
    const verification = data.particular_verification || data.verification;
    const ok = Boolean(verification && verification.status === "ok");
    const failed = Boolean(data.error) || Boolean(verification && verification.status !== "ok");
    verifyStatus.classList.toggle("is-ok", ok);
    verifyStatus.classList.toggle("is-error", failed && !ok);

    const ring = $(".verify__ring", verifyStatus);
    const title = $("strong", verifyStatus);
    const message = $("p", verifyStatus);
    if (ring) ring.textContent = ok ? "✓" : failed ? "!" : "?";
    if (title) {
      title.textContent = ok
        ? "Residuo verificado"
        : failed
          ? "Resultado con advertencias"
          : "Sin verificar";
    }
    if (message) {
      message.textContent = verification
        ? verification.message
        : "Al resolver, sustituimos la solución en la EDO y comprobamos el residuo.";
    }

    const validity = data.validity || {};
    if (resultDomain) resultDomain.textContent = validity.domain || "—";
    if (resultInterval) resultInterval.textContent = validity.interval || "—";
  };

  const renderMethods = (data) => {
    if (!methodList) return;
    const classifications = Array.isArray(data.classifications) ? data.classifications : [];
    methodList.replaceChildren();
    if (methodCount) methodCount.textContent = String(classifications.length);

    if (!classifications.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.innerHTML = "<strong>Sin clasificar</strong><span>Los métodos compatibles aparecerán aquí.</span>";
      methodList.appendChild(empty);
      return;
    }

    classifications.forEach((match) => {
      const item = document.createElement("div");
      item.className = "method";
      const chosen = match.method === data.chosen_method || match.name === data.chosen_method;
      if (chosen) item.classList.add("is-chosen");

      const priority = document.createElement("span");
      priority.className = "method__priority";
      priority.textContent = String(match.priority ?? "·");

      const body = document.createElement("div");
      body.className = "method__body";
      const name = document.createElement("strong");
      name.textContent = match.name || match.method || "Método";
      const evidence = document.createElement("small");
      evidence.textContent = match.evidence || match.method || "";
      body.append(name, evidence);

      item.append(priority, body);
      methodList.appendChild(item);
    });
  };

  const renderSteps = (data) => {
    if (!stepList) return;
    const steps = Array.isArray(data.steps) ? data.steps : [];
    stepList.replaceChildren();
    if (!steps.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.innerHTML = "<strong>Sin pasos todavía</strong><span>Resuelve una ecuación para desplegar el razonamiento paso a paso.</span>";
      stepList.appendChild(empty);
      return;
    }

    const mathNodes = [];
    steps.forEach((step, index) => {
      const details = document.createElement("details");
      details.className = "step";
      details.open = index === 0;

      const summary = document.createElement("summary");
      const number = document.createElement("span");
      number.className = "step__num";
      number.textContent = String(step.number ?? index + 1);
      const title = document.createElement("strong");
      title.textContent = step.title || `Paso ${index + 1}`;
      summary.append(number, title);
      summary.insertAdjacentHTML(
        "beforeend",
        '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m4 6 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      );

      const body = document.createElement("div");
      body.className = "step__body";
      if (step.latex) {
        const math = document.createElement("div");
        math.className = "math";
        math.textContent = `$$${step.latex}$$`;
        body.appendChild(math);
        mathNodes.push(math);
      }
      if (step.explanation) {
        const explanation = document.createElement("p");
        explanation.textContent = step.explanation;
        body.appendChild(explanation);
      }

      details.append(summary, body);
      stepList.appendChild(details);
    });
    typeset(mathNodes);
  };

  const renderWarnings = (data) => {
    if (!warningList) return;
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    warningList.replaceChildren();
    if (!warnings.length) {
      const item = document.createElement("li");
      item.className = "muted";
      item.textContent = "Sin advertencias. Cuando el motor detecte algo relevante, aparecerá aquí.";
      warningList.appendChild(item);
      return;
    }
    warnings.forEach((warning) => {
      const item = document.createElement("li");
      item.textContent = warning;
      warningList.appendChild(item);
    });
  };

  const renderResult = (data) => {
    renderSolution(data);
    renderVerification(data);
    renderMethods(data);
    renderSteps(data);
    renderWarnings(data);

    if (data.error) {
      setEngineStatus("Revisa la ecuación", "error");
      showToast(data.error, "error");
    } else {
      const verified =
        (data.particular_verification || data.verification || {}).status === "ok";
      setEngineStatus(
        verified ? "Solución verificada · residuo 0" : "Resultado con advertencias",
        verified ? "ok" : "error",
      );
    }
  };

  const solve = async () => {
    if (state.busy) return;
    const equation = valueOrEmpty("equation");
    if (!equation) {
      showToast("Escribe una ecuación diferencial.", "error");
      equationInput?.focus();
      return;
    }

    const payload = {
      equation,
      x0: valueOrEmpty("x0"),
      y0: valueOrEmpty("y0"),
      x_min: valueOrEmpty("x_min"),
      x_max: valueOrEmpty("x_max"),
      timeout: 20,
    };
    state.lastPayload = payload;
    setBusy(true);
    setEngineStatus("Resolviendo y verificando…", "busy");
    setPlotNotice("Calculando gráfica…");
    if (canvasEmpty) canvasEmpty.hidden = true;

    try {
      const response = await fetch("/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      renderResult(data);
      await loadPlot({ silent: true });
    } catch (error) {
      setEngineStatus("No se pudo resolver", "error");
      if (solutionContent) solutionContent.hidden = true;
      if (solutionEmpty) {
        solutionEmpty.hidden = false;
        solutionEmpty.innerHTML = `<strong>No se pudo resolver</strong><span>${escapeHtml(error.message)}</span>`;
      }
      if (solutionChip) solutionChip.textContent = "Error";
      clearPlot();
      setPlotNotice(`No se pudo graficar: ${error.message}`);
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  };

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    solve();
  });

  /* ------------------------------------------------------------------ plots */

  const cssColor = (name, fallback) => {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  };

  const setPlotNotice = (message) => {
    if (!plotNotice) return;
    plotNotice.textContent = message || "";
    plotNotice.hidden = !message;
  };

  const clearPlot = () => {
    if (window.Plotly) window.Plotly.purge(plotDiv);
    if (plotDiv) plotDiv.innerHTML = "";
    state.lastFigure = null;
    if (canvasEmpty) {
      canvasEmpty.hidden = false;
      const text = $("p", canvasEmpty);
      if (text) text.textContent = "Resuelve una ecuación para dibujar su lienzo.";
    }
  };

  const updateCanvasModeLabel = () => {
    const label = PLOT_LABELS[plotMode?.value] || "Gráfica";
    if (canvasModeLabel) canvasModeLabel.textContent = label;
    if (canvasHint) canvasHint.textContent = `${label} · zoom, arrastra y exporta · activa el lápiz para anotar`;
  };

  const plotlyData = (figure) => {
    if (figure.kind === "3d") {
      return [{
        type: "surface",
        x: figure.surface.x,
        y: figure.surface.y,
        z: figure.surface.z,
        colorscale: "Viridis",
        showscale: true,
        name: "z = f(x, y)",
      }];
    }
    return (figure.traces || []).map((trace) => {
      if (trace.type === "segments") {
        return {
          type: "scatter",
          mode: "lines",
          x: trace.x,
          y: trace.y,
          hoverinfo: "skip",
          showlegend: false,
          line: { color: trace.color || "#455a64", width: trace.width || 1 },
        };
      }
      if (trace.type === "points") {
        return {
          type: "scatter",
          mode: "markers+text",
          x: trace.x,
          y: trace.y,
          text: trace.text && trace.text.length ? trace.text : undefined,
          textposition: "top center",
          name: trace.label || undefined,
          showlegend: Boolean(trace.label),
          marker: { color: trace.color || "#6a1b9a", size: trace.size || 11 },
        };
      }
      return {
        type: "scatter",
        mode: "lines",
        x: trace.x,
        y: trace.y,
        name: trace.label || undefined,
        showlegend: Boolean(trace.label),
        connectgaps: false,
        line: {
          color: trace.color || "#1565c0",
          width: trace.width || 2,
          dash: trace.dash || "solid",
        },
      };
    });
  };

  const plotlyLayout = (figure) => {
    const ink = cssColor("--ink-soft", "#27364a");
    const muted = cssColor("--muted", "#64748b");
    const grid = cssColor("--line", "#e1e8ef");
    const layout = {
      title: { text: figure.title || "", font: { size: 13, color: ink } },
      margin: { l: 52, r: 22, t: 44, b: 46 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Inter, system-ui, sans-serif", size: 11, color: muted },
      legend: { orientation: "h", x: 0, y: -0.18, font: { size: 10, color: muted } },
      hovermode: "closest",
      hoverlabel: { bgcolor: cssColor("--surface", "#fff"), bordercolor: grid, font: { color: ink } },
    };
    if (figure.kind === "3d") {
      layout.scene = {
        xaxis: { title: figure.x_label || "x", color: muted, gridcolor: grid, zerolinecolor: grid },
        yaxis: { title: figure.y_label || "y", color: muted, gridcolor: grid, zerolinecolor: grid },
        zaxis: { title: figure.z_label || "z", color: muted, gridcolor: grid, zerolinecolor: grid },
        bgcolor: "rgba(0,0,0,0)",
        camera: { eye: { x: 1.5, y: 1.5, z: 1.0 } },
      };
      return layout;
    }
    layout.xaxis = { title: figure.x_label || "x", zeroline: false, gridcolor: grid, color: muted, linecolor: grid };
    layout.yaxis = {
      title: figure.y_label || "y",
      zeroline: Boolean(figure.zero_line),
      gridcolor: grid,
      color: muted,
      linecolor: grid,
    };
    return layout;
  };

  const drawFigure = (figure) => {
    if (!window.Plotly || !figure) return;
    window.Plotly.react(plotDiv, plotlyData(figure), plotlyLayout(figure), {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    });
  };

  const loadPlot = async ({ silent = false } = {}) => {
    updateCanvasModeLabel();
    if (!state.lastPayload) {
      setPlotNotice("Resuelve una ecuación para ver su gráfica.");
      return;
    }
    const requestId = ++state.plotRequest;
    if (!silent) setPlotNotice("Calculando gráfica…");
    try {
      const response = await fetch("/plot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...state.lastPayload, mode: plotMode.value }),
      });
      const data = await response.json();
      if (requestId !== state.plotRequest) return;
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      if (!data.available) {
        clearPlot();
        if (canvasEmpty) {
          canvasEmpty.hidden = false;
          const text = $("p", canvasEmpty);
          if (text) text.textContent = data.notice || "Esta gráfica no está disponible para la ecuación.";
        }
        setPlotNotice(data.notice || "Esta gráfica no está disponible para la ecuación.");
        return;
      }
      if (typeof window.Plotly === "undefined") {
        clearPlot();
        setPlotNotice("No se pudo cargar el motor de gráficas (Plotly). Revisa tu conexión.");
        return;
      }
      state.lastFigure = data.figure;
      if (canvasEmpty) canvasEmpty.hidden = true;
      setPlotNotice(data.notice || "");
      drawFigure(data.figure);
    } catch (error) {
      if (requestId !== state.plotRequest) return;
      clearPlot();
      setPlotNotice(`No se pudo graficar: ${error.message}`);
    }
  };

  plotMode?.addEventListener("change", () => {
    updateCanvasModeLabel();
    if (state.lastPayload) loadPlot();
  });
  plotRefresh?.addEventListener("click", () => loadPlot());

  /* ------------------------------------------------------- canvas editor */

  const annotationContext = annotateCanvas?.getContext("2d") || null;
  let canvasSize = { width: 0, height: 0 };

  const resizeAnnotationCanvas = () => {
    if (!annotateCanvas || !annotationContext || !canvasStage) return;
    const rect = canvasStage.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvasSize = { width: rect.width, height: rect.height };
    annotateCanvas.width = Math.max(1, Math.round(rect.width * dpr));
    annotateCanvas.height = Math.max(1, Math.round(rect.height * dpr));
    annotationContext.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawAnnotations();
  };

  const drawStroke = (stroke) => {
    if (!annotationContext || !canvasSize.width || !stroke.points.length) return;
    annotationContext.beginPath();
    annotationContext.strokeStyle = stroke.color;
    annotationContext.lineWidth = 2.4;
    annotationContext.lineCap = "round";
    annotationContext.lineJoin = "round";
    stroke.points.forEach((point, index) => {
      const x = point.x * canvasSize.width;
      const y = point.y * canvasSize.height;
      if (index === 0) annotationContext.moveTo(x, y);
      else annotationContext.lineTo(x, y);
    });
    annotationContext.stroke();
  };

  const drawAnnotations = () => {
    if (!annotationContext) return;
    annotationContext.clearRect(0, 0, canvasSize.width, canvasSize.height);
    state.strokes.forEach(drawStroke);
    if (state.currentStroke) drawStroke(state.currentStroke);
  };

  const pointFromEvent = (event) => {
    const rect = annotateCanvas.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    };
  };

  annotateCanvas?.addEventListener("pointerdown", (event) => {
    if (!state.annotating) return;
    event.preventDefault();
    annotateCanvas.setPointerCapture(event.pointerId);
    state.currentStroke = {
      color: penColor?.value || "#116a5a",
      points: [pointFromEvent(event)],
    };
    drawAnnotations();
  });

  annotateCanvas?.addEventListener("pointermove", (event) => {
    if (!state.annotating || !state.currentStroke) return;
    event.preventDefault();
    state.currentStroke.points.push(pointFromEvent(event));
    drawAnnotations();
  });

  const finishStroke = (event) => {
    if (!state.currentStroke) return;
    if (event && annotateCanvas?.hasPointerCapture?.(event.pointerId)) {
      annotateCanvas.releasePointerCapture(event.pointerId);
    }
    if (state.currentStroke.points.length > 1) {
      state.strokes.push(state.currentStroke);
    }
    state.currentStroke = null;
    drawAnnotations();
  };

  annotateCanvas?.addEventListener("pointerup", finishStroke);
  annotateCanvas?.addEventListener("pointercancel", finishStroke);
  annotateCanvas?.addEventListener("pointerleave", (event) => {
    if (state.currentStroke) finishStroke(event);
  });

  const toggleAnnotate = () => {
    state.annotating = !state.annotating;
    canvasStage?.classList.toggle("is-annotating", state.annotating);
    const button = $("[data-canvas='annotate']");
    if (button) button.setAttribute("aria-pressed", state.annotating ? "true" : "false");
    if (state.annotating) {
      resizeAnnotationCanvas();
      showToast("Lápiz activo: dibuja sobre la gráfica");
    }
  };

  $("[data-canvas='annotate']")?.addEventListener("click", toggleAnnotate);
  $("[data-canvas='clear']")?.addEventListener("click", () => {
    state.strokes = [];
    state.currentStroke = null;
    drawAnnotations();
    showToast("Anotaciones borradas");
  });
  $("[data-canvas='download']")?.addEventListener("click", () => {
    if (!state.lastFigure) {
      showToast("No hay una gráfica para exportar.", "error");
      return;
    }
    if (!window.Plotly) {
      showToast("Plotly aún no está disponible.", "error");
      return;
    }
    window.Plotly.downloadImage(plotDiv, {
      format: "png",
      filename: "ode-calculator-grafica",
      width: 1400,
      height: 900,
      scale: 2,
    });
    showToast("Exportando gráfica como PNG…");
  });
  $("[data-canvas='fullscreen']")?.addEventListener("click", async () => {
    if (!canvasCard) return;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await canvasCard.requestFullscreen();
    } catch {
      showToast("Tu navegador no permitió pantalla completa.", "error");
    }
  });
  document.addEventListener("fullscreenchange", () => {
    window.setTimeout(() => {
      resizeAnnotationCanvas();
      if (state.lastFigure) drawFigure(state.lastFigure);
    }, 80);
  });

  if (typeof ResizeObserver !== "undefined" && canvasStage) {
    new ResizeObserver(() => resizeAnnotationCanvas()).observe(canvasStage);
  } else {
    window.addEventListener("resize", resizeAnnotationCanvas);
  }

  /* ------------------------------------------------------------ misc links */

  $("#copy-curl")?.addEventListener("click", async () => {
    const code = $(".code-card pre code");
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.textContent);
      showToast("Comando copiado al portapapeles");
    } catch {
      showToast("No se pudo copiar; selecciona el texto manualmente.", "error");
    }
  });

  /* ------------------------------------------------------------------ init */

  const init = () => {
    const stored = window.localStorage.getItem("ode-theme");
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(stored || preferred);

    renderFilters();
    renderExerciseGrid();
    renderGuide(state.selectedExercise);
    updateCanvasModeLabel();

    if (window.location.protocol.startsWith("http")) {
      window.setTimeout(startDemo, 420);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
