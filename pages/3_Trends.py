# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Trends implementation generated with Claude Code and reviewed by Fran.
"""Trends: one card per indicator with data; clicking a card expands its chart inline. Owner: Fran.

Spec screen 4 (docs/ASTRONAUT_HEALTH_APP_SPEC.md): no separate chart page, no mascot
(AGENTS.md 8). The demo controls (advance mission, Reset demo) live in the Main Menu (#94).
Charts come from core.charts; data only through core.data and core.config (pages never read files).
"""
from datetime import datetime

import streamlit as st

from core import charts, config, data

st.title("Trends")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

astronaut = st.session_state["astronaut"]
environment = st.session_state.get("environment")

astronauts = data.load_astronauts()
names = dict(zip(astronauts["id"], astronauts["name"]))
env_name = config.load_environments().get(environment, {}).get("name", environment)
st.caption(f"{names.get(astronaut, astronaut)} · {env_name}")


def _label(info: dict, key: str) -> str:
    name = info.get("name", "")
    return key if not name or name.startswith("TODO") else name


def _valid_baseline(baseline: dict | None) -> bool:
    """AGENTS.md 5.2: a baseline is valid with n >= 2 and std > 0."""
    return baseline is not None and baseline["n"] >= 2 and baseline["std"] > 0


# One card per indicator with measurements for this astronaut, in config order.
# Test fixtures (ids starting with "_") are never shown as health content.
measured = set(data.load_measurements(astronaut=astronaut)["indicator"])
cards = {key: info for key, info in config.load_indicators().items()
         if not key.startswith("_") and key in measured}
latest_values = data.latest_values(astronaut)

st.subheader("Measurements")
if not cards:
    st.info("No measurements yet.")
for key, info in cards.items():
    unit = info.get("unit", "")
    latest = latest_values.get(key)
    summary = "no value yet" if latest is None else f"latest {latest:.1f} {unit}".rstrip()
    with st.expander(f"{_label(info, key)} · {summary}"):
        st.plotly_chart(charts.indicator_chart(astronaut, key, environment=environment),
                        key=f"trends_chart:{astronaut}:{key}")
        baseline = data.get_baseline(astronaut, key)
        z = data.z_score(astronaut, key, latest) if latest is not None else None
        col_latest, col_baseline, col_z = st.columns(3)
        col_latest.metric("Latest value", "—" if latest is None else f"{latest:.1f} {unit}")
        col_baseline.metric(
            "Personal baseline (pre-flight)",
            "—" if baseline is None else f"{baseline['mean']:.1f} ± {baseline['std']:.1f} {unit}",
            help=None if baseline is None else f"Mean ± standard deviation of {baseline['n']} pre-flight measurements.",
        )
        col_z.metric("Distance from baseline (z)", "—" if z is None else f"{z:+.1f}",
                     help="How many standard deviations the latest value is from the personal baseline.")
        if not _valid_baseline(baseline):
            st.caption("Not enough pre-flight measurements for a personal baseline yet "
                       "(at least 2, with some variation).")


# --- Alert history: every alert of this astronaut, newest first (not only this indicator) -----

STATUS_LABELS = {
    "pending_confirmation": "Waiting for the repeat measurement",
    "active": "Active: protocol in progress",
    "resolved": "Resolved",
    "monitoring": "Monitoring",
    "handed_over": "Handed over to the medical team",
    "dismissed": "False alarm: the repeat was normal",
}
problems = config.load_problems()
all_indicators = config.load_indicators()
start = datetime.fromisoformat(config.load_mission()["start"])


def _readable(value) -> str:
    return str(value or "—").replace("_", " ").capitalize()


def _problem_name(problem_id: str) -> str:
    name = problems.get(problem_id, {}).get("name", "")
    return name if name and not name.startswith("TODO") else _readable(problem_id)


def _when(iso) -> str:
    """'2027-04-03 08:00 (day 3)', or '—' when there is no time."""
    if not iso:
        return "—"
    moment = datetime.fromisoformat(iso)
    return f"{moment:%Y-%m-%d %H:%M} (day {(moment - start).days + 1})"


def _reading(indicator_id, value) -> str:
    """'Muscle strength: 390.0 N' for the measurement that raised the alert."""
    if not indicator_id:
        return "—"
    info = all_indicators.get(indicator_id, {})
    name = info.get("name", "")
    name = name if name and not name.startswith("TODO") else _readable(indicator_id)
    if value is None:
        return name
    return f"{name}: {float(value):.1f} {info.get('unit', '')}".rstrip()


st.subheader("Alert history")
st.caption("Every alert of this astronaut and what happened to it. The app guides; it does not diagnose.")
history = sorted(data.load_episodes(astronaut), key=lambda e: e.get("opened_at") or "", reverse=True)
if history:
    st.dataframe(
        [{
            "Alert": _problem_name(e.get("problem")),
            "Severity": _readable(e.get("severity")),
            "Status": STATUS_LABELS.get(e.get("status"), _readable(e.get("status"))),
            "Raised by": _reading((e.get("trigger") or {}).get("indicator"),
                                  (e.get("trigger") or {}).get("value")),
            "Opened": _when(e.get("opened_at")),
            "Closed": _when(e.get("closed_at")),
        } for e in history],
        hide_index=True,
    )
else:
    st.caption("No alerts yet for this astronaut.")

waiting = data.load_pending(astronaut)
if waiting:
    st.markdown("**Waiting alerts**")
    st.caption("Raised while another alert was open (one at a time). The most serious one is "
               "offered when the current alert closes, and it is confirmed again first.")
    st.dataframe(
        [{
            "Alert": _problem_name(p.get("problem")),
            "Severity": _readable(p.get("severity")),
            "Raised by": _reading(p.get("indicator"), p.get("value")),
            "Measured": _when(p.get("measured_at")),
        } for p in waiting],
        hide_index=True,
    )
