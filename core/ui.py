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
  gap: 0.35rem 1.1rem; font-family: {MONO}; font-size: 0.78rem; letter-spacing: 0.08em;
  text-transform: uppercase; color: {MUTED}; padding-right: 7.5rem; }}
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
