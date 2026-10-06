from dataclasses import replace

from swki.kaufteile.bewertung import KaufteilMesswerte, bewerte_kaufteil
from swki.kaufteile.eintrag import eigenschaften
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from tests.kaufteile.beispiel import EINTRAG, L, kopie

Y = (0.0, 1.0, 0.0)


def _messwerte() -> KaufteilMesswerte:
    """Messwerte, wie sie das Muster ohne Mangel liefert."""
    achse = Messgeometrie("achse", (0.0, 0.0, 0.0), Y)
    flansch = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0))
    drehlage = Messgeometrie("ebene", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    pr = EINTRAG["pruefung"]
    mp = {
        messpunkt_schluessel(pr["masse_pruefen"][0]["von"]): flansch,
        messpunkt_schluessel(pr["masse_pruefen"][0]["zu"]): Messgeometrie("ebene", (0.0, -25.0, 0.0), (0.0, -1.0, 0.0)),
        messpunkt_schluessel(pr["masse_pruefen"][1]["von"]): Messgeometrie("achse", (L, 0.0, L), Y),
        messpunkt_schluessel(pr["masse_pruefen"][1]["zu"]): Messgeometrie("achse", (-L, 0.0, L), Y),
    }
    gewinde = {f"flansch.{i}": {"ist": {"durchmesser": 4.2, "modell": "kernloch"}, "abweichung": None} for i in range(1, 5)}
    return KaufteilMesswerte(
        rebuild_fehler=[], koerper=2, flaechenkoerper=0, koerperfehler={"1": 0, "2": 0},
        box=[-30, -25, -30, 30, 82, 30], volumen=220010.0, masse_kg=1.2, masse_ueberschrieben=True,
        material="1.0038 (S235JRG2)", eigenschaften=eigenschaften(EINTRAG),
        einbau={
            "EINBAU_ACHSE": {"ist": {"durchmesser": 10.0, "achse": Y, "punkt": (0.0, -10.0, 0.0)}, "abweichung": None,
                             "bezug": achse},
            "EINBAU_FLANSCH": {"ist": {"normale": (0.0, -1.0, 0.0), "punkt": (25.0, 0.0, 25.0)}, "abweichung": None,
                               "bezug": flansch},
            "EINBAU_DREHLAGE": {"ist": {"abstand_achse": 25.0, "normale": (1.0, 0.0, 0.0)}, "abweichung": None,
                                "bezug": drehlage},
        },
        gewinde=gewinde, messpunkte=mp,
        durchmesser={"Wellen-Ø": {"durchmesser": 10.0, "achse": achse, "referenz": achse},
                     "Zentrierbund-Ø": {"durchmesser": 40.0, "achse": achse, "referenz": achse}},
    )


def _ids(bericht, ok) -> list[str]:
    return [e["id"] for e in bericht["pruefungen"] if e["ok"] is ok]


def test_muster_besteht():
    b = bewerte_kaufteil(EINTRAG, _messwerte())
    assert b["maengel"] == [] and b["bestanden"] is True
    assert _ids(b, True) == ["rebuild", "import", "koerper", "huellquader", "volumen", "einbau:EINBAU_ACHSE",
                             "einbau:EINBAU_FLANSCH", "einbau:EINBAU_DREHLAGE", "gewinde:flansch", "durchmesser:Wellen-Ø",
                             "durchmesser:Zentrierbund-Ø", "mass:Wellenüberstand", "mass:Lochabstand", "material",
                             "eigenschaften", "masse"]
    huelle = next(e for e in b["pruefungen"] if e["id"] == "huellquader")
    assert huelle["ist"] == [60, 107, 60] and huelle["beleg"] == ["d1"]
    flansch = next(e for e in b["pruefungen"] if e["id"] == "einbau:EINBAU_FLANSCH")
    assert flansch["bezug"]["richtung"] == [0.0, -1.0, 0.0]


def test_koerper_import_und_volumen():
    m = replace(_messwerte(), koerper=1, flaechenkoerper=1, koerperfehler={"1": 2}, volumen=230000.0)
    assert {"import", "koerper", "volumen"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))


def test_gegenprobe_und_lage_der_referenzen():
    m = _messwerte()
    m.einbau["EINBAU_ACHSE"]["abweichung"] = "Ø 12.0000 statt 10"
    m.einbau["EINBAU_DREHLAGE"]["bezug"] = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    b = bewerte_kaufteil(EINTRAG, m)
    assert _ids(b, False) == ["einbau:EINBAU_ACHSE", "einbau:EINBAU_DREHLAGE"]
    texte = [x["beschreibung"] for x in b["maengel"]]
    assert texte[0] == "einbau:EINBAU_ACHSE: Ø 12.0000 statt 10"
    assert "enthält EINBAU_ACHSE nicht" in texte[1]


def test_senkrecht_zu():
    m = _messwerte()
    m.einbau["EINBAU_FLANSCH"]["bezug"] = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -0.9998, 0.02))
    m.einbau["EINBAU_FLANSCH"]["ist"]["normale"] = (0.0, -0.9998, 0.02)
    b = bewerte_kaufteil(EINTRAG, m)
    assert "Achse nicht senkrecht zu EINBAU_FLANSCH" in next(x for x in b["maengel"]
                                                             if x["pruefung"] == "einbau:EINBAU_ACHSE")["beschreibung"]


def test_einbau_fehlt_und_gewinde_falsch():
    m = _messwerte()
    m.einbau["EINBAU_FLANSCH"] = "REFERENZ_NICHT_GEFUNDEN: keine ebene Fläche"
    m.gewinde["flansch.3"] = {"ist": {"durchmesser": 6.0, "modell": None}, "abweichung": "Ø 6.0000: weder …"}
    b = bewerte_kaufteil(EINTRAG, m)
    assert {"einbau:EINBAU_FLANSCH", "gewinde:flansch"} <= set(_ids(b, False))


def test_masse_ohne_ueberschreibung_und_ohne_angabe():
    assert "masse" in _ids(bewerte_kaufteil(EINTRAG, replace(_messwerte(), masse_ueberschrieben=False)), False)
    ohne = kopie()
    del ohne["masse"]
    masse = next(e for e in bewerte_kaufteil(ohne, _messwerte())["pruefungen"] if e["id"] == "masse")
    assert masse["ok"] is None and masse["hinweis"] == "Masse aus Material geschätzt"


def test_nicht_belegte_kennmasse_im_bericht():
    spec = kopie()
    del spec["pruefung"]["masse_pruefen"][0]["beleg"]
    mass = next(e for e in bewerte_kaufteil(spec, _messwerte())["pruefungen"] if e["id"] == "mass:Wellenüberstand")
    assert mass["ok"] is True and mass["beleg"] == "nicht belegt"


def test_messpunkt_fehlt_und_eigenschaften():
    m = _messwerte()
    m.messpunkte.pop(next(iter(m.messpunkte)))
    m.eigenschaften = {**m.eigenschaften, "Hersteller": "anders"}
    assert {"mass:Wellenüberstand", "eigenschaften"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))


def test_gewinde_modell_und_uneinheitlich():
    gewinde = next(e for e in bewerte_kaufteil(EINTRAG, _messwerte())["pruefungen"] if e["id"] == "gewinde:flansch")
    assert gewinde["ok"] is True and (gewinde["modell"], gewinde["durchmesser"]) == ("kernloch", 4.2)
    m = _messwerte()
    m.gewinde["flansch.2"] = {"ist": {"durchmesser": 4.134, "modell": "kernloch"}, "abweichung": None}
    mangel = next(x for x in bewerte_kaufteil(EINTRAG, m)["maengel"] if x["pruefung"] == "gewinde:flansch")
    assert "Positionen uneinheitlich" in mangel["beschreibung"]
