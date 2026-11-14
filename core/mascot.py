# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""The mascot: animated face, subtitles and voice. Owner: Ansel.

Rules: AGENTS.md, section 8. Pages call only say(), beside() and voice_toggle().

Layout (provisional, until the team's UI document): the face with its subtitles below, no
speech bubble. size="large": big and centered. beside(): small on the left, and the right
column is returned for the screen's visual (chart, protocol diagram). Buttons go below.

PLACEHOLDER LOOK: the face below (OLED-style eyes and a mouth) only exists so the
other screens can be built. Name, look and the mood-to-situation mapping are still
to be decided by the team.

Voice: browser speech synthesis (no AI service). The HTML runs inside an iframe that
Streamlit re-creates on every rerun, so it first tries the parent page's
speechSynthesis (the parent keeps the user's click activation) and falls back to its own.
Not verified yet in every browser: test it in Chrome, Edge and Firefox.
"""
import html
import json

import streamlit as st
import streamlit.components.v1 as components

from core.models import MASCOT_SIZES, MOODS

MASCOT_NAME = "TODO: mascot name"

# Mouth shape per mood (SVG path inside a 100x100 face). Placeholder.
_MOUTHS = {
    "happy": "M 30 66 Q 50 82 70 66",
    "neutral": "M 32 70 L 68 70",
    "thinking": "M 40 70 Q 50 66 62 72",
    "worried": "M 30 74 Q 50 62 70 74",
    "serious": "M 34 72 L 66 72",
}
# Eye height per mood (squinted, normal...). Placeholder.
_EYE_HEIGHT = {"happy": 14, "neutral": 20, "thinking": 12, "worried": 22, "serious": 10}

_FACE_PX = {"large": 170, "small": 80}
_FONT_PX = {"large": 19, "small": 14}
_CHARS_PER_LINE = {"large": 60, "small": 22}


def frame_height(text: str, size: str) -> int:
    """Iframe height for the face plus its subtitles, so long texts are never cut."""
    lines = max(1, -(-len(text) // _CHARS_PER_LINE[size]))  # ceil
    return _FACE_PX[size] + 34 + lines * round(_FONT_PX[size] * 1.45)


def build_html(text: str, mood: str = "neutral", size: str = "large", voice_on: bool = False) -> str:
    """HTML for one mascot frame. Separate from say() so it can be tested without Streamlit."""
    if mood not in MOODS:
        raise ValueError(f"unknown mood '{mood}', expected one of {MOODS}")
    if size not in MASCOT_SIZES:
        raise ValueError(f"unknown size '{size}', expected one of {MASCOT_SIZES}")

    face_px = _FACE_PX[size]
    eye_h = _EYE_HEIGHT[mood]
    eye_y = 42 - eye_h / 2
    font = _FONT_PX[size]
    speak = "true" if voice_on else "false"

    return f"""
<div class="mascot" style="display:flex;flex-direction:column;align-items:center;gap:10px;font-family:sans-serif;">
  <svg class="face" width="{face_px}" height="{face_px}" viewBox="0 0 100 100" role="img" aria-label="{html.escape(MASCOT_NAME)} ({mood})">
    <rect x="2" y="2" width="96" height="96" rx="20" fill="#111"/>
    <rect class="eye" x="24" y="{eye_y}" width="16" height="{eye_h}" rx="5" fill="#5ef2ff"/>
    <rect class="eye" x="60" y="{eye_y}" width="16" height="{eye_h}" rx="5" fill="#5ef2ff"/>
    <path d="{_MOUTHS[mood]}" stroke="#5ef2ff" stroke-width="5" fill="none" stroke-linecap="round"/>
  </svg>
  <div class="subtitles" style="background:rgba(0,0,0,0.72);color:#fff;border-radius:6px;padding:4px 10px;font-size:{font}px;line-height:1.45;text-align:center;max-width:92%;">
    {html.escape(text)}
  </div>
</div>
<style>
  .eye {{ animation: blink 4s infinite; transform-origin: center; transform-box: fill-box; }}
  @keyframes blink {{ 0%, 94%, 100% {{ transform: scaleY(1); }} 97% {{ transform: scaleY(0.1); }} }}
</style>
<script>
  (function () {{
    if (!{speak}) return;
    var text = {json.dumps(text)};
    var synth = null;
    try {{ synth = window.parent.speechSynthesis; }} catch (e) {{}}
    if (!synth) synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    synth.speak(u);
  }})();
</script>
"""


def say(text: str, mood: str = "neutral", size: str = "large") -> None:
    """Draw the mascot saying `text` and read it aloud if the voice is on."""
    voice_on = bool(st.session_state.get("voice_on", False))
    components.html(build_html(text, mood, size, voice_on), height=frame_height(text, size))


def beside(text: str, mood: str = "neutral"):
    """Mascot small on the left; returns the right column for the screen's visual.

        with mascot.beside(text, mood):
            st.plotly_chart(fig)
        # buttons go here, below both
    """
    mascot_col, visual_col = st.columns([1, 3], vertical_alignment="center")
    with mascot_col:
        say(text, mood, size="small")
    return visual_col


def voice_toggle() -> None:
    """Voice on/off control. Draw it once per astronaut screen."""
    st.session_state["voice_on"] = st.toggle(
        "Voice", value=bool(st.session_state.get("voice_on", False)), help="The mascot reads its messages aloud."
    )
