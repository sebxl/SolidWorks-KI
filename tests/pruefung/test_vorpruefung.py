"""Vorprüfung vor dem Bau, swki urteil und Ersatz des Prüfers nach dem Bau (ohne SolidWorks)."""

import json
from pathlib import Path

import pytest
import yaml

from swki import durchlauf as d
from swki.auftrag import lauf_datei
from swki.cli import main
from swki.pruefung import vorpruefung as vp
from swki.pruefung.befehle import merkmale_fuer, mit_merkmalen
from swki.pruefung.schleife import lies_laeufe
from swki.spec.freigabe import freigeben

SPEC = """art: teil
name: Platte
parameter: {L: 100}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: 60}}]}
    ende: {typ: blind, tiefe: 20}
pruefung:
  huellquader: auto
"""
OK = {"bestanden": True, "maengel": []}
MANGEL = {"bestanden": False, "maengel": [{"knoten": ["f1"], "beschreibung": "Platte 60 statt 80 tief"}]}
STEP = Path(__file__).parent / "daten" / "platte_merkmale.step"


def _merkmale(ok=True, **zusatz):
    return {"id": "merkmale", "ok": ok, "ist": {}, "geprueft": 1, "knoten": [], **zusatz}


@pytest.fixture
def auftrag(tmp_path):
    spec = tmp_path / "platte.yaml"
    spec.write_text(SPEC, encoding="utf-8")
    return spec


def _schreibe(spec, lauf, art, daten):
    pfad = lauf_datei(spec, lauf, art)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten), encoding="utf-8")


def _gebaut(spec, lauf=1, merkmale=None):
    _schreibe(spec, lauf, "protokoll", {"status": "ok", "dauer_s": 20.0, "gestartet": "2026-10-10T10:00:00"})
    _schreibe(spec, lauf, "pruefbericht", {"bestanden": True, "maengel": [],
                                           "pruefungen": [merkmale or _merkmale()]})


def test_vorpruefung_ersetzt_pruefer_nach_dem_bau(auftrag):
    vp.lege_ab(auftrag, OK)
    freigeben(auftrag, yaml.safe_load(SPEC))
    _gebaut(auftrag)
    [lauf] = lies_laeufe(auftrag)
    assert lauf["bestanden"] is True and lauf["pruefer_quelle"] == "vorpruefung"


def test_ohne_vorpruefung_bleibt_der_pruefer_noetig(auftrag):
    freigeben(auftrag, yaml.safe_load(SPEC))
    _gebaut(auftrag)
    [lauf] = lies_laeufe(auftrag)
    assert lauf["pruefer"] == "ausstehend" and lauf["pruefer_quelle"] is None


def test_vorpruefung_gilt_nur_fuer_den_freigegebenen_text(auftrag):
    vp.lege_ab(auftrag, OK)
    auftrag.write_text(SPEC.replace("tiefe: 20", "tiefe: 25"), encoding="utf-8")   # danach geändert
    freigeben(auftrag, yaml.safe_load(auftrag.read_text(encoding="utf-8")))
    _gebaut(auftrag)
    assert lies_laeufe(auftrag)[0]["pruefer"] == "ausstehend"


@pytest.mark.parametrize(("merkmale", "ersetzt"), [
    (_merkmale(), True),
    (_merkmale(nicht_geprueft=["f2: Formschräge (Prüfung formschraegen)"]), True),
    (_merkmale(nicht_geprueft=["r1: Typ rotation"]), False),
    (_merkmale(ok=None, hinweis="STEP des Laufs fehlt"), False),
    (_merkmale(ok=False), False),
])
def test_bildpruefung_nur_ersetzt_wenn_alles_abgebildet(merkmale, ersetzt):
    assert vp.ersetzt_bildpruefung({"pruefungen": [merkmale]}) is ersetzt


def test_vorpruefung_mit_maengeln_zaehlt_als_maengel(auftrag):
    vp.lege_ab(auftrag, MANGEL)
    assert vp.offene_maengel(auftrag) == MANGEL["maengel"]
    auftrag.write_text(SPEC.replace("60", "80"), encoding="utf-8")   # korrigiert, noch nicht neu vorgeprüft
    assert vp.offene_maengel(auftrag) is None


def test_durchlauf_freigeben_haelt_bei_offener_vorpruefung(auftrag, monkeypatch):
    import swki.spec.befehle as sb

    monkeypatch.setattr(sb, "_validieren", lambda a: {"gueltig": True, "hinweise": []})
    monkeypatch.setattr(sb, "_freigeben", lambda a: pytest.fail("darf nicht freigeben"))
    vp.lege_ab(auftrag, MANGEL)
    erg = d.durchlauf(auftrag, freigeben=True)
    assert erg["schritt"] == "vorpruefung" and erg["maengel"] == MANGEL["maengel"]


def test_urteil_befehl_vorpruefung_und_bericht(auftrag, capsys):
    freigeben(auftrag, yaml.safe_load(SPEC))
    _gebaut(auftrag)
    code = main(["urteil", str(auftrag), "--json", '```json\n{"bestanden": true, "maengel": []}\n```'])
    assert code == 0
    # ohne --vorpruefung landet das Urteil beim letzten Lauf
    erg = json.loads(capsys.readouterr().out)
    assert erg["abgelegt"].endswith("platte.lauf-1.pruefer.json") and erg["empfehlung"] == "bestanden"
    assert Path(erg["bericht"]).exists()


def test_urteil_befehl_vorpruefung_vor_dem_bau(auftrag, capsys):
    assert main(["urteil", str(auftrag), "--vorpruefung", "--json", json.dumps(MANGEL)]) == 0
    erg = json.loads(capsys.readouterr().out)
    assert erg["bestanden"] is False and "empfehlung" not in erg
    assert json.loads(vp.vorpruefung_pfad(auftrag).read_text(encoding="utf-8"))["urteil"] == MANGEL


def test_urteil_befehl_ungueltiges_urteil(auftrag, capsys):
    assert main(["urteil", str(auftrag), "--vorpruefung", "--json", '{"bestanden": "ja"}']) == 1
    assert "PRUEFER_URTEIL_UNGUELTIG" in capsys.readouterr().out


def test_validieren_liefert_vorpruefung_auftrag(auftrag, capsys):
    assert main(["validieren", str(auftrag)]) == 0
    erg = json.loads(capsys.readouterr().out)
    assert erg["vorpruefung_auftrag"].startswith("Vorprüfung (vor dem Bau) von platte.yaml")


def test_merkmale_fuer_lauf(tmp_path):
    soll = {"features": [], "parameter": {}}
    erg = merkmale_fuer({"dateien": {"step": str(STEP)}}, tmp_path, soll)
    assert erg["eintrag"]["id"] == "merkmale" and "Bohrung 4× durch" in erg["merkmale_text"]
    assert (tmp_path / "merkmale.txt").exists() and (tmp_path / "merkmale.json").exists()
    # ohne STEP: kein Abbruch, Eintrag ohne Urteil
    assert merkmale_fuer({"dateien": {}}, tmp_path, soll)["eintrag"]["ok"] is None
    kaputt = tmp_path / "kaputt.step"
    kaputt.write_text("ISO-10303-21;", encoding="utf-8")
    erg = merkmale_fuer({"dateien": {"step": str(kaputt)}}, tmp_path, soll)
    assert erg["eintrag"]["ok"] is None and "nicht lesbar" in erg["eintrag"]["hinweis"]


def test_mit_merkmalen_macht_mangel():
    bewertung = {"bestanden": True, "maengel": [], "pruefungen": []}
    e = {"id": "merkmale", "ok": False, "ist": {}, "knoten": ["f3"], "hinweis": "Bohrung (Y 10 | Z 0): Tiefe 12 statt 10"}
    erg = mit_merkmalen(bewertung, {"eintrag": e, "merkmale_text": "Hüllquader …"})
    assert erg["bestanden"] is False and erg["maengel"][0]["knoten"] == ["f3"]
    assert erg["merkmale_text"] == "Hüllquader …"
