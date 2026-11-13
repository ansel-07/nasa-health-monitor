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
