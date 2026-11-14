# AI-assisted: generated with Claude Code and reviewed by Fran.
"""reset_demo() in core/data.py. Uses temporary folders, never data/."""
import pytest

from core import data, models


@pytest.fixture
def folders(tmp_path, monkeypatch):
    """Temporary data/ and data/seed/ folders, with every data path pointing inside them."""
    data_dir = tmp_path / "data"
    seed_dir = data_dir / "seed"
    seed_dir.mkdir(parents=True)
    monkeypatch.setattr(models, "DATA_DIR", data_dir)
    monkeypatch.setattr(models, "SEED_DIR", seed_dir)
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", data_dir / "measurements.csv")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", data_dir / "astronauts.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", data_dir / "episodes.json")
    return data_dir, seed_dir


def test_reset_restores_seed_files(folders):
    data_dir, seed_dir = folders
    (seed_dir / "episodes.json").write_text('{"episodes": [], "pending": []}\n')
    (seed_dir / "measurements.csv").write_text(
        "timestamp,astronaut,indicator,value,unit,phase,source\n"
        "2027-03-01T08:00:00,a1,heart_rate,60,bpm,preflight,simulated\n"
    )

    # The demo changes the runtime data...
    data.reset_demo()
    data.save_episode({"id": "ep-0001", "astronaut": "a1", "status": "active"})
    data.add_measurement({"timestamp": "2027-04-10T08:00:00", "astronaut": "a1",
                          "indicator": "heart_rate", "value": 120, "unit": "bpm",
                          "phase": "mission", "source": "manual"})
    assert len(data.load_episodes()) == 1
    assert len(data.load_measurements()) == 2

    # ...and Reset demo brings back the clean copy.
    data.reset_demo()
    assert data.load_episodes() == []
    assert list(data.load_measurements()["value"]) == [60.0]
    for seed_file in seed_dir.iterdir():
        assert (data_dir / seed_file.name).read_bytes() == seed_file.read_bytes()


def test_reset_keeps_files_not_in_seed(folders):
    data_dir, seed_dir = folders
    (seed_dir / "episodes.json").write_text('{"episodes": [], "pending": []}\n')
    (data_dir / "notes.txt").write_text("keep me")
    data.reset_demo()
    assert (data_dir / "notes.txt").read_text() == "keep me"
    assert seed_dir.is_dir()


def test_reset_without_seed_files_fails(folders):
    with pytest.raises(FileNotFoundError):
        data.reset_demo()


def test_real_seed_folder_has_every_data_file():
    """The repository seed must contain a clean copy of each runtime data file."""
    for path in (models.MEASUREMENTS_FILE, models.ASTRONAUTS_FILE, models.EPISODES_FILE):
        assert (models.SEED_DIR / path.name).is_file()
