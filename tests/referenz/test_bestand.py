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
from swki.bestand import befehle
from swki.bestand.ablage import schreibe_aufnahme
from swki.bestand.spec import validieren
from swki.durchlauf import durchlauf
from swki.konfig import Rechner
from swki.spec.normen import bohrspitze_grad, normmasse

ORDNER = Path(__file__).parent / "bestand"
SPEC = ORDNER / "lagerdeckel_rev.yaml"
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
    """Unabhängig vom Lauf aus den Maßen des Musters (`spikes/s18_muster.py`) und den Parametern: Die Verlängerung trägt in Standard die
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
    """Spec §12: die ganze Revision über `swki durchlauf`, enge Bereiche; das Urteil des Prüfers bleibt dem Referenzlauf vorbehalten."""
    ziel = tmp_path / auftrag
    ziel.mkdir()
    shutil.copy2(SPEC, ziel)
    shutil.copytree(ORDNER / "eingabe", ziel / "eingabe")
    spec = ziel / SPEC.name
    befehle.aufnehmen(ORDNER / "muster" / "Lagerdeckel.SLDPRT", auftrag)
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
