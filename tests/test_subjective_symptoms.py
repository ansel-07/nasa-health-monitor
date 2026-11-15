# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Edu's subjective symptoms (docs/sintomas_subjetivos_atrofia_SANS.md) in config and screens."""
import pytest

from streamlit.testing.v1 import AppTest

from core import activity, config


def issues():
    return config.load_subjective_issues()["issues"]


def test_twelve_routine_symptoms_linked_and_five_alarms_with_actions():
    routine = {k: v for k, v in issues().items() if not v.get("alarm")}
    alarms = {k: v for k, v in issues().items() if v.get("alarm")}
    assert sorted(routine) == [f"MUS_0{i}" for i in range(1, 7)] + [f"VIS_0{i}" for i in range(1, 7)]
    assert sorted(alarms) == [f"ALM_0{i}" for i in range(1, 6)]
    checkins = config.load_checkins()
    assert all(v["check_ins"] and set(v["check_ins"]) <= set(checkins) for v in routine.values())
    assert all(v["action"] and not v["check_ins"] for v in alarms.values())
    assert all(v["question"].endswith("?") or "?" in v["question"] for v in issues().values())


def test_config_rejects_alarm_without_action(monkeypatch):
    bad = {"settings": {"persistence_days": 3, "speed_multiplier": 2},
           "issues": {"ALM_X": {"label": "X", "alarm": True, "check_ins": ["visual_acuity"]}}}
    monkeypatch.setattr(config, "load_subjective_issues", lambda include_examples=False: bad)
    errors = " | ".join(config.validate_activities(config.load_indicators(), {}))
    assert "needs an 'action'" in errors and "not linked to check-ins" in errors


def _menu(monkeypatch, active):
    monkeypatch.setattr(activity, "active_issues", lambda astronaut: active)
    app = AppTest.from_file("../pages/5_Menu.py")
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    return app.run()


@pytest.mark.parametrize("alarm_id", [f"ALM_0{i}" for i in range(1, 6)])
def test_menu_keeps_an_active_alarm_visible(monkeypatch, alarm_id):
    app = _menu(monkeypatch, [{"issue": alarm_id, "since": "2027-04-01T08:00:00", "persistent": False}])
    assert not app.exception
    assert any(issues()[alarm_id]["label"] in e.value and issues()[alarm_id]["action"] in e.value
               for e in app.error)


def test_menu_has_no_alarm_banner_for_routine_symptoms(monkeypatch):
    app = _menu(monkeypatch, [{"issue": "VIS_01", "since": "2027-04-01T08:00:00", "persistent": False}])
    assert not app.exception
    assert not app.error


@pytest.mark.parametrize("alarm_id", [f"ALM_0{i}" for i in range(1, 6)])
def test_saving_an_alarm_in_check_in_shows_the_urgent_action(monkeypatch, alarm_id):
    saved = []
    monkeypatch.setattr(activity, "active_issues", lambda astronaut: [])
    monkeypatch.setattr(activity, "report_issues", lambda astronaut, ids, source: saved.append(ids))
    app = AppTest.from_file("../pages/1_Check_in.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    app.run()
    urgent = next(box for box in app.multiselect if box.label == "Urgent symptoms you have now")
    urgent.select(alarm_id)
    next(b for b in app.button if b.label == "Save issues").click().run()
    assert not app.exception
    assert saved == [[alarm_id]]
    assert any("Urgent symptom:" in e.value and issues()[alarm_id]["action"] in e.value for e in app.error)


@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
@pytest.mark.parametrize("context", ["list", "manual_detail", "waiting_repeat"])
@pytest.mark.parametrize("alarm_id", [f"ALM_0{i}" for i in range(1, 6)])
def test_alarm_action_is_available_without_waiting_for_confirmation(
        tmp_path, monkeypatch, environment, context, alarm_id):
    from core import data, mascot, mission, models

    monkeypatch.setattr(models, "SESSION_DATA", True)
    monkeypatch.setattr(models, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(models, "_session_id", lambda: "alarm-before-confirmation")
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
    if context == "waiting_repeat":
        mission.advance_and_detect(hours=24, environment=environment)
        episode = data.get_open_episode("a1")
        assert episode is not None and episode["status"] == "pending_confirmation"
        indicator = episode["trigger"]["indicator"]
    else:
        indicator = next(iter(config.load_checkins().values()))["indicators"][0]
    checkin_id = next(key for key, item in config.load_checkins().items()
                      if indicator in item["indicators"])
    app = AppTest.from_file("../pages/1_Check_in.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = environment
    app.session_state[f"check_in_selected:a1:{environment}"] = (
        None if context == "list" else checkin_id)
    app.run()
    assert not app.exception
    if context == "waiting_repeat":
        confirm = next(b for b in app.button if b.label == "Confirm repeat measurement")
        assert confirm.disabled  # The alarm form remains usable during this wait.
    before_episodes = data.load_episodes()
    before_pending = data.load_pending()
    before_measurements = data.load_measurements().copy()
    before_clock = mission.now()
    urgent = next(box for box in app.multiselect if box.label == "Urgent symptoms you have now")
    urgent.select(alarm_id)
    next(b for b in app.button if b.label == "Save issues").click().run()
    assert not app.exception
    assert any(issues()[alarm_id]["action"] in item.value for item in app.error)
    assert any(item["issue"] == alarm_id for item in activity.active_issues("a1"))
    assert mission.now() == before_clock
    assert data.load_episodes() == before_episodes
    assert data.load_pending() == before_pending
    assert data.load_measurements().equals(before_measurements)
    # A fresh page render reads the persisted alarm; reporting does not merely flash it.
    menu = AppTest.from_file("../pages/5_Menu.py", default_timeout=30)
    menu.session_state["astronaut"] = "a1"
    menu.session_state["environment"] = environment
    menu.run()
    assert not menu.exception
    assert any(issues()[alarm_id]["action"] in item.value for item in menu.error)


def test_multiple_alarms_keep_each_symptom_and_action_in_dialogue_23(monkeypatch):
    """The supplied single-symptom template must retain every selected urgent action."""
    saved = []
    monkeypatch.setattr(activity, "active_issues", lambda astronaut: [])
    monkeypatch.setattr(activity, "report_issues", lambda astronaut, ids, source: saved.append(ids))
    app = AppTest.from_file("../pages/1_Check_in.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    app.run()
    selected = ["ALM_01", "ALM_03"]
    urgent = next(box for box in app.multiselect if box.label == "Urgent symptoms you have now")
    urgent.set_value(selected)
    next(button for button in app.button if button.label == "Save issues").click().run()
    assert not app.exception
    assert saved == [selected]
    assert len(app.error) == 1
    for issue_id in selected:
        assert issues()[issue_id]["label"] in app.error[0].value
        assert issues()[issue_id]["action"] in app.error[0].value
    assert app.error[0].value.count("Urgent symptom:") == len(selected)
