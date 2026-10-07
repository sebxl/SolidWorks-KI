import os

import pytest

from swki.speicher import Spitzenmessung, privat_mb


def test_privat_mb_des_eigenen_prozesses():
    assert 1 < privat_mb(os.getpid()) < 100_000


def test_spitzenmessung_mit_attrappe():
    werte = iter([100.0, 900.0, 400.0] + [300.0] * 1000)
    with Spitzenmessung(1, takt_s=0.001, messen=lambda pid: next(werte)) as s:
        while s.spitze < 900.0:
            pass
    assert s.vorher == 100.0 and s.spitze == 900.0 and 300.0 <= s.nachher <= 400.0
    assert s.als_dict() == {"vorher": 100.0, "spitze": 900.0, "nachher": s.nachher}


def test_messfehler_am_ende_ueberdeckt_den_originalfehler_nicht():
    """Ist SolidWorks tot, schlägt die letzte Messung mit OSError fehl; der Fehler des Blocks muss ankommen."""
    zaehler = iter(range(1000))

    def messen(pid):
        if next(zaehler) == 0:
            return 500.0
        raise OSError("Prozess beendet")

    with pytest.raises(RuntimeError, match="COM weg"):
        with Spitzenmessung(1, takt_s=60, messen=messen) as s:
            raise RuntimeError("COM weg")
    assert s.vorher == 500.0 and s.nachher == s.spitze == 500.0


def test_messfehler_am_ende_ohne_blockfehler_ist_still():
    zaehler = iter(range(1000))

    def messen(pid):
        if next(zaehler) == 0:
            return 500.0
        raise OSError("Prozess beendet")

    with Spitzenmessung(1, takt_s=60, messen=messen) as s:
        pass
    assert s.als_dict() == {"vorher": 500.0, "spitze": 500.0, "nachher": 500.0}
