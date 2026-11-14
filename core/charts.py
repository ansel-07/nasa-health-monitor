# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Reusable Plotly charts. Owner: Fran.

Used by pages/3_Trends.py (full size) and by pages/1_Check_in.py (compact, next to the mascot).
Pages draw the figure with st.plotly_chart(fig). Contract: AGENTS.md, section 7.

No health threshold is written here: the bands are read from config/problems.json (Edu):
the `levels` of each symptom (watch / concern) or, for problems still in the legacy format,
their `triggers`. Thresholds still marked TODO are skipped, so a band only appears once
Edu has written its value.
"""
from numbers import Real

import pandas as pd
import plotly.graph_objects as go

from core import config, data

# Colours (dataviz reference palette). Severity uses the reserved status colours and
# always comes with a text label, so colour never carries the meaning alone.
MISSION_COLOR = "#2a78d6"
PREFLIGHT_COLOR = "#9e9c97"
BASELINE_COLOR = "#7a7974"
USUAL_RANGE_FILL = "rgba(158, 156, 151, 0.15)"
WARNING, SERIOUS, CRITICAL = "#fab219", "#ec835a", "#d03b3b"
# Symptom levels and problem states (AGENTS.md 5.3), plus the legacy severity names.
SEVERITY_COLORS = {
    "watch": WARNING, "concern": SERIOUS, "medical_urgency": CRITICAL,
    "mild": WARNING, "moderate": SERIOUS, "severe": CRITICAL,
}
# Drawing order of the bands, least serious first (more serious bands are drawn on top).
BAND_RANK = {"watch": 1, "mild": 1, "concern": 2, "moderate": 2, "severe": 3}
BAND_OPACITY = 0.12

# Condition keys that give a band: key -> (direction, is a z-score).
THRESHOLD_KEYS = {
    "above": ("above", False), "at_least": ("above", False), "z_above": ("above", True),
    "below": ("below", False), "at_most": ("below", False), "z_below": ("below", True),
}

FULL_HEIGHT = 420
COMPACT_HEIGHT = 220


def _is_number(x) -> bool:
    return isinstance(x, Real) and not isinstance(x, bool)


def _thresholds(cond: dict, indicator: str, baseline: dict | None) -> list[tuple[str, float]]:
    """(direction, value) for each numeric threshold of a simple condition on this indicator.

    z thresholds become values with the baseline; TODO values and compound conditions
    (all / any / count_at_least) give nothing.
    """
    if cond.get("indicator") != indicator:
        return []
    found = []
    for key, (direction, is_z) in THRESHOLD_KEYS.items():
        threshold = cond.get(key)
        if not _is_number(threshold):
            continue
        if is_z:
            if baseline is None or baseline["std"] == 0:
                continue
            threshold = baseline["mean"] + threshold * baseline["std"]
        found.append((direction, float(threshold)))
    return found


def _applies(rule: dict, environment: str | None) -> bool:
    """Rules without `environments` always apply; the others only in those environments."""
    return "environments" not in rule or environment in rule["environments"]


def threshold_bands(astronaut: str, indicator: str, environment: str | None = None) -> list[dict]:
    """Coloured bands for this indicator, from config/problems.json.

    One item per usable rule: {"severity", "direction": "above" | "below", "value", "problem",
    "symptom", "label"}. For symptom-based problems each level rule of a symptom gives a band
    ("severity" is the level: watch / concern); problems without `symptoms` still use their
    legacy `triggers` ("severity" is mild / moderate / severe; "symptom" is None).
    Only simple conditions on this indicator count. Rules with `environments` only count when
    `environment` is in that list (never when environment is None). Sorted least serious first.
    """
    baseline = data.get_baseline(astronaut, indicator)
    bands = []

    def add(severity, cond, problem_id, symptom_id=None, symptom_name=None):
        if severity not in BAND_RANK:
            return
        label = severity.capitalize()
        if symptom_name and not symptom_name.startswith("TODO"):
            label = f"{label} · {symptom_name}"
        for direction, value in _thresholds(cond, indicator, baseline):
            bands.append({"severity": severity, "direction": direction, "value": value,
                          "problem": problem_id, "symptom": symptom_id, "label": label})

    for problem_id, problem in config.load_problems().items():
        if "symptoms" in problem:
            for symptom_id, symptom in problem["symptoms"].items():
                for rule in symptom.get("levels", []):
                    if _applies(rule, environment):
                        add(rule.get("level"), rule.get("when", {}), problem_id,
                            symptom_id, symptom.get("name"))
        else:  # TRANSITION: legacy format (AGENTS.md 5.3)
            for trigger in problem.get("triggers", []):
                if _applies(trigger, environment):
                    add(trigger.get("severity"), trigger.get("when", {}), problem_id)
    return sorted(bands, key=lambda b: BAND_RANK[b["severity"]])


def _episode_marks(astronaut: str, indicator: str) -> list[dict]:
    """Episodes opened by a measurement of this indicator (where the trigger happened)."""
    marks = []
    for episode in data.load_episodes(astronaut):
        trigger = episode.get("trigger") or {}
        if trigger.get("indicator") != indicator or not _is_number(trigger.get("value")):
            continue
        measured_at = pd.to_datetime(trigger.get("measured_at"), errors="coerce")
        if pd.isna(measured_at):
            continue
        marks.append({
            "x": measured_at,
            "y": float(trigger["value"]),
            "severity": episode.get("severity_initial") or episode.get("severity"),
            "status": episode.get("status", ""),
            "problem": episode.get("problem", ""),
        })
    return marks


def _empty_figure(message: str, compact: bool) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5,
                       xref="paper", yref="paper", font=dict(size=13 if compact else 15))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=COMPACT_HEIGHT if compact else FULL_HEIGHT,
                      margin=dict(l=10, r=10, t=10, b=10))
    return fig


def indicator_chart(astronaut: str, indicator: str, compact: bool = False,
                    environment: str | None = None) -> go.Figure:
    """One indicator over time: personal baseline, severity bands and episode marks.

    Full size (Trends): pre-flight and mission measurements, legend, band labels.
    compact=True (Check-in): mission measurements only, smaller, no legend.
    environment: the current environment (st.session_state["environment"]); adds the bands of
    triggers that only apply there. None: only bands valid in every environment.
    """
    info = config.load_indicators().get(indicator, {})
    name = info.get("name", indicator)
    unit = info.get("unit", "")

    df = data.load_measurements(astronaut=astronaut, indicator=indicator)
    if compact and (df["phase"] == "mission").any():
        df = df[df["phase"] == "mission"]
    if df.empty:
        return _empty_figure("No measurements yet", compact)

    baseline = data.get_baseline(astronaut, indicator)
    bands = threshold_bands(astronaut, indicator, environment)
    marks = _episode_marks(astronaut, indicator)

    fig = go.Figure()
    hover = f"%{{x|%Y-%m-%d %H:%M}}<br>%{{y:.1f}} {unit}<extra>%{{fullData.name}}</extra>"
    for phase, color, label in (("preflight", PREFLIGHT_COLOR, "Pre-flight"),
                                ("mission", MISSION_COLOR, "Mission")):
        part = df[df["phase"] == phase]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["timestamp"], y=part["value"], name=label, mode="lines+markers",
            line=dict(color=color, width=2), marker=dict(color=color, size=8),
            hovertemplate=hover,
        ))

    # Y range covering the data, the baseline and the thresholds, so bands can be drawn to the edge.
    y_values = list(df["value"]) + [b["value"] for b in bands]
    if baseline is not None:
        y_values += [baseline["mean"] - baseline["std"], baseline["mean"] + baseline["std"]]
    y_low, y_high = min(y_values), max(y_values)
    pad = (y_high - y_low) * 0.1 or max(abs(y_high) * 0.1, 1.0)
    y_low, y_high = y_low - pad, y_high + pad

    for band in bands:
        y0, y1 = (band["value"], y_high) if band["direction"] == "above" else (y_low, band["value"])
        fig.add_hrect(
            y0=y0, y1=y1, fillcolor=SEVERITY_COLORS[band["severity"]], opacity=BAND_OPACITY,
            line_width=0, layer="below",
            annotation_text=None if compact else band["label"],
            annotation_position="top right" if band["direction"] == "above" else "bottom right",
        )

    if baseline is not None:
        fig.add_hrect(y0=baseline["mean"] - baseline["std"], y1=baseline["mean"] + baseline["std"],
                      fillcolor=USUAL_RANGE_FILL, line_width=0, layer="below")
        fig.add_hline(
            y=baseline["mean"], line=dict(color=BASELINE_COLOR, width=2, dash="dash"),
            annotation_text="Your baseline", annotation_position="top left",
        )

    if marks:
        fig.add_trace(go.Scatter(
            x=[m["x"] for m in marks], y=[m["y"] for m in marks], name="Alert",
            mode="markers",
            marker=dict(symbol="x", size=12, line=dict(width=2),
                        color=[SEVERITY_COLORS.get(m["severity"], BASELINE_COLOR) for m in marks]),
            customdata=[[m["problem"], m["severity"], m["status"]] for m in marks],
            hovertemplate=("%{x|%Y-%m-%d %H:%M}<br>%{y:.1f} " + unit
                           + "<br>%{customdata[0]}: %{customdata[1]} (%{customdata[2]})<extra>Alert</extra>"),
        ))

    fig.update_yaxes(range=[y_low, y_high], title=None if compact else unit,
                     nticks=4 if compact else None)
    fig.update_xaxes(nticks=4 if compact else None)
    fig.update_layout(
        title=None if compact else name,
        height=COMPACT_HEIGHT if compact else FULL_HEIGHT,
        showlegend=not compact,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
        margin=dict(l=10, r=10, t=10 if compact else 60, b=10),
    )
    return fig
