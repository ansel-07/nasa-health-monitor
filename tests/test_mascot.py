# AI-assisted: generated with Claude Code and reviewed by Ansel.
import pytest

from core.mascot import build_html
from core.models import MASCOT_SIZES, MOODS


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("size", MASCOT_SIZES)
def test_every_mood_and_size_renders(mood, size):
    assert "<svg" in build_html("Hello", mood, size)


def test_text_is_escaped():
    out = build_html("<b>hi</b>", "neutral", "large")
    assert "&lt;b&gt;hi&lt;/b&gt;" in out


def test_unknown_mood_or_size_fails():
    with pytest.raises(ValueError):
        build_html("x", "angry", "large")
    with pytest.raises(ValueError):
        build_html("x", "neutral", "huge")


def test_voice_only_when_on():
    assert "if (!false) return;" in build_html("x", voice_on=False)
    assert "if (!true) return;" in build_html("x", voice_on=True)


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
