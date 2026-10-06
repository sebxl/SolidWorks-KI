import os

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
