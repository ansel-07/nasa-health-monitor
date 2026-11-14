# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Welcome and Main Menu (docs/ASTRONAUT_HEALTH_APP_SPEC.md screens 1-2), through app.py."""
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_welcome_has_no_default_choice_and_next_is_disabled():
    app = AppTest.from_file("../app.py").run()
    assert not app.exception
    assert [box.value for box in app.selectbox] == [None, None]
    assert button(app, "NEXT").disabled
    app.selectbox[0].select("a1").run()
    assert button(app, "NEXT").disabled          # only one of the two chosen


def test_next_opens_the_main_menu_with_the_chosen_context():
    app = AppTest.from_file("../app.py").run()
    app.selectbox[0].select("a2").run()
    app.selectbox[1].select("mars").run()
    assert not button(app, "NEXT").disabled
    button(app, "NEXT").click().run()
    assert not app.exception
    assert app.session_state["astronaut"] == "a2" and app.session_state["environment"] == "mars"
    labels = [item.label for item in app.button]
    assert {"Check-in", "Trends", "Tutorials"} <= set(labels)
    assert "Protocols" not in labels             # only with an active episode or pending alerts


def test_menu_cards_open_their_screens():
    app = AppTest.from_file("../app.py").run()
    app.selectbox[0].select("a1").run()
    app.selectbox[1].select("iss").run()
    button(app, "NEXT").click().run()
    button(app, "Tutorials").click().run()
    assert not app.exception
    assert any(item.value == "Tutorials" for item in app.title)


def test_reset_demo_clears_check_in_session_state(monkeypatch):
    """#132: stale Check-in drafts or retries must not survive Reset demo."""
    from core import data
    monkeypatch.setattr(data, "reset_demo", lambda: None)   # no real files in this test
    app = AppTest.from_file("../app.py").run()
    app.selectbox[0].select("a1").run()
    app.selectbox[1].select("iss").run()
    button(app, "NEXT").click().run()
    app.session_state["check_in_completion:a1:iss"] = {"level": "error", "text": "stale"}
    app.session_state["tutorial_run"] = {"kept": True}
    button(app, "Reset demo").click().run()
    assert not app.exception
    assert "check_in_completion:a1:iss" not in app.session_state
    assert app.session_state["tutorial_run"] == {"kept": True}
    assert app.session_state["astronaut"] == "a1" and app.session_state["environment"] == "iss"
