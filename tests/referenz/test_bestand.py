"""Referenz Bestandsdateien (Musterteil Lagerdeckel): ohne SolidWorks gültig gegen die eingecheckte Aufnahme, Sollwerte aus eigener
Rechnung, `bestand.json` ist die Aufnahme des Musters ohne Rechnerpfad. Der Live-Lauf `test_referenz_lagerdeckel` gehört zur
Regressions-Suite (`tests/live_einzeln.py tests/referenz`); Negativfälle in `tests/live/test_live_bestand.py`."""

import json
import math
import shutil
from pathlib import Path

import pytest
import yaml

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei
from swki.bestand import ausgabe, befehle
from swki.bestand.ablage import schreibe_aufnahme
from swki.bestand.spec import validieren
from swki.durchlauf import durchlauf
from swki.konfig import Rechner, lade_rechner
from swki.spec.normen import bohrspitze_grad, normmasse
from werkzeuge.bestand_muster import HUBEINHEIT, TEILE_HUB, hubeinheit_ordner, muster_ordner

ORDNER = Path(__file__).parent / "bestand"
SPEC = ORDNER / "lagerdeckel_rev.yaml"
SPEC_HUB = ORDNER / "hubeinheit_rev.yaml"
AUFTRAG = "REF-BESTAND"


def _aufnahme() -> dict:
    return json.loads((ORDNER / "bestand.json").read_text(encoding="utf-8"))


def _spec() -> dict:
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def test_referenz_gueltig(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr("swki.bestand.spec.lade_rechner", lambda: r)
    schreibe_aufnahme(r, "REF", 1, _aufnahme())
    pfad = tmp_path / "REF" / SPEC.name
    pfad.parent.mkdir()
    shutil.copy2(SPEC, pfad)
    erg = validieren(pfad)
    assert erg["gueltig"] is True and erg["hinweise"] == [] and erg["punkte"] == 6
    assert erg["folgen"] == {"p1": [], "p2": ["D1@Skizze1"], "p3": ["Bohrung_D@Skizze4"]}


def test_abdeckung_wie_spec_12():
    typen = {p["typ"] for p in _spec()["punkte"]}
    assert typen == {"mass", "gleichung", "unterdruecken", "feature", "eigenschaft"}


def test_aufnahme_gehoert_zum_muster_und_nennt_keinen_rechner():
    sha = sha256_datei(ORDNER / "muster" / "Lagerdeckel.SLDPRT")
    assert _spec()["bestand"]["sha256"] == sha == _aufnahme()["datei"]["sha256"]
    assert ":\\" not in (ORDNER / "bestand.json").read_text(encoding="utf-8")


def test_volumen_delta_aus_rechnung():
    """Unabhängig vom Lauf aus den Maßen des Musters (`werkzeuge/bestand_muster.py`) und den Parametern: Die Verlängerung trägt in Standard die
    Fase (2 × 2 / 2 auf 10 mm), Variante B hat keine; alles andere ist in beiden gleich."""
    s = _spec()
    p = s["parameter"]
    verlaengerung = (p["L_neu"] - 100) * 60 * 20
    bohrungen = 2 * math.pi / 4 * (p["D_neu"] ** 2 - 8 ** 2) * 20
    rippe = 3 * 30 * 5
    d = normmasse("gewinde", "M6")["kernloch"]
    spitze = d / 2 / math.tan(math.radians(bohrspitze_grad()) / 2)
    gewinde = 2 * (math.pi * d ** 2 / 4 * p["TG"] + math.pi * d ** 2 / 12 * spitze)
    variante_b = verlaengerung - bohrungen - rippe - gewinde
    standard = variante_b - (p["L_neu"] - 100) * 2 * 2 / 2
    soll = s["pruefung"]["volumen_delta"]
    assert soll["soll"] == pytest.approx((variante_b + standard) / 2, abs=0.01)
    assert abs(variante_b - standard) / 2 < soll["soll"] * soll["toleranz_prozent"] / 100


@pytest.mark.sw
def test_referenz_lagerdeckel(auftrag, tmp_path):
    """Spec §12: die ganze Revision über `swki durchlauf`, enge Bereiche; das Urteil des Prüfers bleibt dem Referenzlauf vorbehalten.
    In einem anderen SolidWorks-Jahr als dem der Dateien im Git läuft sie am dort erzeugten Muster, nur die Prüfsumme ändert sich."""
    ziel = tmp_path / auftrag
    ziel.mkdir()
    muster = muster_ordner(lade_rechner()) / "Lagerdeckel.SLDPRT"
    spec = ziel / SPEC.name
    spec.write_text(SPEC.read_text(encoding="utf-8").replace(_spec()["bestand"]["sha256"], sha256_datei(muster)), encoding="utf-8")
    shutil.copytree(ORDNER / "eingabe", ziel / "eingabe")
    befehle.aufnehmen(muster, auftrag)
    erg = durchlauf(spec, freigeben=True)
    assert erg["schritt"] == "fertig" and erg["pruefung"]["bestanden"] is True, erg
    assert erg["pruefung"]["ohne_urteil"] == [] and "Vorher-Bilder" in erg["pruefer_auftrag"]
    b = json.loads(lauf_datei(spec, erg["lauf"], "pruefbericht").read_text(encoding="utf-8"))
    assert {k: len(d) for k, d in b["differenzen"].items()} == {"Standard": 7, "Variante B": 7}
    assert all(x["bereich"] is not None for d in b["differenzen"].values() for x in d)
    delta = next(e for e in b["pruefungen"] if e["id"] == "volumen_delta")
    assert delta["ist"]["Variante B"] - delta["ist"]["Standard"] == pytest.approx(20, abs=0.01)  # die Fase auf der Verlängerung
    gewinde = next(e for e in b["pruefungen"] if e["id"] == "punkt:p5")
    assert gewinde["soll"] == {"art": "gewinde", "groesse": "M6", "tiefe": 10, "gewindetiefe": 8, "positionen": [[-38, 24], [-38, -24]]}
    for k in ("Standard", "Variante B"):
        ist = gewinde["ist"][k]
        assert (ist["groesse"], ist["tiefe"], ist["gewindetiefe"]) == ("M6", 10, 8), k
        assert sorted(ist["positionen"]) == [[-38, -24], [-38, 24]], k


@pytest.mark.sw
def test_referenz_hubeinheit(auftrag, tmp_path):
    """Spec §12, Plan Task 13: die Revision der Musterbaugruppe über `swki durchlauf`. Der Prüfer bleibt dem Referenzlauf vorbehalten, sein
    Urteil steht hier als Datei da, damit die Ausgabe laufen kann. Das Muster dient als Original und bleibt byteweise gleich; ausgegeben
    wird nur, was sich ändert oder neu ist. Vor dem ersten Lauf: `-m werkzeuge.bestand_muster hubeinheit`, die SHA-256 in der Spec ist ein
    Platzhalter, bis das Muster im Git liegt."""
    muster = hubeinheit_ordner(lade_rechner())
    originale = {p.relative_to(muster).as_posix(): sha256_datei(p) for p in muster.rglob("*") if p.is_file()}
    ziel = tmp_path / auftrag
    ziel.mkdir()
    platzhalter = yaml.safe_load(SPEC_HUB.read_text(encoding="utf-8"))["bestand"]["sha256"]
    spec = ziel / SPEC_HUB.name
    spec.write_text(SPEC_HUB.read_text(encoding="utf-8").replace(platzhalter, sha256_datei(muster / HUBEINHEIT)), encoding="utf-8")
    shutil.copy2(ORDNER / "anschlag_neu.yaml", ziel)
    shutil.copytree(ORDNER / "eingabe", ziel / "eingabe")
    befehle.aufnehmen(muster / HUBEINHEIT, auftrag)

    erg = durchlauf(spec, freigeben=True, neustart=True)
    assert erg["schritt"] == "fertig" and erg["pruefung"]["bestanden"] is True, erg
    b = json.loads(lauf_datei(spec, erg["lauf"], "pruefbericht").read_text(encoding="utf-8"))
    assert b["bestanden"] is True and b["maengel"] == [], b["maengel"]
    ergebnis = {e["id"]: e for e in b["pruefungen"]}
    assert ergebnis["pfade"]["ok"] is True and ergebnis["dateien"]["ok"] is True
    assert all(ergebnis[f"punkt:{p}"]["ok"] is True for p in ("p1", "p2", "p3", "v1", "v2", "p4", "p5", "p6"))
    assert ergebnis["kollision"]["ok"] is True and ergebnis["bewegung:Hub"]["ok"] is True
    assert b["bewegungen"]["Hub"]["max"] == pytest.approx(30)  # der neue Bereich aus Punkt p4 wird gefahren
    assert {k: v for k, v in originale.items()} == {p.relative_to(muster).as_posix(): sha256_datei(p) for p in muster.rglob("*") if p.is_file()}

    lauf_datei(spec, erg["lauf"], "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    aus = ausgabe.ausgabe(spec)
    assert {d["datei"] for d in aus["dateien"] if not d["neu"]} == {HUBEINHEIT, TEILE_HUB[0], TEILE_HUB[1]}
    assert {Path(d["datei"]).suffix.lower() for d in aus["dateien"] if d["neu"]} == {".sldprt"} and len([d for d in aus["dateien"] if d["neu"]]) == 2
    assert {"Muster.SLDASM", "Lagerdeckel.SLDPRT", "gm42-10.SLDPRT", TEILE_HUB[2]} <= set(aus["unveraendert"])
    assert all(Path(d["ausgabe"]).is_relative_to(aus["ordner"]) for d in aus["dateien"])
