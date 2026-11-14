# AI-assisted: generated with Codex and reviewed by Edu (review pending).
"""Validate the documented synthetic scenario, not astronaut population physiology."""
import ast
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core import charts, config, data, episodes, mission, models, protocol_engine, triggers
from scripts import generate_data as generator


@pytest.fixture
def spec():
    doc = Path(__file__).resolve().parents[1] / "docs" / "DEMO_DATA_HANDOFF.md"
    block = doc.read_text(encoding="utf-8").split("```python\n", 1)[1].split("```", 1)[0]
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
    assert np.isfinite(frame["value"]).all() and (frame["value"] > 0).all()
    assert set(frame["source"]) == {"simulated"}
    for indicator, rows in frame.groupby("indicator"):
        assert set(rows["unit"]) == {args[3][indicator]}
    baselines = frame[frame.phase == "preflight"].groupby(["astronaut", "indicator"]).value
    assert (baselines.count() == spec["PREFLIGHT_DAYS"]).all()
    assert (baselines.std(ddof=1) > 0).all()


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
    assert force["mean"] == pytest.approx(518.75)
    assert left != right

    first = mission.advance_and_detect(24, environment)
    assert {k: first[k] for k in ("revealed", "new_alerts")} == {"revealed": 9, "new_alerts": ["a1"]}
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
    assert {k: second[k] for k in ("revealed", "new_alerts")} == {"revealed": 9, "new_alerts": ["a2"]}
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
