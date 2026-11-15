# AI-assisted: generated with Codex and reviewed by Edu (review pending).
"""Production content boundaries from Edu's guide/#43, using synthetic references."""
from datetime import datetime, timedelta

import pytest

from core import charts, config, data, episodes, mission, models, protocol_engine, triggers


@pytest.mark.parametrize("eye", ["left", "right"])
def test_trt_chart_uses_absolute_units_for_configured_delta(monkeypatch, eye):
    monkeypatch.setattr(data, "get_baseline", lambda *args: {"mean": 300, "std": 5, "n": 14})
    bands = charts.threshold_bands("a1", f"peripapillary_trt_{eye}", "mars")
    assert [(band["severity"], band["low"], band["high"]) for band in bands] == [
        ("watch", 320, 355), ("concern", 355, None),
    ]


@pytest.mark.parametrize("indicator,mean,std,value,level", [
    ("muscle_strength", 500, 25, 399, "concern"),
    ("muscle_strength", 500, 25, 400, "watch"),
    ("muscle_strength", 500, 25, 451, "not_present"),
    *[(f"peripapillary_trt_{eye}", 300, 5, value, level)
      for eye in ("left", "right")
      for value, level in ((319, "not_present"), (320, "watch"),
                           (354, "watch"), (355, "concern"))],
    *[(f"refraction_{eye}", 0, .1, value, level)
      for eye in ("left", "right")
      for value, level in ((.50, "not_present"), (.51, "watch"), (-.51, "not_present"))],
    *[(name, 100, 10, value, level)
      for name in ("muscle_area", "muscle_power", "muscle_endurance")
      for value, level in ((81, "not_present"), (80, "watch"), (70, "concern"))],
    *[(name, 100, 10, value, level)
      for name in ("muscle_tone", "muscle_stiffness")
      for value, level in ((80, "watch"), (120, "watch"), (70, "concern"), (130, "concern"))],
    *[(f"visual_acuity_{eye}", 0, .1, value, level)
      for eye in ("left", "right")
      for value, level in ((.2, "watch"), (.4, "concern"))],
    *[(f"optic_disc_edema_grade_{eye}", 0, 1, value, level)
      for eye in ("left", "right")
      for value, level in ((0, "not_present"), (1, "concern"))],
])
def test_configured_levels_and_state(monkeypatch, indicator, mean, std, value, level):
    monkeypatch.setattr(data, "get_baseline", lambda *args: {"mean": mean, "std": std, "n": 14})
    monkeypatch.setattr(data, "latest_values", lambda *args: {indicator: value})
    pid = "muscle_atrophy" if indicator.startswith("muscle_") else "sans"
    levels = triggers.symptom_levels(pid, "a1", "mars")
    assert levels[indicator] == level
    assert all(v == "not_present" for key, v in levels.items() if key != indicator)
    matches = triggers.evaluate({"astronaut": "a1", "indicator": indicator, "value": value}, "mars")
    assert [m["severity"] for m in matches] == ([] if level == "not_present" else ["watch"])


@pytest.mark.parametrize("pid,indicator,mean,std,value", [
    ("sans", "peripapillary_trt_left", 300, 5, 360),
    ("muscle_atrophy", "muscle_strength", 500, 25, 390),
])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
@pytest.mark.parametrize("red_flags", ["yes", "no"])
def test_real_config_detection_confirmation_protocol(tmp_path, monkeypatch, pid, indicator,
                                                    mean, std, value, environment, red_flags):
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    clock = [datetime(2027, 4, 10, 8)]
    monkeypatch.setattr(mission, "now", lambda: clock[0])
    unit = config.load_indicators()[indicator]["unit"]
    def measurement(value, at, phase="mission"):
        return dict(timestamp=at.isoformat(), astronaut="a1", indicator=indicator,
                    value=value, unit=unit, phase=phase, source="manual")
    for offset, reading in enumerate((mean-std, mean, mean+std), 1):
        data.add_measurement(measurement(reading, clock[0]-timedelta(days=offset), "preflight"))
    episode = episodes.on_new_measurement(measurement(value, clock[0]), environment)
    assert episode["problem"] == pid and episode["status"] == "pending_confirmation"
    clock[0] += timedelta(minutes=config.load_problems()[pid]["confirm_wait_min"])
    episode = episodes.confirm(episode["id"], measurement(value, clock[0]))
    assert episode["status"] == "active" and episode["severity"] == "watch"
    visited = []
    refused_review = False
    for _ in range(35):
        episode = protocol_engine.submit(episode, None)
        if episode["status"] != "active":
            break
        step = protocol_engine.current_step(episode)
        visited.append(step["id"])
        if step["type"] == "question":
            answer = red_flags if step["save_as"] == "red_flags" else "no"
            user_input = {"answer": answer}
        else:
            user_input = {"action": "done" if step["type"] == "action" else "continue"}
            if step["id"] == "u_handover" and not refused_review:
                user_input = {"action": "cannot"}
                refused_review = True
        episode = protocol_engine.submit(episode, user_input)
        if step["id"] == "u_handover" and user_input["action"] == "cannot":
            assert episode["status"] == "active" and episode["current_node"] == "u_no_clinician"
    assert episode["status"] == ("handed_over" if red_flags == "yes" else "monitoring")
    assert episode["severity"] == ("medical_urgency" if red_flags == "yes" else "watch")
    if red_flags == "no":
        assert "w_priority_review" in visited
