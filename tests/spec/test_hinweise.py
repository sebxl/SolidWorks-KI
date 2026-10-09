from swki.spec.hinweise import feste_masse, hinweise, zusammenfassen
from swki.spec.normen import normmasse

from .beispiel import GUELTIG


FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _nb(fid, groesse="M8", **weiteres):
    return {"id": fid, "typ": "normbohrung", "art": "zylinderschraube", "groesse": groesse, "flaeche": FLAECHE,
            "positionen": [["=-L/2+20", 0]], "durch": True, **weiteres}


def _bohrung(fid, **weiteres):
    return {"id": fid, "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[1, 1]], "durchmesser": "=D",
            "durch": True, **weiteres}


def test_feste_zahl_hat_art():
    assert {h["art"] for h in feste_masse(GUELTIG)} == {"feste_zahl"}


def test_gleiche_bohrungen_zusammenfassen():
    spec = {"features": [_nb("f2"), _nb("f3", positionen=[[10, 10]]), _nb("f4", groesse="M10"),
                         _bohrung("f5"), _bohrung("f6", positionen=[[5, 1]])]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f2", "f3"], ["f5", "f6"]]
    assert ergebnis[0]["pfad"] == "features[0], features[1]"
    assert all(h["art"] == "zusammenfassen" and "Regel 2" in h["meldung"] for h in ergebnis)


def test_gleiche_kantenmasse_zusammenfassen():
    spec = {"features": [
        {"id": "f1", "typ": "fase", "kanten": [{"nahe": [0, 0, 0]}], "abstand": 1},
        {"id": "f2", "typ": "fase", "kanten": [{"nahe": [1, 0, 0]}], "abstand": 1},
        {"id": "f3", "typ": "fase", "kanten": [{"nahe": [2, 0, 0]}], "abstand": 2},
        {"id": "f4", "typ": "verrundung", "kanten": [{"nahe": [3, 0, 0]}], "radius": "=R"},
        {"id": "f5", "typ": "verrundung", "kanten": [{"nahe": [4, 0, 0]}], "radius": "=R"},
    ]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f1", "f2"], ["f4", "f5"]]
    assert all("Regel 6" in h["meldung"] for h in ergebnis)


def test_muster_und_spiegeln_mit_festen_zahlen():
    klotz = {"id": "f2", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 5}}]}, "ende": {"typ": "blind", "tiefe": 5}}
    spec = {"features": [
        _bohrung("f1"), klotz,
        {"id": "f3", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 3}},
        {"id": "f4", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": "=A", "anzahl": 3}},
        {"id": "f5", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4},
        {"id": "f6", "typ": "spiegeln", "features": ["f1"], "ebene": "vorne"},
        {"id": "f7", "typ": "spiegeln", "features": ["f2"], "ebene": "vorne"},
    ]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f3"], ["f5"], ["f6"]]
    assert all("Regel 3" in h["meldung"] for h in ergebnis)


def test_senkung_wie_iso_4762():
    m8 = normmasse("zylinderschraube", "M8")
    spec = {"features": [_bohrung("f1", durchmesser=m8["durchgang"],
                                  senkung={"durchmesser": m8["senkung_d"], "tiefe": 5})]}
    [h] = zusammenfassen(spec)
    assert h["knoten"] == ["f1"] and "ISO 4762 M8" in h["meldung"] and "normbohrung" in h["meldung"]


def test_hinweise_erst_feste_zahlen_dann_zusammenfassen():
    alle = hinweise(GUELTIG)
    fest = feste_masse(GUELTIG)
    assert alle[: len(fest)] == fest
    assert [h["knoten"] for h in alle[len(fest):]] == [["f5"]]  # muster_linear mit festem Abstand 20


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


def _rotation(**skizze):
    return {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[0, 0], ["=R", 0], ["=R", "=H"], [0, "=H"]]}},
        {"mittellinie": {"von": [0, -5], "bis": [0, 5]}}, *skizze.get("weitere", [])]}}


def test_mittellinie_ist_kein_anforderungsmass():
    assert feste_masse({"features": [_rotation()]}) == []


def test_vollkreis_und_standardfase_sind_keine_hinweise():
    spec = {"features": [
        {"id": "f1", "typ": "muster_kreis", "features": ["f0"], "achse": "y", "anzahl": 6, "winkel": 360},
        {"id": "f2", "typ": "fase", "kanten": [{"nahe": [0, 0, 0]}], "abstand": "=F", "winkel": 45},
        {"id": "f3", "typ": "fase", "kanten": [{"nahe": [1, 0, 0]}], "abstand": "=F", "winkel": 30},
    ]}
    assert [h["pfad"] for h in feste_masse(spec)] == ["features[2].winkel"]


def test_polygonpunkte_als_ein_sammelhinweis():
    spec = {"features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"polygon": {"punkte": [[15, 40], [17, 40], [17, 43], [15, 43]]}}]}, "ende": {"typ": "blind", "tiefe": "=T"}}]}
    [h] = feste_masse(spec)
    assert h["pfad"] == "features[0].skizze.elemente[0].polygon.punkte"
    assert h["meldung"].startswith("8 feste Zahlen")


def test_kontur_als_ein_sammelhinweis():
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                            {"linie": [0, 30]}, {"linie": [0, 0]}]}
    spec = {"features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"kontur": kontur}]}, "ende": {"typ": "blind", "tiefe": "=T"}}]}
    [h] = feste_masse(spec)
    assert h["pfad"] == "features[0].skizze.elemente[0].kontur"
    assert h["meldung"].startswith("6 feste Zahlen")  # 40, 40, 30, 40, 15, 30 (Nullen zählen nicht)


def test_muster_mit_ausdruecken_kein_hinweis():
    spec = {"features": [
        _bohrung("f1"),
        {"id": "f2", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 2},
         "richtung2": {"achse": "z", "abstand": "=A", "anzahl": 2}},
        {"id": "f3", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4, "winkel": "=W"},
    ]}
    assert zusammenfassen(spec) == []


def test_kreismuster_text_nennt_anzahl_als_zahl():
    spec = {"features": [_bohrung("f1"), {"id": "f2", "typ": "muster_kreis", "features": ["f1"], "achse": "y",
                                          "anzahl": 4}]}
    [h] = zusammenfassen(spec)
    assert "Regel 3" in h["meldung"] and "Anzahl ist immer eine Zahl" in h["meldung"]


def test_senkung_ohne_iso_treffer_und_mit_ausdrucksfehler():
    spec = {"parameter": {}, "features": [
        _bohrung("f1", durchmesser=9, senkung={"durchmesser": 16, "tiefe": 5}),      # Senkung passt zu keiner Größe
        _bohrung("f2", durchmesser="=X", senkung={"durchmesser": 15, "tiefe": 5}),   # unbekannter Parameter
    ]}
    assert [h for h in zusammenfassen(spec) if "ISO 4762" in h["meldung"]] == []


def test_pruefwert_hinweis_bei_abweichendem_huellquader():
    """Retro Messstand: von Hand gerechnete Hüllquader weichen ab → Hinweis vor der Freigabe."""
    spec = {**GUELTIG, "pruefung": {**GUELTIG["pruefung"], "huellquader": ["=L", 30, "=B"]}}
    [h] = [h for h in hinweise(spec) if h["art"] == "pruefwert"]
    assert h["pfad"] == "pruefung.huellquader" and "[100, 20, 60]" in h["meldung"]
    assert not [h for h in hinweise(GUELTIG) if h["art"] == "pruefwert"]
