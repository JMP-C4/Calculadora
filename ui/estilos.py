"""Tokens y hoja de estilos compartida por todas las páginas de EDO-Lab.

La hoja prioriza rejilla fluida, unidades relativas y jerarquía tipográfica.
No fija el ancho de los contenedores principales: el lienzo crece con el
viewport y las columnas se reacomodan antes de generar scroll horizontal.
"""

from __future__ import annotations

CSS_BASE = """
<style>
:root{
  color-scheme: light;
  --edo-fondo: #f7f9fb;
  --edo-superficie: #ffffff;
  --edo-texto: #102033;
  --edo-texto-suave: #52657a;
  --edo-borde: rgba(16,32,51,.14);
  --edo-suave: rgba(16,32,51,.045);
  --edo-primario: #175c56;
  --edo-primario-suave: rgba(23,92,86,.10);
  --edo-ok: #12704f;
  --edo-ok-suave: rgba(18,112,79,.12);
  --edo-ambar: #9a5b06;
  --edo-ambar-suave: rgba(154,91,6,.12);
  --edo-rojo: #b02f3d;
  --edo-rojo-suave: rgba(176,47,61,.12);
  --espacio: clamp(.75rem, 1.4vw, 1.5rem);
  --radio: clamp(10px, 1vw, 16px);
  --ancho-max: min(100%, 1800px);
  --altura-lienzo: clamp(320px, 56dvh, 720px);
  --altura-scroll: clamp(240px, 48dvh, 560px);
}

.stApp{background:var(--edo-fondo);}
.block-container{
  max-width:var(--ancho-max);
  margin-inline:auto;
  padding:var(--espacio) clamp(.75rem, 3vw, 2.5rem) calc(var(--espacio) * 3);
}

/* Tipografía: jerarquía fluida, números alineados y títulos sin viudas. */
html, body, [class*="css"]{font-size:clamp(.94rem,.35vw + .85rem,1.02rem);line-height:1.55;}
h1,h2,h3,h4{text-wrap:balance;line-height:1.25;letter-spacing:-.02em;font-weight:650;}
h1{font-size:clamp(1.55rem,2.4vw,2.35rem);}
h2{font-size:clamp(1.25rem,1.7vw,1.8rem);}
h3{font-size:clamp(1.08rem,1.25vw,1.35rem);}
p,li{max-width:82ch;}
[data-testid="stMetricValue"]{font-size:clamp(1.15rem,1.3vw,1.45rem);font-variant-numeric:tabular-nums;}
[data-testid="stDataFrame"]{font-variant-numeric:tabular-nums;}

.edo-icono{width:1em;height:1em;flex:none;vertical-align:-.14em;color:currentColor;}
.edo-marca{display:flex;align-items:center;gap:.6rem;font-size:clamp(1.35rem,2vw,1.9rem);font-weight:700;letter-spacing:-.03em;}
.edo-marca .edo-icono{width:1.25em;height:1.25em;padding:.24em;border-radius:.35em;background:var(--edo-primario);color:#fff;}
.edo-lema{color:var(--edo-texto-suave);font-size:clamp(.82rem,.3vw + .76rem,.95rem);}
.edo-cabecera{
  display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;
  gap:var(--espacio);padding:.2rem 0 1rem;margin-bottom:var(--espacio);
  border-bottom:1px solid var(--edo-borde);
}
.edo-titulo{display:flex;align-items:center;gap:.55rem;min-width:0;}
.edo-titulo .edo-icono{width:1.3em;height:1.3em;color:var(--edo-primario);}
.edo-nav,
.edo-nav-marker{display:none;}
div:has(> .edo-nav-marker) + div{
  padding:.55rem .7rem;margin-bottom:var(--espacio);
  border:1px solid var(--edo-borde);border-radius:var(--radio);
  background:var(--edo-superficie);
}
div:has(> .edo-nav-marker) + div [data-testid="stSegmentedControl"]{width:100%;}
div:has(> .edo-nav-marker) + div label{
  font-size:.78rem;color:var(--edo-texto-suave);font-weight:600;
  letter-spacing:.02em;text-transform:uppercase;
}
.edo-panel,.edo-panel [data-testid="stVerticalBlock"]{min-width:0;}
.edo-panel{overflow-wrap:anywhere;}

[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:var(--radio);border-color:var(--edo-borde);
  background:var(--edo-superficie);
}
.edo-tarjeta{
  border:1px solid var(--edo-borde);border-radius:var(--radio);
  padding:var(--espacio);margin-bottom:var(--espacio);background:var(--edo-superficie);
}
[data-testid="stHorizontalBlock"]{gap:var(--espacio)!important;align-items:start;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{min-width:0;}
[data-testid="stExpander"] details{border-radius:var(--radio);border-color:var(--edo-borde);}
[data-testid="stExpander"] summary{font-weight:600;}

/* Badges y estados */
.edo-badge{
  display:inline-flex;align-items:center;gap:.35rem;flex-wrap:wrap;
  border-radius:999px;padding:.2rem .7rem;font-size:.84rem;font-weight:600;
  border:1px solid transparent;line-height:1.35;
}
.edo-badge-ok{background:var(--edo-ok-suave);color:var(--edo-ok);border-color:rgba(18,112,79,.32);}
.edo-badge-warn{background:var(--edo-ambar-suave);color:var(--edo-ambar);border-color:rgba(154,91,6,.32);}
.edo-badge-error{background:var(--edo-rojo-suave);color:var(--edo-rojo);border-color:rgba(176,47,61,.32);}
.edo-badge-info{background:var(--edo-primario-suave);color:var(--edo-primario);border-color:rgba(23,92,86,.28);}

/* Listas largas con scroll propio, sin fijar el ancho. */
.edo-scroll,
.edo-marcador-scroll + [data-testid="stVerticalBlock"],
div:has(> .edo-marcador-scroll) + [data-testid="stVerticalBlock"]{
  height:var(--altura-scroll)!important;
  max-height:var(--altura-scroll);
  overflow:auto;padding-right:.5rem;
  scrollbar-width:thin;overscroll-behavior:contain;
}
.edo-scroll::-webkit-scrollbar{width:8px;height:8px;}
.edo-scroll::-webkit-scrollbar-thumb{background:rgba(82,101,122,.45);border-radius:8px;}

/* Katex y tablas: desbordamiento controlado dentro del panel. */
.katex-display{max-width:100%;overflow-x:auto;overflow-y:hidden;padding:.45rem 0;}
[data-testid="stDataFrame"] > div{max-width:100%;overflow:auto;}
.js-plotly-plot,.stDataFrame{max-width:100%;}

/* Lienzo: toma altura del viewport y mantiene zoom/paneo sin tapar la gráfica. */
.edo-marcador-lienzo{display:none;}
.edo-marcador-lienzo + [data-testid="stPlotlyChart"],
div:has(> .edo-marcador-lienzo) + [data-testid="stPlotlyChart"]{
  width:100%;min-width:0;height:var(--altura-lienzo)!important;
}
.edo-marcador-lienzo + [data-testid="stPlotlyChart"] .js-plotly-plot,
div:has(> .edo-marcador-lienzo) + [data-testid="stPlotlyChart"] .js-plotly-plot{
  width:100%!important;height:100%!important;
}

.stTabs [data-baseweb="tab-list"]{
  display:flex;flex-wrap:nowrap;overflow-x:auto;gap:.25rem;scrollbar-width:thin;
  padding-bottom:.15rem;
}
.stTabs [data-baseweb="tab"]{white-space:nowrap;flex:none;}
.edo-pie{color:var(--edo-texto-suave);font-size:.82rem;padding-top:var(--espacio);}

/* Foco, movimiento y áreas seguras. */
:focus-visible{outline:2px solid var(--edo-primario);outline-offset:2px;border-radius:4px;}
*{scroll-margin-top:1rem;}
html{overscroll-behavior-y:auto;}
@media (pointer:fine){html{overscroll-behavior-y:none;}}
@supports (padding: env(safe-area-inset-left)){
  .block-container{
    padding-left:max(clamp(.75rem,3vw,2.5rem),env(safe-area-inset-left));
    padding-right:max(clamp(.75rem,3vw,2.5rem),env(safe-area-inset-right));
  }
}

@media (max-width: 1180px){
  :root{--altura-lienzo:clamp(300px,48dvh,600px);}
  .edo-cabecera{justify-content:flex-start;}
}
@media (max-width: 700px){
  :root{--altura-lienzo:clamp(280px,52dvh,520px);--altura-scroll:clamp(220px,42dvh,420px);}
  .block-container{padding:.75rem .85rem 2.5rem;}
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{flex:1 1 100%;}
  .edo-badge{white-space:normal;}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;}
}
</style>
"""

CSS_OSCURO = """
<style>
.stApp{
  color-scheme: dark;
  --edo-fondo:#0c141d;
  --edo-superficie:#131f2b;
  --edo-texto:#eaf2f8;
  --edo-texto-suave:#a9bbca;
  --edo-borde:rgba(226,232,240,.18);
  --edo-suave:rgba(148,163,184,.08);
  --edo-primario:#7dd3c4;
  --edo-primario-suave:rgba(125,211,196,.12);
  --edo-ok:#5ee0a5;
  --edo-ok-suave:rgba(94,224,165,.12);
  --edo-ambar:#f3c26b;
  --edo-ambar-suave:rgba(243,194,107,.12);
  --edo-rojo:#fb8b96;
  --edo-rojo-suave:rgba(251,139,150,.12);
}
</style>
"""


def css(oscuro: bool = False) -> str:
    """Devuelve el bloque CSS completo, con variante oscura opcional."""

    return CSS_BASE + (CSS_OSCURO if oscuro else "")


CSS = css(False)

__all__ = ["CSS", "CSS_BASE", "CSS_OSCURO", "css"]
