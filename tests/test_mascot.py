# AI-assisted: generated with Claude Code and reviewed by Ansel.
import pytest

from core.mascot import build_html
from core.models import MASCOT_SIZES, MOODS


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("size", MASCOT_SIZES)
def test_every_mood_and_size_renders(mood, size):
    assert "<svg" in build_html("Hello", mood, size)


def test_text_is_escaped():
    out = build_html("<b>hi</b> there", "neutral", "large")
    assert '<span class="w" data-i="0">&lt;b&gt;hi&lt;/b&gt;</span>' in out
    assert '<span class="w" data-i="10">there</span>' in out
    assert "<b>hi</b>" not in out


def test_script_text_cannot_close_the_script():
    out = build_html("a </script><script>alert(1)</script>", voice_on=True)
    assert "</script><script>alert" not in out


def test_unknown_mood_or_size_fails():
    with pytest.raises(ValueError):
        build_html("x", "angry", "large")
    with pytest.raises(ValueError):
        build_html("x", "neutral", "huge")


def test_voice_only_when_on_and_text_is_new():
    assert "var SPEAK = false" in build_html("x", voice_on=False)
    assert "var SPEAK = true" in build_html("x", voice_on=True)
    assert "var SPEAK = false" in build_html("x", voice_on=True, animate=False)


@pytest.mark.parametrize("mood", MOODS)
def test_face_has_no_frame(mood):
    out = build_html("Hello", mood)
    assert 'fill="#111"' not in out and out.count("<rect") == 2


def test_same_text_shows_full_subtitles_without_reveal():
    assert ".w { visibility: hidden; }" in build_html("Hello there")
    still = build_html("Hello there", animate=False)
    assert ".w { visibility: visible; }" in still and "ANIMATE = false" in still


def test_subtitles_instead_of_a_bubble():
    out = build_html("Hello", "neutral", "large")
    assert 'class="subtitles"' in out and 'class="bubble"' not in out


@pytest.mark.parametrize("size", MASCOT_SIZES)
def test_frame_grows_with_long_texts(size):
    from core.mascot import frame_height
    assert frame_height("x" * 400, size) > frame_height("Hi", size)


def test_beside_returns_the_visual_column():
    from streamlit.testing.v1 import AppTest

    def script():
        import streamlit as st
        from core import mascot
        with mascot.beside("Look at this chart.", "thinking"):
            st.write("visual here")
        st.button("Below")

    app = AppTest.from_function(script).run()
    assert not app.exception
    assert app.markdown[0].value == "visual here"
    assert app.button[0].label == "Below"


def _run(script, state=None):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_function(script)
    for key, value in (state or {}).items():
        app.session_state[key] = value
    return app.run()


def _frames(app):
    """HTML of the mascot iframes drawn in the last run."""
    return [node.proto.html for node in app.get("iframe")] if app.get("iframe") else []


def _styles(app):
    return " ".join(node.proto.body for node in app.get("html"))


def test_same_text_twice_is_silent_the_second_time():
    def script():
        from core import mascot
        mascot.say("Hello there", "happy")

    app = _run(script, {"voice_on": True})
    assert app.session_state["mascot_last_text"] == "Hello there"
    app.run()
    assert not app.exception
    assert app.session_state["mascot_last_text"] == "Hello there"


def test_render_animates_only_new_text(monkeypatch):
    import streamlit as st
    from core import mascot
    calls = []
    monkeypatch.setattr(mascot.st, "iframe", lambda body, height: calls.append(body))
    st.session_state.clear()
    mascot._render("One", "neutral", "large")
    mascot._render("One", "neutral", "large")
    mascot._render("Two", "neutral", "large")
    assert ["ANIMATE = true" in body for body in calls] == [True, False, True]
    st.session_state.clear()


def test_turning_the_voice_on_clears_the_last_text():
    import streamlit as st
    from core import mascot
    st.session_state.clear()
    st.session_state["mascot_last_text"] = "Hello"
    mascot._voice_changed()
    assert st.session_state["voice_on"] is True and "mascot_last_text" not in st.session_state
    st.session_state["mascot_last_text"] = "Hello"
    mascot._voice_changed()
    assert st.session_state["voice_on"] is False and st.session_state["mascot_last_text"] == "Hello"
    st.session_state.clear()


def test_beside_moves_only_after_a_large_mascot():
    def script():
        from core import mascot
        with mascot.beside("Chart", "neutral"):
            pass

    assert "mascot-to-side" not in _styles(_run(script))
    assert "mascot-to-side" in _styles(_run(script, {"mascot_layout": "large"}))
    app = _run(script, {"mascot_layout": "large"})
    app.run()   # later reruns never replay the move
    assert "mascot-to-side" not in _styles(app)


def test_large_say_moves_back_only_after_a_small_mascot():
    def script():
        from core import mascot
        mascot.say("Alone", "neutral")

    assert "mascot-to-centre" not in _styles(_run(script))
    assert "mascot-to-centre" not in _styles(_run(script, {"mascot_layout": "large"}))
    app = _run(script, {"mascot_layout": "small"})
    assert "mascot-to-centre" in _styles(app)
    assert app.session_state["mascot_layout"] == "large"


def test_voice_toggle_is_drawn():
    def script():
        from core import mascot
        mascot.voice_toggle()

    app = _run(script)
    assert not app.exception and app.toggle[0].label == "Voice"
    app.toggle[0].set_value(True).run()
    assert app.session_state["voice_on"] is True


def test_face_is_capped_by_the_screen_width():
    """Task 8 (narrow screens): on a phone the face is limited by the width, not only the height."""
    big, small = build_html("Hi", size="large"), build_html("Hi", size="small")
    assert "MAX_W = 0.55" in big and "p.innerWidth * MAX_W * SCALE" in big
    assert "SCALE = 1.0" in big and "SCALE = 0.45" in small
