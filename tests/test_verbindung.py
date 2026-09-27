import math

from swki.verbindung import grad, in_mm, in_mm3, jahr_aus_revision, mm, wert


def test_jahr_aus_revision():
    assert jahr_aus_revision("33.2.0") == 2025
    assert jahr_aus_revision("34.0.1") == 2026


def test_einheiten():
    assert mm(1000) == 1.0
    assert in_mm(0.02) == 20.0
    assert in_mm3(1.2e-4) == 120000.0
    assert grad(180) == math.pi


def test_wert():
    assert wert(lambda: 5) == 5
    assert wert(5) == 5


def test_com_hilfen():
    import pythoncom

    from swki.verbindung import byref_bool, byref_str, byref_variant, r8_array

    a = r8_array([1, 2.5, -3])
    assert a.varianttype == pythoncom.VT_ARRAY | pythoncom.VT_R8 and a.value == [1.0, 2.5, -3.0]
    assert byref_bool().varianttype == pythoncom.VT_BYREF | pythoncom.VT_BOOL
    assert byref_variant().varianttype == pythoncom.VT_BYREF | pythoncom.VT_VARIANT
    assert byref_str().varianttype == pythoncom.VT_BYREF | pythoncom.VT_BSTR
