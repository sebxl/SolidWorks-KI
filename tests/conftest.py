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


def nur_testauftrag(name: str) -> str:
    """Die Fixture `auftrag` löscht im echten Arbeitsordner: Ein Tippfehler im Modul darf keinen echten Auftrag treffen."""
    if not name.startswith(("LIVE-", "REF-")):
        raise ValueError(f"{name!r} ist kein Testauftrag (Präfix LIVE- oder REF-): die Fixture auftrag löscht ihn nicht")
    return name


@pytest.fixture
def auftrag(request):
    """Bestandsdateien: Auftrag `AUFTRAG` des Testmoduls im echten Arbeitsordner, vorher und nachher geleert. Module mit eigenem
    Fixture `auftrag` überschreiben dieses."""
    name = nur_testauftrag(request.module.AUFTRAG)
    pfad = lade_rechner().arbeitsordner / name
    _aufraeumen(pfad)
    yield name
    _aufraeumen(pfad)
