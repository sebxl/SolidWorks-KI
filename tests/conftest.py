import shutil
import stat
from pathlib import Path

import pytest

from swki.konfig import lade_rechner


@pytest.fixture
def swki_home(tmp_path, monkeypatch):
    """Isoliertes SWKI_HOME für Tests."""
    monkeypatch.setenv("SWKI_HOME", str(tmp_path / "swki_home"))
    return tmp_path / "swki_home"


def _aufraeumen(pfad: Path) -> None:
    for p in pfad.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IWRITE)  # Bestandskopien sind schreibgeschützt
    shutil.rmtree(pfad, ignore_errors=True)


@pytest.fixture
def auftrag(request):
    """Bestandsdateien: Auftrag `AUFTRAG` des Testmoduls im echten Arbeitsordner, vorher und nachher geleert. Module mit eigenem
    Fixture `auftrag` überschreiben dieses."""
    name = request.module.AUFTRAG
    pfad = lade_rechner().arbeitsordner / name
    _aufraeumen(pfad)
    yield name
    _aufraeumen(pfad)
