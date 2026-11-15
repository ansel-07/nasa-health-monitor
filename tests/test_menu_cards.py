# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Main Menu: the Check-in card shows when a repeat measurement is waiting."""
from streamlit.testing.v1 import AppTest

from core import data, episodes


def _menu(monkeypatch, open_episode):
    monkeypatch.setattr(data, "get_open_episode", lambda astronaut: open_episode)
    monkeypatch.setattr(episodes, "get_pending", lambda astronaut: [])
    app = AppTest.from_file("../pages/5_Menu.py")
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    return app.run()


def _checkin_card(app):
    return next(b for b in app.button if b.label == "Check-in")


def test_checkin_card_is_primary_with_a_repeat_waiting(monkeypatch):
    app = _menu(monkeypatch, {"id": "ep-1", "problem": "sans", "status": "pending_confirmation"})
    assert not app.exception
    assert _checkin_card(app).proto.type == "primary"
    assert any("Repeat measurement waiting" in h.proto.body for h in app.get("html"))


def test_checkin_card_is_normal_without_a_repeat(monkeypatch):
    app = _menu(monkeypatch, None)
    assert not app.exception
    assert _checkin_card(app).proto.type == "secondary"
    assert not any("Repeat measurement waiting" in h.proto.body for h in app.get("html"))
