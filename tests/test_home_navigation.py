# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Button navigation from the Home (no sidebar menu), through app.py."""
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_home_has_the_navigation_buttons_and_no_back_button():
    app = AppTest.from_file("../app.py").run()
    assert not app.exception
    labels = [item.label for item in app.button]
    assert {"Start check-in", "View history", "Reset demo"} <= set(labels)
    assert "← Back to Home" not in labels


def test_view_history_opens_trends():
    # AppTest runs the target page directly (not through app.py), so the "Back to Home"
    # button added by app.py is checked manually in the browser, not here.
    app = AppTest.from_file("../app.py").run()
    button(app, "View history").click().run()
    assert not app.exception
    assert any(item.value == "Trends" for item in app.title)
