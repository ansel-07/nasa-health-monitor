# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Reusable Plotly charts. Owner: Fran.

Used by pages/3_Trends.py (full size) and by pages/1_Check_in.py (compact, next to the mascot).
Pages draw the figure with st.plotly_chart(fig). Contract: AGENTS.md, section 7.

No health threshold is written here: the bands are read from config/problems.json (Edu):
the `levels` of each symptom (watch / concern) or, for problems still in the legacy format,
their `triggers`. Thresholds still marked TODO are skipped, so a band only appears once
Edu has written its value.
"""
from datetime import datetime, timedelta
from numbers import Real

import pandas as pd
import plotly.graph_objects as go

from core import config, data, mission
from core.models import CONDITION_METRICS

# Colours of the app theme (docs/UI_STYLE.md): mission data in the cyan accent, pre-flight and
# the baseline in muted blue-grey. Severity uses the reserved status colours and always comes
# with a text label, so colour never carries the meaning alone.
MISSION_COLOR = "#5EF2FF"
PREFLIGHT_COLOR = "#7C8BA5"
BASELINE_COLOR = "#9FB0C8"
USUAL_RANGE_FILL = "rgba(124, 139, 165, 0.16)"
WARNING, SERIOUS, CRITICAL = "#FFB547", "#FF8A4C", "#FF5C5C"
GRID_COLOR = "rgba(124, 139, 165, 0.18)"
FONT_FAMILY = "'IBM Plex Sans', sans-serif"
# Symptom levels and problem states (AGENTS.md 5.3), plus the legacy severity names.
SEVERITY_COLORS = {
    "watch": WARNING, "concern": SERIOUS, "medical_urgency": CRITICAL,
    "mild": WARNING, "moderate": SERIOUS, "severe": CRITICAL,
}
# Drawing order of the bands, least serious first (more serious bands are drawn on top).
BAND_RANK = {"watch": 1, "mild": 1, "concern": 2, "moderate": 2, "severe": 3}
BAND_OPACITY = 0.12

# Condition keys that give a band: key -> (direction, is a z-score).
LOWER_KEYS, UPPER_KEYS = ("above", "at_least"), ("below", "at_most")  # bounds on the metric
Z_KEYS = ("z_above", "z_below")  # legacy form of a strict z_score bound

FULL_HEIGHT = 420
COMPACT_HEIGHT = 220
# Projector-friendly text (AGENTS.md 15: charts must read well on a projector).
FULL_FONT_SIZE = 15
COMPACT_FONT_SIZE = 14
NOW_COLOR = "#E6EDF7"


def _is_number(x) -> bool:
    return isinstance(x, Real) and not isinstance(x, bool)


def _valid_baseline(baseline: dict | None, metric: str) -> bool:
    """AGENTS.md 5.2: n >= 2 and std > 0 (and mean > 0 for baseline_fraction)."""
    if baseline is None or baseline["n"] < 2 or not baseline["std"] > 0:
        return False
    return metric != "baseline_fraction" or baseline["mean"] > 0


def _to_value(metric: str, t: float, baseline: dict | None) -> float:
    """A bound on the metric, converted to the indicator's unit (raw, fraction, delta, z)."""
    if metric == "raw":
        return t
    mu, sigma = baseline["mean"], baseline["std"]
    return {"baseline_fraction": mu * t, "baseline_delta": mu + t, "z_score": mu + t * sigma}[metric]


def _intervals(cond: dict, indicator: str, baseline: dict | None) -> list[tuple[float | None, float | None]]:
    """(low, high) value ranges, in the indicator's unit, where a simple condition is true.

    None means open-ended (to the edge of the chart). Several bounds in one condition are ANDed
    (AGENTS.md 6), so {"at_least": 20, "below": 55} is one range. abs_z_score gives two ranges,
    one on each side of the baseline. Nothing for: another indicator, compound conditions,
    unknown metrics, bounds still marked TODO, or no valid baseline (5.2) when one is needed.
    """
    if cond.get("indicator") != indicator:
        return []
    metric = cond.get("metric", "raw")
    if metric not in CONDITION_METRICS:
        return []
    keys = [k for k in LOWER_KEYS + UPPER_KEYS + Z_KEYS if k in cond]
    if not keys or not all(_is_number(cond[k]) for k in keys):
        return []
    z_bounds = any(k in Z_KEYS for k in keys)
    if (metric != "raw" or z_bounds) and not _valid_baseline(baseline, "z_score" if z_bounds and metric == "raw" else metric):
        return []
    lows = [float(cond[k]) for k in LOWER_KEYS if k in cond]
    highs = [float(cond[k]) for k in UPPER_KEYS if k in cond]

    if metric == "abs_z_score":
        mu, sigma = baseline["mean"], baseline["std"]
        a, b = (max(lows) if lows else None), (min(highs) if highs else None)
        if a is not None and b is not None and a >= b:
            return []
        if a is None:  # |z| below b: one range around the baseline
            return [(mu - b * sigma, mu + b * sigma)]
        return [(None if b is None else mu - b * sigma, mu - a * sigma),
                (mu + a * sigma, None if b is None else mu + b * sigma)]

    low_values = [_to_value(metric, t, baseline) for t in lows]
    high_values = [_to_value(metric, t, baseline) for t in highs]
    if "z_above" in cond:
        low_values.append(baseline["mean"] + cond["z_above"] * baseline["std"])
    if "z_below" in cond:
        high_values.append(baseline["mean"] + cond["z_below"] * baseline["std"])
    low = max(low_values) if low_values else None
    high = min(high_values) if high_values else None
    if low is not None and high is not None and low >= high:
        return []
    return [(low, high)]


def _applies(rule: dict, environment: str | None) -> bool:
    """Rules without `environments` always apply; the others only in those environments."""
    return "environments" not in rule or environment in rule["environments"]


def threshold_bands(astronaut: str, indicator: str, environment: str | None = None) -> list[dict]:
    """Coloured bands for this indicator, from config/problems.json.

    One item per value range of a usable rule: {"severity", "low", "high" (None = to the edge),
    "direction": "above" | "below" | "between", "value" (the bound of a one-sided band, else None),
    "problem", "symptom", "label"}. Bounds use `metric` (raw, baseline_fraction, baseline_delta,
    z_score, abs_z_score) converted with the baseline. For symptom-based problems each level rule of a symptom gives a band
    ("severity" is the level: watch / concern); problems without `symptoms` still use their
    legacy `triggers` ("severity" is mild / moderate / severe; "symptom" is None).
    Only simple conditions on this indicator count. Rules with `environments` only count when
    `environment` is in that list (never when environment is None). Sorted least serious first.
    """
    return _bands(indicator, environment, data.get_baseline(astronaut, indicator))


def _bands(indicator: str, environment: str | None, baseline: dict | None) -> list[dict]:
    """threshold_bands() with the baseline already known (the chart computes it once)."""
    bands = []

    def add(severity, cond, problem_id, symptom_id=None, symptom_name=None):
        if severity not in BAND_RANK:
            return
        label = severity.capitalize()
        if symptom_name and not symptom_name.startswith("TODO"):
            label = f"{label} · {symptom_name}"
        for low, high in _intervals(cond, indicator, baseline):
            direction = "between" if low is not None and high is not None else (
                "above" if high is None else "below")
            bands.append({"severity": severity, "low": low, "high": high, "direction": direction,
                          "value": low if direction == "above" else high if direction == "below" else None,
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


def _mission_start() -> datetime:
    return datetime.fromisoformat(config.load_mission()["start"])


def _mission_day(moment, start: datetime | None = None) -> float:
    """Mission day of a time: 1.0 at the mission start, 2.0 a day later; pre-flight is <= 0.

    Pass `start` when converting many times (one chart), so the mission file is read once.
    """
    start = _mission_start() if start is None else start
    return (pd.Timestamp(moment).to_pydatetime() - start) / timedelta(days=1) + 1


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
    bands = _bands(indicator, environment, baseline)
    start = _mission_start()
    marks = _episode_marks(astronaut, indicator)

    fig = go.Figure()
    # x = mission day (projector-friendly); the real time stays in the hover text.
    hover = f"Day %{{x:.1f}} · %{{customdata}}<br>%{{y:.1f}} {unit}<extra>%{{fullData.name}}</extra>"
    marker_size = 10 if compact else 8
    for phase, color, label in (("preflight", PREFLIGHT_COLOR, "Pre-flight"),
                                ("mission", MISSION_COLOR, "Mission")):
        part = df[df["phase"] == phase]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=[_mission_day(t, start) for t in part["timestamp"]], y=part["value"], name=label,
            mode="lines+markers", line=dict(color=color, width=2),
            marker=dict(color=color, size=marker_size),
            customdata=[t.strftime("%Y-%m-%d %H:%M") for t in part["timestamp"]],
            hovertemplate=hover,
        ))

    # Y range covering the data, the baseline and the thresholds, so bands can be drawn to the edge.
    y_values = list(df["value"]) + [v for b in bands for v in (b["low"], b["high"]) if v is not None]
    if baseline is not None:
        y_values += [baseline["mean"] - baseline["std"], baseline["mean"] + baseline["std"]]
    y_low, y_high = min(y_values), max(y_values)
    pad = (y_high - y_low) * 0.1 or max(abs(y_high) * 0.1, 1.0)
    y_low, y_high = y_low - pad, y_high + pad

    for band in bands:
        y0 = y_low if band["low"] is None else band["low"]
        y1 = y_high if band["high"] is None else band["high"]
        # A label only in the full chart. Never pass a position without a text: Plotly would
        # then draw its default label "new text" (#125).
        label = {} if compact else dict(
            annotation_text=band["label"],
            annotation_position="bottom right" if band["direction"] == "below" else "top right")
        fig.add_hrect(y0=y0, y1=y1, fillcolor=SEVERITY_COLORS[band["severity"]],
                      opacity=BAND_OPACITY, line_width=0, layer="below", **label)

    if baseline is not None:
        fig.add_hrect(y0=baseline["mean"] - baseline["std"], y1=baseline["mean"] + baseline["std"],
                      fillcolor=USUAL_RANGE_FILL, line_width=0, layer="below")
        fig.add_hline(
            y=baseline["mean"], line=dict(color=BASELINE_COLOR, width=2, dash="dash"),
            annotation_text="Your baseline", annotation_position="top left",
        )

    if marks:
        fig.add_trace(go.Scatter(
            x=[_mission_day(m["x"], start) for m in marks], y=[m["y"] for m in marks], name="Alert",
            mode="markers",
            marker=dict(symbol="x", size=12, line=dict(width=2),
                        color=[SEVERITY_COLORS.get(m["severity"], BASELINE_COLOR) for m in marks]),
            customdata=[[m["problem"], m["severity"], m["status"], m["x"].strftime("%Y-%m-%d %H:%M")]
                        for m in marks],
            hovertemplate=("Day %{x:.1f} · %{customdata[3]}<br>%{y:.1f} " + unit
                           + "<br>%{customdata[0]}: %{customdata[1]} (%{customdata[2]})<extra>Alert</extra>"),
        ))

    # Launch (mission day 1) separates pre-flight from mission; "Now" is the mission clock.
    if (df["phase"] == "preflight").any() and (df["phase"] == "mission").any():
        launch_label = {} if compact else dict(annotation_text="Launch", annotation_position="top")
        fig.add_vline(x=1, line=dict(color=BASELINE_COLOR, width=1, dash="dot"), **launch_label)
    fig.add_vline(x=_mission_day(mission.now(), start), line=dict(color=NOW_COLOR, width=1, dash="dash"),
                  annotation_text="Now", annotation_position="top")

    fig.update_yaxes(range=[y_low, y_high], title=None if compact else unit,
                     nticks=4 if compact else None, gridcolor=GRID_COLOR, zeroline=False)
    fig.update_xaxes(title="Mission day", tickformat="d", nticks=5 if compact else None,
                     gridcolor=GRID_COLOR, zeroline=False)
    fig.update_layout(
        font=dict(size=COMPACT_FONT_SIZE if compact else FULL_FONT_SIZE, family=FONT_FAMILY),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=FULL_FONT_SIZE + 1),
        title=None if compact else name,
        height=COMPACT_HEIGHT if compact else FULL_HEIGHT,
        showlegend=not compact,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
        margin=dict(l=10, r=10, t=30 if compact else 60, b=10),
    )
    return fig
