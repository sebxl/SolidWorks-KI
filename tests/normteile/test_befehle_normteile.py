import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import Rechner
from swki.normteile import befehle
from swki.normteile.erzeugen import vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.tabelle import lade_normtabelle

DATEN = Path(__file__).parent / "daten"


@pytest.fixture
def wissen(tmp_path, monkeypatch):
    ziel = tmp_path / "wissen"
    shutil.copytree(DATEN, ziel)
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit", tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    return ziel


@pytest.fixture
def gebaut(monkeypatch):
    aufrufe = []

    def fake(spec, ordner, mit_bildern=False, lauf=0):
        aufrufe.append((spec["name"], mit_bildern))
        teil = ordner / f"{spec['name']}.sldprt"
        teil.write_bytes(b"teil")
        bilder = {"iso": str(ordner / "bilder" / "iso.png")} if mit_bildern else {}
        return {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "teil": str(teil),
                "bilder": bilder, "fehler": None}

    monkeypatch.setattr(befehle.bau, "baue_und_pruefe", fake)
    return aufrufe


def _urteil(wissen, tmp_path, bestanden=True):
    t = lade_normtabelle("ISO 9999", wissen)
    datei = tmp_path / "urteil.json"
    maengel = [] if bestanden else [{"knoten": ["f1"], "beschreibung": "Ring liegt falsch"}]
    datei.write_text(json.dumps({"bestanden": bestanden, "maengel": maengel}), encoding="utf-8")
    return befehle.urteil("ISO 9999", datei, vorlage_pruefsumme(vorlage_text(t, wissen)), wissen)


def test_hole_ohne_urteil(wissen, gebaut):
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT" and gebaut == []


def test_hole_baut_legt_ab_und_trifft_den_cache(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    erst = befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    ziel = tmp_path / "bib" / "2025" / "ISO9999_M6x12_8_8.sldprt"
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and ziel.read_bytes() == b"teil"
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["bestanden"] is True and eintrag["groesse"] == "M6" and eintrag["laenge"] == 12.0
    zweit = befehle.hole("ISO 9999", "M6 x 12", wissen=wissen)
    assert zweit["gebaut"] is False and zweit["pfad"] == str(ziel) and len(gebaut) == 1


def test_geaenderte_tabelle_baut_neu(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    pfad = wissen / "iso9999.yaml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("b: 12}", "b: 12.5}"), encoding="utf-8")
    assert befehle.liste(wissen=wissen)["teile"][0]["aktuell"] is False
    assert befehle.hole("ISO 9999", "M6x12", wissen=wissen)["gebaut"] is True and len(gebaut) == 2
    assert befehle.liste(nur_veraltet=True, wissen=wissen)["teile"] == []


def test_geaenderte_vorlage_braucht_neues_urteil(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    vorlage = wissen / "vorlagen" / "iso9999.yaml"
    vorlage.write_text(vorlage.read_text(encoding="utf-8") + "# geändert\n", encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_nicht_bestandenes_urteil_sperrt(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path, bestanden=False)
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_gescheiterte_pruefung_legt_nichts_ab(wissen, monkeypatch, tmp_path):
    _urteil(wissen, tmp_path)
    monkeypatch.setattr(befehle.bau, "baue_und_pruefe", lambda spec, ordner, mit_bildern=False, lauf=0: {
        "bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": None,
        "maengel": [{"pruefung": "mass:s", "knoten": ["f2"], "beschreibung": "s 6.2 statt 6"}]})
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMTEIL_PRUEFUNG" and e.value.daten["maengel"][0]["pruefung"] == "mass:s"
    assert not (tmp_path / "bib").exists()
    assert (Path(e.value.daten["ordner"]) / "spec.yaml").is_file()


def test_urteil_zu_alter_vorlage_wird_abgelehnt(wissen, tmp_path):
    datei = tmp_path / "u.json"
    datei.write_text('{"bestanden": true, "maengel": []}', encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.urteil("ISO 9999", datei, "0" * 64, wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_muster_baut_kleinste_groesse_mit_bildern(wissen, gebaut):
    m = befehle.muster("ISO 9999", wissen)
    assert m["schluessel"] == "ISO9999_M5x10_8_8" and gebaut == [("ISO9999_M5x10_8_8", True)]
    assert Path(m["spec"]).is_file() and m["bilder"] and m["bestanden"] is True


def test_tabellen_pruefen(wissen):
    e = befehle.tabellen_pruefen(wissen=wissen)
    assert e["gueltig"] is True and e["normen"]["ISO 9999"]["gesperrt"] == ["M8"]


def test_tabellen_pruefen_meldet_befunde(wissen):
    pfad = wissen / "iso9999.yaml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("b: 12}", "b: 5}"), encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.tabellen_pruefen(wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG"


def _tabelle_aendern(wissen, alt, neu):
    pfad = wissen / "iso9999.yaml"
    text = pfad.read_text(encoding="utf-8")
    assert alt in text
    pfad.write_text(text.replace(alt, neu), encoding="utf-8")


def test_hole_tabelle_ohne_status_ist_ungueltig(wissen, gebaut):
    _tabelle_aendern(wissen, "b: 12}, laengen: [10, 12, 16, 20], status: abgeglichen}",
                     "b: 12}, laengen: [10, 12, 16, 20]}")
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG" and gebaut == []


def test_hole_tabelle_ohne_laengen_ist_ungueltig(wissen, gebaut):
    _tabelle_aendern(wissen, "laengen: [10, 12, 16, 20], ", "")
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG" and gebaut == []


def test_tabellen_pruefen_ohne_status_meldet_befund_ohne_absturz(wissen):
    _tabelle_aendern(wissen, "b: 12}, laengen: [10, 12, 16, 20], status: abgeglichen}",
                     "b: 12}, laengen: [10, 12, 16, 20]}")
    with pytest.raises(NormteilFehler) as e:
        befehle.tabellen_pruefen(wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG"
    assert e.value.daten["normen"]["ISO 9999"]["befunde"]


def test_tabellen_pruefen_ohne_norm_meldet_befund_ohne_absturz(wissen):
    _tabelle_aendern(wissen, "norm: ISO 9999\n", "")
    with pytest.raises(NormteilFehler) as e:
        befehle.tabellen_pruefen("iso9999", wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG"
    assert e.value.daten["normen"]["iso9999"]["befunde"]


def test_hole_regelverletzung_ist_ungueltig(wissen, gebaut):
    _tabelle_aendern(wissen, "b: 12}", "b: 5}")
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG" and gebaut == []


def test_hole_gesperrte_groesse_bleibt_gesperrt(wissen, gebaut):
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M8x16", wissen=wissen)
    assert e.value.daten["code"] == "NORMTEIL_GESPERRT" and gebaut == []


def test_hole_reicht_laufnummer_an_den_bau(wissen, monkeypatch, tmp_path):
    _urteil(wissen, tmp_path)
    laeufe = []

    def fake(spec, ordner, mit_bildern=False, lauf=0):
        laeufe.append((ordner.name, lauf))
        teil = ordner / f"{spec['name']}.sldprt"
        teil.write_bytes(b"teil")
        return {"bestanden": True, "pruefungen": [], "maengel": [], "teil": str(teil), "bilder": {}, "fehler": None}

    monkeypatch.setattr(befehle.bau, "baue_und_pruefe", fake)
    befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    befehle.hole("ISO 9999", "M6x16", wissen=wissen)
    befehle.hole("ISO 9999", "M6x12", "A2", wissen=wissen)
    assert laeufe == [("lauf-1", 1), ("lauf-1", 1), ("lauf-1", 1)]
    # Zweiter Bau desselben Schlüssels (Tabelle geändert) zählt hoch.
    _tabelle_aendern(wissen, "b: 12}", "b: 12.5}")
    befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert laeufe[-1] == ("lauf-2", 2)


def test_cli_unbekannte_norm(capsys):
    code = main(["normteil", "hole", "ISO 1", "M8x30"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 1 and daten["code"] == "NORMTEIL_UNBEKANNT"
