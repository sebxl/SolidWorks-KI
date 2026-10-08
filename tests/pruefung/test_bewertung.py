import copy

import pytest

from swki.pruefung.bewertung import Messwerte, baum_kennzahl, bewerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.spec.normen import normmasse

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
    assert ids == ["rebuild", "skizzen", "koerper", "huellquader", "volumen", "mass:Achsabstand", "schwerpunkt",
                   "material", "eigenschaften"]


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


NB = {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
      "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+10", 0], ["=L/2-10", 0]], "durch": True}
# Durchgangsbohrungen auf der Plattenfläche: das Sollvolumen wäre berechenbar (Messstand Umbau 2) – hier ohne Volumen,
# die Messwerte-Attrappe kennt nur die Platte
OHNE_VOLUMEN = {k: v for k, v in SPEC["pruefung"].items() if k != "volumen"}
SPEC_NB = {**SPEC, "features": [*SPEC["features"], NB], "pruefung": OHNE_VOLUMEN}
# typ = swWzdHoleTypes_e (Art und Ende zusammen): ISO 4762 durch = 14
IST_NB = {"typ": 14, "befestigung": 139, "norm": 8, "groesse": normmasse("zylinderschraube", "M8")["sw_groesse"],
          "ende": 1, "tiefe": 0.0, "gewindetiefe": 0.0, "positionen": 2}


def test_normbohrung_passt():
    bericht = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": IST_NB}), STANDARD)
    assert bericht["bestanden"] is True
    assert [p["id"] for p in bericht["pruefungen"]][:3] == ["rebuild", "skizzen", "normbohrungen"]


def test_normbohrung_groesse_weicht_ab():
    [mangel] = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": IST_NB | {"groesse": "M10"}}), STANDARD)["maengel"]
    assert mangel["pruefung"] == "normbohrungen" and mangel["knoten"] == ["f2"]
    assert "groesse: ist M10" in mangel["beschreibung"]


def test_normbohrung_fehlt_im_teil():
    [mangel] = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": "Feature f2 fehlt im Teil"}), STANDARD)["maengel"]
    assert mangel["knoten"] == ["f2"] and "fehlt" in mangel["beschreibung"]


def test_normbohrung_soll_aus_freigegebener_kopie():
    # Nachgebessert auf M10 (Text, von der Prüfsumme nicht geschützt): gebaut ist M10, Soll bleibt M8
    nachgebessert = copy.deepcopy(SPEC_NB)
    nachgebessert["features"][1]["groesse"] = "M10"
    ist = IST_NB | {"groesse": normmasse("zylinderschraube", "M10")["sw_groesse"]}
    bericht = bewerte(nachgebessert, _messwerte(normbohrungen={"f2": ist}), STANDARD, freigegeben=SPEC_NB)
    assert [m["pruefung"] for m in bericht["maengel"]] == ["normbohrungen"]


def test_normbohrung_tiefen():
    gewinde = {k: v for k, v in NB.items() if k != "durch"} | {"art": "gewinde", "groesse": "M10", "tiefe": "=T",
                                                               "gewindetiefe": 12}
    ohne_volumen = {k: v for k, v in SPEC["pruefung"].items() if k != "volumen"}  # Sackloch: Soll wäre berechenbar
    spec = {**SPEC, "parameter": {"L": 100, "T": 16}, "features": [SPEC["features"][0], gewinde], "pruefung": ohne_volumen}
    ist = IST_NB | {"typ": 46, "befestigung": 147, "groesse": normmasse("gewinde", "M10")["sw_groesse"], "ende": 0,
                    "tiefe": 16.0, "gewindetiefe": 11.0}
    [mangel] = bewerte(spec, _messwerte(normbohrungen={"f2": ist}), STANDARD)["maengel"]
    assert mangel["beschreibung"] == "normbohrungen: {'f2': ['gewindetiefe: ist 11 statt 12']}"


def test_normbohrung_stift_durch():
    # Stift mit durch (CreateDefinition) liest FastenerType2 = -1; die Art zeigt dann nur Type = 25 (swHoleThru)
    stift = {**NB, "art": "stift", "groesse": 8}
    spec = {**SPEC, "features": [SPEC["features"][0], stift], "pruefung": OHNE_VOLUMEN}
    ist = IST_NB | {"typ": 25, "befestigung": -1, "groesse": normmasse("stift", 8)["sw_groesse"]}
    assert bewerte(spec, _messwerte(normbohrungen={"f2": ist}), STANDARD)["bestanden"] is True
    [mangel] = bewerte(spec, _messwerte(normbohrungen={"f2": ist | {"typ": 22}}), STANDARD)["maengel"]
    assert mangel["knoten"] == ["f2"] and "typ: ist 22 statt 25" in mangel["beschreibung"]


def test_baum_kennzahl():
    protokoll = {"knoten": [{"id": "f1", "sw_name": "f1"}, {"id": "f2", "sw_name": "f2, f2_senkung"},
                            {"id": "f3", "sw_name": None}]}
    assert baum_kennzahl(SPEC_NB, protokoll) == {"knoten": 2, "features": 3}
    assert baum_kennzahl(SPEC_NB, None) == {"knoten": 2, "features": 0}


def test_ein_koerper_besteht():
    bericht = bewerte(SPEC, _messwerte(koerper=1), STANDARD)
    koerper = next(p for p in bericht["pruefungen"] if p["id"] == "koerper")
    assert koerper["ok"] is True and bericht["bestanden"] is True


def test_mehrere_koerper_sind_ein_mangel():
    bericht = bewerte(SPEC, _messwerte(koerper=2), STANDARD)
    [mangel] = bericht["maengel"]
    assert bericht["bestanden"] is False
    assert mangel["pruefung"] == "koerper" and mangel["beschreibung"] == "koerper: 2 Volumenkörper statt 1"


def test_koerper_ohne_angabe_gilt_als_ein_koerper():
    assert _messwerte().koerper == 1


DM_SPEC = {**SPEC, "features": SPEC["features"] + [{"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"}],
           "pruefung": {"durchmesser_pruefen": [
               {"was": "d", "feature": "f1", "nahe": [5, 10, 0], "soll": 10, "referenz": "EINBAU_ACHSE"}]}}


def _dm(d=10.0, achspunkt=(0.0, 0.0, 0.0)):
    return {"d": {"durchmesser": d, "achse": Messgeometrie("achse", achspunkt, (0, 1, 0)),
                  "referenz": Messgeometrie("achse", (0, 5, 0), (0, -1, 0))}}


def test_durchmesser_ok():
    bericht = bewerte(DM_SPEC, _messwerte(durchmesser=_dm()), STANDARD)
    [p] = [p for p in bericht["pruefungen"] if p["id"] == "durchmesser:d"]
    assert bericht["bestanden"] and p["ok"] is True and p["ist"] == 10.0 and p["achsversatz"] == 0.0


@pytest.mark.parametrize("messung", [
    _dm(d=10.05),                                          # Durchmesser außerhalb 0,01
    _dm(achspunkt=(0.5, 0.0, 0.0)),                        # nicht koaxial zur Bezugsachse
    "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche",       # Messung gescheitert
])
def test_durchmesser_mangel(messung):
    m = _messwerte(durchmesser=messung if isinstance(messung, dict) else {"d": messung})
    bericht = bewerte(DM_SPEC, m, STANDARD)
    assert [x["pruefung"] for x in bericht["maengel"]] == ["durchmesser:d"]
    assert bericht["maengel"][0]["knoten"] == ["f1"]
