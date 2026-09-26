import pytest


@pytest.fixture
def swki_home(tmp_path, monkeypatch):
    """Isoliertes SWKI_HOME für Tests."""
    monkeypatch.setenv("SWKI_HOME", str(tmp_path / "swki_home"))
    return tmp_path / "swki_home"
