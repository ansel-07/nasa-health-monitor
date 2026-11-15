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
    expected = (f"This needs urgent attention. You've reported {issues()[alarm_id]['label']}. "
                f"Here's what to do: {issues()[alarm_id]['action']}")
    assert [e.value for e in app.error] == [expected]


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
    assert app.error[0].value.count("This needs urgent attention.") == len(selected)
