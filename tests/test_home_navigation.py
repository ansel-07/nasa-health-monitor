# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Welcome and Main Menu (docs/ASTRONAUT_HEALTH_APP_SPEC.md screens 1-2), through app.py."""
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(item for item in app.button if item.label == label)


def _welcome(app, astronaut="a1", environment="iss"):
    app.button(key=f"welcome_astronaut_{astronaut}").click().run()
    app.button(key=f"welcome_environment_{environment}").click().run()
    return app


def test_welcome_starts_with_one_button_per_astronaut_and_no_dropdowns():
    app = AppTest.from_file("../app.py").run()
    assert not app.exception
    assert not app.selectbox and all(item.label != "NEXT" for item in app.button)
    labels = [item.label for item in app.button]
    assert {"Astronaut A", "Astronaut B"} <= set(labels)
    assert "International Space Station" not in labels    # environments come in step 2
    assert "astronaut" not in app.session_state


def test_astronaut_button_asks_for_the_environment_and_can_go_back():
    app = AppTest.from_file("../app.py").run()
    app.button(key="welcome_astronaut_a2").click().run()
    assert not app.exception
    assert app.session_state["astronaut"] == "a2" and app.session_state["welcome_step"] == 2
    assert "International Space Station" in [item.label for item in app.button]
    button(app, "Change astronaut").click().run()
    assert app.session_state["welcome_step"] == 1
    assert "Astronaut A" in [item.label for item in app.button]


def test_environment_button_opens_the_main_menu_with_the_chosen_context():
    app = _welcome(AppTest.from_file("../app.py").run(), "a2", "mars")
    assert not app.exception
    assert app.session_state["astronaut"] == "a2" and app.session_state["environment"] == "mars"
    labels = [item.label for item in app.button]
    assert {"Check-in", "Trends", "Tutorials"} <= set(labels)
    assert "Protocols" not in labels             # only with an active episode or pending alerts


def test_leaving_welcome_forgets_the_step():
    """Arriving at Welcome again (Change astronaut) must start at step 1. AppTest cannot click app.py's
    back button after a page switch, so this checks the state the Main Menu leaves behind."""
    app = AppTest.from_file("../app.py").run()
    app.button(key="welcome_astronaut_a1").click().run()
    assert app.session_state["welcome_step"] == 2
    app.button(key="welcome_environment_iss").click().run()
    assert "welcome_step" not in app.session_state


def test_menu_cards_open_their_screens():
    app = _welcome(AppTest.from_file("../app.py").run())
    button(app, "Tutorials").click().run()
    assert not app.exception
    assert any(item.label == "Start tutorial" for item in app.button)


def test_reset_demo_clears_check_in_session_state(monkeypatch):
    """#132: stale Check-in drafts or retries must not survive Reset demo."""
    from core import data
    monkeypatch.setattr(data, "reset_demo", lambda: None)   # no real files in this test
    app = _welcome(AppTest.from_file("../app.py").run())
    app.session_state["check_in_completion:a1:iss"] = {"level": "error", "text": "stale"}
    app.session_state["tutorial_run"] = {"kept": True}
    button(app, "Reset demo").click().run()
    assert not app.exception
    assert "check_in_completion:a1:iss" not in app.session_state
    assert app.session_state["tutorial_run"] == {"kept": True}
    assert app.session_state["astronaut"] == "a1" and app.session_state["environment"] == "iss"


def _menu():
    return _welcome(AppTest.from_file("../app.py").run())


def test_advance_error_is_shown_not_raised(monkeypatch):
    """docs/CODE_REVIEW.md BUG-1: a detection error must not crash the Main Menu."""
    from core import mission

    def fail(hours, environment):
        raise ValueError("synthetic detection failure.")
    monkeypatch.setattr(mission, "advance_and_detect", fail)
    app = _menu()
    button(app, "Advance mission 24 h").click().run()
    assert not app.exception
    assert any("could not be fully advanced" in e.value and "synthetic detection failure" in e.value
               for e in app.error)


def test_reset_error_is_shown_and_check_in_state_is_kept(monkeypatch):
    from core import data

    def fail():
        raise FileNotFoundError("no seed files")
    monkeypatch.setattr(data, "reset_demo", fail)
    app = _menu()
    app.session_state["check_in_draft:a1:iss"] = {"kept": True}
    button(app, "Reset demo").click().run()
    assert not app.exception
    assert any("could not be reset" in e.value for e in app.error)
    assert app.session_state["check_in_draft:a1:iss"] == {"kept": True}


def test_advance_success_message_mentions_recovered_rows(monkeypatch):
    from core import mission
    monkeypatch.setattr(mission, "advance_and_detect",
                        lambda hours, environment: {"revealed": 3, "new_alerts": [], "recovered": 2})
    app = _menu()
    button(app, "Advance mission 24 h").click().run()
    assert not app.exception
    assert any("3 new simulated measurement(s), 2 left from an earlier advance" in i.value for i in app.info)

