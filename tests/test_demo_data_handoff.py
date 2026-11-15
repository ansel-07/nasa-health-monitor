# AI-assisted: generated with Codex and reviewed by Edu.
"""Validate the documented synthetic scenario, not astronaut population physiology."""
import ast
from datetime import datetime, timedelta
from math import pi
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core import charts, config, data, episodes, mission, models, protocol_engine, triggers
from scripts import generate_data as generator


@pytest.fixture
def spec():
    doc = Path(__file__).resolve().parents[1] / "docs" / "DEMO_DATA_HANDOFF.md"
    block = doc.read_text(encoding="utf-8").split("## 2. Complete generator input", 1)[1].split("```python\n", 1)[1].split("```", 1)[0]
    # Parse literal assignments only; never execute documentation as Python code.
    return {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(block).body}


@pytest.fixture
def generated(spec):
    mission_config = config.load_mission()
    units = {key: info["unit"] for key, info in config.load_indicators().items()}
    args = (spec["INDICATOR_PARAMS"], spec["ANOMALIES"], mission_config["astronauts"], units,
            datetime.fromisoformat(mission_config["start"]), spec["PREFLIGHT_DAYS"],
            spec["MISSION_DAYS"], spec["SEED"], spec["MEASURE_HOUR"])
    return generator.generate(*args), args


def test_documented_parameters_are_complete_and_reproducible(spec, generated):
    frame, args = generated
    assert generator.find_todos(spec["INDICATOR_PARAMS"], spec["ANOMALIES"],
                                {"MISSION_DAYS": spec["MISSION_DAYS"], "DEMO_DAY": spec["DEMO_DAY"]}) == []
    assert generator.check_params(args[0], args[1], args[2], args[3], spec["MISSION_DAYS"]) == []
    assert generator.check_scenario(spec["MISSION_DAYS"], spec["DEMO_DAY"], spec["ANOMALIES"]) == []
    pd.testing.assert_frame_equal(frame, generator.generate(*args))
    assert len(frame) == len(args[2]) * len(args[0]) * (spec["PREFLIGHT_DAYS"] + spec["MISSION_DAYS"])
    assert not frame.duplicated(["timestamp", "astronaut", "indicator"]).any()
    # The handoff covers all channels even before Fran integrates the expanded block.
    expected = {"muscle_strength", "muscle_area", "muscle_power", "muscle_endurance",
                "muscle_tone", "muscle_stiffness"}
    expected.update(f"{name}_{eye}" for name in
                    ("peripapillary_trt", "refraction", "optic_disc_edema_grade", "visual_acuity")
                    for eye in ("left", "right"))
    assert set(spec["INDICATOR_PARAMS"]) == expected
    assert len(spec["INDICATOR_PARAMS"]) == 14
    assert np.isfinite(frame["value"]).all()
    positive = frame[frame.indicator.str.startswith("muscle_")
                     | frame.indicator.str.startswith("peripapillary_trt_")]
    assert (positive.value > 0).all()
    grades = frame[frame.indicator.str.startswith("optic_disc_edema_grade_")]
    assert (grades.value == 0).all()  # Selected grade-0 appearance, not proof that OCT edema is absent.
    endurance = frame[frame.indicator == "muscle_endurance"]
    assert (endurance.value % 1 == 0).all()
    assert (frame[frame.indicator.str.startswith("refraction_")].value < 0).all()
    assert frame[frame.indicator.str.startswith("visual_acuity_")].value.between(-.1, .1).all()
    assert set(frame["source"]) == {"simulated"}
    for indicator, rows in frame.groupby("indicator"):
        assert set(rows["unit"]) == {args[3][indicator]}
    baselines = frame[frame.phase == "preflight"].groupby(["astronaut", "indicator"]).value
    assert (baselines.count() == spec["PREFLIGHT_DAYS"]).all()
    deviations = baselines.std(ddof=1)
    ordinal = deviations.index.get_level_values("indicator").str.startswith("optic_disc_edema_grade_")
    assert (deviations[~ordinal] > 0).all()
    assert (deviations[ordinal] == 0).all()  # Raw grade rules do not require a baseline.


def test_selected_magnitudes_and_persistence_are_human_plausible(generated):
    """Study envelopes are plausibility checks, not medical normality thresholds."""
    frame, args = generated
    trt = frame[frame.indicator.str.startswith("peripapillary_trt_")]
    assert trt.value.between(272, 420).all()  # Patel 2018, BMO-250 observed preflight range.
    force = frame[frame.indicator == "muscle_strength"]
    # Dodds 2014, male age-30 10th-90th centiles; selected fictional grip profiles only.
    assert (force.value / 9.80665).between(38, 64).all()
    start = args[4]
    for astronaut, indicator, day, value in (
        ("a1", "peripapillary_trt_left", 1, 360), ("a2", "muscle_strength", 2, 390)
    ):
        after = frame[(frame.astronaut == astronaut) & (frame.indicator == indicator)
                      & (frame.phase == "mission")
                      & (frame.timestamp >= (start + timedelta(days=day-1)).isoformat())]
        assert len(after) == args[6] - day + 1
        assert (after.value == value).all()  # No scripted overnight recovery.


@pytest.mark.parametrize("indicator,low,high", [
    ("muscle_area", 10.07 - 1.41, 10.07 + 1.41),  # Hides L5 magnitude anchor, not a right-side norm.
    ("muscle_power", (177.6 - 55.7) * pi/3, (177.6 + 55.7) * pi/3),  # Laughlin torque -> power.
    ("muscle_endurance", 14.4 - 3.4, 14.4 + 3.4),  # Hillen 40% preflight 1RM task.
    ("muscle_tone", 16.28 - 3.14, 16.28 + 3.14),  # Lukas dominant rectus femoris.
    ("muscle_stiffness", 294 - 74.61, 294 + 74.61),
])
def test_added_muscle_channels_stay_near_published_magnitude_anchors(generated, indicator, low, high):
    """Chosen fixture stays near study means; cohort SDs are not medical limits or daily noise."""
    frame, _ = generated
    assert frame[frame.indicator == indicator].value.between(low, high).all()


@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_documented_data_reaches_real_confirmation_and_protocol(tmp_path, monkeypatch, spec,
                                                               generated, environment):
    frame, args = generated
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    # Use core APIs for measurement writes; preserve the real baseline/evaluator/clock.
    monkeypatch.setattr(data, "load_astronauts", lambda: pd.DataFrame({"id": args[2]}))
    for row in frame.to_dict("records"):
        data.add_measurement(row)
    start = args[4]
    assert generator.seed_clock(start, spec["DEMO_DAY"]) == start
    assert mission.now() == start
    assert set(data.load_measurements().phase) == {"preflight"}
    assert data.load_episodes() == []  # Ingesting history cannot open episodes.

    left = data.get_baseline("a1", "peripapillary_trt_left")
    right = data.get_baseline("a1", "peripapillary_trt_right")
    force = data.get_baseline("a2", "muscle_strength")
    assert left["mean"] == pytest.approx(297.8357142857)
    assert force["mean"] == pytest.approx(489.6071428571)
    assert left != right

    first = mission.advance_and_detect(24, environment)
    assert {k: first[k] for k in ("revealed", "new_alerts")} == {"revealed": 42, "new_alerts": ["a1"]}
    eye_episode = data.get_open_episode("a1")
    assert eye_episode["problem"] == "sans" and eye_episode["status"] == "pending_confirmation"
    assert eye_episode["trigger"]["indicator"] == "peripapillary_trt_left"
    assert eye_episode["symptoms"]["peripapillary_trt_left"] == "concern"
    assert eye_episode["symptoms"]["peripapillary_trt_right"] == "not_present"
    assert 360 - left["mean"] >= 55
    assert [(b["low"], b["high"]) for b in charts.threshold_bands(
        "a1", "peripapillary_trt_left", environment)] == [
        (left["mean"] + 20, left["mean"] + 55), (left["mean"] + 55, None)]

    second = mission.advance_and_detect(24, environment)
    assert {k: second[k] for k in ("revealed", "new_alerts")} == {"revealed": 42, "new_alerts": ["a2", "a3"]}
    muscle_episode = data.get_open_episode("a2")
    assert muscle_episode["problem"] == "muscle_atrophy"
    assert muscle_episode["symptoms"]["muscle_strength"] == "concern"
    assert 390 / force["mean"] < .80

    for episode, value in ((eye_episode, 360), (muscle_episode, 390)):
        pid = episode["problem"]
        indicator = episode["trigger"]["indicator"]
        wait = config.load_problems()[pid]["confirm_wait_min"]
        mission.advance(hours=wait / 60)
        repeat = dict(timestamp=mission.now().isoformat(), astronaut=episode["astronaut"],
                      indicator=indicator, value=value, unit=args[3][indicator],
                      phase="mission", source="manual")
        active = episodes.confirm(episode["id"], repeat)
        assert active["status"] == "active" and active["severity"] == "watch"
        # Evaluate a repeated observation against its own stored reference.
        assert triggers.evaluate(repeat, environment)[0]["severity"] == "watch"
        nodes = []
        for _ in range(30):
            active = protocol_engine.submit(active, None)
            if active["status"] != "active":
                break
            step = protocol_engine.current_step(active)
            nodes.append(step["id"])
            if step["type"] == "question":
                response = {"answer": "no"}
            else:
                response = {"action": "done" if step["type"] == "action" else "continue"}
            active = protocol_engine.submit(active, response)
        assert "w_priority_review" in nodes
        assert active["status"] == "monitoring" and active["severity"] == "watch"
    # New mission/manual rows never alter frozen preflight references.
    assert data.get_baseline("a1", "peripapillary_trt_left") == left
    assert data.get_baseline("a2", "muscle_strength") == force


def test_bulk_advance_attributes_sans_to_the_abnormal_indicator(tmp_path, monkeypatch, generated):
    frame, args = generated
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    monkeypatch.setattr(data, "load_astronauts", lambda: pd.DataFrame({"id": args[2]}))
    for row in frame.to_dict("records"):
        data.add_measurement(row)
    result = mission.advance_and_detect(24, "mars")
    assert {k: result[k] for k in ("revealed", "new_alerts")} == {"revealed": 42, "new_alerts": ["a1"]}
    episode = data.get_open_episode("a1")
    assert episode["trigger"]["indicator"] == "peripapillary_trt_left"
    assert episode["trigger"]["value"] == 360


def test_scripted_abnormalities_preserve_eye_and_task_identity(spec, generated):
    """Persistent scenario overrides must stay on the selected eye and force task."""
    frame, _ = generated
    scripted = spec["ANOMALIES"]
    assert {(row["astronaut"], row["indicator"]) for row in scripted} == {
        ("a1", "peripapillary_trt_left"), ("a2", "muscle_strength")}
    assert all(1 <= row["day"] <= spec["MISSION_DAYS"] for row in scripted)
    assert len({(row["astronaut"], row["indicator"], row["day"]) for row in scripted}) == len(scripted)
    # Every fictional astronaut retains a separate preflight reference per eye/site.
    preflight = frame[frame.phase == "preflight"]
    for astronaut in preflight.astronaut.unique():
        for prefix in ("peripapillary_trt", "refraction", "visual_acuity"):
            eyes = [preflight[(preflight.astronaut == astronaut)
                             & (preflight.indicator == f"{prefix}_{eye}")].value
                    for eye in ("left", "right")]
            assert all(len(values) == spec["PREFLIGHT_DAYS"] for values in eyes)
            assert not np.array_equal(eyes[0].to_numpy(), eyes[1].to_numpy())
