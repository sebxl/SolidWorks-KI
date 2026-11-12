"""Abgleich Spec-Stand gegen Ist (Spec Bestandsdateien §8.6): rein, ohne SolidWorks.

Protokollform wie ein echter Lauf: Teil mit `f1` (Extrusion), `winkel` (Schnitt) und `gewinde` (Normbohrung, Bohrungsassistent mit
Unterfeatures); Baugruppe mit `komponenten`, Knoten `komponente` und Verknüpfungs-Knoten."""

import copy

import pytest

from swki.bestand.abgleich import (abgleich_baugruppe, abgleich_dateien, abgleich_teil, ist_erklaert, normalisiere_lagen,
                                   ungeprueft_teil)


def _m(name, wert, art="groesse", einheit="mm"):
    return {"name": name, "pfad": "features[0].profil.laenge", "art": art, "bezug": None, "roh": wert, "vorzeichen": 1,
            "wert": wert, "einheit": einheit}


def _f(name, typ, eltern=(), kinder=(), unter=()):
    return {"name": name, "typ": typ, "eltern": list(eltern), "kinder": list(kinder), "unter": list(unter),
            "unterdrueckt": {"Standard": False}, "tabelle": False}


def _ist_masse(name, feature, wert, zustand="treibend", einheit="mm"):
    return {"name": name, "feature": feature, "werte": {"Standard": wert}, "einheit": einheit, "zustand": zustand, "quelle": None,
            "gruppe": None, "punkte": []}


PROTOKOLL_TEIL = {"status": "ok", "knoten": [
    {"id": "f1", "typ": "extrusion", "sw_name": "f1", "status": "ok", "punkte": None,
     "masse": [_m("D1@f1_skizze", 40.0), _m("D2@f1_skizze", 20.0), _m("D1@f1", 8.0, "tiefe")]},
    {"id": "winkel", "typ": "schnitt", "sw_name": "winkel", "status": "ok", "punkte": None,
     "masse": [_m("D1@winkel_skizze", 12.0), _m("D1@winkel", 3.0, "tiefe")]},
    {"id": "gewinde", "typ": "normbohrung", "sw_name": "gewinde", "status": "ok", "punkte": [[10.0, 5.0, 8.0]],
     "masse": [_m("D1@gewinde_positionen", 10.0, "lage")]}]}

SPEC_TEIL = {"name": "Platte", "material": "1.0038", "eigenschaften": {"Benennung": "Platte"}}


def _ist_teil():
    return {
        "aktiv": "Standard", "konfigurationen": ["Standard"], "material": "1.0038 (S235JR)", "gleichungen": [], "variablen": {},
        "eigenschaften": {"datei": {"Ersteller": "SolidWorks-KI", "Auftrag": "A", "Material": "1.0038", "Benennung": "Platte"},
                          "konfiguration": {"Standard": {}}},
        "features": [
            _f("Ebene vorne", "RefPlane"), _f("Ebene oben", "RefPlane"), _f("Ebene rechts", "RefPlane"),
            _f("Ursprung", "OriginProfileFeature"),
            _f("f1_skizze", "ProfileFeature", kinder=["f1"]),
            _f("f1", "Extrusion", eltern=["f1_skizze"], unter=["f1_skizze"]),
            _f("winkel_skizze", "ProfileFeature", kinder=["winkel"]),
            _f("winkel", "ICE", eltern=["winkel_skizze"], unter=["winkel_skizze"]),
            _f("Skizze5", "ProfileFeature"), _f("gewinde_positionen", "ProfileFeature"),
            _f("gewinde", "HoleWzd", unter=["Skizze5", "gewinde_positionen"])],
        "masse": [_ist_masse("D1@f1_skizze", "f1_skizze", 40.0), _ist_masse("D2@f1_skizze", "f1_skizze", 20.0),
                  _ist_masse("D1@f1", "f1", 8.0), _ist_masse("D1@winkel_skizze", "winkel_skizze", 12.0),
                  _ist_masse("D1@winkel", "winkel", 3.0), _ist_masse("D1@gewinde_positionen", "gewinde_positionen", 10.0)],
    }


def _namen(liste):
    return [e["name"] for e in liste]


def test_unveraendertes_teil_nennt_nichts():
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, _ist_teil(), auftrag="A")
    assert a["features_neu"] == [] and a["features_fehlen"] == []
    assert a["masse"] == [] and a["masse_neu"] == [] and a["material"] is None
    assert a["eigenschaften"] == {"geaendert": [], "fehlen": [], "neu": []}
    assert a["vollstaendig"] is True and a["luecken"] == []
    # Nichts gefunden: die geänderte Datei bleibt unerklärt (der Aufrufer weiß, dass die SHA-256 abweicht)
    assert a["nicht_erklaert"] is True


def test_neues_feature_wird_genannt():
    ist = _ist_teil()
    ist["features"].append(_f("Verrundung1", "Fillet", eltern=["f1"]))
    ist["features"][5]["kinder"].append("Verrundung1")   # f1 hat jetzt ein Kind: das Kind ist nicht dadurch erklärt
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert _namen(a["features_neu"]) == ["Verrundung1"] and a["features_neu"][0]["typ"] == "Fillet"
    assert a["features_neu"][0]["eltern"] == ["f1"]
    assert a["features_fehlen"] == [] and a["nicht_erklaert"] is False


def test_neue_skizze_ohne_zugehoeriges_feature_wird_genannt():
    ist = _ist_teil()
    ist["features"].append(_f("Skizze10", "ProfileFeature"))
    assert _namen(abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["features_neu"]) == ["Skizze10"]


def test_umbenanntes_feature_ist_weg_und_neu():
    ist = _ist_teil()
    ist["features"][5]["name"] = "Grundkoerper"
    ist["masse"][2]["name"] = "D1@Grundkoerper"
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["features_fehlen"] == [{"name": "f1", "knoten": "f1", "typ": "extrusion"}]
    assert _namen(a["features_neu"]) == ["Grundkoerper"]
    assert [m["name"] for m in a["masse"]] == ["D1@f1"] and a["masse"][0]["ist"] is None   # das Maß heißt jetzt anders


def test_geloeschtes_feature_fehlt():
    ist = _ist_teil()
    del ist["features"][7]
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert _namen(a["features_fehlen"]) == ["winkel"] and a["nicht_erklaert"] is False


def test_skizze_eines_soll_features_ist_erklaert():
    """Eine Skizze, die weder im Soll noch im Maßprotokoll steht, aber Unterfeature eines Soll-Features ist."""
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    for k in protokoll["knoten"]:
        k["masse"] = []
    ist = _ist_teil()
    ist["features"][4]["name"] = "Skizze1"
    ist["features"][5]["unter"] = ["Skizze1"]
    ist["features"][5]["eltern"] = ["Skizze1"]
    ist["masse"] = []
    a = abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")
    assert a["features_neu"] == []
    assert ist_erklaert(ist["features"][4], {"f1", "winkel", "gewinde"}, {f["name"]: f for f in ist["features"]})


def test_hilfsskizzen_des_compilers_sind_erklaert():
    """`<id>_skizze` und `<id>_positionen` ohne Maße und ohne Beziehung zum Feature."""
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    for k in protokoll["knoten"]:
        k["masse"] = []
    ist = _ist_teil()
    ist["masse"] = []
    ist["features"] = [f for f in ist["features"] if f["name"] != "Skizze5"]
    for f in ist["features"]:
        f["unter"] = []
    assert abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")["features_neu"] == []


def test_unterfeature_des_bohrungsassistenten_ist_erklaert():
    ist = _ist_teil()
    ist["features"].insert(10, _f("Gewinde-M5", "ProfileFeature"))     # Name unbekannt, nur über `unter` erklärt
    ist["features"][-1]["unter"].append("Gewinde-M5")
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["features_neu"] == []
    assert ist_erklaert(ist["features"][10], {"gewinde"}, {f["name"]: f for f in ist["features"]})


def test_vorlage_ist_erklaert():
    ist = _ist_teil()
    alle = {f["name"]: f for f in ist["features"]}
    soll = {"f1", "winkel", "gewinde"}
    for name in ("Ebene vorne", "Ebene oben", "Ebene rechts", "Ursprung"):
        assert ist_erklaert(alle[name], soll, alle), name
    assert ist_erklaert(_f("Notizen", "CommentsFolder"), soll, alle)


def test_vorlage_gilt_nicht_fuer_spaeter_eingefuegte_ebene():
    ist = _ist_teil()
    ist["features"].append(_f("Ebene1", "RefPlane", eltern=["f1"]))
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert _namen(a["features_neu"]) == ["Ebene1"]


def test_vierte_ebene_am_anfang_ist_neu():
    ist = _ist_teil()
    ist["features"].insert(3, _f("Ebene1", "RefPlane"))
    assert _namen(abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["features_neu"]) == ["Ebene1"]


def test_unbekannter_typ_zaehlt_als_neu():
    ist = _ist_teil()
    ist["features"].insert(0, _f("Koordinatensystem1", "CoordSys"))
    assert _namen(abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["features_neu"]) == ["Koordinatensystem1"]


def test_ebene_des_compilers_ueber_das_massprotokoll_erklaert():
    """Eine versetzte Skizzenebene entsteht ohne Namen (`Ebene1`), ihr Maß `D1@Ebene1` steht im Maßprotokoll des Knotens."""
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][0]["masse"].append(_m("D1@Ebene1", 5.0, "versatz"))
    ist = _ist_teil()
    ist["features"].insert(5, _f("Ebene1", "RefPlane"))
    ist["masse"].append(_ist_masse("D1@Ebene1", "Ebene1", 5.0))
    assert abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")["features_neu"] == []


def test_referenzachse_des_musters_ist_erklaert():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"].append({"id": "m1", "typ": "muster_linear", "sw_name": "m1", "status": "ok", "masse": []})
    ist = _ist_teil()
    ist["features"] += [_f("achse_x", "RefAxis"), _f("m1", "LPattern")]
    assert abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")["features_neu"] == []


def test_skript_features_mit_nummer_stehen_im_sw_namen():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][0]["sw_name"] = "f1, f1_2"
    ist = _ist_teil()
    ist["features"].insert(6, _f("f1_2", "Extrusion"))
    a = abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")
    assert a["features_neu"] == [] and a["features_fehlen"] == []
    del ist["features"][6]
    assert _namen(abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")["features_fehlen"]) == ["f1_2"]


def test_sw_namen_haben_vorrang_vor_sw_name():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][0]["sw_name"] = "f1, f1_2"
    protokoll["knoten"][0]["sw_namen"] = ["f1", "f1_2"]
    ist = _ist_teil()
    ist["features"].insert(6, _f("f1_2", "Extrusion"))
    assert abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")["features_neu"] == []


def test_masse_geaendert_und_neu():
    ist = _ist_teil()
    ist["masse"][0]["werte"]["Standard"] = 45.0
    ist["masse"].append(_ist_masse("D3@f1_skizze", "f1_skizze", 7.0))
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert [(m["name"], m["soll"], m["ist"]) for m in a["masse"]] == [("D1@f1_skizze", 40.0, 45.0)]
    assert [(m["name"], m["feature"], m["ist"]) for m in a["masse_neu"]] == [("D3@f1_skizze", "f1_skizze", 7.0)]
    assert a["nicht_erklaert"] is False


def test_masse_vergleich_nimmt_den_betrag_und_gleiche_werte_sind_keine_abweichung():
    ist = _ist_teil()
    ist["masse"][2]["werte"]["Standard"] = -8.0000001
    assert abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["masse"] == []


def test_ganzzahlige_masse_sind_keine_neuen_masse():
    ist = _ist_teil()
    ist["masse"].append(_ist_masse("D1@Muster1", "Muster1", 3, einheit=""))
    assert abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["masse_neu"] == []


def test_material_und_eigenschaften():
    ist = _ist_teil()
    ist["material"] = "Aluminium 6061"
    ist["eigenschaften"]["datei"]["Benennung"] = "Deckel"
    del ist["eigenschaften"]["datei"]["Ersteller"]
    ist["eigenschaften"]["datei"]["Zeichnung"] = "Z-1"
    ist["eigenschaften"]["konfiguration"]["Standard"] = {"Gewicht": "2 kg"}
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["material"] == {"soll": "1.0038", "ist": "Aluminium 6061"}
    assert a["eigenschaften"]["geaendert"] == [{"name": "Benennung", "soll": "Platte", "ist": "Deckel"}]
    assert a["eigenschaften"]["fehlen"] == [{"name": "Ersteller", "soll": "SolidWorks-KI"}]
    assert a["eigenschaften"]["neu"] == [{"name": "Zeichnung", "ist": "Z-1", "konfiguration": None},
                                         {"name": "Gewicht", "ist": "2 kg", "konfiguration": "Standard"}]
    assert a["nicht_erklaert"] is False


def test_material_ohne_soll_aber_in_der_datei_wird_genannt():
    spec = {"name": "Platte"}
    ist = _ist_teil()
    ist["eigenschaften"]["datei"].pop("Material")
    ist["eigenschaften"]["datei"].pop("Benennung")
    a = abgleich_teil(PROTOKOLL_TEIL, spec, ist, auftrag="A")
    assert a["material"] == {"soll": None, "ist": "1.0038 (S235JR)"}


def test_auftrag_ohne_angabe_wird_nicht_beurteilt():
    ist = _ist_teil()
    ist["eigenschaften"]["datei"]["Auftrag"] = "ganz anders"
    assert abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist)["eigenschaften"]["neu"] == []
    assert abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["eigenschaften"]["geaendert"] == [
        {"name": "Auftrag", "soll": "A", "ist": "ganz anders"}]


def test_ohne_daten_sagt_der_teil_abgleich_nie_unveraendert():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    for k in protokoll["knoten"]:
        k.pop("sw_name")
        k.pop("masse")
    a = abgleich_teil(protokoll, SPEC_TEIL, _ist_teil(), auftrag="A")
    assert a["features_geprueft"] is False and a["masse_geprueft"] is False and a["vollstaendig"] is False
    assert a["nicht_erklaert"] is True and len(a["luecken"]) == 3      # Features, Maße, Gleichungen
    assert a["features_neu"] == [] and a["features_fehlen"] == []      # nichts behauptet


def test_von_hand_unterdrueckte_features_werden_genannt():
    ist = _ist_teil()
    ist["features"][5]["unterdrueckt"] = {"Standard": True}
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["features_unterdrueckt"] == [{"name": "f1", "konfiguration": "Standard"}] and a["nicht_erklaert"] is False


def test_geaenderte_reihenfolge_wird_genannt():
    ist = _ist_teil()
    ist["features"][5], ist["features"][7] = ist["features"][7], ist["features"][5]      # f1 und winkel getauscht
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["reihenfolge"] == {"soll": ["f1", "winkel", "gewinde"], "ist": ["winkel", "f1", "gewinde"]}
    assert a["nicht_erklaert"] is False


def test_eingefuegtes_feature_aendert_die_reihenfolge_der_soll_features_nicht():
    ist = _ist_teil()
    ist["features"].insert(6, _f("Verrundung1", "Fillet", eltern=["f1"]))
    assert abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")["reihenfolge"] is None


def test_von_hand_angelegte_gleichungen_werden_genannt():
    ist = _ist_teil()
    ist["gleichungen"] = [{"index": 0, "text": '"L"= 40', "links": "L", "global": True},
                          {"index": 1, "text": '"D1@f1_skizze" = "L"', "links": "D1@f1_skizze", "global": False}]
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert [g["links"] for g in a["gleichungen_neu"]] == ["L", "D1@f1_skizze"] and a["nicht_erklaert"] is False


def test_gleichungen_der_spec_werden_nicht_beurteilt_aber_als_luecke_genannt():
    ist = _ist_teil()
    ist["gleichungen"] = [{"index": 0, "text": '"L"= 40', "links": "L", "global": True}]
    a = abgleich_teil(PROTOKOLL_TEIL, {**SPEC_TEIL, "gleichungen": True}, ist, auftrag="A")
    assert a["gleichungen_neu"] == [] and a["vollstaendig"] is False and "gleichungen: true" in a["luecken"][0]


def test_ist_ohne_features_ist_eine_luecke():
    ist = _ist_teil()
    del ist["features"]
    a = abgleich_teil(PROTOKOLL_TEIL, SPEC_TEIL, ist, auftrag="A")
    assert a["features_geprueft"] is False and a["vollstaendig"] is False and a["nicht_erklaert"] is True


def test_ungeprueft_teil_nennt_den_grund():
    a = ungeprueft_teil("Datei nicht lesbar")
    assert a["nicht_erklaert"] is True and a["vollstaendig"] is False and a["luecken"] == ["Datei nicht lesbar"]
    assert a["features_neu"] == [] and a["masse"] == [] and a["material"] is None


# --- Dateien --------------------------------------------------------------------------------------------------------

def test_dateien_geaendert_neu_fehlend():
    soll = {"A.sldprt": "1", "B.sldprt": "2", "C.sldprt": "3"}
    ist = {"a.SLDPRT": "1", "B.sldprt": "9", "D.sldprt": "4"}
    a = abgleich_dateien(soll, ist)
    assert a == {"geaendert": ["B.sldprt"], "neu": ["D.sldprt"], "fehlend": ["C.sldprt"]}


def test_dateien_ohne_protokolleintrag_sind_neu_auch_normteil_kopien():
    assert abgleich_dateien({}, {"swki/ISO4762_M5x20.sldprt": "x"})["neu"] == ["swki/ISO4762_M5x20.sldprt"]


# --- Baugruppe ------------------------------------------------------------------------------------------------------

def _lage(x_m=0.0, y_m=0.0, z_m=0.0):
    return [1, 0, 0, 0, 1, 0, 0, 0, 1, x_m, y_m, z_m, 1, 0, 0, 0]


PROTOKOLL_BG = {
    "status": "ok",
    "komponenten": [{"id": "platte", "sw_name": "Platte-1", "datei": "A_Platte_1.sldprt"},
                    {"id": "schraube.1", "sw_name": "Schraube-1", "datei": "ISO4762_M5x20.sldprt"},
                    {"id": "schraube.2", "sw_name": "Schraube-2", "datei": "ISO4762_M5x20.sldprt"}],
    "knoten": [{"id": "platte", "typ": "komponente", "sw_name": "Platte-1", "status": "ok"},
               {"id": "schraube.1", "typ": "komponente", "sw_name": "Schraube-1", "status": "ok"},
               {"id": "schraube.2", "typ": "komponente", "sw_name": "Schraube-2", "status": "ok"},
               {"id": "v1", "typ": "konzentrisch", "sw_name": "v1", "status": "ok"},
               {"id": "v2", "typ": "abstand", "sw_name": "v2", "status": "ok"},
               {"id": "v3", "typ": "grenze_abstand", "sw_name": "v3", "status": "ok"},
               {"id": "grundstellung:schlitten", "typ": "grundstellung", "sw_name": None, "status": "ok"}]}
_PARTNER = ["Platte-1", "Schraube-1"]


def _soll(typ, wert=None, mn=None, mx=None, ausrichtung=None, partner=None):
    return {"typ": typ, "partner": list(partner or _PARTNER), "ausrichtung": ausrichtung, "wert": wert, "min": mn, "max": mx}


# Soll je Verknüpfung wie `soll_verknuepfungen` (swki.aenderungen) es aus Spec und Protokoll baut
SOLL_VERKNUEPFUNGEN = {"v1": _soll("konzentrisch"), "v2": _soll("abstand", 5.0), "v3": _soll("grenze_abstand", 0.0, 0.0, 25.0)}


def _mate(typ, wert=None, mn=None, mx=None, fehler=0, unterdrueckt=False, partner=("Platte-1", "Schraube-1")):
    return {"typ": typ, "ausrichtung": 0, "wert": wert, "min": mn, "max": mx, "werte": {}, "grenze": mn is not None,
            "gesteuert": False, "partner": list(partner), "fehler": {"Standard": fehler},
            "unterdrueckt": {"Standard": unterdrueckt}}


def _komp(datei, lage=None, virtuell=False, unterdrueckt=False):
    return {"datei": datei, "konfiguration": "Standard", "virtuell": virtuell, "muster": False, "loesen": 0,
            "fixiert": {"Standard": False}, "unterdrueckt": {"Standard": unterdrueckt}, "status": {"Standard": 3},
            "transform": {"Standard": None if unterdrueckt else (lage or _lage())}}


def _ist_bg():
    return {"aktiv": "Standard", "konfigurationen": ["Standard"],
            "komponenten": {"Platte-1": _komp("A_Platte_1.sldprt"),
                            "Schraube-1": _komp("ISO4762_M5x20.sldprt", _lage(0.01, 0, 0)),
                            "Schraube-2": _komp("teile/ISO4762_M5x20.sldprt", _lage(0.02, 0, 0))},
            "verknuepfungen": {"v1": _mate(1), "v2": _mate(5, wert=5.0), "v3": _mate(5, wert=0.0, mn=0.0, mx=25.0)}}


SOLL_LAGEN = {"Platte-1": _lage(), "Schraube-1": _lage(0.01, 0, 0), "Schraube-2": _lage(0.02, 0, 0)}


def test_unveraenderte_baugruppe_nennt_nichts():
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, _ist_bg(), SOLL_LAGEN)
    for schluessel in ("komponenten_neu", "komponenten_weg", "andere_datei", "verknuepfungen_neu", "verknuepfungen_weg", "werte",
                       "fehler", "unterdrueckt", "lagen"):
        assert a[schluessel] == [], schluessel
    assert a["lage_geprueft"] is True and a["vollstaendig"] is True and a["nicht_erklaert"] is True


def test_neue_komponente_und_gleiche_datei():
    ist = _ist_bg()
    ist["komponenten"]["Schraube-3"] = _komp("ISO4762_M5x20.sldprt", _lage(0.03, 0, 0))
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["komponenten_neu"] == [{"name": "Schraube-3", "datei": "ISO4762_M5x20.sldprt", "virtuell": False,
                                     "gleiche_datei_wie": ["Schraube-1", "Schraube-2"]}]
    assert a["komponenten_weg"] == [] and a["nicht_erklaert"] is False


def test_neue_komponente_neuer_datei_ohne_gleiche():
    ist = _ist_bg()
    ist["komponenten"]["Deckel-1"] = _komp("Deckel.SLDPRT")
    [neu] = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["komponenten_neu"]
    assert neu["name"] == "Deckel-1" and neu["gleiche_datei_wie"] == []


def test_untergeordnete_komponente_ist_neu():
    ist = _ist_bg()
    ist["komponenten"]["Unter-1/Teil-1"] = _komp("teile/Teil.SLDPRT")
    assert [k["name"] for k in abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["komponenten_neu"]] == ["Unter-1/Teil-1"]


def test_virtuelle_komponente_wird_als_virtuell_genannt():
    ist = _ist_bg()
    ist["komponenten"]["Teil1^Haupt-1"] = _komp("Teil1^Haupt.sldprt", virtuell=True)
    [neu] = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["komponenten_neu"]
    assert neu["virtuell"] is True


def test_umbenannte_komponente():
    ist = _ist_bg()
    ist["komponenten"]["Stift-1"] = ist["komponenten"].pop("Schraube-1")
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert [k["name"] for k in a["komponenten_weg"]] == ["Schraube-1"] and a["komponenten_weg"][0]["datei"] == "ISO4762_M5x20.sldprt"
    assert [k["name"] for k in a["komponenten_neu"]] == ["Stift-1"]
    assert a["umbenannt"] == [{"von": "Schraube-1", "nach": "Stift-1", "datei": "ISO4762_M5x20.sldprt"}]


def test_geloeschte_komponente_ist_weg():
    ist = _ist_bg()
    del ist["komponenten"]["Schraube-2"]
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert [k["name"] for k in a["komponenten_weg"]] == ["Schraube-2"] and a["umbenannt"] == []


def test_andere_datei_bei_gleichem_namen():
    ist = _ist_bg()
    ist["komponenten"]["Platte-1"]["datei"] = "Platte_V2.SLDPRT"
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["andere_datei"] == [{"name": "Platte-1", "soll": "A_Platte_1.sldprt", "ist": "Platte_V2.SLDPRT"}]
    assert a["komponenten_neu"] == [] and a["komponenten_weg"] == []


def test_datei_vergleich_ignoriert_ordner_und_schreibweise():
    ist = _ist_bg()
    ist["komponenten"]["Platte-1"]["datei"] = "teile/a_platte_1.SLDPRT"
    ist["komponenten"]["Schraube-1"]["datei"] = "teile\\ISO4762_M5x20.sldprt"
    assert abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["andere_datei"] == []


def test_unterdrueckte_komponente_wird_genannt_und_lage_bleibt_ungeprueft():
    ist = _ist_bg()
    ist["komponenten"]["Schraube-2"] = _komp("ISO4762_M5x20.sldprt", unterdrueckt=True)
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["komponenten_unterdrueckt"] == [{"name": "Schraube-2", "konfiguration": "Standard"}]
    assert a["lage_geprueft"] is False and a["lage_ungeprueft"] == ["Schraube-2"]


def test_neue_verknuepfung_und_geaenderter_wert():
    ist = _ist_bg()
    ist["verknuepfungen"]["Deckungsgleich9"] = _mate(0)
    ist["verknuepfungen"]["v2"]["wert"] = 7.5
    del ist["verknuepfungen"]["v1"]
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert [v["name"] for v in a["verknuepfungen_neu"]] == ["Deckungsgleich9"]
    assert a["verknuepfungen_neu"][0]["typ"] == "deckungsgleich"
    assert [v["name"] for v in a["verknuepfungen_weg"]] == ["v1"] and a["verknuepfungen_weg"][0]["id"] == "v1"
    assert a["werte"] == [{"id": "v2", "name": "v2", "feld": "wert", "soll": 5.0, "ist": 7.5, "delta": 2.5}]
    assert a["nicht_erklaert"] is False


def test_wert_ohne_ist_wird_genannt():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["wert"] = None
    [w] = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["werte"]
    assert w["ist"] is None and w["delta"] is None and w["soll"] == 5.0


def test_geaenderter_typ_einer_verknuepfung():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["typ"] = 0
    ist["verknuepfungen"]["v2"]["wert"] = None
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["typ_geaendert"] == [{"id": "v2", "name": "v2", "soll": "abstand", "ist": "deckungsgleich"}]


def test_grenzen_werden_mit_dem_bereich_verglichen():
    ist = _ist_bg()
    ist["verknuepfungen"]["v3"]["max"] = 30.0
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["werte"] == [{"id": "v3", "name": "v3", "feld": "max", "soll": 25.0, "ist": 30.0, "delta": 5.0}]


def test_verknuepfung_mit_fehler():
    ist = _ist_bg()
    ist["verknuepfungen"]["v1"]["fehler"] = {"Standard": 3}
    ist["verknuepfungen"]["v2"]["unterdrueckt"] = {"Standard": True}
    ist["verknuepfungen"]["Neu1"] = _mate(0, fehler=2)
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["fehler"] == [{"name": "Neu1", "konfiguration": "Standard", "code": 2, "neu": True},
                           {"name": "v1", "konfiguration": "Standard", "code": 3, "neu": False}]
    assert a["unterdrueckt"] == [{"name": "v2", "konfiguration": "Standard", "neu": False}]


def test_lage_aus_export():
    """Format von --lagen: Export mit name/pfad/transform je Komponente."""
    export = {"masse_kg": 1.2, "komponenten": [{"name": n, "pfad": f"D:\\x\\{n}.sldprt", "transform": t}
                                               for n, t in SOLL_LAGEN.items()]}
    ist = _ist_bg()
    ist["komponenten"]["Schraube-1"]["transform"]["Standard"] = _lage(0.011, 0.0, 0.0)   # 1 mm in x verschoben
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, export)
    assert a["lage_geprueft"] is True
    [lage] = a["lagen"]
    assert lage["name"] == "Schraube-1" and lage["verschiebung_mm"] == pytest.approx(1.0)
    assert lage["soll"] == _lage(0.01, 0, 0) and lage["ist"] == _lage(0.011, 0, 0)
    assert a["nicht_erklaert"] is False


def test_lage_aus_dem_pruefbericht_und_aus_einer_liste_gleich():
    ist = _ist_bg()
    ist["komponenten"]["Platte-1"]["transform"]["Standard"] = _lage(0, 0.005, 0)
    a1 = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    a2 = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, [{"name": n, "transform": t} for n, t in SOLL_LAGEN.items()])
    assert a1["lagen"] == a2["lagen"] and a1["lagen"][0]["verschiebung_mm"] == pytest.approx(5.0)


def test_drehung_wird_als_lageabweichung_erkannt():
    ist = _ist_bg()
    ist["komponenten"]["Platte-1"]["transform"]["Standard"] = [0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
    [lage] = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["lagen"]
    assert lage["name"] == "Platte-1" and lage["verschiebung_mm"] == 0.0 and lage["abweichung"] == pytest.approx(1.0)


def test_kleine_lageabweichung_unter_der_toleranz_zaehlt_nicht():
    ist = _ist_bg()
    ist["komponenten"]["Platte-1"]["transform"]["Standard"] = _lage(1e-9, 0, 0)
    assert abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)["lagen"] == []


def test_ohne_lagen_steht_das_da():
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, _ist_bg(), None)
    assert a["lage_geprueft"] is False and a["lagen"] == []
    assert a["lage_ungeprueft"] == ["Platte-1", "Schraube-1", "Schraube-2"]
    assert a["vollstaendig"] is False and any("Lage" in text for text in a["luecken"])
    assert a["nicht_erklaert"] is True


def test_lagen_ohne_eine_komponente_sind_nicht_vollstaendig_geprueft():
    soll = {k: v for k, v in SOLL_LAGEN.items() if k != "Schraube-2"}
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, _ist_bg(), soll)
    assert a["lage_geprueft"] is False and a["lage_ungeprueft"] == ["Schraube-2"]


def test_leere_lagen_sind_nicht_geprueft():
    assert abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, _ist_bg(), {})["lage_geprueft"] is False
    assert abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, _ist_bg(), {"komponenten": []})["lage_geprueft"] is False


def test_protokoll_ohne_komponenten_und_knoten_ist_nie_unveraendert():
    a = abgleich_baugruppe({"status": "ok"}, SOLL_VERKNUEPFUNGEN, _ist_bg(), SOLL_LAGEN)
    assert a["komponenten_geprueft"] is False and a["verknuepfungen_geprueft"] is False
    assert a["vollstaendig"] is False and a["nicht_erklaert"] is True
    assert a["komponenten_neu"] == [] and a["verknuepfungen_neu"] == []   # nichts behauptet


def test_ist_ohne_komponenten_ist_eine_luecke():
    ist = _ist_bg()
    del ist["komponenten"]
    a = abgleich_baugruppe(PROTOKOLL_BG, SOLL_VERKNUEPFUNGEN, ist, SOLL_LAGEN)
    assert a["komponenten_geprueft"] is False and a["komponenten_weg"] == [] and a["vollstaendig"] is False


@pytest.mark.parametrize("lagen", [None, {}])
def test_normalisiere_lagen_leer(lagen):
    assert normalisiere_lagen(lagen) == {}


def test_normalisiere_lagen_formen():
    t = _lage(1, 2, 3)
    assert normalisiere_lagen({"komponenten": [{"name": "X-1", "pfad": "p", "transform": t}]}) == {"X-1": t}
    assert normalisiere_lagen({"X-1": t}) == {"X-1": t}
    assert normalisiere_lagen([{"name": "X-1", "transform": t}]) == {"X-1": t}
    assert normalisiere_lagen({"lagen": {"X-1": t}, "bestanden": True}) == {"X-1": t}      # ganzer Prüfbericht
