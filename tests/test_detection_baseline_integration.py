# AI-assisted: generated with Codex and reviewed by Juan Carlos.
"""Detection integration with real CSV/JSON storage and personal baseline math.

All values, rules and protocols here are synthetic test fixtures, not health
content. Only paths and the mission clock are replaced; core functions run
their actual implementations, including the configuration loaders.
"""
import json
from datetime import datetime, timedelta

import pytest

from core import config, data, episodes, mission, models, triggers


SIGNAL = "synthetic_signal"
OTHER = "synthetic_other"
PROBLEM = "synthetic_problem"


@pytest.fixture
def integration(tmp_path, monkeypatch, request):
    config_dir = tmp_path / "config"
    protocols_dir = config_dir / "protocols"
    protocols_dir.mkdir(parents=True)
    direction = getattr(request, "param", "z_above")
    sign = 1 if direction == "z_above" else -1
    indicators = {
        indicator: {"name": indicator, "unit": "test units", "how_to_measure": "Test input.",
                    "why_it_matters": "Synthetic test fixture.", "source": "none"}
        for indicator in (SIGNAL, OTHER)
    }
    problems = {}
    for problem, indicator in ((PROBLEM, SIGNAL), ("synthetic_other_problem", OTHER)):
        problems[problem] = {
            "name": problem, "confirm_wait_min": 5, "protocol": f"protocols/{problem}.json",
            "triggers": [
                {"severity": "mild", "when": {"indicator": indicator, direction: sign * 2}},
                {"severity": "moderate", "when": {"indicator": indicator, direction: sign * 3}},
            ], "source": "none",
        }
        (protocols_dir / f"{problem}.json").write_text(json.dumps({
            "problem": problem, "start": "first_step", "nodes": {
                "first_step": {"type": "info", "text": "Synthetic protocol step.", "next": "end"},
                "end": {"type": "end", "text": "Synthetic end.", "outcome": "resolved"},
            },
        }), encoding="utf-8")
    for filename, content in (("indicators.json", indicators), ("problems.json", problems)):
        (config_dir / filename).write_text(json.dumps(content), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    clock = [datetime(2027, 4, 10, 8)]
    monkeypatch.setattr(mission, "now", lambda: clock[0])
    return clock, sign


def measurement(clock, value, astronaut="a1", indicator=SIGNAL):
    return {"timestamp": clock[0].isoformat(), "astronaut": astronaut, "indicator": indicator,
            "value": value, "unit": "test units", "phase": "mission", "source": "manual"}


def seed_preflight(clock, values=(8, 10, 12), astronaut="a1", indicator=SIGNAL):
    for index, value in enumerate(values):
        data.add_measurement({
            **measurement(clock, value, astronaut, indicator), "phase": "preflight", "source": "simulated",
            "timestamp": (clock[0] - timedelta(days=10) + timedelta(hours=index)).isoformat(),
        })


@pytest.mark.parametrize("integration", ["z_above", "z_below"], indirect=True)
@pytest.mark.parametrize("repeat_delta,status,severity", [
    (8, "active", "moderate"), (6, "active", "mild"),
    (0, "dismissed", "mild"), (4, "dismissed", "mild"),
])
def test_personal_z_score_opens_and_confirms_or_dismisses(integration, repeat_delta, status, severity):
    clock, sign = integration
    seed_preflight(clock)
    baseline = {"mean": 10.0, "std": 2.0, "n": 3}
    assert data.get_baseline("a1", SIGNAL) == baseline
    assert data.load_episodes() == []

    initial = measurement(clock, 10 + sign * 6)
    # At z=+/-3 the moderate threshold is not crossed: comparisons are strict.
    assert triggers.evaluate(initial, "mars") == [{
        "problem": PROBLEM, "severity": "mild", "indicator": SIGNAL,
        "value": initial["value"], "z": sign * 3.0,
    }]
    opened = episodes.on_new_measurement(initial, "mars")
    assert opened["status"] == "pending_confirmation"
    assert opened["trigger"]["z"] == sign * 3.0
    assert opened["severity_initial"] == "mild"
    assert data.get_open_episode("a1") == opened

    clock[0] += timedelta(minutes=5)
    repeated = measurement(clock, 10 + sign * repeat_delta)
    assert data.z_score("a1", SIGNAL, repeated["value"]) == pytest.approx(sign * repeat_delta / 2)
    result = episodes.confirm(opened["id"], repeated)
    assert result["status"] == status
    assert result["severity"] == severity
    assert result["severity_initial"] == "mild"
    assert result["trigger"] == opened["trigger"]
    assert data.load_episodes() == [result]
    assert data.load_pending() == []
    assert data.get_baseline("a1", SIGNAL) == baseline
    assert len(data.load_measurements(phase="mission")) == 2
    assert len(data.load_measurements(phase="preflight")) == 3
    if status == "active":
        assert result["current_node"] == config.load_protocol(PROBLEM)["start"]
        assert data.get_open_episode("a1") == result
        assert result["closed_at"] is None
    else:
        assert data.get_open_episode("a1") is None
        assert result["closed_at"] == clock[0].isoformat()


def test_same_value_uses_each_astronauts_own_baseline(integration):
    clock, _ = integration
    seed_preflight(clock)
    seed_preflight(clock, (14, 16, 18), astronaut="a2")
    assert data.z_score("a1", SIGNAL, 16) == 3.0
    assert data.z_score("a2", SIGNAL, 16) == 0.0
    first = episodes.on_new_measurement(measurement(clock, 16), "mars")
    assert episodes.on_new_measurement(measurement(clock, 16, astronaut="a2"), "mars") is None
    assert data.get_open_episode("a2") is None
    clock[0] += timedelta(minutes=5)
    assert episodes.confirm(first["id"], measurement(clock, 16))["status"] == "active"
    assert [e["astronaut"] for e in data.load_episodes()] == ["a1"]
    assert data.get_baseline("a2", SIGNAL) == {"mean": 16.0, "std": 2.0, "n": 3}


def test_each_indicator_uses_its_own_preflight_measurements(integration):
    clock, _ = integration
    seed_preflight(clock)
    seed_preflight(clock, (14, 16, 18), indicator=OTHER)
    assert episodes.on_new_measurement(measurement(clock, 16, indicator=OTHER), "mars") is None
    result = episodes.on_new_measurement(measurement(clock, 16), "mars")
    assert result["problem"] == PROBLEM
    assert result["trigger"]["z"] == 3.0
    assert data.get_baseline("a1", OTHER) == {"mean": 16.0, "std": 2.0, "n": 3}
    assert data.load_pending() == []


def test_simulated_history_does_not_open_episodes_or_change_baseline(integration):
    clock, _ = integration
    seed_preflight(clock)
    data.add_measurement({
        **measurement(clock, 100), "source": "simulated",
        "timestamp": (clock[0] - timedelta(hours=1)).isoformat(),
    })
    assert data.load_episodes() == []
    assert episodes.on_new_measurement(measurement(clock, 10), "mars") is None
    assert data.load_episodes() == []
    assert data.get_baseline("a1", SIGNAL) == {"mean": 10.0, "std": 2.0, "n": 3}


def test_real_baseline_confirmation_still_enforces_wait(integration):
    clock, _ = integration
    seed_preflight(clock)
    opened = episodes.on_new_measurement(measurement(clock, 16), "mars")
    clock[0] += timedelta(minutes=4)
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(opened["id"], measurement(clock, 18))
    assert data.get_open_episode("a1") == opened
    assert len(data.load_measurements(phase="mission")) == 1
    clock[0] += timedelta(minutes=1)
    assert episodes.confirm(opened["id"], measurement(clock, 18))["status"] == "active"


@pytest.mark.parametrize("values", [(), (10,), (10, 10, 10)])
def test_unavailable_or_zero_variance_baseline_does_not_trigger(integration, values):
    clock, _ = integration
    seed_preflight(clock, values)
    assert data.z_score("a1", SIGNAL, 16) is None
    assert episodes.on_new_measurement(measurement(clock, 16), "mars") is None
    assert data.load_episodes() == []
    assert len(data.load_measurements(phase="mission")) == 1
