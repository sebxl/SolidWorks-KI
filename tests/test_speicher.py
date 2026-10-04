import os

from swki.speicher import privat_mb


def test_privat_mb_des_eigenen_prozesses():
    assert 1 < privat_mb(os.getpid()) < 100_000
