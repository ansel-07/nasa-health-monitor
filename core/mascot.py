# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""The mascot: animated face, subtitles and voice. Owner: Ansel.

Rules: AGENTS.md, section 8; layout: docs/FRONTEND_MASCOT_LAYOUT.md section 1.
Pages call only say(), beside() and voice_toggle(); one mascot per screen run.

- Alone: say(text, mood, size="large"), big and centred (35 % of the browser height).
- With a chart or flowchart: beside(text, mood), small on the left (45 % of big); the right
  column is returned for the visual. Buttons go below. Moving between the two layouts plays a
  short entry animation once (CSS in the parent page, keyed containers).
- Subtitles are revealed word by word (with the voice when it is on) and the mouth talks
  meanwhile, only when the text is new (session_state["mascot_last_text"]). A rerun with the
  same text shows the full subtitles at once, silently.

Voice: browser speech synthesis (no AI service). The HTML runs inside an iframe that
Streamlit re-creates on every rerun, so it first tries the parent page's speechSynthesis
(the parent keeps the user's click activation) and falls back to its own.
"""
import html
import json
import re

import streamlit as st

from core.models import MASCOT_SIZES, MOODS

MASCOT_NAME = "TODO: mascot name"

# Face drawn on the page background, no frame (spec section 2: viewBox 0 0 122 120).
_VIEWBOX_W, _VIEWBOX_H = 122, 120
# Mouth per mood (SVG path in the viewBox) and an open mouth used while talking.
_MOUTHS = {
    "happy": "M24 87 Q61 119 99 87",
    "neutral": "M30 96 L92 96",
    "thinking": "M40 97 Q61 90 84 101",
    "worried": "M26 104 Q61 80 96 104",
    "serious": "M34 98 L88 98",
}
_OPEN_MOUTH = "M44 90 Q61 84 78 90 Q78 110 61 112 Q44 110 44 90 Z"
# Eye height per mood (squinted, normal...); eyes stay centred on y = 42.
_EYE_HEIGHT = {"happy": 18, "neutral": 26, "thinking": 14, "worried": 30, "serious": 12}

# Fallback face heights when the parent page cannot be measured (35 % of 1080 px; 45 % of it).
_FACE_PX = {"large": 380, "small": 171}
_FACE_SHARE = {"large": 0.35, "small": 0.35 * 0.45}
# Narrow screens (phones): the big face is at most 55 % of the browser width, subtitles smaller.
_MAX_WIDTH_SHARE = 0.55
_NARROW_PX, _NARROW_FONT_PX = 640, {"large": 22, "small": 16}
_FONT_PX = {"large": 28, "small": 18}
_CHARS_PER_LINE = {"large": 48, "small": 18}
_WORD_MS, _TALK_MS, _BOUNDARY_WAIT_MS = 330, 160, 700

_LAST_TEXT = "mascot_last_text"
_LAYOUT = "mascot_layout"

# Entry animations (FRONTEND_MASCOT_LAYOUT.md 1.5), emitted only on the run where the layout changes.
_REDUCED = ("@media (prefers-reduced-motion: reduce) {{ {sel} {{ animation: none !important; }} }}")
_TO_SIDE_CSS = """<style>
@keyframes mascot-to-side { from { transform: translateX(150%) scale(2.22); } to { transform: none; } }
@keyframes mascot-fade-in { from { opacity: 0; } to { opacity: 1; } }
.st-key-mascot_side { animation: mascot-to-side 600ms ease-in-out; transform-origin: center top; }
.st-key-mascot_visual { animation: mascot-fade-in 300ms ease-in 300ms both; }
@media (max-width: 768px) { .st-key-mascot_side { animation: none; } }
""" + _REDUCED.format(sel=".st-key-mascot_side, .st-key-mascot_visual") + "\n</style>"
_TO_CENTRE_CSS = """<style>
@keyframes mascot-to-centre { from { transform: translateX(-37.5%) scale(0.45); } to { transform: none; } }
.st-key-mascot_alone { animation: mascot-to-centre 600ms ease-in-out; transform-origin: center top; }
""" + _REDUCED.format(sel=".st-key-mascot_alone") + "\n</style>"


def frame_height(text: str, size: str) -> int:
    """Fallback iframe height for the face plus its subtitles, so long texts are never cut.

    The frame resizes itself to its content in the browser; this is the first height.
    """
    lines = max(1, -(-len(text) // _CHARS_PER_LINE[size]))  # ceil
    return _FACE_PX[size] + 40 + lines * round(_FONT_PX[size] * 1.45)


def _word_spans(text: str) -> str:
    """Each word in a hidden span with its character index (matches speech boundary events)."""
    return " ".join(f'<span class="w" data-i="{m.start()}">{html.escape(m.group())}</span>'
                    for m in re.finditer(r"\S+", text))


def build_html(text: str, mood: str = "neutral", size: str = "large", voice_on: bool = False,
               animate: bool = True) -> str:
    """HTML for one mascot frame. Separate from say() so it can be tested without Streamlit.

    animate=False (same text as the last render): full subtitles at once, no voice, no talking.
    """
    if mood not in MOODS:
        raise ValueError(f"unknown mood '{mood}', expected one of {MOODS}")
    if size not in MASCOT_SIZES:
        raise ValueError(f"unknown size '{size}', expected one of {MASCOT_SIZES}")

    face_px = _FACE_PX[size]
    face_w = round(face_px * _VIEWBOX_W / _VIEWBOX_H)
    eye_h = _EYE_HEIGHT[mood]
    eye_y = 42 - eye_h / 2
    font = _FONT_PX[size]
    speak = "true" if (voice_on and animate) else "false"
    hidden = "hidden" if animate else "visible"
    # json.dumps does not escape "</", which would close the <script> early (CODE_REVIEW BUG-18).
    text_js = json.dumps(text).replace("</", "<\\/")

    return f"""
<div class="mascot" style="display:flex;flex-direction:column;align-items:center;gap:12px;font-family:sans-serif;">
  <svg class="face" width="{face_w}" height="{face_px}" viewBox="0 0 {_VIEWBOX_W} {_VIEWBOX_H}" fill="none" role="img" aria-label="{html.escape(MASCOT_NAME)} ({mood})">
    <rect class="eye" x="13" y="{eye_y}" width="30" height="{eye_h}" rx="9" fill="#5EF2FF"/>
    <rect class="eye" x="80" y="{eye_y}" width="30" height="{eye_h}" rx="9" fill="#5EF2FF"/>
    <path class="mouth" d="{_MOUTHS[mood]}" stroke="#5EF2FF" stroke-width="9" stroke-linecap="round"/>
    <path class="mouth-open" d="{_OPEN_MOUTH}" fill="#5EF2FF" style="display:none"/>
  </svg>
  <div class="subtitles" style="background:rgba(0,0,0,0.72);color:#fff;border-radius:8px;padding:6px 14px;font-size:{font}px;line-height:1.45;text-align:center;max-width:92%;">
    {_word_spans(text)}
  </div>
</div>
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
  .w {{ visibility: {hidden}; }}
  .eye {{ animation: blink 4s infinite; transform-origin: center; transform-box: fill-box; }}
  @keyframes blink {{ 0%, 94%, 100% {{ transform: scaleY(1); }} 97% {{ transform: scaleY(0.1); }} }}
</style>
<script>
  (function () {{
    var SPEAK = {speak}, ANIMATE = {"true" if animate else "false"}, SHARE = {_FACE_SHARE[size]};
    var SCALE = {_FACE_SHARE[size] / _FACE_SHARE["large"]}, MAX_W = {_MAX_WIDTH_SHARE};
    var face = document.querySelector(".face");
    function fit() {{
      try {{
        var px = document.body.scrollHeight + "px", frame = window.frameElement;
        frame.style.height = px;
        // Streamlit's element container keeps the fallback height: resize it too.
        var box = frame.parentElement;
        if (box && box.getAttribute("data-testid") === "stElementContainer") {{ box.style.height = px; box.style.flex = "0 0 " + px; }}
      }} catch (e) {{}}
    }}
    try {{
      var p = window.parent;
      var h = Math.round(Math.min(p.innerHeight * SHARE, p.innerWidth * MAX_W * SCALE));
      if (p.innerWidth < {_NARROW_PX}) document.querySelector(".subtitles").style.fontSize = "{_NARROW_FONT_PX[size]}px";
      if (h > 40) {{ face.setAttribute("height", h); face.setAttribute("width", Math.round(h * {_VIEWBOX_W} / {_VIEWBOX_H})); }}
    }} catch (e) {{}}
    fit();
    window.addEventListener("load", fit);
    if (window.ResizeObserver) new ResizeObserver(fit).observe(document.body);
    if (!ANIMATE) return;

    var words = Array.prototype.slice.call(document.querySelectorAll(".w"));
    var mouth = document.querySelector(".mouth"), open = document.querySelector(".mouth-open");
    var done = false, timer = null, next = 0, isOpen = false;
    var talking = setInterval(function () {{
      isOpen = !isOpen;
      mouth.style.display = isOpen ? "none" : "";
      open.style.display = isOpen ? "" : "none";
    }}, {_TALK_MS});
    function finish() {{
      if (done) return;
      done = true;
      words.forEach(function (w) {{ w.style.visibility = "visible"; }});
      clearInterval(timer); clearInterval(talking);
      mouth.style.display = ""; open.style.display = "none";
    }}
    function upTo(charIndex) {{
      words.forEach(function (w, k) {{
        if (+w.dataset.i <= charIndex) {{ w.style.visibility = "visible"; next = Math.max(next, k + 1); }}
      }});
    }}
    function startTimer() {{
      if (timer || done) return;
      timer = setInterval(function () {{
        if (next >= words.length) {{ finish(); return; }}
        words[next++].style.visibility = "visible";
        if (next >= words.length) finish();
      }}, {_WORD_MS});
    }}
    if (!words.length) {{ finish(); return; }}

    var synth = null, Utterance = window.SpeechSynthesisUtterance;
    try {{ synth = window.parent.speechSynthesis; Utterance = window.parent.SpeechSynthesisUtterance; }} catch (e) {{}}
    if (!synth) {{ synth = window.speechSynthesis; Utterance = window.SpeechSynthesisUtterance; }}
    if (synth) synth.cancel();   // a new line cuts the previous one
    if (!SPEAK || !synth || !Utterance) {{ startTimer(); return; }}
    var u = new Utterance({text_js});
    u.lang = "en-US";
    var boundary = false, started = false;
    u.onstart = function () {{
      started = true;
      setTimeout(function () {{ if (!boundary) startTimer(); }}, {_BOUNDARY_WAIT_MS});
    }};
    u.onboundary = function (e) {{ boundary = true; upTo(e.charIndex); }};
    u.onend = finish;
    u.onerror = finish;
    synth.speak(u);
    // Some browsers never fire "start" (blocked audio): fall back to the timer.
    setTimeout(function () {{ if (!started) startTimer(); }}, 1500);
  }})();
</script>
"""


def _render(text: str, mood: str, size: str) -> None:
    """Draw one frame; speak and animate only when the text differs from the last one."""
    animate = st.session_state.get(_LAST_TEXT) != text
    voice_on = bool(st.session_state.get("voice_on", False))
    # st.iframe (not the deprecated components.html): same-origin, so the frame can use the
    # parent's speech synthesis and resize itself.
    st.iframe(build_html(text, mood, size, voice_on, animate=animate), height=frame_height(text, size))
    st.session_state[_LAST_TEXT] = text


def say(text: str, mood: str = "neutral", size: str = "large") -> None:
    """Draw the mascot saying `text` and read it aloud if the voice is on.

    size="large": big and centred (animates back from the side if the last mascot was small).
    size="small": the small face only; beside() uses it for the mascot column.
    """
    if size != "large":
        _render(text, mood, size)
        return
    with st.container(key="mascot_alone"):
        if st.session_state.get(_LAYOUT) == "small":
            st.html(_TO_CENTRE_CSS)
        _render(text, mood, size)
    st.session_state[_LAYOUT] = "large"


def beside(text: str, mood: str = "neutral"):
    """Mascot small on the left; returns the right column for the screen's visual.

        with mascot.beside(text, mood):
            st.plotly_chart(fig)
        # buttons go here, below both
    """
    if st.session_state.get(_LAYOUT) == "large":
        st.html(_TO_SIDE_CSS)
    mascot_col, visual_col = st.columns([1, 3], vertical_alignment="top")  # top: visible next to long lists
    with mascot_col, st.container(key="mascot_side"):
        say(text, mood, size="small")
    st.session_state[_LAYOUT] = "small"
    return visual_col.container(key="mascot_visual")


def _voice_changed() -> None:
    st.session_state["voice_on"] = not st.session_state.get("voice_on", False)
    if st.session_state["voice_on"]:
        # Turning the voice on speaks the current line at once (FRONTEND_MASCOT_LAYOUT.md 1.4).
        st.session_state.pop(_LAST_TEXT, None)


def voice_toggle() -> None:
    """Voice on/off control, fixed in the top-right corner. Draw it once per astronaut screen."""
    with st.container(key="mascot_voice"):
        # Top-right corner of the window (no Streamlit header: config.toml ui.hideTopBar).
        st.html("<style>.st-key-mascot_voice { position: fixed; top: 0.75rem; right: 1.5rem; "
                "z-index: 1000000; width: auto !important; }</style>")
        st.toggle("Voice", value=bool(st.session_state.get("voice_on", False)),
                  on_change=_voice_changed, help="The mascot reads its messages aloud.")
