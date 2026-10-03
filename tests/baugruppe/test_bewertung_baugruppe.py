import pytest

from swki.baugruppe.aufloesen import verknuepfungen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, gewindepaarungen, stueckliste_soll
from swki.baugruppe.geometrie import ueberlappung_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from tests.baugruppe.beispiel import schreibe

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}, "namensschema": {"datei": "{auftrag}_{name}"}}
SOLL_GEWINDE = ueberlappung_soll(8, 1.25, 6.8, 9.6)
Y = (0.0, 1.0, 0.0)


@pytest.fixture
def bg(tmp_path):
    return lade_baugruppe(schreibe(tmp_path / "A"))


def _messwerte(bg, **aenderungen) -> BaugruppenMesswerte:
    mp = bg.spec["pruefung"]["masse_pruefen"][0]
    werte = dict(
        rebuild_fehler=[],
        verknuepfungen={v.id: 0 for v in verknuepfungen(bg.spec, bg.quellen)},
        komponenten={i: {"status": 3, "fixiert": i == "platte"}
                     for i in ("platte", "deckel", "schraube.1", "schraube.2", "stift")},
        stueckliste=stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD),
        interferenzen=[{"paar": ["platte", "schraube.1"], "volumen": SOLL_GEWINDE},
                       {"paar": ["platte", "schraube.2"], "volumen": SOLL_GEWINDE}],
        box=[-50.0, 0.0, -30.0, 50.0, 35.0, 30.0], masse_kg=1.2, eigenschaften={"Benennung": "Probe"},
        messpunkte={messpunkt_schluessel(mp["von"]): Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
                    messpunkt_schluessel(mp["zu"]): Messgeometrie("ebene", (0.0, 35.0, 0.0), Y)},
        schrauben={"schraube.1": Messgeometrie("ebene", (-30.0, 26.4, 0.0), Y),
                   "schraube.2": Messgeometrie("ebene", (30.0, 26.4, 0.0), Y)},
        gewindebohrungen=[
            {"teil": "platte", "feature": "f2", "instanz": 1, "eintritt": Messgeometrie("punkt", (-30.0, 20.0, 0.0))},
            {"teil": "platte", "feature": "f2", "instanz": 2, "eintritt": Messgeometrie("punkt", (30.0, 20.0, 0.0))}],
        teilberichte={d: {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True, "knoten": []}], "maengel": []}
                      for d in ("platte.yaml", "deckel.yaml")},
    )
    werte.update(aenderungen)
    return BaugruppenMesswerte(**werte)


def _bewerte(bg, m) -> dict:
    return bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))


def _maengel(bericht) -> dict:
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_alles_ok(bg):
    bericht = _bewerte(bg, _messwerte(bg))
    assert bericht["bestanden"], bericht["maengel"]
    assert [g["einschraublaenge"] for g in bericht["gewindepaarungen"]] == [9.6, 9.6]
    assert bericht["teilpruefungen"] == {"platte": {"bestanden": True, "maengel": 0},
                                         "deckel": {"bestanden": True, "maengel": 0}}
    ids = {p["id"] for p in bericht["pruefungen"]}
    assert {"rebuild", "verknuepfungen", "bestimmtheit", "stueckliste", "kollision", "gewinde:schraube.1",
            "mass:Gesamthöhe", "eigenschaften", "platte: rebuild"} <= ids


def test_fehlende_verknuepfung(bg):
    m = _messwerte(bg)
    del m.verknuepfungen["v5.2"]
    assert _maengel(_bewerte(bg, m))["verknuepfungen"]["knoten"] == ["v5.2"]


def test_unterbestimmt_ist_mangel(bg):
    m = _messwerte(bg)
    m.komponenten["deckel"]["status"] = 2
    mangel = _maengel(_bewerte(bg, m))["bestimmtheit"]
    assert mangel["knoten"] == ["deckel"] and "unterbestimmt" in mangel["beschreibung"]


def test_unterbestimmt_erlaubt(bg):
    bg.spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    m = _messwerte(bg)
    m.komponenten["deckel"]["status"] = 2
    assert _bewerte(bg, m)["bestanden"]


def test_ueberbestimmt(bg):
    m = _messwerte(bg)
    m.komponenten["stift"]["status"] = 4
    assert "überbestimmt" in _maengel(_bewerte(bg, m))["bestimmtheit"]["beschreibung"]


def test_fixierte_komponente_nicht_fixiert(bg):
    m = _messwerte(bg)
    m.komponenten["platte"]["fixiert"] = False
    assert "nicht fixiert" in _maengel(_bewerte(bg, m))["bestimmtheit"]["beschreibung"]


def test_stueckliste(bg):
    m = _messwerte(bg)
    m.stueckliste["ISO4762_M8x16_8_8.sldprt"] = 1
    assert "stueckliste" in _maengel(_bewerte(bg, m))


def test_fremde_kollision(bg):
    m = _messwerte(bg)
    m.interferenzen.append({"paar": ["deckel", "stift"], "volumen": 5.0})
    maengel = _maengel(_bewerte(bg, m))
    assert maengel["kollision"]["knoten"] == ["deckel", "stift"]
    assert not any(p.startswith("gewinde:") for p in maengel)


def test_gewinde_zu_lang(bg):
    m = _messwerte(bg)
    m.gewindebohrungen[0]["eintritt"] = Messgeometrie("punkt", (-30.0, 24.4, 0.0))   # Einschraublänge 14 > 12
    m.interferenzen[0]["volumen"] = ueberlappung_soll(8, 1.25, 6.8, 14.0)
    mangel = _maengel(_bewerte(bg, m))["gewinde:schraube.1"]
    assert "Einschraublänge 14.00" in mangel["beschreibung"] and mangel["knoten"] == ["schraube.1", "platte"]


def test_gewinde_volumen_falsch(bg):
    m = _messwerte(bg)
    m.interferenzen[1]["volumen"] = SOLL_GEWINDE * 1.05
    assert "gewinde:schraube.2" in _maengel(_bewerte(bg, m))


def test_teilbericht_mit_praefix(bg):
    m = _messwerte(bg)
    m.teilberichte["platte.yaml"] = {"bestanden": False, "maengel": [{}], "pruefungen": [
        {"id": "mass:A", "ok": False, "ist": 59.0, "soll": 60.0, "knoten": ["f2"]}]}
    mangel = _maengel(_bewerte(bg, m))["platte: mass:A"]
    assert mangel["knoten"] == ["platte/f2"] and "ist 59.0 statt 60.0" in mangel["beschreibung"]


def test_mass_ausserhalb_toleranz(bg):
    mp = bg.spec["pruefung"]["masse_pruefen"][0]
    m = _messwerte(bg)
    m.messpunkte[messpunkt_schluessel(mp["zu"])] = Messgeometrie("ebene", (0.0, 35.5, 0.0), Y)
    assert _maengel(_bewerte(bg, m))["mass:Gesamthöhe"]["knoten"] == ["deckel", "platte"]


def test_gewindepaarung_ueber_die_lage():
    schrauben = {"s.1": Messgeometrie("ebene", (0.0, 30.0, 0.0), Y)}
    bohrungen = [{"teil": "t", "feature": "f2", "instanz": 1, "eintritt": Messgeometrie("punkt", (0.05, 20.0, 0.0))},
                 {"teil": "t", "feature": "f2", "instanz": 2, "eintritt": Messgeometrie("punkt", (1.0, 20.0, 0.0))}]
    assert [(g.schraube, g.instanz) for g in gewindepaarungen(schrauben, bohrungen, 0.1)] == [("s.1", 1)]


def test_stueckliste_soll(bg):
    assert stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD) == {
        "A_Platte.sldprt": 1, "A_Deckel.sldprt": 1, "ISO4762_M8x16_8_8.sldprt": 2, "ISO8734_8x16_St.sldprt": 1}


def test_stueckliste_schreibungsunabhaengig(bg):
    # SolidWorks liefert bei Eigenteilen ".SLDPRT" (Spike S12 Zeile 14), der Soll-Name steht mit ".sldprt"
    m = _messwerte(bg)
    m.stueckliste = {n.replace(".sldprt", ".SLDPRT"): c for n, c in m.stueckliste.items()}
    bericht = _bewerte(bg, m)
    assert bericht["bestanden"], bericht["maengel"]
    m.stueckliste["ISO4762_M8x16_8_8.SLDPRT"] = 1
    assert _maengel(_bewerte(bg, m))["stueckliste"]["knoten"] == []


def test_fixierte_komponente_ueberbestimmt(bg):
    m = _messwerte(bg)
    m.komponenten["platte"]["status"] = 4
    mangel = _maengel(_bewerte(bg, m))["bestimmtheit"]
    assert mangel["knoten"] == ["platte"] and "überbestimmt" in mangel["beschreibung"]


def test_fixierte_komponente_status_voll_bestimmt_ist_kein_mangel(bg):
    m = _messwerte(bg)
    m.komponenten["platte"]["status"] = 3
    assert _bewerte(bg, m)["bestanden"]


def test_huellquader(bg):
    bg.spec["pruefung"]["huellquader"] = [100, 35, 60]
    bericht = _bewerte(bg, _messwerte(bg))
    assert bericht["bestanden"], bericht["maengel"]
    assert next(p for p in bericht["pruefungen"] if p["id"] == "huellquader")["ist"] == [100.0, 35.0, 60.0]


def test_huellquader_abweichend(bg):
    bg.spec["pruefung"]["huellquader"] = [100, 35, 60]
    mangel = _maengel(_bewerte(bg, _messwerte(bg, box=[-50.0, 0.0, -30.0, 50.0, 35.5, 30.0])))["huellquader"]
    assert "ist [100.0, 35.5, 60.0] statt [100.0, 35.0, 60.0]" in mangel["beschreibung"]


def test_huellquader_eigene_toleranz(bg):
    bg.spec["pruefung"]["huellquader"] = [100, 35, 60]
    bg.spec["pruefung"]["huellquader_tol"] = 1.0
    assert _bewerte(bg, _messwerte(bg, box=[-50.0, 0.0, -30.0, 50.0, 35.5, 30.0]))["bestanden"]


def test_masse_innerhalb_toleranz(bg):
    bg.spec["pruefung"]["masse"] = {"soll": 1.2, "toleranz_prozent": 2}
    bericht = _bewerte(bg, _messwerte(bg, masse_kg=1.21))   # 0,83 % Abweichung
    assert bericht["bestanden"], bericht["maengel"]
    assert bericht["masse_kg"] == 1.21


def test_masse_ausserhalb_toleranz(bg):
    bg.spec["pruefung"]["masse"] = {"soll": 1.2, "toleranz_prozent": 2}
    mangel = _maengel(_bewerte(bg, _messwerte(bg, masse_kg=1.3)))["masse"]   # 8,3 % Abweichung
    assert "ist 1.3 statt 1.2" in mangel["beschreibung"]


def test_masse_vorgabetoleranz_aus_standard(bg):
    bg.spec["pruefung"]["masse"] = {"soll": 1.2}   # Vorgabe 0,5 %
    assert "masse" in _maengel(_bewerte(bg, _messwerte(bg, masse_kg=1.21)))
    assert _bewerte(bg, _messwerte(bg, masse_kg=1.203))["bestanden"]


def test_masse_ohne_vorgabe_nur_berichtet(bg):
    bericht = _bewerte(bg, _messwerte(bg, masse_kg=7.77))
    assert bericht["bestanden"] and bericht["masse_kg"] == 7.77
    assert "masse" not in {p["id"] for p in bericht["pruefungen"]}


def test_gewinde_durch_ohne_volumenpruefung(bg):
    f2 = next(f for f in bg.quellen["platte"].spec["features"] if f["id"] == "f2")
    f2["durch"] = True
    del f2["tiefe"], f2["gewindetiefe"]
    m = _messwerte(bg)
    m.interferenzen[0]["volumen"] = 1.0   # beliebiges Volumen: bei durch nicht gegen ein Soll geprüft
    bericht = _bewerte(bg, m)
    assert bericht["bestanden"], bericht["maengel"]
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "gewinde:schraube.1")
    assert pruefung["ok"] is None and "durch" in pruefung["hinweis"] and pruefung["ist"] == 1.0
    assert [g["einschraublaenge"] for g in bericht["gewindepaarungen"]] == [9.6, 9.6]
