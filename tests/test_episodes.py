# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Episode lifecycle integration tests with synthetic rules and temporary storage."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from core import config, data, episodes, mission, models


def rule(severity="mild", indicator="x", above=10, **extra):
    return {"severity": severity, "when": {"indicator": indicator, "above": above}, **extra}


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(data, "load_indicators", lambda: {"x": {}, "y": {}})
    problems = {"problem_a": {"confirm_wait_min": 5, "triggers": [rule()]}}
    monkeypatch.setattr(config, "load_problems", lambda: problems)
    monkeypatch.setattr(config, "load_protocol", lambda problem: {"start": "first_node"})
    clock = [datetime(2027, 4, 10, 8)]
    monkeypatch.setattr(mission, "now", lambda: clock[0])
    return clock, problems


def measurement(clock, **extra):
    return {"timestamp": clock[0].isoformat(), "astronaut": "a1", "indicator": "x",
            "value": 20, "unit": "example", "phase": "mission", "source": "manual", **extra}


def open_episode(state):
    clock, _ = state
    return episodes.on_new_measurement(measurement(clock), "mars")


def repeat(state, episode, **extra):
    clock, _ = state
    clock[0] += timedelta(minutes=5)
    return episodes.confirm(episode["id"], measurement(clock, **extra))


def test_opens_complete_episode_and_persists_measurement(state):
    clock, _ = state
    m = measurement(clock)
    original = deepcopy(m)
    result = episodes.on_new_measurement(m, "mars")
    assert result == {
        "id": "ep-0001", "astronaut": "a1", "problem": "problem_a", "environment": "mars",
        "status": "pending_confirmation", "severity_initial": "mild", "severity": "mild",
        "trigger": {"indicator": "x", "value": 20, "z": None, "measured_at": clock[0].isoformat()},
        "current_node": None, "vars": {}, "answers": {}, "log": [],
        "opened_at": clock[0].isoformat(), "closed_at": None, "outcome": None,
    }
    assert data.load_episodes() == [result]
    assert len(data.load_measurements()) == 1
    assert m == original


def test_normal_measurement_is_saved_without_episode(state):
    clock, _ = state
    assert episodes.on_new_measurement(measurement(clock, value=0), "mars") is None
    assert data.load_episodes() == []
    assert len(data.load_measurements()) == 1


def test_highest_severity_opens_and_ties_follow_configuration(state):
    clock, problems = state
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule("severe")]}
    problems["problem_c"] = {"confirm_wait_min": 5, "triggers": [rule("severe")]}
    result = open_episode(state)
    assert result["problem"] == "problem_b"
    assert [p["problem"] for p in episodes.get_pending("a1")] == ["problem_c", "problem_a"]
    assert all(set(p) == {"astronaut", "problem", "severity", "indicator", "value", "z", "measured_at"}
               for p in data.load_pending())


@pytest.mark.parametrize("status", ["pending_confirmation", "active"])
def test_open_episode_keeps_severity_and_same_problem_is_not_queued(state, status):
    clock, problems = state
    episode = open_episode(state)
    episode["status"] = status
    data.save_episode(episode)
    problems["problem_a"]["triggers"].append(rule("severe"))
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule("moderate")]}
    clock[0] += timedelta(minutes=1)
    result = episodes.on_new_measurement(measurement(clock, source="protocol"), "mars")
    assert result == episode
    assert len(data.load_episodes()) == 1
    assert [p["problem"] for p in data.load_pending()] == ["problem_b"]


def test_pending_replaces_evidence_and_severity_without_affecting_other_astronauts(state):
    clock, problems = state
    open_episode(state)
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule("severe")]}
    clock[0] += timedelta(minutes=1)
    episodes.on_new_measurement(measurement(clock), "mars")
    other = {**data.load_pending()[0], "astronaut": "a2"}
    data.save_pending(data.load_pending() + [other])
    problems["problem_b"]["triggers"] = [rule("mild")]
    clock[0] += timedelta(minutes=1)
    episodes.on_new_measurement(measurement(clock, value=15), "mars")
    pending = episodes.get_pending("a1")
    assert len(pending) == 1
    assert pending[0]["severity"] == "mild"
    assert pending[0]["value"] == 15
    assert pending[0]["measured_at"] == clock[0].isoformat()
    assert data.load_pending("a2") == [other]


def test_older_pending_evidence_cannot_replace_newer(state):
    clock, problems = state
    open_episode(state)
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule()]}
    clock[0] += timedelta(minutes=2)
    episodes.on_new_measurement(measurement(clock), "mars")
    original = data.load_pending()
    episodes.on_new_measurement(measurement(clock, timestamp=(clock[0] - timedelta(minutes=1)).isoformat(), value=12), "mars")
    assert data.load_pending() == original


def test_astronauts_have_independent_open_episodes_and_unique_ids(state):
    clock, _ = state
    first = open_episode(state)
    second = episodes.on_new_measurement(measurement(clock, astronaut="a2"), "iss")
    assert first["id"] != second["id"]
    assert data.get_open_episode("a1")["id"] == first["id"]
    assert data.get_open_episode("a2")["id"] == second["id"]


@pytest.mark.parametrize("source", ["manual", "protocol", "simulated"])
def test_already_stored_new_measurement_is_evaluated_without_duplicate_csv_row(state, source):
    clock, _ = state
    m = measurement(clock, source=source)
    data.add_measurement(m)
    assert episodes.on_new_measurement(m, "mars")["status"] == "pending_confirmation"
    assert len(data.load_measurements()) == 1
    episodes.on_new_measurement(m, "mars")
    assert len(data.load_measurements()) == 1
    assert len(data.load_episodes()) == 1


def test_replaying_closed_episodes_original_measurement_does_not_reopen_it(state):
    clock, _ = state
    m = measurement(clock)
    episode = open_episode(state)
    episode.update(status="resolved", closed_at=clock[0].isoformat(), outcome="resolved")
    data.save_episode(episode)
    assert episodes.on_new_measurement(m, "mars") is None
    assert len(data.load_episodes()) == 1


def test_confirmation_activates_with_repeat_severity_and_preserves_initial_trigger(state):
    _, problems = state
    problems["problem_a"]["triggers"].append(rule("severe", above=30))
    initial = open_episode(state)
    result = repeat(state, initial, value=40)
    assert result["status"] == "active"
    assert result["severity"] == "severe"
    assert result["severity_initial"] == "mild"
    assert result["trigger"] == initial["trigger"]
    assert result["current_node"] == "first_node"
    assert result["closed_at"] is None and result["outcome"] is None
    assert data.load_episodes() == [result]
    assert len(data.load_measurements()) == 2


def test_confirmation_may_lower_severity(state):
    clock, problems = state
    problems["problem_a"]["triggers"].append(rule("severe", above=30))
    initial = episodes.on_new_measurement(measurement(clock, value=40), "mars")
    result = repeat(state, initial)
    assert result["severity_initial"] == "severe"
    assert result["severity"] == "mild"


def test_confirmation_dismisses_without_automatically_opening_pending(state):
    clock, problems = state
    initial = open_episode(state)
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule(above=-1)]}
    result = repeat(state, initial, value=0)
    assert result["status"] == "dismissed"
    assert result["closed_at"] == clock[0].isoformat()
    assert result["outcome"] is None
    assert data.get_open_episode("a1") is None
    assert [p["problem"] for p in episodes.get_pending("a1")] == ["problem_b"]
    assert len(data.load_episodes()) == 1


def test_confirm_uses_saved_environment_and_queues_other_matches(state):
    _, problems = state
    problems["problem_a"]["triggers"] = [rule(environments=["mars"])]
    initial = open_episode(state)
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule()]}
    assert repeat(state, initial)["status"] == "active"
    assert len(data.load_pending()) == 1


@pytest.mark.parametrize("extra", [{"astronaut": "a2"}, {"indicator": "y"}])
def test_wrong_repeat_leaves_storage_unchanged(state, extra):
    initial = open_episode(state)
    with pytest.raises(ValueError, match="same indicator"):
        repeat(state, initial, **extra)
    assert data.load_episodes() == [initial]
    assert len(data.load_measurements()) == 1


@pytest.mark.parametrize("minutes", [0, 4])
def test_confirmation_enforces_wait(state, minutes):
    clock, _ = state
    initial = open_episode(state)
    clock[0] += timedelta(minutes=minutes)
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(initial["id"], measurement(clock))
    assert data.load_episodes() == [initial]
    assert len(data.load_measurements()) == 1


def test_old_sample_cannot_confirm_even_after_clock_wait(state):
    clock, _ = state
    initial = open_episode(state)
    old = measurement(clock)
    clock[0] += timedelta(minutes=10)
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(initial["id"], old)


def test_wait_starts_when_episode_is_opened_not_at_original_measurement(state):
    clock, _ = state
    old_timestamp = (clock[0] - timedelta(minutes=10)).isoformat()
    initial = episodes.on_new_measurement(measurement(clock, timestamp=old_timestamp), "mars")
    clock[0] += timedelta(minutes=1)
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(initial["id"], measurement(clock))


def test_zero_wait_still_requires_newer_sample(state):
    clock, problems = state
    problems["problem_a"]["confirm_wait_min"] = 0
    initial = open_episode(state)
    with pytest.raises(ValueError, match="later than the original"):
        episodes.confirm(initial["id"], measurement(clock))
    clock[0] += timedelta(seconds=1)
    assert episodes.confirm(initial["id"], measurement(clock))["status"] == "active"


def test_duplicate_confirm_is_rejected_without_duplicate_measurement(state):
    initial = open_episode(state)
    repeat(state, initial)
    with pytest.raises(ValueError, match="pending_confirmation"):
        repeat(state, initial)
    assert len(data.load_measurements()) == 2


def test_unknown_episode_is_rejected(state):
    clock, _ = state
    with pytest.raises(ValueError, match="pending_confirmation"):
        episodes.confirm("missing", measurement(clock))


def test_get_pending_is_read_only_sorted_stably_and_available_after_closure(state):
    clock, _ = state
    initial = open_episode(state)
    items = [{"astronaut": astronaut, "problem": problem, "severity": severity}
             for astronaut, problem, severity in [
                 ("a1", "b", "mild"), ("a2", "e", "severe"),
                 ("a1", "c", "severe"), ("a1", "d", "severe"),
             ]]
    data.save_pending(items)
    initial.update(status="monitoring", outcome="monitoring", closed_at=clock[0].isoformat())
    data.save_episode(initial)
    assert [p["problem"] for p in episodes.get_pending("a1")] == ["c", "d", "b"]
    assert data.load_pending() == items
    assert data.load_episodes() == [initial]


@pytest.mark.parametrize("wait", ["TODO_EDU", None, -1, True, float("inf")])
def test_invalid_wait_does_not_save_partial_episode_or_measurement(state, wait):
    _, problems = state
    problems["problem_a"]["confirm_wait_min"] = wait
    with pytest.raises(ValueError, match="confirm_wait_min"):
        open_episode(state)
    assert data.load_episodes() == []
    assert data.load_measurements().empty


def test_missing_baseline_cannot_dismiss_original_problem(state):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"] = [{"severity": "mild", "when": {"indicator": "x", "z_above": 2}}]
    with pytest.raises(ValueError, match="baseline"):
        repeat(state, initial)
    assert data.load_episodes() == [initial]
    assert len(data.load_measurements()) == 1


@pytest.mark.parametrize("z,status", [(3, "active"), (0, "dismissed")])
def test_confirmation_evaluates_available_personal_baseline(state, monkeypatch, z, status):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"] = [{"severity": "moderate", "when": {"indicator": "x", "z_above": 2}}]
    monkeypatch.setattr(data, "z_score", lambda *args: z)
    result = repeat(state, initial)
    assert result["status"] == status
    if status == "active":
        assert result["severity"] == "moderate"


def test_already_stored_repeat_is_not_appended_twice(state):
    clock, _ = state
    initial = open_episode(state)
    clock[0] += timedelta(minutes=5)
    m = measurement(clock)
    data.add_measurement(m)
    assert episodes.confirm(initial["id"], m)["status"] == "active"
    assert len(data.load_measurements()) == 2


def test_confirmation_configuration_error_keeps_storage_unchanged(state):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"][0]["when"]["above"] = "TODO_EDU"
    with pytest.raises(ValueError, match="TODO"):
        repeat(state, initial)
    assert data.load_episodes() == [initial]
    assert len(data.load_measurements()) == 1


def test_unknown_higher_severity_blocks_understated_confirmation(state):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"].append({"severity": "severe", "when": {"indicator": "x", "z_above": 2}})
    with pytest.raises(ValueError, match="baseline"):
        repeat(state, initial)
    assert data.load_episodes() == [initial]


def test_known_higher_severity_does_not_require_lower_severity_baseline(state):
    _, problems = state
    problems["problem_a"]["triggers"] = [rule("severe")]
    initial = open_episode(state)
    problems["problem_a"]["triggers"].append({"severity": "mild", "when": {"indicator": "x", "z_above": 2}})
    assert repeat(state, initial)["severity"] == "severe"


def test_false_all_branch_allows_dismissal_despite_missing_baseline(state):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"] = [{"severity": "mild", "when": {"all": [
        {"indicator": "x", "above": 30}, {"indicator": "x", "z_above": 2},
    ]}}]
    assert repeat(state, initial)["status"] == "dismissed"


def test_true_any_branch_allows_confirmation_despite_missing_baseline(state):
    _, problems = state
    initial = open_episode(state)
    problems["problem_a"]["triggers"] = [{"severity": "mild", "when": {"any": [
        {"indicator": "x", "above": 10}, {"indicator": "x", "z_above": 2},
    ]}}]
    assert repeat(state, initial)["status"] == "active"


@pytest.mark.parametrize("extra", [
    {"phase": "preflight"}, {"timestamp": "invalid"},
    {"timestamp": "2027-04-10T08:00:00+00:00"},
    {"timestamp": "2027-04-10T09:00:00"}, {"value": float("nan")},
    {"value": True}, {"source": "unknown"}, {"unit": "TODO_EDU"},
])
def test_invalid_or_preflight_measurement_never_opens_episode(state, extra):
    clock, _ = state
    with pytest.raises(ValueError):
        episodes.on_new_measurement(measurement(clock, **extra), "mars")
    assert data.load_episodes() == []
    assert data.load_measurements().empty


def test_duplicate_open_episodes_are_reported_not_silently_modified(state):
    clock, _ = state
    initial = open_episode(state)
    data.save_episode({**initial, "id": "ep-0002"})
    with pytest.raises(ValueError, match="multiple open"):
        episodes.on_new_measurement(measurement(clock), "mars")


@pytest.mark.parametrize("operator,repeat_value,status", [
    ("at_least", 20, "active"), ("at_least", 19, "dismissed"),
    ("at_most", 20, "active"), ("at_most", 21, "dismissed"),
])
def test_inclusive_triggers_open_at_boundary_and_confirm_consistently(state, operator, repeat_value, status):
    _, problems = state
    problems["problem_a"]["triggers"] = [{
        "severity": "mild", "when": {"indicator": "x", operator: 20},
    }]
    initial = open_episode(state)
    assert initial["status"] == "pending_confirmation"
    assert initial["trigger"]["value"] == 20
    result = repeat(state, initial, value=repeat_value)
    assert result["status"] == status
    assert data.load_episodes() == [result]
    assert len(data.load_measurements()) == 2


@pytest.fixture
def pending_state(state, monkeypatch):
    clock, problems = state
    monkeypatch.setattr(config, "load_indicators", lambda: {"x": {}, "y": {}})
    data.save_pending([{
        "astronaut": "a1", "problem": "problem_a", "severity": "moderate",
        "indicator": "x", "value": 20, "z": 1.5,
        "measured_at": (clock[0] - timedelta(hours=2)).isoformat(),
    }])
    return clock, problems


def test_accept_pending_starts_new_wait_preserves_evidence_and_does_not_record_measurement(pending_state):
    clock, _ = pending_state
    item = data.load_pending()[0]
    result = episodes.accept_pending("a1", "iss")
    assert result["status"] == "pending_confirmation"
    assert result["environment"] == "iss"
    assert result["opened_at"] == clock[0].isoformat()
    assert result["severity_initial"] == result["severity"] == "moderate"
    assert result["trigger"] == {key: item[key] for key in ("indicator", "value", "z", "measured_at")}
    assert result["current_node"] is None
    assert result["vars"] == result["answers"] == {}
    assert data.load_pending() == []
    assert data.load_episodes() == [result]
    assert data.load_measurements().empty


def test_accept_pending_orders_by_severity_preserves_ties_and_other_astronauts(pending_state):
    _, problems = pending_state
    base = data.load_pending()[0]
    problems.update({key: {"confirm_wait_min": 5, "triggers": [rule()]}
                     for key in ("problem_b", "problem_c", "problem_d")})
    items = [base, {**base, "astronaut": "a2", "problem": "problem_b", "severity": "severe"},
             {**base, "problem": "problem_c", "severity": "severe"},
             {**base, "problem": "problem_d", "severity": "severe"}]
    data.save_pending(items)
    assert episodes.accept_pending("a1", "mars")["problem"] == "problem_c"
    assert data.load_pending() == items[:2] + items[3:]


@pytest.mark.parametrize("status", ["pending_confirmation", "active"])
def test_accept_pending_does_not_replace_open_episode(pending_state, status):
    existing = {"id": "ep-0007", "astronaut": "a1", "problem": "other", "status": status}
    data.save_episode(existing)
    before = data.load_pending()
    assert episodes.accept_pending("a1", "mars") == existing
    assert data.load_pending() == before
    assert data.load_episodes() == [existing]


@pytest.mark.parametrize("status", ["dismissed", "resolved", "monitoring", "handed_over"])
def test_accept_pending_after_each_closed_state(pending_state, status):
    existing = {"id": "ep-0007", "astronaut": "a1", "problem": "other", "status": status}
    data.save_episode(existing)
    result = episodes.accept_pending("a1", "mars")
    assert result["id"] == "ep-0008"
    assert result["status"] == "pending_confirmation"
    assert data.load_episodes()[0] == existing


def test_accept_pending_is_idempotent_on_repeated_click(pending_state):
    result = episodes.accept_pending("a1", "mars")
    assert episodes.accept_pending("a1", "mars") == result
    assert len(data.load_episodes()) == 1
    assert data.load_measurements().empty


def test_accept_pending_empty_or_other_astronaut_queue_returns_none(pending_state):
    before = data.load_pending()
    assert episodes.accept_pending("a2", "mars") is None
    assert data.load_pending() == before
    data.save_pending([])
    assert episodes.accept_pending("a1", "mars") is None
    assert data.load_episodes() == []


def test_accept_pending_never_promotes_fixture(pending_state):
    item = {**data.load_pending()[0], "problem": "_example", "severity": "severe"}
    data.save_pending([item])
    assert episodes.accept_pending("a1", "mars") is None
    assert data.load_pending() == [item]


def test_promoted_alert_requires_fresh_wait_and_can_then_be_confirmed(pending_state):
    clock, _ = pending_state
    result = episodes.accept_pending("a1", "mars")
    clock[0] += timedelta(minutes=1)
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(result["id"], measurement(clock))
    assert data.load_measurements().empty
    clock[0] += timedelta(minutes=4)
    confirmed = episodes.confirm(result["id"], measurement(clock))
    assert confirmed["status"] == "active"
    assert confirmed["severity"] == "mild"
    assert confirmed["severity_initial"] == "moderate"
    assert len(data.load_measurements()) == 1


def test_promoted_alert_can_be_dismissed_without_consuming_next_pending(pending_state):
    clock, problems = pending_state
    original = data.load_pending()[0]
    problems["problem_b"] = {"confirm_wait_min": 5, "triggers": [rule()]}
    other = {**original, "problem": "problem_b", "severity": "mild"}
    data.save_pending([original, other])
    promoted = episodes.accept_pending("a1", "mars")
    clock[0] += timedelta(minutes=5)
    assert episodes.confirm(promoted["id"], measurement(clock, value=0))["status"] == "dismissed"
    assert data.load_pending() == [other]
    assert episodes.accept_pending("a1", "mars")["problem"] == "problem_b"


@pytest.mark.parametrize("change", [
    {"indicator": "unknown"}, {"problem": "unknown"}, {"value": float("nan")},
    {"z": float("inf")}, {"measured_at": "invalid"}, {"measured_at": "2027-04-11T08:00:00"},
])
def test_accept_invalid_evidence_preserves_queue_and_episodes(pending_state, change):
    item = {**data.load_pending()[0], **change}
    data.save_pending([item])
    before = models.EPISODES_FILE.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        episodes.accept_pending("a1", "mars")
    assert models.EPISODES_FILE.read_text(encoding="utf-8") == before
    assert data.load_episodes() == []


def test_accept_unconfigured_wait_or_environment_keeps_alert_pending(pending_state):
    _, problems = pending_state
    before = data.load_pending()
    with pytest.raises(ValueError, match="environment"):
        episodes.accept_pending("a1", "unknown")
    problems["problem_a"]["confirm_wait_min"] = "TODO_EDU"
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.accept_pending("a1", "mars")
    assert data.load_pending() == before
    assert data.load_episodes() == []


def test_check_in_reviews_and_confirms_pending_with_real_storage(pending_state, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    from core import mascot

    clock, problems = pending_state
    problems["problem_a"]["name"] = "Synthetic alert"
    metadata = {"name": "Synthetic indicator", "unit": "example",
                "how_to_measure": "Synthetic test instructions.", "why_it_matters": "Synthetic test content."}
    monkeypatch.setattr(config, "load_indicators", lambda: {"x": metadata})
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
    data.save_episode({"id": "ep-0001", "astronaut": "a1", "problem": "other", "status": "resolved"})
    page = Path(__file__).resolve().parents[1] / "pages" / "1_Check_in.py"
    app = AppTest.from_file(str(page))
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "mars"
    app.run()
    next(b for b in app.button if b.label == "Review next alert").click().run()
    assert not app.exception
    opened = data.get_open_episode("a1")
    assert opened["id"] == "ep-0002"
    assert opened["status"] == "pending_confirmation"
    assert app.number_input[0].disabled
    assert data.load_pending() == []
    assert data.load_measurements().empty
    clock[0] += timedelta(minutes=5)
    app.run()
    app.number_input[0].set_value(20)
    next(b for b in app.button if b.label == "Confirm repeat measurement").click().run()
    assert not app.exception
    assert data.get_open_episode("a1")["status"] == "active"
    assert any(b.label == "Open Protocol" for b in app.button)
    app.run()
    assert len(data.load_episodes()) == 2
    assert len(data.load_measurements()) == 1
