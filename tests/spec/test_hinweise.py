from swki.spec.hinweise import feste_masse

from .beispiel import GUELTIG


def test_feste_masse_im_beispiel():
    # Null (Lage auf Achse/Ebene), Ausdrücke, Anzahlen und Anker ("nahe") bleiben unbeanstandet
    assert [h["pfad"] for h in feste_masse(GUELTIG)] == [
        "features[1].durchmesser", "features[2].radius", "features[3].abstand", "features[4].richtung1.abstand",
    ]


def test_verschachtelte_masse():
    spec = {"features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": -15}},
                    "elemente": [{"rechteck": {"mitte": [5, 0], "breite": "=L", "hoehe": 10}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"nahe": [0, 20, 0]}, "positionen": [[12.5, "=B"]],
         "durchmesser": "=D", "tiefe": "=T", "senkung": {"durchmesser": 14, "tiefe": "=S"}},
    ]}
    hinweise = feste_masse(spec)
    assert [h["pfad"] for h in hinweise] == [
        "features[0].skizze.ebene.versatz.abstand", "features[0].skizze.elemente[0].rechteck.mitte[0]",
        "features[0].skizze.elemente[0].rechteck.hoehe", "features[1].positionen[0][0]",
        "features[1].senkung.durchmesser",
    ]
    assert "-15" in hinweise[0]["meldung"]


def test_nur_parameter_keine_hinweise():
    spec = {"features": [{"id": "f1", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": "=F",
                          "winkel": "=W"}]}
    assert feste_masse(spec) == []
