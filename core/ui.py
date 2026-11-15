# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared look of every screen: global styles and the mission status bar. Owner: Ansel.

Style rules: docs/UI_STYLE.md. The theme (colours, IBM Plex fonts) is in .streamlit/config.toml;
this module only adds what the theme cannot express.
"""
import html
from datetime import datetime
from numbers import Real

import streamlit as st

from core import config, data, mission

# Palette (docs/UI_STYLE.md); the same values as .streamlit/config.toml.
BACKGROUND, SURFACE, BORDER = "#0B1220", "#131C2E", "#22304A"
TEXT, MUTED, ACCENT = "#E6EDF7", "#7C8BA5", "#5EF2FF"
NORMAL, WATCH, URGENCY = "#3DDC97", "#FFB547", "#FF5C5C"
MONO = "'IBM Plex Mono', monospace"

_CSS = f"""<style>
/* Centred app column, like a native app window. */
[data-testid="stMainBlockContainer"] {{ max-width: 1100px; margin: 0 auto;
  padding: 1.25rem 2rem 3rem; }}
/* Section labels (st.subheader): small, monospaced, upper case; never a page title. */
[data-testid="stHeadingWithActionElements"] h3, h3 {{ font-family: {MONO}; font-size: 0.8rem;
  font-weight: 500; letter-spacing: 0.12em; text-transform: uppercase; color: {MUTED};
  padding: 1.25rem 0 0.25rem; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}
/* Data reads as data: numbers and captions of metrics in the monospaced face. */
[data-testid="stMetricValue"] {{ font-family: {MONO}; }}
[data-testid="stMetricLabel"] p {{ font-family: {MONO}; font-size: 0.75rem; letter-spacing: 0.08em;
  text-transform: uppercase; color: {MUTED}; }}
[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 0.5rem;
  padding: 0.75rem 1rem; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}
/* Primary buttons are cyan: dark text keeps them readable on a projector. */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p {{
  color: {BACKGROUND} !important; font-weight: 600; }}
[data-testid="stBaseButton-primary"]:disabled, [data-testid="stBaseButton-primaryFormSubmit"]:disabled,
[data-testid="stBaseButton-primary"]:disabled p, [data-testid="stBaseButton-primaryFormSubmit"]:disabled p {{
  color: {MUTED} !important; }}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
  background: {SURFACE}; }}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
  border-color: {ACCENT}; }}
[data-testid="stExpander"] details {{ background: {SURFACE}; }}
[data-testid="stExpander"] summary p {{ font-weight: 500; }}
/* Urgent alerts pulse a few times, then stay still. */
@keyframes ui-pulse {{ 0%, 100% {{ box-shadow: 0 0 0 0 rgba(255, 92, 92, 0); }}
  50% {{ box-shadow: 0 0 0 6px rgba(255, 92, 92, 0.25); }} }}
[data-testid="stAlertContentError"] {{ border-radius: 0.5rem; }}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {{ animation: ui-pulse 1.6s ease-in-out 3;
  border-radius: 0.5rem; }}
/* New content fades in (screen changes); nothing moves for people who ask for less motion. */
@keyframes ui-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
[data-testid="stElementContainer"], [data-testid="stVerticalBlock"] {{ animation: ui-fade 220ms ease-out; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
/* Mission status bar. */
.ui-status {{ display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center;
  gap: 0.35rem 0.9rem; font-family: {MONO}; font-size: 0.74rem; white-space: nowrap; letter-spacing: 0.08em;
  text-transform: uppercase; color: {MUTED}; padding-right: 6.5rem; }}
.ui-status b {{ color: {TEXT}; font-weight: 500; }}
.ui-status .ui-live {{ width: 0.5rem; height: 0.5rem; border-radius: 50%; background: {NORMAL};
  box-shadow: 0 0 0 3px rgba(61, 220, 151, 0.18); }}
.ui-footnote {{ font-family: {MONO}; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: {MUTED}; text-align: center; padding-top: 1.5rem; }}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 0.75rem 1rem 2rem; }}
  .ui-status {{ justify-content: flex-start; padding-right: 0; padding-top: 2.25rem; }}
}}
</style>"""


def styles() -> None:
    """Global styles; app.py draws them once per run, before the page."""
    st.html(_CSS)


def format_delay(minutes) -> str | None:
    """One-way signal delay for the status bar: '<1 S', '1 S', '22 MIN'; None if unknown."""
    if not isinstance(minutes, Real) or isinstance(minutes, bool) or minutes < 0:
        return None
    seconds = minutes * 60
    if seconds < 1:
        return "<1 S"
    if seconds < 60:
        return f"{round(seconds)} S"
    return f"{round(minutes):d} MIN"


def status_items(astronaut_name: str, environment: dict, now: datetime, start: datetime) -> list[tuple[str, str]]:
    """(label, value) pairs of the mission status bar, in display order."""
    items = [("", astronaut_name), ("", environment.get("name", "")),
             ("Mission day", str((now - start).days + 1)), ("", f"{now:%Y-%m-%d %H:%M}")]
    delay = format_delay(environment.get("comm_delay_min"))
    if delay:
        items.append(("One-way delay", delay))
    return items


def status_bar(astronaut: str, environment: str) -> None:
    """Mission status line (astronaut, environment, day, mission time, signal delay)."""
    names = dict(zip(*[data.load_astronauts()[column] for column in ("id", "name")]))
    items = status_items(names.get(astronaut, astronaut), config.load_environments().get(environment, {}),
                         mission.now(), datetime.fromisoformat(config.load_mission()["start"]))
    spans = "".join(f"<span>{html.escape(label) + ' ' if label else ''}<b>{html.escape(value)}</b></span>"
                    for label, value in items)
    st.html(f'<div class="ui-status" role="status"><span class="ui-live" aria-hidden="true"></span>{spans}</div>')


def footnote(text: str) -> None:
    """Small centred line at the foot of a screen (e.g. the Welcome's prototype notice)."""
    st.html(f'<div class="ui-footnote">{html.escape(text)}</div>')


# --- Cards -------------------------------------------------------------------------------------

def _card_css(key: str, primary: bool) -> str:
    sel = f".st-key-{key}"
    edge = ACCENT if primary else BORDER
    glow = "box-shadow: 0 0 0 1px rgba(94, 242, 255, 0.35), 0 0 24px rgba(94, 242, 255, 0.12);" if primary else ""
    return f"""<style>
{sel} {{ position: relative; background: {SURFACE}; border: 1px solid {edge}; border-radius: 0.75rem;
  padding: 1rem 1.1rem 0.9rem; gap: 0.35rem; min-height: 8.5rem; transition: border-color 150ms, transform 150ms; {glow} }}
{sel}:hover {{ border-color: {ACCENT}; transform: translateY(-1px); }}
{sel} [data-testid="stVerticalBlock"], {sel} [data-testid="stElementContainer"] {{ position: static; }}
/* The whole card is the button: the real button covers it, its own label hidden. */
{sel} [data-testid="stButton"] {{ position: absolute; inset: 0; z-index: 2; margin: 0; }}
{sel} [data-testid="stButton"] button {{ width: 100%; height: 100%; opacity: 0; cursor: pointer; }}
{sel} [data-testid="stButton"] button:focus-visible {{ opacity: 1; background: transparent;
  outline: 2px solid {ACCENT}; color: transparent; }}
{sel} .ui-card-title {{ font-size: 1.15rem; font-weight: 600; color: {TEXT}; }}
{sel} .ui-card-status {{ font-family: {MONO}; font-size: 0.75rem; letter-spacing: 0.06em;
  text-transform: uppercase; color: {MUTED}; }}
{sel} [data-testid="stMarkdownContainer"] p {{ margin: 0; }}
{sel} [data-testid="stMarkdownContainer"] p span {{ color: {ACCENT}; font-size: 1.6rem; line-height: 1.2; }}
{sel} [data-testid="stProgressBarTrack"] {{ background: {BORDER}; }}
</style>"""


def level_color(level: int) -> str:
    """Colour of an activity bar (time since completion, not health): full, half, low."""
    return NORMAL if level >= 80 else WATCH if level >= 40 else URGENCY


def card(key: str, label: str, icon: str, status: str = "", level: int | None = None,
         primary: bool = False) -> bool:
    """A clickable card: Material icon, label, a status line and an optional activity bar.

    The whole card is one button whose label is `label` (what screen readers and tests see).
    Returns True when clicked.
    """
    box = f"ui_card_{key}".replace(":", "_")
    with st.container(key=box):
        st.html(_card_css(box, primary))
        st.markdown(f":material/{icon}:")
        st.html(f'<div class="ui-card-title">{html.escape(label)}</div>'
                + (f'<div class="ui-card-status">{html.escape(status)}</div>' if status else ""))
        if level is not None:
            st.html(f"<style>.st-key-{box} [data-testid='stProgressBarTrack'] > div "
                    f"{{ background-color: {level_color(level)}; }}</style>")
            st.progress(level)
        return st.button(label, key=key, type="primary" if primary else "secondary")


# --- Data tiles --------------------------------------------------------------------------------

_BAND_TONES = {"watch": WATCH, "mild": WATCH, "concern": "#FF8A4C", "moderate": "#FF8A4C",
               "medical_urgency": URGENCY, "severe": URGENCY}


def band_status(bands: list[dict], value: float | None) -> dict | None:
    """The most serious band (charts.threshold_bands, Edu's rules) that contains `value`."""
    if value is None:
        return None
    inside = [band for band in bands
              if (band["low"] is None or value >= band["low"]) and (band["high"] is None or value <= band["high"])]
    return inside[-1] if inside else None   # bands are sorted least serious first


def chip(text: str, tone: str = MUTED) -> None:
    """A small status label; colour always comes with the words."""
    st.html(f'<span style="display:inline-block;font-family:{MONO};font-size:0.72rem;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{tone};border:1px solid {tone};border-radius:999px;'
            f'padding:0.15rem 0.6rem;">{html.escape(text)}</span>')


def indicator_tiles(astronaut: str, indicator: str, unit: str, environment: str | None) -> None:
    """Latest value, personal baseline and distance from it, plus the band it falls in.

    Presentation only: the numbers come from core.data and the bands from config/ (Edu).
    """
    from core import charts   # charts imports plotly; keep it out of the status bar's path

    latest = data.latest_values(astronaut).get(indicator)
    baseline = data.get_baseline(astronaut, indicator)
    valid = baseline is not None and baseline["n"] >= 2 and baseline["std"] > 0
    band = band_status(charts.threshold_bands(astronaut, indicator, environment), latest)
    if band:
        chip(band["label"], _BAND_TONES.get(band["severity"], WATCH))
    elif latest is not None and not valid:
        chip("No valid pre-flight baseline yet")
    latest_col, baseline_col, delta_col = st.columns(3)
    latest_col.metric("Latest", "—" if latest is None else f"{latest:.1f} {unit}")
    baseline_col.metric("Baseline", f"{baseline['mean']:.1f} {unit}" if valid else "—")
    if valid and latest is not None:
        z = (latest - baseline["mean"]) / baseline["std"]
        delta_col.metric("From baseline", f"{latest - baseline['mean']:+.1f} {unit}", f"z {z:+.1f}",
                         delta_color="off")
    else:
        delta_col.metric("From baseline", "—")
