"""Live: Bemaßungsbezug – Maße zu Rand und Mitte statt Gleichungen, Handänderung an Maßen (Spec Bemaßungsbezug §3,
§8, §10.5) und die Rechteckfälle mit Eckradius, Kreis in der Tasche und Gleichungen bei mitte (SolidWorks muss laufen)."""

import json
import math
import shutil

import pythoncom
import pytest
import yaml

from swki.auftrag import lauf_ordner
from swki.cli import main
from swki.compiler import sw
from swki.compiler.topologie import flaechen
from swki.konfig import lade_rechner
from swki.pruefung.messen import gleichungen_anzahl, oeffne, skizzenstatus
from swki.verbindung import verbinde

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-BEZUG"
SW_IN_DIESER_KONFIGURATION = 1  # swSetValueInConfiguration_e.swSetValue_InThisConfiguration
BREITE = "features[0].skizze.elemente[0].rechteck.breite"
RANDMASS = "features[1].positionen[0][0]"
PLATTE = {
    "art": "teil", "name": "Platte", "material": "1.0038", "eigenschaften": {"Benennung": "Testplatte Bezug"},
    "parameter": {"L": 160, "B": 100, "H": 12, "RA": 10, "ZG": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [
             {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B", "bezug": {"u": "mitte", "v": "mitte"}}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+RA", "=ZG"], ["=-L/2+RA", "=-ZG"]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10,
         "gewindetiefe": 8},
    ],
    "pruefung": {
        "huellquader": ["=L", "=H", "=B"],
        "masse_pruefen": [{"was": "Abstand Gewinde", "von": {"feature": "f2", "instanz": 1, "achse": True},
                           "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": "=2*ZG"}],
    },
}
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def spec_pfad(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    pfad = ordner / "platte.yaml"
    pfad.write_text(yaml.safe_dump(PLATTE, allow_unicode=True), encoding="utf-8")
    yield pfad
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _gebaut(capsys, spec_pfad):
    """Freigeben und bauen (Lauf 1); liefert den Pfad der Teiledatei und das Maßprotokoll (Pfad → Maß) des Laufs."""
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    protokoll = json.loads((spec_pfad.parent / "protokolle" / "platte.lauf-1.protokoll.json").read_text(encoding="utf-8"))
    masse = {m["pfad"]: m for k in protokoll["knoten"] for m in k.get("masse") or []}
    return lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Platte.sldprt", masse


def feature_masse(feature) -> list[float]:
    """Werte (mm) der Maße eines Features bzw. einer Skizze (IFeature.GetFirstDisplayDimension, wie Spike S9a)."""
    werte, dd = [], feature.GetFirstDisplayDimension
    while dd is not None:
        werte.append(round(dd.GetDimension2(0).SystemValue * 1000, 6))
        dd = feature.GetNextDisplayDimension(dd)
    return werte


def _unterfeature(feature, name: str):
    """Unterfeature nach Namen (die Positionsskizze f2_positionen trägt nach dem Bau die Symmetrielinie, ist also nicht
    mehr die Unterskizze ohne Segmente, die skizze.positionsskizze sucht)."""
    unter = feature.GetFirstSubFeature
    while unter is not None and unter.Name != name:
        unter = unter.GetNextSubFeature
    assert unter is not None, name
    return unter


def _achsen_x(feature) -> list[float]:
    return sorted({round(z.punkt[0], 4) for z in flaechen(feature) if z.art == "zylinder"})


def _aendere_mass(pfad, name: str, wert_mm: float) -> list[float]:
    """Wie ein Anwender: Teil öffnen, Maß ändern (IDimension.SetSystemValue3, Spike S17 Fall 5), neu aufbauen,
    speichern, schließen. Liefert die x-Lagen der Bohrungsachsen von f2 nach dem Neuaufbau."""
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, pfad)
    try:
        model.Parameter(name).SetSystemValue3(wert_mm / 1000, SW_IN_DIESER_KONFIGURATION, None)
        sw.rebuild(model)
        assert set(skizzenstatus(model).values()) == {sw.SW_FULLY_CONSTRAINED}
        achsen = _achsen_x(model.FeatureByName("f2"))
        sw.speichere(model, pfad)
    finally:
        sw.schliesse(app, model)
    return achsen


def test_platte_mit_bezuegen_ohne_gleichungen(capsys, spec_pfad):
    datei, masse = _gebaut(capsys, spec_pfad)
    assert masse[RANDMASS]["bezug"] == "-rand" and masse[RANDMASS]["wert"] == pytest.approx(10)
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, datei)
    try:
        assert gleichungen_anzahl(model) == 0
        status = skizzenstatus(model)
        assert status and set(status.values()) == {sw.SW_FULLY_CONSTRAINED}, status
        f2 = model.FeatureByName("f2")
        werte = feature_masse(_unterfeature(f2, "f2_positionen"))
        assert 10 in werte and 40 in werte, werte  # 10 mm zum linken Rand, 40 mm zwischen den Gewinden
        assert _achsen_x(f2) == [-70.0]
    finally:
        sw.schliesse(app, model)
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["maengel"] == [], bericht["maengel"]


def test_handaenderung_erhaelt_randabstand(capsys, spec_pfad):
    datei, masse = _gebaut(capsys, spec_pfad)
    # Platte 160 → 150, symmetrisch: linker Rand bei −75, die Gewinde bleiben 10 mm davon
    assert _aendere_mass(datei, masse[BREITE]["name"], 150) == [pytest.approx(-65, abs=0.01)]
    code, daten = _lauf(capsys, "aenderungen", str(spec_pfad))
    assert code == 0, daten
    [eintrag] = daten["geaendert"]
    assert eintrag["vorschlaege"] == [{"parameter": "L", "neu": pytest.approx(150)}]
    assert [d for d in eintrag["masse"] if d["art"] == "lage"] == []


def test_handaenderung_randmass_ergibt_delta(capsys, spec_pfad):
    datei, masse = _gebaut(capsys, spec_pfad)
    assert _aendere_mass(datei, masse[RANDMASS]["name"], 12) == [pytest.approx(-68, abs=0.01)]
    code, daten = _lauf(capsys, "aenderungen", str(spec_pfad))
    assert code == 0, daten
    [eintrag] = daten["geaendert"]
    assert eintrag["vorschlaege"] == [{"pfad": RANDMASS, "bezug": "-rand", "delta": pytest.approx(2)}]


def _mass_name(protokoll, pfad: str) -> str:
    [name] = [m["name"] for k in protokoll.knoten for m in k.masse or [] if m["pfad"] == pfad]
    return name


@pytest.mark.parametrize(("mitte", "bezug", "box", "box_breiter"), [
    # Fall c: um den Ursprung, zwei Seitenmitten
    ([0, 0], {"u": "mitte", "v": "mitte"}, [-50, 0, -30, 50, 10, 30], [-60, 0, -30, 60, 10, 30]),
    # Fall b: Mitte (0, −20), Höhe 60 (v −50 … 10), v über die dem Ursprung nächste Seite (v = 10) und ihren
    # Mittelpunkt; oben: Z = −v
    ([0, -20], None, [-50, 0, -10, 50, 10, 50], [-60, 0, -10, 60, 10, 50]),
])
def test_rechteck_mit_eckradius_und_seitenmittelpunkt(mitte, bezug, box, box_breiter):
    """Fälle b und c mit Radius: Seitenmittelpunkt (sgATMIDDLE), danach die Eckverrundungen über die Linienpaare
    (Ruling 10); Lage wie in der Spec, Breite per Maß änderbar und symmetrisch zu u = 0."""
    r = {"mitte": mitte, "breite": "=L", "hoehe": 60, "radius": 8} | ({"bezug": bezug} if bezug else {})
    spec = {"art": "teil", "name": "T", "parameter": {"L": 100}, "features": [{
        "id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [{"rechteck": r}]},
        "ende": {"typ": "blind", "tiefe": 10}}]}
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None
        assert set(skizzenstatus(ctx.model).values()) == {sw.SW_FULLY_CONSTRAINED}
        assert sw.teilebox_mm(ctx.model) == pytest.approx(box, abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((6000 - (4 - math.pi) * 64) * 10, abs=1e-3)
        ctx.model.Parameter(_mass_name(protokoll, BREITE)).SetSystemValue3(0.12, SW_IN_DIESER_KONFIGURATION, None)
        sw.rebuild(ctx.model)
        assert set(skizzenstatus(ctx.model).values()) == {sw.SW_FULLY_CONSTRAINED}
        assert sw.teilebox_mm(ctx.model) == pytest.approx(box_breiter, abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((7200 - (4 - math.pi) * 64) * 10, abs=1e-3)


def test_rechteck_mit_eckradius_versetzt_mit_mitte():
    """Fall d mit Radius: Tasche um (20, 10) über die Diagonale, danach die Eckverrundung."""
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": DECKFLAECHE, "elemente": [{"rechteck": {
        "mitte": [20, 10], "breite": 30, "hoehe": 20, "radius": 4, "bezug": {"u": "mitte", "v": "mitte"}}}]},
        "ende": {"typ": "blind", "tiefe": 5}}
    with gebautes_teil({"art": "teil", "name": "T", "features": [KLOTZ, tasche]}) as (ctx, fehler, _):
        assert fehler is None
        assert set(skizzenstatus(ctx.model).values()) == {sw.SW_FULLY_CONSTRAINED}
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - (600 - (4 - math.pi) * 16) * 5, abs=1e-3)
        boden = [f for f in flaechen(ctx.ergebnis("f2").features[0]) if f.art == "ebene" and f.normale[1] > 0.5]
        assert len(boden) == 1


def test_kreis_mittig_in_tasche_gleicher_mitte():
    """Kreis und Rechteck (Fall d) um dieselbe Mitte: der Mittelpunkt der Diagonale entsteht dort, wo schon der
    Kreismittelpunkt liegt (CreatePoint an belegter Stelle) – keine Überbestimmung. Der Schnitt lässt einen Zapfen stehen."""
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": DECKFLAECHE, "elemente": [
        {"rechteck": {"mitte": [20, 10], "breite": 30, "hoehe": 20, "bezug": {"u": "mitte", "v": "mitte"}}},
        {"kreis": {"mitte": [20, 10], "durchmesser": 8, "bezug": {"u": "mitte", "v": "mitte"}}}]},
        "ende": {"typ": "blind", "tiefe": 5}}
    with gebautes_teil({"art": "teil", "name": "T", "features": [KLOTZ, tasche]}) as (ctx, fehler, _):
        assert fehler is None
        assert set(skizzenstatus(ctx.model).values()) == {sw.SW_FULLY_CONSTRAINED}
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - (600 - 16 * math.pi) * 5, abs=1e-3)


def test_gleichung_des_paarabstands_mit_negativer_koordinate():
    """gleichungen: true, mitte-Paar, dessen erster Punkt auf der Achse negativ ist: der Paarabstand bekommt die
    Gleichung -(2 * -"ZG"); SolidWorks muss sie annehmen und ZG muss den Abstand treiben."""
    nb = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": DECKFLAECHE,
          "positionen": [["=-L/2+RA", "=-ZG"], ["=-L/2+RA", "=ZG"]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10,
          "gewindetiefe": 8}
    klotz = {**KLOTZ, "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L",
                                                                             "hoehe": 60}}]}}
    spec = {"art": "teil", "name": "T", "parameter": {"L": 100, "RA": 10, "ZG": 20}, "gleichungen": True,
            "features": [klotz, nb]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None, fehler  # Kontext.mass meldet eine abgelehnte Gleichung als GLEICHUNG_FEHLER
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        [paar] = [t for t in texte if "@f2_positionen" in t]  # Randmaß ohne Gleichung, nur der Paarabstand
        assert '2 * -"ZG"' in paar, texte
        f2 = ctx.ergebnis("f2").features[0]
        assert sorted({round(z.punkt[2], 4) for z in flaechen(f2) if z.art == "zylinder"}) == [-20.0, 20.0]
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"ZG" = 20'), '"ZG" = 25')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert sorted({round(z.punkt[2], 4) for z in flaechen(f2) if z.art == "zylinder"}) == [-25.0, 25.0]
