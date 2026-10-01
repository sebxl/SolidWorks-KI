from swki.compiler.handler.normbohrung import hole_werte


def test_gewinde_mit_gewindetiefe():
    assert hole_werte("gewinde", 0.012) == [0.012, -1, -1, -1, -1, -1, 2, 0, -1, -1, -1, -1]


def test_gewinde_durchgehend():
    werte = hole_werte("gewinde", None)
    assert werte[0] == -1 and werte[6] == 2 and werte[7] == 1


def test_zylinderschraube_normale_passung():
    assert hole_werte("zylinderschraube", None) == [-1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1]


def test_stift_nur_normwerte():
    assert hole_werte("stift", None) == [-1.0] * 12
