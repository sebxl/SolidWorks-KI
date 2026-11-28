"""Abschnitt „Zeichnung“ im Bericht (Z1.4 Task 5): Prüfbericht, Prüfer-Urteil, ZEICHNUNGSPRUEFER_FEHLT."""

from swki.pruefung.bericht import bericht_markdown, zeichnung_stufe, zeichnung_urteil_hinweise

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


def _statuszeile(zeichnung):
    return _md(zeichnung).split(chr(10))[2]


def test_stufen_geprueft_maengel_ungeprueft():
    gut = {"bestanden": True, "maengel": [], "sha256_slddrw": "abc"}
    assert zeichnung_stufe({"pruefbericht": PRUEFBERICHT, "urteil": gut}) == "geprueft"
    z = _statuszeile({"pruefbericht": PRUEFBERICHT, "urteil": gut})
    assert "ungeprüft" not in z and "Mängeln" not in z
    # Prüfer sagt bestanden, Maschine nicht
    pb = {**PRUEFBERICHT, "bestanden": False}
    assert zeichnung_stufe({"pruefbericht": pb, "urteil": gut}) == "maengel"
    assert "Zeichnung mit Mängeln" in _statuszeile({"pruefbericht": pb, "urteil": gut})
    # Maschine ok, Prüfer nicht
    schlecht = {"bestanden": False, "maengel": [{"knoten": [], "beschreibung": "x"}], "sha256_slddrw": "abc"}
    assert zeichnung_stufe({"pruefbericht": PRUEFBERICHT, "urteil": schlecht}) == "maengel"
    assert zeichnung_stufe({"pruefbericht": PRUEFBERICHT, "urteil": None}) == "ungeprueft"
    # ungeprüft schlägt Mängel
    assert zeichnung_stufe({"pruefbericht": pb, "urteil": None}) == "ungeprueft"


def test_pruefbericht_veraltet_macht_alles_ungeprueft():
    gut = {"bestanden": True, "maengel": [], "sha256_slddrw": "abc"}
    z = {"pruefbericht": PRUEFBERICHT, "urteil": gut, "pruefbericht_veraltet": True}
    assert zeichnung_stufe(z) == "ungeprueft"
    assert "ZEICHNUNG_PRUEFBERICHT_VERALTET" in _md(z) and "Zeichnung ungeprüft" in _statuszeile(z)


def test_fehlender_sha_im_pruefbericht_gilt_als_veraltet():
    pb = {k: v for k, v in PRUEFBERICHT.items() if k != "ist"}
    hinweise = zeichnung_urteil_hinweise({"pruefbericht": pb, "urteil": {"bestanden": True, "maengel": [],
                                                                         "sha256_slddrw": "abc"}})
    assert any("ZEICHNUNGSPRUEFER_VERALTET" in h for h in hinweise)


def test_hinweise_keine_liste_wird_gemeldet():
    urteil = {"bestanden": True, "maengel": [], "sha256_slddrw": "abc", "hinweise": "Text statt Liste"}
    md = _md({"pruefbericht": PRUEFBERICHT, "urteil": urteil})
    assert "hinweise" in md and "keine Liste" in md


def test_beispiel_json_der_agent_datei_ist_ein_gueltiges_urteil(tmp_path):
    import json
    from pathlib import Path

    from swki.pruefung.schleife import lies_urteil

    agent = (Path(__file__).resolve().parents[2] / ".claude" / "agents" / "zeichnungspruefer.md").read_text(encoding="utf-8")
    beispiele = [z.strip() for z in agent.splitlines() if z.startswith("    {")]
    assert len(beispiele) == 2
    for i, b in enumerate(beispiele):
        datei = tmp_path / f"u{i}.json"
        datei.write_text(b, encoding="utf-8")
        assert lies_urteil(datei) == json.loads(b)


def test_befehl_bericht_veraltet_wenn_slddrw_anders(tmp_path):
    import hashlib

    from swki.pruefung.befehle import pruefbericht_veraltet

    drw = tmp_path / "a.slddrw"
    drw.write_bytes(b"inhalt")
    sha = hashlib.sha256(b"inhalt").hexdigest()
    pb = {"zeichnung": str(drw), "ist": {"sha256_slddrw": sha}}
    assert pruefbericht_veraltet(pb) is False
    drw.write_bytes(b"anders")
    assert pruefbericht_veraltet(pb) is True
    drw.unlink()
    assert pruefbericht_veraltet(pb) is True
    assert pruefbericht_veraltet({"zeichnung": str(drw)}) is True


def test_auftrag_ohne_sha_ist_ein_fehler(tmp_path):
    import pytest

    from swki.cli import SwkiFehler
    from swki.durchlauf import zeichnungspruefer_auftrag

    with pytest.raises(SwkiFehler):
        zeichnungspruefer_auftrag(tmp_path / "a.yaml", 1, {"pdf": "x.pdf", "ist": {}})


# --- Gesamtreview I2: Zeichnung ohne Prüfbericht ---------------------------------------------------------------------

def test_zeichnung_ohne_pruefbericht_ist_ungeprueft():
    z = {"pruefbericht": None, "urteil": None, "pruefbericht_fehlt": True}
    assert zeichnung_stufe(z) == "ungeprueft"
    assert [h.split(":")[0] for h in zeichnung_urteil_hinweise(z)] == ["ZEICHNUNG_PRUEFBERICHT_FEHLT"]
    md = _md(z)
    assert "Zeichnung ungeprüft" in _statuszeile(z) and "ZEICHNUNG_PRUEFBERICHT_FEHLT" in md
    assert "maschinell: nicht bestanden" not in md and "maschinell: kein Prüfbericht" in md


def test_befehl_bericht_meldet_zeichnung_ohne_pruefbericht(tmp_path, monkeypatch):
    """`swki zeichnen` löscht den alten Prüfbericht, `zeichnung pruefen` bei Abbruch auch: liegt danach eine Zeichnung
    im Lauf, ist der Bericht „Zeichnung ungeprüft“, nie still „bestanden“."""
    from types import SimpleNamespace

    from swki.pruefung import befehle

    spec = tmp_path / "auftraege" / "A-1" / "p.yaml"
    (spec.parent / "protokolle").mkdir(parents=True)
    spec.write_text("art: teil\nname: Platte\n", encoding="utf-8")
    arbeit = tmp_path / "arbeit"
    monkeypatch.setattr(befehle, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=arbeit))
    monkeypatch.setattr(befehle, "lade_spec_beliebig", lambda p: {"name": "Platte", "art": "teil"})
    monkeypatch.setattr(befehle, "status", lambda p: {"laeufe": LAEUFE, "empfehlung": "bestanden", "text": "ok"})
    monkeypatch.setattr(befehle, "_compiler_aenderungen", lambda seit: [])
    monkeypatch.setattr(befehle, "_lies", lambda p: None)
    assert "zeichnung" not in befehle.bericht(spec)                    # ohne Zeichnung kein Abschnitt
    (arbeit / "A-1" / "lauf-2" / "zeichnung").mkdir(parents=True)
    (arbeit / "A-1" / "lauf-2" / "zeichnung" / "Platte.SLDDRW").write_bytes(b"x")
    erg = befehle.bericht(spec)
    assert erg["zeichnung"] == "ungeprueft"
    assert "ZEICHNUNG_PRUEFBERICHT_FEHLT" in (spec.parent / "bericht.md").read_text(encoding="utf-8")
