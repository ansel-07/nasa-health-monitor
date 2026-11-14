# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Edu's subjective symptoms (docs/sintomas_subjetivos_atrofia_SANS.md) in config and screens."""
from streamlit.testing.v1 import AppTest

from core import activity, config


def issues():
    return config.load_subjective_issues()["issues"]


def test_twelve_routine_symptoms_linked_and_four_alarms_with_actions():
    routine = {k: v for k, v in issues().items() if not v.get("alarm")}
    alarms = {k: v for k, v in issues().items() if v.get("alarm")}
    assert sorted(routine) == [f"MUS_0{i}" for i in range(1, 7)] + [f"VIS_0{i}" for i in range(1, 7)]
    assert sorted(alarms) == [f"ALM_0{i}" for i in range(1, 5)]
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


def test_menu_keeps_an_active_alarm_visible(monkeypatch):
    app = _menu(monkeypatch, [{"issue": "ALM_02", "since": "2027-04-01T08:00:00", "persistent": False}])
    assert not app.exception
    assert any("Urgent symptom: New distortion in the centre of vision" in e.value for e in app.error)


def test_menu_has_no_alarm_banner_for_routine_symptoms(monkeypatch):
    app = _menu(monkeypatch, [{"issue": "VIS_01", "since": "2027-04-01T08:00:00", "persistent": False}])
    assert not app.exception
    assert not app.error


def test_saving_an_alarm_in_check_in_shows_the_urgent_action(monkeypatch):
    saved = []
    monkeypatch.setattr(activity, "active_issues", lambda astronaut: [])
    monkeypatch.setattr(activity, "report_issues", lambda astronaut, ids, source: saved.append(ids))
    app = AppTest.from_file("../pages/1_Check_in.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    app.run()
    urgent = next(box for box in app.multiselect if box.label == "Urgent symptoms you have now")
    urgent.select("ALM_01")
    next(b for b in app.button if b.label == "Save issues").click().run()
    assert not app.exception
    assert saved == [["ALM_01"]]
    assert any("Urgent symptom reported" in e.value and "crew medical officer" in e.value for e in app.error)
