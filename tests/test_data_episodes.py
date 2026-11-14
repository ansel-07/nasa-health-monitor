# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Episodes and pending list in core/data.py. Uses a temporary file, never data/."""
import json

import pytest

from core import data, models


@pytest.fixture
def episodes_file(tmp_path, monkeypatch):
    """Redirect data/episodes.json to a temporary file (not created yet)."""
    path = tmp_path / "episodes.json"
    monkeypatch.setattr(models, "EPISODES_FILE", path)
    return path


def episode(id_, astronaut="a1", status="active", problem="problem_1"):
    return {"id": id_, "astronaut": astronaut, "problem": problem, "status": status,
            "severity": "mild", "vars": {}, "answers": {}, "log": []}


def pending(astronaut="a1", problem="problem_2"):
    return {"astronaut": astronaut, "problem": problem, "severity": "mild",
            "indicator": "sleep_hours", "value": 5.0, "z": -2.3,
            "measured_at": "2027-04-10T08:00:00"}


def test_missing_or_empty_file(episodes_file):
    assert data.load_episodes() == []
    assert data.load_pending() == []
    assert data.get_open_episode("a1") is None
    episodes_file.write_text("")
    assert data.load_episodes() == []


def test_save_episode_creates_then_replaces(episodes_file):
    data.save_episode(episode("ep-0001"))
    data.save_episode(episode("ep-0002", astronaut="a2"))
    data.save_episode({**episode("ep-0001"), "status": "resolved"})

    episodes = data.load_episodes()
    assert [e["id"] for e in episodes] == ["ep-0001", "ep-0002"]
    assert episodes[0]["status"] == "resolved"


def test_save_episode_requires_id(episodes_file):
    with pytest.raises(ValueError):
        data.save_episode({"astronaut": "a1"})


def test_load_episodes_filters_by_astronaut(episodes_file):
    data.save_episode(episode("ep-0001", astronaut="a1"))
    data.save_episode(episode("ep-0002", astronaut="a2"))
    assert [e["id"] for e in data.load_episodes("a2")] == ["ep-0002"]
    assert len(data.load_episodes()) == 2


def test_get_open_episode(episodes_file):
    data.save_episode(episode("ep-0001", status="resolved"))
    data.save_episode(episode("ep-0002", status="dismissed"))
    data.save_episode(episode("ep-0003", astronaut="a2", status="active"))
    assert data.get_open_episode("a1") is None

    data.save_episode(episode("ep-0004", status="pending_confirmation"))
    assert data.get_open_episode("a1")["id"] == "ep-0004"
    data.save_episode({**episode("ep-0004"), "status": "active"})
    assert data.get_open_episode("a1")["status"] == "active"


def test_save_pending_replaces_whole_list_and_keeps_episodes(episodes_file):
    data.save_episode(episode("ep-0001"))
    data.save_pending([pending("a1"), pending("a2")])
    assert len(data.load_pending()) == 2
    assert [p["astronaut"] for p in data.load_pending("a2")] == ["a2"]

    data.save_pending([pending("a3")])
    assert [p["astronaut"] for p in data.load_pending()] == ["a3"]
    assert [e["id"] for e in data.load_episodes()] == ["ep-0001"]


def test_file_format_matches_contract(episodes_file):
    data.save_episode(episode("ep-0001"))
    data.save_pending([pending()])
    content = json.loads(episodes_file.read_text(encoding="utf-8"))
    assert set(content) == {"episodes", "pending"}
    assert not list(episodes_file.parent.glob(".episodes-*.tmp"))
