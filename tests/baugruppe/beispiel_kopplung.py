"""Zahnstangentrieb als Beispiel für die Kopplungen (Spec 4b §5.1) – nur für Tests ohne SolidWorks (Plausibilität,
Bewegungen, Bewertung). Die echte Referenz liegt in tests/referenz/zahnstangentrieb/."""

import copy

from swki.baugruppe.modell import Quelle


def _block(name: str, *weitere) -> dict:
    return {"art": "teil", "name": name, "parameter": {"L": 100, "B": 60, "H": 20},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "oben",
                                     "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                          "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


def _verzahnung(fid: str, art: str, zaehne: int, abstand: float = 0) -> dict:
    return {"id": fid, "typ": "verzahnung", "art": art, "ebene": {"versatz": {"ebene": "vorne", "abstand": abstand}},
            "mitte": [0, 0], "modul": "=M", "zaehne": zaehne, "breite": 10, "zahndickenabmass": -0.05}


def _welle(name: str, *verzahnungen) -> dict:
    return {"art": "teil", "name": name, "parameter": {"M": 2},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
                          "ende": {"typ": "blind", "tiefe": 80}},
                         *verzahnungen, {"id": "ACHSE", "typ": "referenz", "achse": "z"}]}


TEILE = {
    "grundplatte": _block("Grundplatte"),
    "schlitten": _block("Schlitten"),
    "zahnstange": {**_block("Zahnstange"), "parameter": {"L": 100, "B": 60, "H": 20, "M": 2},
                   "features": [*_block("Zahnstange")["features"], _verzahnung("z1", "zahnstange", 40)]},
    "lagerbock": _block("Lagerbock", {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
                                      "positionen": [[-30, 0], [30, 0]], "durchmesser": 12.5, "durch": True}),
    "ritzelwelle": _welle("Ritzelwelle", _verzahnung("z1", "stirnrad", 20, 10), _verzahnung("z2", "stirnrad", 25, 40)),
    "antriebswelle": _welle("Antriebswelle", _verzahnung("z1", "stirnrad", 50, 40)),
}


def _v(vid, typ, a, b, **weitere) -> dict:
    return {"id": vid, "typ": typ, "a": a, "b": b, **weitere}


def _f(k: str, flaeche: str, feature: str = "f1") -> dict:
    return {"komponente": k, "feature": feature, "flaeche": flaeche}


SPEC = {
    "art": "baugruppe", "name": "Trieb", "parameter": {"HUB": 220},
    "komponenten": [
        {"id": "grundplatte", "quelle": {"teil": "grundplatte.yaml"}, "fixiert": True},
        {"id": "schlitten", "quelle": {"teil": "schlitten.yaml"}, "gruppe": "schieber"},
        {"id": "zahnstange", "quelle": {"teil": "zahnstange.yaml"}, "gruppe": "schieber"},
        {"id": "lagerbock", "quelle": {"teil": "lagerbock.yaml"}},
        {"id": "ritzelwelle", "quelle": {"teil": "ritzelwelle.yaml"}},
        {"id": "antriebswelle", "quelle": {"teil": "antriebswelle.yaml"}},
    ],
    "verknuepfungen": [
        _v("v1", "deckungsgleich", _f("schlitten", "-y"), _f("grundplatte", "+y"), ausrichtung="entgegengesetzt"),
        _v("v2", "deckungsgleich", _f("schlitten", "-z"), _f("grundplatte", "-z"), ausrichtung="gleich"),
        _v("g1", "grenze_abstand", _f("schlitten", "-x"), _f("grundplatte", "-x"), ausrichtung="gleich", min=0,
           max="=HUB"),
        _v("v3", "deckungsgleich", _f("zahnstange", "-y"), _f("schlitten", "+y"), ausrichtung="entgegengesetzt"),
        _v("v4", "deckungsgleich", _f("zahnstange", "-x"), _f("schlitten", "-x"), ausrichtung="gleich"),
        _v("v5", "deckungsgleich", _f("zahnstange", "-z"), _f("schlitten", "-z"), ausrichtung="gleich"),
        _v("v6", "deckungsgleich", _f("lagerbock", "-y"), _f("grundplatte", "+y"), ausrichtung="entgegengesetzt"),
        _v("v7", "deckungsgleich", _f("lagerbock", "-x"), _f("grundplatte", "-x"), ausrichtung="gleich"),
        _v("v8", "deckungsgleich", _f("lagerbock", "+z"), _f("grundplatte", "+z"), ausrichtung="gleich"),
        _v("s1", "scharnier", {"komponente": "ritzelwelle", "referenz": "ACHSE"},
           {"komponente": "lagerbock", "feature": "f2", "instanz": 1, "achse": True},
           anlage_a=_f("ritzelwelle", "-z"), anlage_b=_f("lagerbock", "+y")),
        _v("s2", "scharnier", {"komponente": "antriebswelle", "referenz": "ACHSE"},
           {"komponente": "lagerbock", "feature": "f2", "instanz": 2, "achse": True},
           anlage_a=_f("antriebswelle", "-z"), anlage_b=_f("lagerbock", "+y")),
        _v("k1", "zahnstange", {"komponente": "ritzelwelle", "feature": "z1"}, {"komponente": "zahnstange", "feature": "z1"}),
        _v("k2", "zahnrad", {"komponente": "antriebswelle", "feature": "z1"}, {"komponente": "ritzelwelle", "feature": "z2"}),
    ],
    "freiheitsgrade": {"schieber": 1, "ritzelwelle": "gekoppelt", "antriebswelle": "gekoppelt"},
    "bewegungen": [{"name": "Schlittenhub", "grenze": "g1", "erwartet": {"endlagen": [
        {"komponente": "schlitten", "verschiebung": ["=HUB", 0, 0]},
        {"komponente": "zahnstange", "verschiebung": ["=HUB", 0, 0]},
        {"komponente": "ritzelwelle", "drehung": {"achse": [0, 0, -1], "winkel": "=HUB*360/(pi*40)"}},
        {"komponente": "antriebswelle", "drehung": {"achse": [0, 0, 1], "winkel": "=HUB*360/(pi*40)*25/50"}},
    ]}}],
}


def quellen(teile: dict | None = None) -> dict[str, Quelle]:
    teile = teile or TEILE
    return {k["id"]: Quelle("teil", teile[k["id"]], datei=k["quelle"]["teil"]) for k in SPEC["komponenten"]}


def spec() -> dict:
    return copy.deepcopy(SPEC)


def v(s: dict, vid: str) -> dict:
    return next(x for x in s["verknuepfungen"] if x["id"] == vid)
