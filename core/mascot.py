# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""The mascot, Lumi: animated face, subtitles and voice. Owner: Ansel.

Rules: AGENTS.md, section 8; layout: docs/FRONTEND_MASCOT_LAYOUT.md section 1.
Pages call only say(), beside() and voice_toggle(); one mascot per screen run.

- Welcome only: say(text, mood, size="large"), big and centred (35 % of the browser height).
- Alone on any other screen: say(text, mood, size="medium"), a compact assistant line: the face
  (at most 112 px) on the left of its subtitles, in a panel (docs/UI_STYLE.md).
- With a chart or flowchart: beside(text, mood), small on the left (45 % of big); the right
  column is returned for the visual. Buttons go below. Moving between layouts plays a short
  entry animation once (CSS in the parent page, keyed containers).
- Subtitles are revealed word by word (with the voice when it is on) and the mouth talks
  meanwhile, only when the text is new (session_state["mascot_last_text"]). A rerun with the
  same text shows the full subtitles at once, silently.

Face: Lumi (core/lumi.py, Ansel's design), drawn in the astronaut's health state: alarm (red)
for an urgent symptom or an episode in medical urgency; symptom (amber) for a routine symptom,
a pending alert or an open episode; nominal (blue) otherwise. The mood only names the line.

Voice: browser speech synthesis (no AI service). The HTML runs inside an iframe that
Streamlit re-creates on every rerun, so it first tries the parent page's speechSynthesis
(the parent keeps the user's click activation) and falls back to its own.
"""
import html
import json
import re

import streamlit as st

from core import lumi
from core.models import MASCOT_SIZES, MOODS

MASCOT_NAME = "Lumi"

# Lumi's face, square viewBox, drawn without its box on the page background (or the panel).
_VIEWBOX_W, _VIEWBOX_H = 200, 200
_URGENT_SEVERITIES = {"medical_urgency", "severe"}

# Fallback face heights when the parent page cannot be measured (35 % of 1080 px; 45 % of it).
_FACE_PX = {"large": 380, "medium": 104, "small": 171}
_FACE_SHARE = {"large": 0.35, "medium": 0.13, "small": 0.35 * 0.45}
_FACE_MAX_PX = {"large": 2000, "medium": 112, "small": 2000}
# Narrow screens (phones): the big face is at most 55 % of the browser width, subtitles smaller.
_MAX_WIDTH_SHARE = 0.55
_NARROW_PX, _NARROW_FONT_PX = 640, {"large": 22, "medium": 17, "small": 16}
_FONT_PX = {"large": 28, "medium": 21, "small": 17}
_CHARS_PER_LINE = {"large": 48, "medium": 60, "small": 18}
# Colours and fonts of docs/UI_STYLE.md (the iframe does not inherit the page's styles).
_TEXT, _SURFACE, _BORDER, _BACKGROUND = "#E6EDF7", "#131C2E", "#22304A", "#0B1220"
_FONT_FACES = "".join(
    f"@font-face {{ font-family: 'IBM Plex Sans'; font-weight: {weight}; "
    f"src: url('/app/static/fonts/IBMPlexSans-{name}.woff2') format('woff2'); }}"
    for weight, name in ((400, "Regular"), (500, "Medium")))
_WORD_MS, _BOUNDARY_WAIT_MS = 330, 700

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
_FADE_CSS = """<style>
@keyframes mascot-fade-in { from { opacity: 0; } to { opacity: 1; } }
{sel} { animation: mascot-fade-in 400ms ease-out; }
</style>"""
_TO_CENTRE_CSS = """<style>
@keyframes mascot-to-centre { from { transform: translateX(-37.5%) scale(0.45); } to { transform: none; } }
.st-key-mascot_alone { animation: mascot-to-centre 600ms ease-in-out; transform-origin: center top; }
""" + _REDUCED.format(sel=".st-key-mascot_alone") + "\n</style>"


def frame_height(text: str, size: str) -> int:
    """Fallback iframe height for the face plus its subtitles, so long texts are never cut.

    The frame resizes itself to its content in the browser; this is the first height.
    """
    lines = max(1, -(-len(text) // _CHARS_PER_LINE[size]))  # ceil
    text_px = lines * round(_FONT_PX[size] * 1.45)
    if size == "medium":   # face and subtitles side by side, inside a padded panel
        return max(_FACE_PX[size], text_px) + 34
    return _FACE_PX[size] + 40 + text_px


def _word_spans(text: str) -> str:
    """Each word in a hidden span with its character index (matches speech boundary events)."""
    return " ".join(f'<span class="w" data-i="{m.start()}">{html.escape(m.group())}</span>'
                    for m in re.finditer(r"\S+", text))


def health_state(astronaut: str | None) -> str:
    """Lumi's state from what the app already knows (priority: alarm > symptom > nominal)."""
    if not astronaut:
        return "nominal"
    from core import activity, config, data   # imported here: pages patch these modules in tests
    try:
        definitions = config.load_subjective_issues().get("issues", {})
        issues = [definitions.get(item["issue"], {}) for item in activity.active_issues(astronaut)]
        episode = data.get_open_episode(astronaut)
        if any(issue.get("alarm") for issue in issues) or (episode and episode.get("severity") in _URGENT_SEVERITIES):
            return "alarm"
        if issues or episode or data.load_pending(astronaut):
            return "symptom"
    except Exception:   # the face must never break a screen; errors are shown by the page
        return "nominal"
    return "nominal"


def build_html(text: str, mood: str = "neutral", size: str = "large", voice_on: bool = False,
               animate: bool = True, state: str = "nominal") -> str:
    """HTML for one mascot frame. Separate from say() so it can be tested without Streamlit.

    animate=False (same text as the last render): full subtitles at once, no voice, no talking.
    """
    if mood not in MOODS:
        raise ValueError(f"unknown mood '{mood}', expected one of {MOODS}")
    if size not in MASCOT_SIZES:
        raise ValueError(f"unknown size '{size}', expected one of {MASCOT_SIZES}")

    face_px = _FACE_PX[size]
    face_w = round(face_px * _VIEWBOX_W / _VIEWBOX_H)
    font = _FONT_PX[size]
    speak = "true" if (voice_on and animate) else "false"
    hidden = "hidden" if animate else "visible"
    # json.dumps does not escape "</", which would close the <script> early (CODE_REVIEW BUG-18).
    text_js = json.dumps(text).replace("</", "<\\/")

    row = size == "medium"
    layout = ("flex-direction:row;align-items:center;gap:22px;padding:12px 22px;"
              f"background:{_SURFACE};border:1px solid {_BORDER};border-radius:12px;"
              if row else "flex-direction:column;align-items:center;gap:14px;")
    return f"""
<div class="mascot" style="display:flex;{layout}font-family:'IBM Plex Sans',sans-serif;">
  {lumi.face_svg(state, face_w, face_px, html.escape(f"{MASCOT_NAME} ({mood})"))}
  <div class="subtitles" style="color:{_TEXT};font-weight:{500 if size == "large" else 400};font-size:{font}px;line-height:1.45;text-align:{"left" if row else "center"};max-width:{"none" if row else "92%"};flex:{"1" if row else "none"};">
    {_word_spans(text)}
  </div>
</div>
<style>
  {_FONT_FACES}
  html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
  .face {{ flex: none; }}
  .w {{ visibility: {hidden}; }}
  {lumi.face_css(_SURFACE if row else _BACKGROUND)}
</style>
<script>
  (function () {{
    var SPEAK = {speak}, ANIMATE = {"true" if animate else "false"}, SHARE = {_FACE_SHARE[size]};
    var SCALE = {_FACE_SHARE[size] / _FACE_SHARE["large"]}, MAX_W = {_MAX_WIDTH_SHARE}, MAX_PX = {_FACE_MAX_PX[size]};
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
      var h = Math.round(Math.min(p.innerHeight * SHARE, p.innerWidth * MAX_W * SCALE, MAX_PX));
      if (p.innerWidth < {_NARROW_PX}) document.querySelector(".subtitles").style.fontSize = "{_NARROW_FONT_PX[size]}px";
      if (h > 40) {{ face.setAttribute("height", h); face.setAttribute("width", Math.round(h * {_VIEWBOX_W} / {_VIEWBOX_H})); }}
    }} catch (e) {{}}
    fit();
    window.addEventListener("load", fit);
    if (window.ResizeObserver) new ResizeObserver(fit).observe(document.body);
    if (!ANIMATE) return;

    var words = Array.prototype.slice.call(document.querySelectorAll(".w"));
    var head = document.querySelector(".lumi");
    var done = false, timer = null, next = 0;
    head.classList.add("speaking");   // Lumi's LED capsule talks until the line is finished
    function finish() {{
      if (done) return;
      done = true;
      words.forEach(function (w) {{ w.style.visibility = "visible"; }});
      clearInterval(timer);
      head.classList.remove("speaking");
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
    state = health_state(st.session_state.get("astronaut"))
    st.iframe(build_html(text, mood, size, voice_on, animate=animate, state=state), height=frame_height(text, size))
    st.session_state[_LAST_TEXT] = text


def say(text: str, mood: str = "neutral", size: str = "large") -> None:
    """Draw the mascot saying `text` and read it aloud if the voice is on.

    size="large": big and centred, Welcome only (animates back from the side after a small one).
    size="medium": the compact assistant line of every other screen (fades in after a small one).
    size="small": the small face only; beside() uses it for the mascot column.
    """
    if size == "small":
        _render(text, mood, size)
        return
    with st.container(key="mascot_alone"):
        if st.session_state.get(_LAYOUT) == "small":
            st.html(_TO_CENTRE_CSS if size == "large" else _FADE_CSS.replace("{sel}", ".st-key-mascot_alone"))
        _render(text, mood, size)
    st.session_state[_LAYOUT] = size


def beside(text: str, mood: str = "neutral"):
    """Mascot small on the left; returns the right column for the screen's visual.

        with mascot.beside(text, mood):
            st.plotly_chart(fig)
        # buttons go here, below both
    """
    if st.session_state.get(_LAYOUT) == "large":
        st.html(_TO_SIDE_CSS)
    elif st.session_state.get(_LAYOUT) == "medium":
        st.html(_FADE_CSS.replace("{sel}", ".st-key-mascot_side, .st-key-mascot_visual"))
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
