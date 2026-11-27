"""Abschnitt „Zeichnung“ im Bericht (Z1.4 Task 5): Prüfbericht, Prüfer-Urteil, ZEICHNUNGSPRUEFER_FEHLT."""

from swki.pruefung.bericht import bericht_markdown

LAEUFE = [{"lauf": 2, "bau": "ok", "code_maengel": 0, "pruefer": "bestanden", "offen": 0, "dauer_s": 9.4}]
PRUEFBERICHT = {"bestanden": True, "maengel": [], "pdf": "C:/l/zeichnung/a.pdf", "lauf": 2,
                "ist": {"sha256_slddrw": "abc"}, "pruefungen": [{"id": "vollstaendig", "ok": True}, {"id": "lesbarkeit", "ok": None}],
                "nicht_geprueft": ["lesbarkeit"], "meldungen": ["M1"]}


def _md(zeichnung):
    return bericht_markdown({"name": "Platte"}, "A-1", LAEUFE, ("bestanden", "Lauf 2 bestanden: Bericht schreiben"),
                            {"maengel": [], "bilder": {}}, {"bestanden": True, "maengel": []}, None, [],
                            zeichnung=zeichnung)


def test_ohne_zeichnung_kein_abschnitt():
    assert "## Zeichnung" not in _md(None)


def test_ohne_urteil_zeichnungspruefer_fehlt_und_status_ungeprueft():
    md = _md({"pruefbericht": PRUEFBERICHT, "urteil": None})
    assert "## Zeichnung" in md and "ZEICHNUNGSPRUEFER_FEHLT" in md
    assert "Zeichnung ungeprüft" in md.split("\n")[2]   # Statuszeile
    assert "C:/l/zeichnung/a.pdf" in md and "lesbarkeit" in md


def test_mit_urteil_listet_maengel_und_status_nicht_ungeprueft():
    urteil = {"sha256_slddrw": "abc", "bestanden": False, "maengel": [{"knoten": ["bohrung1"], "regel": "Z-TOL-1", "beschreibung": "Toleranz fehlt"}]}
    md = _md({"pruefbericht": PRUEFBERICHT, "urteil": urteil})
    assert "ZEICHNUNGSPRUEFER_FEHLT" not in md and "Zeichnung ungeprüft" not in md
    assert "bohrung1: Toleranz fehlt" in md and "Z-TOL-1" in md


def test_maschinelle_maengel_stehen_im_abschnitt():
    pb = {**PRUEFBERICHT, "bestanden": False,
          "maengel": [{"pruefung": "toleranzen", "regel": "Z-TOL-2", "merkmal": "m3", "text": "Ⓔ an Abmaß"}]}
    md = _md({"pruefbericht": pb, "urteil": {"bestanden": True, "maengel": [], "sha256_slddrw": "abc"}})
    assert "Z-TOL-2" in md and "Ⓔ an Abmaß" in md


def test_urteil_zu_anderer_zeichnung_ist_veraltet():
    for urteil in ({"bestanden": True, "maengel": [], "sha256_slddrw": "alt"}, {"bestanden": True, "maengel": []}):
        md = _md({"pruefbericht": PRUEFBERICHT, "urteil": urteil})
        assert "ZEICHNUNGSPRUEFER_VERALTET" in md and "Zeichnung ungeprüft" in md.split(chr(10))[2]
        assert "ZEICHNUNGSPRUEFER_FEHLT" not in md


def test_kopfmeldungen_und_nicht_geprueft_stehen_im_bericht():
    pb = {**PRUEFBERICHT, "bestanden": False, "kopf": {"ok": False, "meldungen": ["ZEICHNUNG_GEAENDERT: Handänderung"]}}
    md = _md({"pruefbericht": pb, "urteil": {"bestanden": True, "maengel": [], "sha256_slddrw": "abc"}})
    assert "ZEICHNUNG_GEAENDERT" in md and "nicht geprüft (ok: null): lesbarkeit" in md
