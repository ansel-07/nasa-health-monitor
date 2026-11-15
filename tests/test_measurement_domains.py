# AI-assisted: generated with Codex for Juan Carlos; human review pending.
"""Edu's #236 invalid representations must never consume a real alert."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from core import config, data, episodes, mission, models, protocol_engine


@pytest.fixture
def storage(tmp_path, monkeypatch):
    for name, filename in (("MEASUREMENTS_FILE", "measurements.csv"), ("EPISODES_FILE", "episodes.json")):
        monkeypatch.setattr(models, name, tmp_path / filename)
    clock = datetime(2027, 4, 2, 1)
    monkeypatch.setattr(mission, "now", lambda: clock)
    # Test domains from #245's examples; production domains remain Edu's work.
    indicators = config.load_indicators()
    for key in ("peripapillary_trt_left", "peripapillary_trt_right"):
        indicators[key].setdefault("valid", {"min": 0})
    for key in ("optic_disc_edema_grade_left", "optic_disc_edema_grade_right", "muscle_endurance"):
        indicators[key].setdefault("valid", {"min": 0, "integer": True})
    monkeypatch.setattr(config, "load_indicators", lambda: indicators)
    return clock


def reading(indicator, value, **extra):
    return {"astronaut": "a1", "indicator": indicator, "value": value,
            "unit": config.load_indicators()[indicator]["unit"],
            "timestamp": mission.now().isoformat(), "phase": "mission", "source": "manual", **extra}


def pending(indicator):
    at = (mission.now() - timedelta(hours=1)).isoformat()
    episode = {"id": "ep-0001", "astronaut": "a1", "problem": "sans", "environment": "iss",
               "status": "pending_confirmation", "severity_initial": "watch", "severity": "watch",
               "trigger": {"indicator": indicator, "value": 360, "z": None, "measured_at": at},
               "current_node": None, "vars": {}, "answers": {}, "log": [], "opened_at": at,
               "closed_at": None, "outcome": None}
    data.save_episode(episode)
    return episode


INVALID = [("peripapillary_trt_left", -1), ("peripapillary_trt_right", -1),
           ("optic_disc_edema_grade_left", .5), ("optic_disc_edema_grade_right", .5),
           ("optic_disc_edema_grade_left", -1), ("muscle_endurance", 2.5), ("muscle_endurance", -1)]


@pytest.mark.parametrize("indicator,value", INVALID)
@pytest.mark.parametrize("entry", ["manual", "protocol", "simulated", "confirm"])
def test_invalid_representation_never_changes_storage(storage, indicator, value, entry):
    episode = pending(indicator)
    before = models.EPISODES_FILE.read_bytes()
    measurement = reading(indicator, value, source="manual" if entry == "confirm" else entry)
    with pytest.raises(ValueError, match="cannot be below 0|whole number"):
        if entry == "confirm":
            episodes.confirm(episode["id"], measurement)
        else:
            episodes.on_new_measurement(measurement, "iss")
    assert models.EPISODES_FILE.read_bytes() == before
    assert not models.MEASUREMENTS_FILE.exists()
    assert data.get_open_episode("a1") == episode


@pytest.mark.parametrize("indicator", list(config.load_indicators()))
@pytest.mark.parametrize("entry", ["record", "confirm"])
def test_wrong_units_cannot_be_saved_or_confirm_an_alert(storage, indicator, entry):
    episode = pending(indicator)
    before = models.EPISODES_FILE.read_bytes()
    with pytest.raises(ValueError, match="must be entered in"):
        measurement = reading(indicator, 50, unit="wrong unit")
        if entry == "confirm":
            episodes.confirm(episode["id"], measurement)
        else:
            episodes.on_new_measurement(measurement, "iss")
    assert models.EPISODES_FILE.read_bytes() == before
    assert not models.MEASUREMENTS_FILE.exists()


@pytest.mark.parametrize("indicator,value", [("refraction_left", -1.25), ("refraction_right", -.5),
    ("visual_acuity_left", -.1), ("visual_acuity_right", -.2),
    ("optic_disc_edema_grade_left", 0), ("optic_disc_edema_grade_right", 1),
    ("muscle_endurance", 0), ("muscle_endurance", 12)])
def test_signed_vision_and_whole_counts_remain_valid(storage, indicator, value):
    episodes.on_new_measurement(reading(indicator, value), "iss")
    rows = data.load_measurements("a1", indicator)
    assert len(rows) == 1 and rows.iloc[0]["value"] == value


def test_protocol_engine_rejects_before_advancing_or_saving(storage, monkeypatch):
    episode = pending("peripapillary_trt_left")
    episode.update(status="active", current_node="measure")
    data.save_episode(episode)
    original = deepcopy(episode)
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: {
        "problem": "sans", "start": "measure", "nodes": {
            "measure": {"type": "measure", "indicator": "peripapillary_trt_left",
                        "save_as": "repeat", "next": "done"},
            "done": {"type": "end", "outcome": "resolved", "text": "Synthetic end."}}})
    with pytest.raises(ValueError, match="cannot be below 0"):
        protocol_engine.submit(episode, {"value": -1})
    assert episode == original == data.get_open_episode("a1")
    assert not models.MEASUREMENTS_FILE.exists()
