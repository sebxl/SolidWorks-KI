"""Außengewinde eines Kaufteils (Kolbenstange) in einer Gewinde-Normbohrung eines Eigenteils: geprüft wie eine
Schraube (gewinde:<instanz>.<gruppe>.<i>), nicht als Kollision (Anlass: AP 6.8, Schieberkopf auf Festo ADNM-25)."""

import copy

import pytest
import yaml

from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.geometrie import ueberlappung_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import aussengewinde_kaufteil, gewindebohrungen_kaufteil
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.geometrie import Messgeometrie
from swki.spec.laden import SpecFehler
from tests.baugruppe.beispiel_kaufteil import BAUGRUPPE, HALTER, katalog
from tests.kaufteile.beispiel import kopie as eintrag_kopie

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}, "namensschema": {"datei": "{auftrag}_{name}"}}
Y = (0.0, 1.0, 0.0)
WELLE = {"art": "aussen", "groesse": "M8", "gewindetiefe": 12, "tiefe": 12, "normale": [0, -1, 0],
         "positionen": [[0, -13, 0]]}
NENN8 = {"modell": "nenn", "durchmesser": 8.0}
ANFANG = (0.0, 5.0, 0.0)  # Gewindeanfang in Baugruppenkoordinaten, Gewinde in +y


def _eintrag() -> dict:
    e = eintrag_kopie()
    e["gewinde"]["welle"] = copy.deepcopy(WELLE)
    return e


def _schreibe(ordner, groesse: str = "M8", baugruppe: dict | None = None):
    """Halter mit Gewinde-Normbohrung f4 (Tiefe 9, Gewindetiefe 8) und Baugruppe Halter + Motor (ohne Schrauben)."""
    halter = copy.deepcopy(HALTER)
    halter["features"].append({"id": "f4", "typ": "normbohrung", "art": "gewinde", "groesse": groesse,
                               "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[30, 0]], "tiefe": 9,
                               "gewindetiefe": 8})
    if baugruppe is None:
        baugruppe = copy.deepcopy(BAUGRUPPE)
        baugruppe["komponenten"] = baugruppe["komponenten"][:2]
        baugruppe["verknuepfungen"] = baugruppe["verknuepfungen"][:3]
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("halter.yaml", halter), ("motorprobe.yaml", baugruppe)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return lade_baugruppe(ordner / "motorprobe.yaml")


def _messwerte(bg, abstand: float, volumen: float, modell: dict | None = NENN8, versatz: float = 0.0,
               paar=("halter", "motor")) -> BaugruppenMesswerte:
    """Eintritt der Bohrung f4.1 liegt `abstand` hinter dem Gewindeanfang auf der Gewindeachse (seitlich `versatz`)."""
    ids = [i.id for i in instanzen(bg.spec, bg.quellen)]
    return BaugruppenMesswerte(
        rebuild_fehler=[], verknuepfungen={v.id: 0 for v in verknuepfungen(bg.spec, bg.quellen)},
        komponenten={i: {"status": 3, "fixiert": i == "halter"} for i in ids},
        stueckliste=stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD),
        interferenzen=[{"paar": list(paar), "volumen": volumen}] if volumen else [], box=[0, 0, 0, 1, 1, 1],
        masse_kg=1.0, eigenschaften={"Benennung": "Motorprobe"},
        gewindebohrungen=[{"teil": "halter", "feature": "f4", "instanz": 1,
                           "eintritt": Messgeometrie("punkt", (versatz, ANFANG[1] + abstand, 0.0))}],
        aussengewinde=[{"teil": "motor", "gruppe": "welle", "instanz": 1, "groesse": "M8", "laenge": 12, "tiefe": 12,
                        "anfang": Messgeometrie("ebene", ANFANG, Y)}],
        teilberichte={"halter.yaml": {"bestanden": True, "pruefungen": [], "maengel": []}},
        gewinde_modelle={"SWKI-MUSTER_GM42-10": {"welle": modell}} if modell else {})


def _bericht(bg, m) -> dict:
    return bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))


def _pruefung(bericht: dict, pid: str) -> dict | None:
    return next((e for e in bericht["pruefungen"] if e["id"] == pid), None)


@pytest.fixture
def bg(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch, _eintrag())
    return _schreibe(tmp_path / "A")


def test_aussengewinde_gehoert_nicht_zu_den_gewindebohrungen(bg):
    spec = bg.quellen["motor"].spec
    assert {b["feature"] for b in gewindebohrungen_kaufteil(spec)} == {"flansch"}
    [a] = aussengewinde_kaufteil(spec)
    assert {k: v for k, v in a.items() if k != "anfang"} == {"gruppe": "welle", "instanz": 1, "groesse": "M8",
                                                              "laenge": 12, "tiefe": 12}
    assert a["anfang"] == Messgeometrie("ebene", (0, -13, 0), (0, -1, 0))


def test_gewindepaarung_statt_kollision(bg):
    soll = ueberlappung_soll(8.0, 1.25, 6.8, 6.0)
    bericht = _bericht(bg, _messwerte(bg, 6.0, soll))
    g = _pruefung(bericht, "gewinde:motor.welle.1")
    assert g["ok"] is True and g["soll"] == round(soll, 3) and g["einschraublaenge"] == 6.0
    assert g["knoten"] == ["motor", "halter"] and g["gewindetiefe"] == 8 and g["tiefe"] == 9
    assert _pruefung(bericht, "kollision")["ok"] is True and bericht["bestanden"] is True
    assert bericht["gewindepaarungen"] == [{"schraube": "motor.welle.1", "teil": "halter", "bohrung": "f4.1",
                                            "einschraublaenge": 6.0, "volumen": round(soll, 3),
                                            "soll": round(soll, 3), "gewindetiefe": 8, "tiefe": 9}]
    text = bericht_markdown({"name": "Motorprobe"}, "A", [], ("WEITER", "x"), bericht, None, None, [])
    assert "| Schraube bzw. Außengewinde | Teil | Bohrung |" in text
    assert f"| motor.welle.1 | halter | f4.1 | 6.0 | 8.0 | {round(soll, 3)} / {round(soll, 3)} |" in text


def test_falsches_volumen_und_zu_tief(bg):
    soll = ueberlappung_soll(8.0, 1.25, 6.8, 6.0)
    falsch = _bericht(bg, _messwerte(bg, 6.0, soll * 1.1))
    assert _pruefung(falsch, "gewinde:motor.welle.1")["ok"] is False
    assert _pruefung(falsch, "kollision")["ok"] is True
    tief = _pruefung(_bericht(bg, _messwerte(bg, 2.0, ueberlappung_soll(8.0, 1.25, 6.8, 10.0))), "gewinde:motor.welle.1")
    assert tief["ok"] is False and "Einschraublänge 10.00 mm größer als Gewindetiefe 8" in tief["hinweis"]


def test_groesse_muss_passen(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch, _eintrag())
    bg = _schreibe(tmp_path / "A", groesse="M5")
    g = _pruefung(_bericht(bg, _messwerte(bg, 6.0, 50.0)), "gewinde:motor.welle.1")
    assert g["ok"] is False and "M8 passt nicht in Gewindebohrung M5" in g["hinweis"]


def test_achse_verfehlt_bleibt_kollision(bg):
    bericht = _bericht(bg, _messwerte(bg, 6.0, 40.0, versatz=0.5))
    assert _pruefung(bericht, "gewinde:motor.welle.1") is None
    kollision = _pruefung(bericht, "kollision")
    assert kollision["ok"] is False and kollision["knoten"] == ["halter", "motor"]


def test_nicht_erreicht_und_modell_unbekannt(bg):
    bericht = _bericht(bg, _messwerte(bg, 13.0, 0.0))
    assert _pruefung(bericht, "gewinde:motor.welle.1") is None and bericht["gewindepaarungen"] == []
    unbekannt = _pruefung(_bericht(bg, _messwerte(bg, 6.0, 30.0, modell=None)), "gewinde:motor.welle.1")
    assert unbekannt["ok"] is None and "Gewindemodell von SWKI-MUSTER GM42-10.welle unbekannt" in unbekannt["hinweis"]


def test_schraube_passt_nicht_ins_aussengewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch, _eintrag())
    spec = copy.deepcopy(BAUGRUPPE)
    spec["komponenten"][2] = {"id": "schraube", "quelle": {"normteil": "ISO 4762 M8x16"},
                              "je_position": {"komponente": "motor", "gewinde": "welle"}}
    spec["verknuepfungen"][3]["b"] = {"komponente": "halter", "feature": "f1", "flaeche": "-y"}
    spec["verknuepfungen"][4]["b"] = {"komponente": "motor", "gewinde": "welle", "instanz": "je", "achse": True}
    with pytest.raises(SpecFehler) as e:
        _schreibe(tmp_path / "A", baugruppe=spec)
    assert [f"{b['pfad']}: {b['meldung']}" for b in e.value.daten["befunde"]] == [
        "verknuepfungen[4]: Passung: welle von SWKI-MUSTER GM42-10 ist ein Außengewinde (keine Schraube hinein)"]
