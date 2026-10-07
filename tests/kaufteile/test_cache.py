import pytest

from swki.kaufteile import cache


@pytest.mark.parametrize("inhalt", [b"{kaputt", b"\xff\xfe\x00\x80", b"[1, 2]", b"42", b"null", b""])
def test_defekter_cacheeintrag_gilt_als_fehlend(tmp_path, inhalt):
    """Unlesbar, kein JSON oder kein Objekt: wie fehlend behandeln (neu aufnehmen), nie abstürzen."""
    (tmp_path / "H_B.json").write_bytes(inhalt)
    assert cache.lies(tmp_path, "H_B") is None
    assert cache.ist_aktuell(tmp_path, "H_B", "x") is False


def test_lies_fehlende_und_gueltige_datei(tmp_path):
    assert cache.lies(tmp_path, "H_B") is None
    (tmp_path / "H_B.json").write_text('{"pruefsumme": "abc", "bestanden": true}', encoding="utf-8")
    assert cache.lies(tmp_path, "H_B") == {"pruefsumme": "abc", "bestanden": True}
