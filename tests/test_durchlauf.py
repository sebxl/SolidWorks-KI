"""swki durchlauf ohne SolidWorks: Schritte, Abbruch im richtigen Schritt, kompakte Ausgabe."""

from pathlib import Path

import pytest

from swki import durchlauf as d
from swki.cli import SwkiFehler


class _BauAbbruch(SwkiFehler):
    def __init__(self, daten):
        super().__init__("abbruch")
        self.daten = daten


@pytest.fixture
def schritte(monkeypatch):
    aufrufe = []
    import swki.compiler.bauen as cb
    import swki.pruefung.befehle as pb
    import swki.spec.befehle as sb

    monkeypatch.setattr(sb, "_validieren", lambda a: aufrufe.append("validieren") or {"gueltig": True, "hinweise": []})
    monkeypatch.setattr(sb, "_freigeben", lambda a: aufrufe.append("freigeben") or {"kopie": "x.freigegeben.yaml"})
    monkeypatch.setattr(cb, "_bauen", lambda a: aufrufe.append("bauen") or {"lauf": 3, "dauer_s": 12.0})
    monkeypatch.setattr(cb, "BauAbbruch", _BauAbbruch)
    bericht = {"bestanden": True, "maengel": [], "pruefungen": [{"id": "volumen", "ok": True}, {"id": "v", "ok": None}],
               "bilder": {"iso": "C:/l/bilder/iso.png"}, "steckbrief_text": "Zeile 1\nZeile 2"}
    monkeypatch.setattr(pb, "pruefen", lambda s, n: aufrufe.append(f"pruefen {n}") or bericht)
    monkeypatch.setattr(pb, "status", lambda s, m: {"empfehlung": "pruefer_fehlt", "text": "t"})
    return aufrufe


def test_alle_schritte_in_reihenfolge(schritte, tmp_path):
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert schritte == ["validieren", "freigeben", "bauen", "pruefen 3"]
    assert erg["schritt"] == "fertig" and erg["lauf"] == 3 and erg["pruefung"]["bestanden"] is True
    assert erg["pruefung"]["ohne_urteil"] == ["v"] and erg["pruefung"]["steckbrief"] == ["Zeile 1", "Zeile 2"]
    assert erg["pruefung"]["bilder"] == [str(Path("C:/l/bilder"))]
    assert "Prüfe Lauf 3 von a.yaml" in erg["pruefer_auftrag"] and "Prüfbericht:" in erg["pruefer_auftrag"]


def test_ohne_freigeben_kein_freigabeschritt(schritte, tmp_path):
    d.durchlauf(tmp_path / "a.yaml")
    assert "freigeben" not in schritte


def test_bauabbruch_endet_im_schritt_bauen(schritte, monkeypatch, tmp_path):
    import swki.compiler.bauen as cb

    def wirf(a):
        raise _BauAbbruch({"lauf": 4, "fehler": {"code": "X"}, "knoten": [{"id": "f1", "status": "ok"},
                                                                          {"id": "f2", "status": "fehler"}]})
    monkeypatch.setattr(cb, "_bauen", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml")
    assert erg["schritt"] == "bauen" and erg["fehler"] == {"code": "X"} and [k["id"] for k in erg["knoten"]] == ["f2"]


def test_validierfehler_endet_vor_dem_bau(schritte, monkeypatch, tmp_path):
    import swki.spec.befehle as sb

    def wirf(a):
        raise SwkiFehler("Schema: x fehlt")
    monkeypatch.setattr(sb, "_validieren", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert erg["schritt"] == "validieren" and "bauen" not in schritte


def test_pruefwert_hinweis_stoppt_vor_der_freigabe(schritte, monkeypatch, tmp_path):
    """Ein Prüfwert, der von der Rechnung aus den Features abweicht, würde nach der Freigabe eine neue Freigabe kosten."""
    import swki.spec.befehle as sb

    hinweis = {"art": "pruefwert", "pfad": "pruefung.huellquader", "meldung": "weicht ab"}
    monkeypatch.setattr(sb, "_validieren", lambda a: schritte.append("validieren") or {"gueltig": True,
                                                                                          "hinweise": [hinweis]})
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert erg["schritt"] == "validieren" and erg["pruefwerte"] == [hinweis]
    assert schritte == ["validieren"]
