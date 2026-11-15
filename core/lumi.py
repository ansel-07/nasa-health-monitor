# AI-assisted: Lumi designed by Ansel with an AI assistant; integrated with Claude Code and reviewed by Ansel.
"""
Lumi — mascota LED para la app de seguimiento médico (NASA Space Apps 2026).

Uso en Streamlit:

    from lumi import lumi

    lumi("nominal", "All vitals steady and clear. Ready whenever you need a check-in.")
    lumi("MUS", "I noticed a mild change in your log - how are you feeling right now?")
    lumi("ALM", "Elevated reading detected! Please pause, rest, and review alert steps.")

    with st.sidebar:
        lumi("nominal", "Hi! Ready for today's check-in?", layout="column", size=180)

Estados aceptados (sin distinguir mayúsculas):
    nominal  <- "nominal", "ok", "none"
    symptom  <- "symptom", "followup", "VIS", "MUS"
    alarm    <- "alarm", "urgent", "ALM"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ALIASES = {
    "nominal": "nominal", "ok": "nominal", "none": "nominal", "": "nominal",
    "symptom": "symptom", "followup": "symptom", "follow-up": "symptom",
    "vis": "symptom", "mus": "symptom",
    "alarm": "alarm", "urgent": "alarm", "alm": "alarm",
}

COLORS = {"nominal": "#38BDF8", "symptom": "#FBBF24", "alarm": "#F87171"}


def normalize_state(state: str | None) -> str:
    key = (state or "").strip().lower()
    if key not in _ALIASES:
        raise ValueError(f"Estado de Lumi desconocido: {state!r}")
    return _ALIASES[key]


def lumi_html(
    state: str = "nominal",
    message: str = "",
    *,
    label: str | None = None,
    speaking: bool | None = None,
    layout: str = "row",
    size: int = 200,
    voice: bool = False,
    typing_ms: int = 30,
    demo: bool = False,
) -> str:
    """Devuelve el HTML autocontenido de Lumi (útil fuera de Streamlit)."""
    cfg = {
        "state": normalize_state(state),
        "message": message or "",
        "label": label,
        "speaking": speaking,
        "layout": layout,
        "size": size,
        "voice": voice,
        "typingMs": typing_ms,
        "demo": demo,
    }
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    return (_TEMPLATE.replace("__LUMI_CONFIG__", cfg_json)
            .replace("__LUMI_HEADS__", json.dumps(HEADS)))


def lumi(
    state: str = "nominal",
    message: str = "",
    *,
    label: str | None = None,
    speaking: bool | None = None,
    layout: str = "row",
    size: int = 200,
    voice: bool = False,
    typing_ms: int = 30,
    height: int | None = None,
) -> None:
    """Pinta a Lumi en Streamlit.

    state     : estado de salud (ver aliases arriba).
    message   : diálogo en inglés. Mientras se escribe, Lumi "habla".
    label     : texto pequeño encima del diálogo (por defecto, el nombre del estado).
    speaking  : None -> habla mientras escribe el mensaje.
                True -> habla indefinidamente; False -> nunca.
    layout    : "row" (cabecera: mascota + bocadillo al lado),
                "column" (barra lateral: bocadillo debajo),
                "solo" (solo la mascota).
    voice     : lee el mensaje con speechSynthesis del navegador (en-US).
    height    : alto del iframe; si es None se calcula.
    """
    import streamlit as st

    if height is None:
        if layout == "column":
            height = size + 150
        else:
            height = size + 12
    # st.iframe, not the deprecated components.html (AGENTS.md 3).
    st.iframe(
        lumi_html(state, message, label=label, speaking=speaking, layout=layout,
                  size=size, voice=voice, typing_ms=typing_ms),
        height=height,
    )


# ---------------------------------------------------------------------------
# Cabezas: polígonos de esquinas redondeadas y lados ligeramente abombados.
# Las tres tienen 8 vértices en el mismo orden (empezando arriba a la izquierda,
# sentido horario) para que el path tenga los mismos comandos y se pueda
# morfear con la propiedad CSS `d`. Los vértices marcados con "+" son de relleno:
# están sobre la curva del lado y apenas se notan.
#   N3 (nominal, hexágono con mofletes), S2 (seguimiento, heptágono irregular),
#   B4 (alarma, octógono afinado).
# ---------------------------------------------------------------------------
def _rounded_poly(pts, r, bulge=0.0):
    """bulge: número o lista (un valor por lado i -> i+1)."""
    import math
    n = len(pts)
    bulges = bulge if isinstance(bulge, (list, tuple)) else [bulge] * n
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n

    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy)
        return dx / l, dy / l, l

    A, B = [], []
    for i, v in enumerate(pts):
        p, q = pts[i - 1], pts[(i + 1) % n]
        ux, uy, lp = unit(v, p)
        vx, vy, lq = unit(v, q)
        rr = min(r, lp * .45, lq * .45)
        A.append((v[0] + ux * rr, v[1] + uy * rr))
        B.append((v[0] + vx * rr, v[1] + vy * rr))

    f = lambda p: f"{p[0]:.1f} {p[1]:.1f}"
    d = f"M{f(B[0])}"
    for i in range(n):
        j = (i + 1) % n
        s, e = B[i], A[j]
        mx, my = (s[0] + e[0]) / 2, (s[1] + e[1]) / 2
        ox, oy = mx - cx, my - cy
        ol = math.hypot(ox, oy)
        L = math.hypot(e[0] - s[0], e[1] - s[1])
        c = (mx + ox / ol * bulges[i] * L, my + oy / ol * bulges[i] * L)
        d += f" Q{f(c)} {f(e)} Q{f(pts[j])} {f(B[j])}"
    return d + " Z"


def _pad(a, b, bulge, centroid):
    """Vértice de relleno en el punto medio del lado a-b, empujado hacia fuera
    lo mismo que la curva abombada en ese punto."""
    import math
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ox, oy = mx - centroid[0], my - centroid[1]
    ol = math.hypot(ox, oy)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    k = 0.5 * bulge * L
    return (mx + ox / ol * k, my + oy / ol * k)


def _heads():
    # N3 (6 vértices -> 8)
    n3 = [(62, 55), (138, 55), (166, 112), (132, 162), (68, 162), (34, 112)]
    c = (100, 110)
    nominal = [n3[0], n3[1], _pad(n3[1], n3[2], .06, c), n3[2], n3[3], n3[4], n3[5],
               _pad(n3[5], n3[0], .06, c)]
    # S2 (7 vértices -> 8)
    s2 = [(70, 48), (124, 44), (154, 92), (148, 148), (108, 170), (64, 164), (46, 100)]
    c = (109, 117)
    symptom = s2 + [_pad(s2[6], s2[0], .04, c)]
    # B4 (8 vértices)
    alarm = [(72, 50), (128, 50), (158, 74), (160, 112), (124, 166), (76, 166), (40, 112), (42, 74)]
    return {
        "nominal": _rounded_poly(nominal, 24, [.06, .025, .025, .06, .06, .06, .025, .025]),
        "symptom": _rounded_poly(symptom, 16, [.04] * 6 + [.015, .015]),
        "alarm": _rounded_poly(alarm, 16, .04),
    }


HEADS = _heads()


_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; background: transparent;
    font-family: "Source Sans Pro", "Inter", system-ui, -apple-system, sans-serif; }
  .wrap { display: flex; gap: 18px; align-items: center; padding: 4px; }
  .wrap.column { flex-direction: column; align-items: stretch; }
  .wrap.column .box { align-self: center; }

  .box { --size: 200px; width: var(--size); height: var(--size); flex: none;
    background: #0B0F19; border-radius: 22px; position: relative; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.06); }
  .box svg { width: 100%; height: 100%; display: block; overflow: visible; }

  .lumi { color: var(--c, #38BDF8); transition: color .6s ease; }

  /* flotación en gravedad cero */
  .float { animation: float 4.2s ease-in-out infinite; }
  .shadow { transform-box: fill-box; transform-origin: center;
    animation: shadow 4.2s ease-in-out infinite; opacity: .22; }
  @keyframes float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-7px) } }
  @keyframes shadow { 0%,100% { transform: scaleX(1); opacity: .24 } 50% { transform: scaleX(.82); opacity: .14 } }

  .glow { filter: drop-shadow(0 0 2.5px currentColor) drop-shadow(0 0 9px currentColor); }

  .tilt { transform-box: view-box; transform-origin: 100px 112px;
    transition: transform .8s cubic-bezier(.34,1.3,.5,1); }

  .head, .head-bg, .ant { transition: d .8s cubic-bezier(.34,1.2,.5,1); }
  .head { fill: currentColor; fill-opacity: .07; stroke: currentColor; stroke-width: 5;
    stroke-linejoin: round; }
  .head-bg { fill: #0B0F19; }
  .ant { fill: none; stroke: currentColor; stroke-width: 4.5; stroke-linecap: round; }
  .tip { fill: currentColor; transition: cx .8s cubic-bezier(.34,1.2,.5,1), cy .8s cubic-bezier(.34,1.2,.5,1);
    transform-box: fill-box; transform-origin: center; }
  .lumi[data-state="alarm"] .tip { animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; transform: scale(1) } 50% { opacity: .55; transform: scale(1.35) } }

  /* rasgos: cada estado tiene su grupo y se hace crossfade */
  .feat { opacity: 0; transition: opacity .35s ease; }
  .lumi[data-state="nominal"] .f-nominal,
  .lumi[data-state="symptom"] .f-symptom,
  .lumi[data-state="alarm"]   .f-alarm { opacity: 1; }

  .stroke { fill: none; stroke: currentColor; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
  .fill { fill: currentColor; }

  /* parpadeo */
  .eyes { transform-box: fill-box; transform-origin: center; animation: blink 5.2s infinite; }
  @keyframes blink { 0%, 92%, 100% { transform: scaleY(1) } 94% { transform: scaleY(.08) } 96% { transform: scaleY(1) } }

  /* boca: reposo vs. cápsula hablando */
  .mouth-rest { transition: opacity .15s ease; }
  .talk { fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 5; opacity: 0;
    transition: opacity .15s ease; }
  .lumi.speaking .mouth-rest { opacity: 0 !important; }
  .lumi.speaking .talk { opacity: 1; animation: talk .72s linear infinite; }
  @keyframes talk {
    0% { stroke-width: 5 } 14% { stroke-width: 14 } 28% { stroke-width: 7 } 42% { stroke-width: 12 }
    56% { stroke-width: 5 } 70% { stroke-width: 15 } 85% { stroke-width: 8 } 100% { stroke-width: 5 } }

  /* bocadillo */
  .bubble { flex: 1; min-width: 0; background: #161B26; border: 1px solid rgba(255,255,255,.07);
    border-radius: 18px; padding: 14px 18px; color: #E5E7EB; }
  .bubble .label { font-size: 13px; color: #9CA3AF; margin-bottom: 6px; display: flex; align-items: center; gap: 8px; }
  .bubble .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--c); transition: background .6s;
    box-shadow: 0 0 8px var(--c); }
  .bubble .text { font-size: 18px; line-height: 1.4; min-height: 1.4em; white-space: pre-wrap; }
  .bubble .caret { display: inline-block; width: 2px; height: 1em; background: var(--c); margin-left: 2px;
    vertical-align: -2px; animation: caret .8s steps(1) infinite; }
  @keyframes caret { 50% { opacity: 0 } }
  .wrap.solo .bubble, .bubble.empty { display: none; }

  /* demo */
  .demo { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
  .demo button { background: #1F2937; color: #E5E7EB; border: 1px solid #374151; border-radius: 999px;
    padding: 8px 14px; font: inherit; font-size: 14px; cursor: pointer; }
  .demo button:hover { border-color: #6B7280; }

  @media (prefers-reduced-motion: reduce) {
    .float, .shadow, .tip, .eyes { animation: none !important; }
  }
</style></head>
<body>
<div class="wrap" id="wrap">
  <div class="box" id="box">
    <svg viewBox="0 0 200 200" aria-label="Lumi" role="img">
      <g class="lumi" id="lumi" data-state="nominal">
        <ellipse class="shadow" cx="100" cy="186" rx="42" ry="5.5" fill="currentColor"/>
        <g class="float">
          <g class="tilt" id="tilt">
            <g class="glow">
              <path class="ant" id="antL"/>
              <path class="ant" id="antR"/>
              <circle class="tip" id="tipL" r="5.5"/>
              <circle class="tip" id="tipR" r="5.5"/>
              <path class="head-bg" id="headBg"/>
              <path class="head" id="head"/>

              <!-- Nominal: ojos ◠ ◠ y sonrisa ‿ -->
              <g class="feat f-nominal">
                <g class="eyes">
                  <path class="stroke" d="M69 104 Q79 91 89 104"/>
                  <path class="stroke" d="M111 104 Q121 91 131 104"/>
                </g>
                <path class="stroke mouth-rest" d="M89 125 Q100 137 111 125"/>
              </g>

              <!-- Seguimiento: ojos sin cejas, uno algo más grande, boca ◡ -->
              <g class="feat f-symptom">
                <g class="eyes">
                  <circle class="fill" cx="81" cy="103" r="6.5"/>
                  <circle class="fill" cx="119" cy="101" r="8.5"/>
                </g>
                <path class="stroke mouth-rest" d="M92 129 Q101 135 110 127"/>
              </g>

              <!-- Alarma: ojos muy abiertos, boca ﹏ -->
              <g class="feat f-alarm">
                <g class="eyes">
                  <circle class="fill" cx="80" cy="103" r="9.5"/>
                  <circle class="fill" cx="120" cy="103" r="9.5"/>
                </g>
                <path class="stroke mouth-rest" d="M85 133 Q90 125 95 131 Q100 136 105 131 Q110 125 115 133"/>
              </g>

              <!-- Cápsula LED al hablar -->
              <line class="talk" id="talk" x1="93" y1="129" x2="107" y2="129"/>
            </g>
          </g>
        </g>
      </g>
    </svg>
  </div>
  <div class="bubble" id="bubble">
    <div class="label"><span class="dot"></span><span id="label"></span></div>
    <div class="text"><span id="text"></span><span class="caret" id="caret"></span></div>
  </div>
</div>
<div class="demo" id="demo" hidden></div>

<script>
(() => {
  const CFG = __LUMI_CONFIG__;
  const HEADS = __LUMI_HEADS__;

  // Las cabezas vienen de Python (HEADS): misma estructura de comandos -> morph con CSS `d`.
  const SHAPES = {
    nominal: {
      color: "#38BDF8", name: "Nominal", tilt: 0,
      head: HEADS.nominal,
      antL: "M82 58 Q70 40 59 24", antR: "M118 58 Q130 40 141 24",
      tipL: [59, 24], tipR: [141, 24],
      talkY: 129,
    },
    symptom: {
      color: "#FBBF24", name: "Symptom follow-up", tilt: -7,
      head: HEADS.symptom,
      antL: "M84 50 Q58 26 36 60", antR: "M116 50 Q142 26 164 60",
      tipL: [36, 60], tipR: [164, 60],
      talkY: 130,
    },
    alarm: {
      color: "#F87171", name: "Urgent alarm", tilt: 0,
      head: HEADS.alarm,
      antL: "M86 54 Q84 36 82 16", antR: "M114 54 Q116 36 118 16",
      tipL: [82, 16], tipR: [118, 16],
      talkY: 131,
    },
  };

  const $ = (id) => document.getElementById(id);
  const lumiEl = $("lumi"), wrap = $("wrap"), bubble = $("bubble");
  let state = null, typingTimer = null, typing = false, voicing = false, forced = null;

  function setPath(el, d) { el.setAttribute("d", d); el.style.d = `path("${d}")`; }
  function setTip(el, [x, y]) { el.setAttribute("cx", x); el.setAttribute("cy", y); el.style.cx = x + "px"; el.style.cy = y + "px"; }

  function setState(s) {
    const sh = SHAPES[s]; if (!sh) return;
    state = s;
    lumiEl.dataset.state = s;
    document.documentElement.style.setProperty("--c", sh.color);
    setPath($("head"), sh.head); setPath($("headBg"), sh.head);
    setPath($("antL"), sh.antL); setPath($("antR"), sh.antR);
    setTip($("tipL"), sh.tipL); setTip($("tipR"), sh.tipR);
    $("tilt").style.transform = `rotate(${sh.tilt}deg)`;
    $("talk").setAttribute("y1", sh.talkY); $("talk").setAttribute("y2", sh.talkY);
    if (!CFG.label) $("label").textContent = sh.name;
  }

  function refreshSpeaking() {
    const on = forced === null ? (typing || voicing) : forced;
    lumiEl.classList.toggle("speaking", on);
  }

  function say(text, { voice = CFG.voice, ms = CFG.typingMs } = {}) {
    clearInterval(typingTimer);
    const out = $("text"); out.textContent = "";
    bubble.classList.toggle("empty", !text);
    $("caret").style.display = text ? "" : "none";
    if (!text) { typing = false; refreshSpeaking(); return; }
    let i = 0; typing = true; refreshSpeaking();
    typingTimer = setInterval(() => {
      out.textContent = text.slice(0, ++i);
      if (i >= text.length) {
        clearInterval(typingTimer); typing = false; refreshSpeaking();
        setTimeout(() => { $("caret").style.display = "none"; }, 900);
      }
    }, ms);
    if (voice && "speechSynthesis" in window) {
      try {
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "en-US"; u.rate = 1.05; u.pitch = 1.25;
        u.onstart = () => { voicing = true; refreshSpeaking(); };
        u.onend = u.onerror = () => { voicing = false; refreshSpeaking(); };
        speechSynthesis.speak(u);
      } catch (e) { /* sin voz, no pasa nada */ }
    }
  }

  // ---- init ----
  $("box").style.setProperty("--size", CFG.size + "px");
  wrap.classList.add(CFG.layout || "row");
  if (CFG.label) $("label").textContent = CFG.label;
  forced = (CFG.speaking === true || CFG.speaking === false) ? CFG.speaking : null;
  setState(CFG.state || "nominal");
  say(CFG.message || "");

  window.Lumi = { setState, say, speak: (on) => { forced = on; refreshSpeaking(); } };

  if (CFG.demo) {
    const demo = $("demo"); demo.hidden = false;
    const lines = {
      nominal: "All vitals steady and clear. Ready whenever you need a check-in.",
      symptom: "I noticed a mild change in your log. How are you feeling right now?",
      alarm: "Elevated reading detected! Please pause, rest, and review alert steps.",
    };
    for (const s of Object.keys(SHAPES)) {
      const b = document.createElement("button");
      b.textContent = SHAPES[s].name;
      b.onclick = () => { setState(s); say(lines[s]); };
      demo.appendChild(b);
    }
    const v = document.createElement("button");
    v.textContent = "🔊 Speak with voice";
    v.onclick = () => say(lines[state], { voice: true });
    demo.appendChild(v);
  }
})();
</script>
</body></html>
"""


# ---------------------------------------------------------------------------
# Face only, for core/mascot.py (subtitles below, no bubble; AGENTS.md 8). Same SVG, CSS and
# shapes as the template above; the state is drawn statically (no morph between reruns).
# ---------------------------------------------------------------------------
SHAPES = {
    "nominal": {"head": HEADS["nominal"], "antL": "M82 58 Q70 40 59 24", "antR": "M118 58 Q130 40 141 24",
                "tipL": (59, 24), "tipR": (141, 24), "tilt": 0, "talkY": 129},
    "symptom": {"head": HEADS["symptom"], "antL": "M84 50 Q58 26 36 60", "antR": "M116 50 Q142 26 164 60",
                "tipL": (36, 60), "tipR": (164, 60), "tilt": -7, "talkY": 130},
    "alarm": {"head": HEADS["alarm"], "antL": "M86 54 Q84 36 82 16", "antR": "M114 54 Q116 36 118 16",
              "tipL": (82, 16), "tipR": (118, 16), "tilt": 0, "talkY": 131},
}
STATES = list(SHAPES)


def face_css(backdrop: str) -> str:
    """Lumi's face CSS (float, glow, blink, talking capsule), taken from the template.

    backdrop: colour behind the face; the head is filled with it so the antennae end at the head.
    """
    css = _TEMPLATE.split("<style>", 1)[1].split("/* bocadillo */", 1)[0]
    css = css.split("  .lumi {", 1)[1]
    reduced = _TEMPLATE.split("@media (prefers-reduced-motion", 1)[1].split("</style>", 1)[0]
    return ("  .lumi {" + css.replace("fill: #0B0F19;", f"fill: {backdrop};")
            + "@media (prefers-reduced-motion" + reduced)


def face_svg(state: str, width: int, height: int, label: str) -> str:
    """Lumi's SVG in one state. The mouth talks when the class "speaking" is on .lumi."""
    s = normalize_state(state)
    sh = SHAPES[s]
    svg = _TEMPLATE.split('<svg viewBox="0 0 200 200" aria-label="Lumi" role="img">', 1)[1].split("</svg>", 1)[0]
    svg = (svg.replace('data-state="nominal"', f'data-state="{s}" style="--c:{COLORS[s]}"')
              .replace('<path class="ant" id="antL"/>', f'<path class="ant" id="antL" d="{sh["antL"]}"/>')
              .replace('<path class="ant" id="antR"/>', f'<path class="ant" id="antR" d="{sh["antR"]}"/>')
              .replace('<circle class="tip" id="tipL" r="5.5"/>',
                       f'<circle class="tip" id="tipL" r="5.5" cx="{sh["tipL"][0]}" cy="{sh["tipL"][1]}"/>')
              .replace('<circle class="tip" id="tipR" r="5.5"/>',
                       f'<circle class="tip" id="tipR" r="5.5" cx="{sh["tipR"][0]}" cy="{sh["tipR"][1]}"/>')
              .replace('<path class="head-bg" id="headBg"/>', f'<path class="head-bg" id="headBg" d="{sh["head"]}"/>')
              .replace('<path class="head" id="head"/>', f'<path class="head" id="head" d="{sh["head"]}"/>')
              .replace('<g class="tilt" id="tilt">', f'<g class="tilt" id="tilt" style="transform: rotate({sh["tilt"]}deg)">')
              .replace('y1="129" x2="107" y2="129"', f'y1="{sh["talkY"]}" x2="107" y2="{sh["talkY"]}"'))
    return (f'<svg class="face" width="{width}" height="{height}" viewBox="0 0 200 200" '
            f'role="img" aria-label="{label}" style="overflow:visible">{svg}</svg>')


if __name__ == "__main__":
    # python lumi.py demo.html  -> genera una página de prueba sin Streamlit
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "lumi_demo.html")
    out.write_text(
        lumi_html("nominal", "All vitals steady and clear. Ready whenever you need a check-in.",
                  demo=True, size=240),
        encoding="utf-8",
    )
    print(f"Demo escrita en {out}")
