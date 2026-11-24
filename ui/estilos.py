"""Hoja de estilos compartida por todas las páginas de EDO-Lab."""

from __future__ import annotations

CSS_BASE = """
<style>
:root{
  --espacio: clamp(0.75rem, 1.5vw, 1.5rem);
  --radio: 12px;
  --max-ancho: 1400px;
  --edo-borde: rgba(128,128,128,.25);
  --edo-suave: rgba(128,128,128,.08);
  --edo-azul: #2563eb;
  --edo-verde: #15803d;
  --edo-ambar: #b45309;
  --edo-rojo: #b91c1c;
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
h3{font-size: clamp(1.05rem, 1.8vw, 1.35rem);}
p, li{max-width: 80ch;}

/* Tarjetas nativas de Streamlit con borde suave */
[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius: var(--radio);
  border-color: var(--edo-borde);
}

/* Tarjetas propias */
.edo-tarjeta{
  border: 1px solid var(--edo-borde);
  border-radius: var(--radio);
  padding: var(--espacio);
  margin-bottom: var(--espacio);
  background: var(--edo-suave);
}

.edo-cabecera{
  display:flex;
  flex-wrap:wrap;
  align-items:center;
  justify-content:space-between;
  gap:.75rem;
  padding:.35rem 0 1rem;
  border-bottom:1px solid var(--edo-borde);
  margin-bottom:1rem;
}
.edo-marca{font-size:clamp(1.35rem,2.4vw,1.9rem);font-weight:800;letter-spacing:-.02em;}
.edo-lema{opacity:.75;font-size:.95rem;}

.edo-badge{
  display:inline-flex;
  align-items:center;
  gap:.35rem;
  border-radius:999px;
  padding:.15rem .65rem;
  font-size:.86rem;
  font-weight:600;
  border:1px solid transparent;
  white-space:nowrap;
}
.edo-badge-ok{background:rgba(21,128,61,.12);color:var(--edo-verde);border-color:rgba(21,128,61,.35);}
.edo-badge-warn{background:rgba(180,83,9,.12);color:var(--edo-ambar);border-color:rgba(180,83,9,.35);}
.edo-badge-error{background:rgba(185,28,28,.12);color:var(--edo-rojo);border-color:rgba(185,28,28,.35);}
.edo-badge-info{background:rgba(37,99,235,.12);color:var(--edo-azul);border-color:rgba(37,99,235,.35);}

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
.stTabs [data-baseweb="tab"]{white-space: nowrap;}

/* Gráficas y tablas se ajustan al ancho */
.js-plotly-plot, .stDataFrame{max-width: 100%;}

/* Tablas anchas con scroll dentro de su contenedor */
[data-testid="stDataFrame"] > div{overflow-x:auto;}

/* Métricas legibles */
[data-testid="stMetricValue"]{font-size:1.25rem;}

/* Pie discreto */
.edo-pie{opacity:.65;font-size:.82rem;padding-top:1.5rem;}

/* Móvil */
@media (max-width: 700px){
  .block-container{padding: .75rem 1rem 3rem;}
  .edo-scroll{max-height: 50vh;}
  .stTabs [data-baseweb="tab-list"]{padding-bottom:.25rem;}
}
</style>
"""

CSS_OSCURO = """
<style>
.stApp{
  --edo-borde: rgba(226,232,240,.22);
  --edo-suave: rgba(148,163,184,.08);
  --edo-azul: #93c5fd;
  --edo-verde: #4ade80;
  --edo-ambar: #fbbf24;
  --edo-rojo: #f87171;
}
.stApp [data-testid="stVerticalBlockBorderWrapper"]{
  border-color: rgba(226,232,240,.22);
}
</style>
"""


def css(oscuro: bool = False) -> str:
    """Devuelve el bloque CSS completo, con variante oscura opcional."""

    return CSS_BASE + (CSS_OSCURO if oscuro else "")


CSS = css(False)

__all__ = ["CSS", "CSS_BASE", "CSS_OSCURO", "css"]
