"""Live: Negativfälle am Linearschlitten (Spec 4a §12, Präzisierung 13) – Stellungskollision, Grenze im Modell zu weit,
umgekehrte Richtung, zweiter Freiheitsgrad. Jeder Fall liefert genau seine Mängelmenge."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.baugruppe import sw_baugruppe
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-SCHLITTEN"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "schlitten"
ANSCHLAG = {
    "art": "teil", "name": "Anschlag", "material": "1.0038", "eigenschaften": {"Benennung": "Anschlag"},
    "parameter": {"L": 24, "B": 20, "H": 20},  # L 24 aus Task 9 (Quadrat scheiterte damals am Rechteckwerkzeug, behoben)
    "features": [{"id": "f1", "typ": "extrusion",
                  "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                  "ende": {"typ": "blind", "tiefe": "=H"}}],
    "pruefung": {"huellquader": ["=L", "=H", "=B"]},
}


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _aendere(ordner: Path, aendern) -> Path:
    pfad = ordner / "linearschlitten.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _v(spec: dict, vid: str) -> dict:
    return next(v for v in spec["verknuepfungen"] if v["id"] == vid)


def _baue_und_pruefe(capsys, pfad: Path) -> dict:
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code in (0, 1) and "maengel" in bericht, bericht
    return bericht


def _maengel(bericht: dict) -> dict:
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_stellungskollision(capsys, auftrag):
    # Anschlag auf der rechten Leiste bei x 80…104 (der Hebel schwenkt nach +z über die rechte Leiste, Spike S13
    # Zeile 7): er trifft den geschwenkten Hebel nur, wenn der Schlitten auf max steht (Bolzen bei x = 90) – das finden
    # nur die Paarläufe, in beiden Richtungen; die Grundstellungsläufe bleiben frei
    (auftrag / "anschlag.yaml").write_text(yaml.safe_dump(ANSCHLAG, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def aendern(s):
        s["parameter"]["AX"] = 230
        s["komponenten"].append({"id": "anschlag", "quelle": {"teil": "anschlag.yaml"}})
        s["verknuepfungen"] += [
            {"id": "v30", "typ": "deckungsgleich", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "-y"},
             "b": {"komponente": "leiste_rechts", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
            {"id": "v31", "typ": "abstand", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "-x"},
             "b": {"komponente": "grundplatte", "feature": "f1", "flaeche": "-x"}, "ausrichtung": "gleich", "wert": "=AX"},
            {"id": "v32", "typ": "deckungsgleich", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "+z"},
             "b": {"komponente": "grundplatte", "feature": "f1", "flaeche": "+z"}, "ausrichtung": "gleich"},
        ]
        s["pruefung"]["huellquader"] = [300, 65, 100]  # der Anschlag ragt 10 mm über den Hebel

    bericht = _baue_und_pruefe(capsys, _aendere(auftrag, aendern))
    maengel = _maengel(bericht)
    assert set(maengel) == {"bewegung_kollision:Hebelschwenk", "bewegung_kollision:Schlittenhub"}, maengel
    for m in maengel.values():
        assert set(m["knoten"]) == {"anschlag", "hebel"}, maengel
    grund = [x for x in bericht["bewegungen"]["laeufe"] if not x["gegen"]]
    assert [x["kollisionen"] for x in grund] == [0, 0], bericht["bewegungen"]


def test_grenze_im_modell_zu_weit(capsys, auftrag, monkeypatch):
    # Der Bau setzt die obere Grenze von g1 um 20 mm zu weit (die Spec bleibt gültig und unverändert): der Schritt
    # über HUB hinaus geht durch
    original = sw_baugruppe.grenzen

    def zu_weit(v, parameter):
        g = original(v, parameter)
        return {**g, "max": (g["max"][0] + 20, None)} if v.id == "g1" else g

    monkeypatch.setattr(sw_baugruppe, "grenzen", zu_weit)
    maengel = _maengel(_baue_und_pruefe(capsys, auftrag / "linearschlitten.yaml"))
    assert set(maengel) == {"grenze:Schlittenhub"}, maengel


def test_umgekehrte_richtung(capsys, auftrag):
    # g1 an den Flächen +x: Grundstellung am Ende +x, der Hub fährt nach −x – Schlitten und Hebel enden 2 · HUB neben
    # der Soll-Endlage; sonst bleibt alles frei
    def aendern(s):
        _v(s, "g1")["a"]["flaeche"] = "+x"
        _v(s, "g1")["b"]["flaeche"] = "+x"

    bericht = _baue_und_pruefe(capsys, _aendere(auftrag, aendern))
    maengel = _maengel(bericht)
    assert set(maengel) == {"endlage:Schlittenhub:schlitten", "endlage:Schlittenhub:hebel"}, maengel
    ist = next(p["ist"] for p in bericht["pruefungen"] if p["id"] == "endlage:Schlittenhub:schlitten")
    assert ist == pytest.approx([-220.0, 0.0, 0.0], abs=0.1), ist


def test_zweiter_freiheitsgrad(capsys, auftrag):
    # ohne v21 ist der Schlitten auch quer (z) verschiebbar: mit Antrieb bleibt er unterbestimmt. Mitfahrer melden wie
    # ihr Träger (Spike S13 Zeile 4): der Hebel (fährt auf dem Schlitten) ist dann ebenfalls unterbestimmt, ebenso der
    # Drehbolzen ohne `freiheitsgrade`-Angabe (statische `bestimmtheit`)
    maengel = _maengel(_baue_und_pruefe(capsys, _aendere(
        auftrag, lambda s: s.update(verknuepfungen=[v for v in s["verknuepfungen"] if v["id"] != "v21"]))))
    assert set(maengel) == {"freiheitsgrad:schlitten", "freiheitsgrad:hebel", "bestimmtheit"}, maengel
