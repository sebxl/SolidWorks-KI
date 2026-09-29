import copy

import pytest

from swki.pruefung.bewertung import Messwerte, bewerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
VON = {"feature": "f2", "instanz": 1, "achse": True}
ZU = {"feature": "f2", "instanz": 2, "achse": True}
SPEC = {
    "art": "teil", "name": "P", "material": "1.2312", "eigenschaften": {"Benennung": "Platte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]}, "ende": {"typ": "blind", "tiefe": 20}},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "volumen": {"soll": "auto"},
        "masse_pruefen": [{"was": "Achsabstand", "von": VON, "zu": ZU, "soll": 80}],
        "schwerpunkt": {"soll": [0, None, 0]},
    },
}


def _messwerte(**aenderungen) -> Messwerte:
    werte = dict(
        rebuild_fehler=[], skizzen={"f1_skizze": 3}, box=[-50, 0, -30, 50, 20, 30], volumen=120000.0,
        schwerpunkt=(0.0, 10.0, 0.0), material="1.2312 (40CrMnMoS8-6)", eigenschaften={"Benennung": "Platte", "Auftrag": "A"},
        messpunkte={
            messpunkt_schluessel(VON): Messgeometrie("achse", (-40, 20, 0), (0, 1, 0)),
            messpunkt_schluessel(ZU): Messgeometrie("achse", (40, 0, 0), (0, -1, 0)),
        },
    )
    werte.update(aenderungen)
    return Messwerte(**werte)


def test_alles_bestanden():
    bericht = bewerte(SPEC, _messwerte(), STANDARD)
    assert bericht["bestanden"] is True and bericht["maengel"] == []
    ids = [p["id"] for p in bericht["pruefungen"]]
    assert ids == ["rebuild", "skizzen", "huellquader", "volumen", "mass:Achsabstand", "schwerpunkt", "material",
                   "eigenschaften"]


def test_maengel_mit_knoten():
    spec = copy.deepcopy(SPEC)
    spec["features"].append({"id": "f2", "typ": "skript", "datei": "skripte/f2.py", "luecke": "Gewinde"})
    m = _messwerte(rebuild_fehler=["f2_senkung: Code 71"], skizzen={"f1/f1_skizze": 3, "f2_2/Skizze7": 2},
                   box=[-50, 0, -30, 50, 21, 30], volumen=118000.0)
    bericht = bewerte(spec, m, STANDARD)
    assert bericht["bestanden"] is False
    maengel = {x["pruefung"]: x for x in bericht["maengel"]}
    assert maengel["rebuild"]["knoten"] == ["f2"]
    assert maengel["skizzen"]["knoten"] == ["f2"]
    assert maengel["huellquader"]["beschreibung"] == "huellquader: ist [100, 21, 60] statt [100.0, 20.0, 60.0]"
    assert "volumen" not in maengel  # mit Skript ist das Sollvolumen nicht analytisch berechenbar (Hinweis, kein Mangel)


def test_masspruefung_falsch_und_nicht_messbar():
    m = _messwerte()
    m.messpunkte[messpunkt_schluessel(ZU)] = Messgeometrie("achse", (41, 0, 0), (0, 1, 0))
    [mangel] = bewerte(SPEC, m, STANDARD)["maengel"]
    assert mangel["knoten"] == ["f2"] and "ist 81" in mangel["beschreibung"]
    m.messpunkte[messpunkt_schluessel(ZU)] = "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche für Instanz 2"
    [mangel] = bewerte(SPEC, m, STANDARD)["maengel"]
    assert "Instanz 2" in mangel["beschreibung"]


def test_volumen_nicht_berechenbar_ist_kein_mangel():
    spec = copy.deepcopy(SPEC)
    spec["features"].append({"id": "f2", "typ": "verrundung", "kanten": [{"nahe": [0, 0, 0]}], "radius": 2})
    bericht = bewerte(spec, _messwerte(), STANDARD)
    volumen = next(p for p in bericht["pruefungen"] if p["id"] == "volumen")
    assert volumen["ok"] is None and "f2: verrundung" in volumen["hinweis"]
    assert bericht["bestanden"] is True


def test_material_und_eigenschaften():
    bericht = bewerte(SPEC, _messwerte(material="Stahl", eigenschaften={}), STANDARD)
    assert {x["pruefung"] for x in bericht["maengel"]} == {"material", "eigenschaften"}


def test_schwerpunkt_spiegelfehler():
    [mangel] = bewerte(SPEC, _messwerte(schwerpunkt=(0.0, 10.0, -3.0)), STANDARD)["maengel"]
    assert mangel["pruefung"] == "schwerpunkt"


@pytest.mark.parametrize("mp", [VON, {"punkt": [0, 0, 0]}, {"feature": "f1", "flaeche": "+y"}])
def test_messpunkt_schluessel_stabil(mp):
    assert messpunkt_schluessel(mp) == messpunkt_schluessel(dict(reversed(list(mp.items()))))


def test_sollvolumen_aus_freigegebener_spec():
    # Nachgebessert: Tiefe im Bauweg auf 21 geändert (fest eingetragen, von der Prüfsumme nicht erfasst) –
    # das Soll kommt aus der freigegebenen Kopie (Tiefe 20), das zu hohe Volumen wird ein Mangel
    nachgebessert = copy.deepcopy(SPEC)
    nachgebessert["features"][0]["ende"]["tiefe"] = 21
    bericht = bewerte(nachgebessert, _messwerte(volumen=126000.0), STANDARD, freigegeben=SPEC)
    volumen = next(p for p in bericht["pruefungen"] if p["id"] == "volumen")
    assert volumen["soll"] == 120000.0 and volumen["ok"] is False
