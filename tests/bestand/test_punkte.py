"""Punkt-Handler ohne SolidWorks (Spec Bestandsdateien §4.1, §6). Rückgaben von SolidWorks beweisen nichts (S18c), darum prüfen
die Tests vor allem, was nach dem Neuaufbau nachgemessen wird."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.bestand import punkte
from swki.bestand.fehler import BESTAND_ALTWERT, BESTAND_REFERENZ, KINDER_FEHLEN
from swki.bestand.punkte import PUNKTE, kontext, punkt_handler
from swki.compiler.fehler import (FEATURE_NICHT_ERZEUGT, GLEICHUNG_FEHLER, MATERIAL_UNBEKANNT, REBUILD_FEHLER, UNBEKANNTER_TYP,
                                  BauFehler)
from swki.compiler.kontext import FeatureErgebnis
from tests.bestand.beispiel_aufnahme import aufnahme as beispiel
from tests.bestand.sw_attrappe import Feat, teil_aus


def _aufnahme(**aenderungen) -> dict:
    a = beispiel()
    a["reihenfolge"] = {k: [f["name"] for f in a["features"]] for k in a["konfigurationen"]}
    a["geometrie"] = {k: {"koerper": 1, "volumen": 12345.6, "box": [0] * 6, "schwerpunkt": [0] * 3} for k in a["konfigurationen"]}
    a.update(aenderungen)
    return a


def _spec(*p, **mehr) -> dict:
    return {"parameter": {"A": 45}, "punkte": list(p), **mehr}


def _ctx(teil, *p, spec=None):
    return kontext(SimpleNamespace(), teil, spec or _spec(*p), Path("A/aenderung.yaml"), 0.01)


MASS = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": "alle"}


@pytest.fixture
def aufnahme():
    return _aufnahme()


def _anwenden(teil, p, aufnahme, spec=None):
    ctx = _ctx(teil, p, spec=spec)
    ctx.knoten = p["id"]
    return punkt_handler(p["typ"])(ctx, p, aufnahme), ctx


def test_registry_kennt_alle_punkte_und_nur_die():
    assert set(PUNKTE) == {"mass", "gleichung", "unterdruecken", "aufheben", "loeschen", "feature", "material", "eigenschaft",
                           "skript"}
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_neu")
    assert e.value.code == UNBEKANNTER_TYP


def test_mass_prueft_alt_live_und_setzt_in_meter(aufnahme):
    a = _aufnahme(masse=[m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m
                         for m in aufnahme["masse"]])
    teil = teil_aus(a)
    namen, ctx = _anwenden(teil, MASS, a)
    assert teil.masse["D2@Skizze4"].gesetzt == [(0.045, 2, None)]  # swSetValue_InAllConfigurations
    assert namen == ["D2@Skizze4"]
    assert teil.aktiv == "Standard"
    m = ctx.masse["p1"][0]
    assert (m["name"], m["wert"], m["einheit"], m["roh"]) == ("D2@Skizze4", 45, "mm", 45)


def test_mass_ausdruck_aus_parametern_und_winkel_in_radiant():
    a = _aufnahme()
    a["masse"].append({"name": "D2@Fase3", "feature": "Fase3", "werte": {"Standard": 45.0, "Variante B": 45.0}, "einheit": "Grad",
                       "zustand": "treibend", "quelle": None, "gruppe": None, "punkte": []})
    teil = teil_aus(a)
    teil.masse["D2@Fase3"].werte = dict.fromkeys(a["konfigurationen"], 0.7853981634)
    p = {"id": "p1", "typ": "mass", "mass": "D2@Fase3", "alt": 45, "neu": "=A-15"}
    _, ctx = _anwenden(teil, p, a)
    assert teil.masse["D2@Fase3"].gesetzt[0][0] == pytest.approx(0.5235987756)
    assert ctx.masse["p1"][0]["einheit"] == "grad"


def test_mass_altwert_weicht_im_bau_ab(aufnahme):
    teil = teil_aus(aufnahme)
    teil.masse["D2@Skizze4"].werte["Standard"] = 0.041
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, MASS, aufnahme)
    assert e.value.code == BESTAND_ALTWERT and "41" in str(e.value)
    assert teil.masse["D2@Skizze4"].gesetzt == []


def test_mass_altwert_in_anderer_konfiguration_faellt_auf():
    """Mit Namen läse SolidWorks in nicht aktiven Konfigurationen 0 (S18b): Nur Umschalten sieht die Abweichung."""
    a = _aufnahme(masse=[m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m
                         for m in _aufnahme()["masse"]])
    teil = teil_aus(a)
    teil.masse["D2@Skizze4"].werte["Variante B"] = 0.050
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, MASS, a)
    assert e.value.code == BESTAND_ALTWERT and "Variante B" in str(e.value)


def test_mass_in_benannten_konfigurationen():
    a = _aufnahme()
    a["masse"] = [m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m for m in a["masse"]]
    teil = teil_aus(a)
    _anwenden(teil, MASS | {"konfigurationen": ["Variante B"]}, a)
    assert teil.masse["D2@Skizze4"].gesetzt == [(0.045, 3, ["Variante B"])]
    assert teil.masse["D2@Skizze4"].werte == {"Standard": 0.040, "Variante B": 0.045}
    assert teil.aktiv == "Standard"


def test_mass_status_ungleich_null_bricht_ab():
    a = _aufnahme()
    a["masse"] = [m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m for m in a["masse"]]
    teil = teil_aus(a)
    teil.masse["D2@Skizze4"].status = 3  # swSetValue_DrivenDimension
    with pytest.raises(BauFehler, match="Status 3"):
        _anwenden(teil, MASS, a)


def test_mass_status_null_und_neuaufbau_dreht_zurueck():
    """S18c: Das gesteuerte Maß meldet Status 0, Wert 90, nach dem Neuaufbau wieder 100."""
    a = _aufnahme()
    a["masse"] = [m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m for m in a["masse"]]
    teil = teil_aus(a)
    teil.masse["D2@Skizze4"].einfrieren = True
    with pytest.raises(BauFehler, match="nach dem Neuaufbau"):
        _anwenden(teil, MASS, a)


def test_mass_nicht_lesbarer_wert_ist_keine_abweichung():
    """Plan Review Focus 5: `None` darf weder als Änderung noch als Absturz enden."""
    a = _aufnahme()
    teil = teil_aus(a)
    dim = teil.masse["D2@Skizze4"]
    lesen = dim.GetSystemValue3
    dim.GetSystemValue3 = lambda o, n: (None,) if teil.aktiv == "Variante B" else lesen(o, n)
    _anwenden(teil, MASS, a)
    assert dim.gesetzt == [(0.045, 2, None)]


def test_mass_gibt_es_nicht_mehr(aufnahme):
    teil = teil_aus(aufnahme)
    del teil.masse["D2@Skizze4"]
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, MASS, aufnahme)
    assert e.value.code == BESTAND_REFERENZ


VARIABLE = {"id": "p1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}


def test_variable_setzt_und_misst_nach(aufnahme):
    teil = teil_aus(aufnahme)
    namen, _ = _anwenden(teil, VARIABLE, aufnahme)
    assert namen == ["L"]
    assert teil.gleichungen.gesetzt == [(0, '"L" = 110', 2, None)]  # swAllConfiguration, keine neue Gleichung
    assert teil.gleichungen.GetCount == len(aufnahme["gleichungen"])


def test_variable_altwert_live(aufnahme):
    teil = teil_aus(aufnahme)
    teil.gleichungen.zeilen[0]["wert"] = 99.0
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, VARIABLE, aufnahme)
    assert e.value.code == BESTAND_ALTWERT and teil.gleichungen.gesetzt == []


def test_variable_abhaengig_wird_nicht_still_ueberschrieben(aufnahme):
    teil = teil_aus(aufnahme)
    teil.gleichungen.zeilen[0]["text"] = '"L" = "M" * 2'
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, VARIABLE, aufnahme)
    assert e.value.code == GLEICHUNG_FEHLER and '"M"' in str(e.value) and teil.gleichungen.gesetzt == []


def test_variable_wirkt_nicht(aufnahme):
    teil = teil_aus(aufnahme)
    teil.gleichungen.SetEquationAndConfigurationOption = lambda i, text, o, n: i
    with pytest.raises(BauFehler, match="nach dem Neuaufbau"):
        _anwenden(teil, VARIABLE, aufnahme)


GLEICHUNG = {"id": "p1", "typ": "gleichung", "gleichung": "D3@Skizze2", "alt": '"D1@Skizze1"  +5', "neu": '"D1@Skizze1" + 7'}


def test_gleichung_aendert_rechte_seite(aufnahme):
    teil = teil_aus(aufnahme)
    namen, _ = _anwenden(teil, GLEICHUNG, aufnahme)
    assert namen == ["D3@Skizze2"]
    assert teil.gleichungen.gesetzt == [(2, '"D3@Skizze2" = "D1@Skizze1" + 7', 2, None)]


def test_gleichung_altwert_live(aufnahme):
    teil = teil_aus(aufnahme)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, GLEICHUNG | {"alt": '"D1@Skizze1" + 6'}, aufnahme)
    assert e.value.code == BESTAND_ALTWERT


def test_gleichung_fehlt(aufnahme):
    teil = teil_aus(aufnahme)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, GLEICHUNG | {"gleichung": "D9@Skizze9"}, aufnahme)
    assert e.value.code == BESTAND_REFERENZ


def test_unterdruecken_nur_mit_namen_und_je_konfiguration_nachgemessen(aufnahme):
    teil = teil_aus(aufnahme)
    namen, _ = _anwenden(teil, {"id": "p1", "typ": "unterdruecken", "feature": "Fase3"}, aufnahme)
    assert namen == ["Fase3"]
    assert teil.unterdrueckungen == [("Fase3", 0, 3)]  # nie Option 1 (S18c)
    assert teil.feature("Fase3").unterdrueckt == {"Standard", "Variante B"}


def test_unterdruecken_in_einer_konfiguration(aufnahme):
    teil = teil_aus(aufnahme)
    _anwenden(teil, {"id": "p1", "typ": "unterdruecken", "feature": "Fase3", "konfigurationen": ["Variante B"]}, aufnahme)
    assert teil.feature("Fase3").unterdrueckt == {"Variante B"}


def test_aufheben(aufnahme):
    teil = teil_aus(aufnahme)
    teil.feature("Fase3").unterdrueckt = {"Variante B"}
    _anwenden(teil, {"id": "p1", "typ": "aufheben", "feature": "Fase3"}, aufnahme)
    assert teil.feature("Fase3").unterdrueckt == set()


def test_unterdruecken_ohne_wirkung_faellt_auf(aufnahme):
    """Eine Gleichung kann die Unterdrückung steuern (Task 5, Bedenken 2): Der Neuaufbau nimmt sie still zurück."""
    teil = teil_aus(aufnahme)
    teil.bei_neuaufbau = lambda t: t.feature("Fase3").unterdrueckt.clear()
    with pytest.raises(BauFehler, match="Fase3"):
        _anwenden(teil, {"id": "p1", "typ": "unterdruecken", "feature": "Fase3"}, aufnahme)


def test_unterdruecken_unbekanntes_feature(aufnahme):
    teil = teil_aus(aufnahme)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, {"id": "p1", "typ": "unterdruecken", "feature": "Gibtsnicht"}, aufnahme)
    assert e.value.code == BESTAND_REFERENZ


def test_loeschen_mit_kindern_und_aufgenommener_skizze(aufnahme):
    teil = teil_aus(aufnahme)
    p = {"id": "p1", "typ": "loeschen", "feature": "Bohrung2", "kinder": ["Fase3", "Verrundung1"]}
    namen, _ = _anwenden(teil, p, aufnahme)
    assert set(namen) == {"Bohrung2", "Fase3", "Verrundung1", "Skizze4"}
    assert teil.feature("Bohrung2") is None


def test_loeschen_nennt_kinder(aufnahme):
    teil = teil_aus(aufnahme)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, {"id": "p1", "typ": "loeschen", "feature": "Bohrung2", "kinder": ["Fase3"]}, aufnahme)
    assert e.value.code == KINDER_FEHLEN and "Verrundung1" in str(e.value)


def test_loeschen_ohne_wirkung(aufnahme):
    """S18c: Eine Skizze mit Kind bleibt einfach stehen."""
    teil = teil_aus(aufnahme)
    teil.Extension.DeleteSelection2 = lambda option: False
    with pytest.raises(BauFehler, match="nicht gelöscht"):
        _anwenden(teil, {"id": "p1", "typ": "loeschen", "feature": "Verrundung1"}, aufnahme)


def _bohrung_attrappe(teil, senkung=False):
    """Wie der Handler normbohrung: Feature `id`, Positionsskizze `id_positionen`, weitere Unterskizze ohne Namen."""

    def handler(ctx, f):
        pos, frei = Feat(teil, f"{f['id']}_positionen", "ProfileFeature"), Feat(teil, "Skizze6", "ProfileFeature")
        haupt = teil.neues_feature(f["id"], "HoleWzd", [pos, frei])
        for k in teil.konfigurationen:
            if k != teil.aktiv:
                haupt.unterdrueckt.add(k)
                pos.unterdrueckt.add(k)
                frei.unterdrueckt.add(k)
        features = [haupt]
        ctx.mass(f"D1@{f['id']}_positionen", 12, f"{ctx.pfad(f['id'])}.positionen[0][0]", "lage", wert=12.0)
        if senkung:
            features.append(teil.neues_feature(f"{f['id']}_senkung", "Cut"))
        return FeatureErgebnis(features, punkte=[(1.0, 2.0, 3.0)])

    return handler


FEATURE = {"id": "p3", "typ": "feature", "name": "Gewinde M6 Deckel",
           "feature": {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [0, 30, 20]},
                       "positionen": [[1, 2]], "tiefe": 10}}


@pytest.fixture
def bohrung_handler(monkeypatch):
    def setze(teil, **art):
        monkeypatch.setattr(punkte, "alle_handler", lambda: {"normbohrung": _bohrung_attrappe(teil, **art)})

    return setze


def test_feature_punkt_benennt_um(aufnahme, bohrung_handler):
    teil = teil_aus(aufnahme)
    bohrung_handler(teil, senkung=True)
    namen, ctx = _anwenden(teil, FEATURE, aufnahme)
    assert {"Gewinde M6 Deckel", "Gewinde M6 Deckel Skizze", "Gewinde M6 Deckel Senkung", "Skizze6"} == set(namen)
    assert teil.feature("Gewinde M6 Deckel Skizze").GetTypeName2 == "ProfileFeature"
    assert ctx.ergebnisse["p3"].sw_name == "Gewinde M6 Deckel, Gewinde M6 Deckel Senkung"
    assert teil.feature("Bohrung2") is not None  # fremde Namen bleiben


def test_feature_punkt_massprotokoll_zeigt_auf_neue_namen_und_den_punkt(aufnahme, bohrung_handler):
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    _, ctx = _anwenden(teil, FEATURE, aufnahme)
    m = ctx.masse["p3"][0]
    assert m["name"] == "D1@Gewinde M6 Deckel Skizze"  # sonst findet `Parameter` das Maß nicht mehr
    assert m["pfad"] == "punkte[p3].feature.positionen[0][0]"


def test_feature_punkt_name_doppelt(aufnahme, bohrung_handler):
    """S18c: Ein doppelter Name bleibt ohne Ausnahme still alt."""
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, FEATURE | {"name": "Bohrung2"}, aufnahme)
    assert e.value.code == FEATURE_NICHT_ERZEUGT and "Bohrung2" in str(e.value)


def test_feature_punkt_hebt_in_allen_konfigurationen_auf(aufnahme, bohrung_handler):
    """S18c: Ein Feature aus Variante B ist in Standard unterdrückt."""
    teil = teil_aus(aufnahme)
    teil.aktiv = aufnahme["aktiv"] = "Variante B"
    bohrung_handler(teil)
    _anwenden(teil, FEATURE, aufnahme)
    assert not teil.feature("Gewinde M6 Deckel").unterdrueckt
    assert not teil.feature("Gewinde M6 Deckel Skizze").unterdrueckt
    assert all(option == 3 for _, _, option in teil.unterdrueckungen)  # nie Option 1


def test_feature_punkt_aufheben_ohne_wirkung_faellt_auf(aufnahme, bohrung_handler):
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    original = Feat.SetSuppression2
    Feat.SetSuppression2 = lambda self, a, o, n: True
    try:
        with pytest.raises(BauFehler, match="unterdrückt"):
            _anwenden(teil, FEATURE, aufnahme)
    finally:
        Feat.SetSuppression2 = original


def test_feature_punkt_kennt_fremdes_feature(aufnahme):
    teil = teil_aus(aufnahme)
    p = {"id": "p3", "typ": "feature", "name": "N",
         "feature": {"typ": "fase", "kanten": {"feature": "Schnitt-Linear1", "auswahl": "alle_kanten"}, "abstand": 1}}
    ctx = _ctx(teil, p)
    assert ctx.ergebnisse["Schnitt-Linear1"].features[0] is teil.feature("Schnitt-Linear1")
    assert ctx.gleichungen is False  # swki legt keine Gleichungen an


def test_kontext_kennt_features_aus_der_pruefung(aufnahme):
    teil = teil_aus(aufnahme)
    spec = _spec(MASS, pruefung={"masse_pruefen": [{"was": "x", "von": {"feature": "Fase3", "flaeche": "+x"},
                                                    "zu": {"punkt": [0, 0, 0]}, "soll": 1}]})
    assert "Fase3" in _ctx(teil, spec=spec).ergebnisse


def test_kontext_fremdes_feature_fehlt(aufnahme):
    teil = teil_aus(aufnahme)
    p = {"id": "p3", "typ": "feature", "name": "N", "feature": {"typ": "fase", "kanten": {"feature": "Weg", "auswahl": "alle_kanten"}}}
    with pytest.raises(BauFehler) as e:
        _ctx(teil, p)
    assert e.value.code == BESTAND_REFERENZ


def test_kontext_nennt_feature_punkte_als_features(aufnahme):
    teil = teil_aus(aufnahme)
    ctx = _ctx(teil, MASS, FEATURE)
    assert ctx.spec["parameter"] == {"A": 45}
    assert ctx.pfad("p3") == "features[0]" and ctx.spec["features"][0]["typ"] == "normbohrung"


def test_feature_punkt_nach_in_jeder_konfiguration(aufnahme, bohrung_handler):
    """Sonde Task 6: ReorderFeature wirkt nur in der aktiven Konfiguration, die übrige behielte die alte Reihenfolge."""
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    _anwenden(teil, FEATURE | {"nach": "Fase3"}, aufnahme)
    for k in aufnahme["konfigurationen"]:
        teil.aktiv = k
        namen = [f.Name for f in teil.ordnung[k]]
        assert namen.index("Gewinde M6 Deckel") == namen.index("Fase3") + 1, k
    assert teil.aktiv == aufnahme["konfigurationen"][-1]


def test_feature_punkt_nach_endet_auf_der_aktiven_konfiguration(aufnahme, bohrung_handler):
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    _anwenden(teil, FEATURE | {"nach": "Fase3"}, aufnahme)
    assert teil.aktiv == aufnahme["aktiv"]


def test_feature_punkt_nach_fehlschlag_bricht_ab(aufnahme, bohrung_handler):
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    teil.reorder_unmoeglich = {"Gewinde M6 Deckel"}
    with pytest.raises(BauFehler, match="beschädigt"):
        _anwenden(teil, FEATURE | {"nach": "Fase3"}, aufnahme)


def test_feature_punkt_nach_stimmt_nicht(aufnahme, bohrung_handler):
    """Rückgabe True genügt nicht: Der Baum entscheidet."""
    teil = teil_aus(aufnahme)
    bohrung_handler(teil)
    teil.Extension.ReorderFeature = lambda name, ziel, ort: True
    with pytest.raises(BauFehler, match="steht nicht hinter"):
        _anwenden(teil, FEATURE | {"nach": "Fase3"}, aufnahme)


def test_feature_punkt_unbekannter_handler(aufnahme, monkeypatch):
    monkeypatch.setattr(punkte, "alle_handler", lambda: {})
    teil = teil_aus(aufnahme)
    with pytest.raises(BauFehler) as e:
        _anwenden(teil, FEATURE, aufnahme)
    assert e.value.code == UNBEKANNTER_TYP


def test_feature_nach_konfigurationswechsel_mit_frischen_objekten(aufnahme, bohrung_handler):
    """S18c: Ein vor dem Umschalten geholtes IFeature zeigt auf den alten Stand."""
    teil = teil_aus(aufnahme)
    ctx = _ctx(teil, MASS)
    ctx.ergebnisse["Fase3"] = FeatureErgebnis([SimpleNamespace(Name="Fase3")])
    a = _aufnahme()
    a["masse"] = [m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m for m in a["masse"]]
    teil.masse["D2@Skizze4"].werte = {"Standard": 0.04, "Variante B": 0.04}
    ctx.knoten = "p1"
    punkt_handler("mass")(ctx, MASS, a)
    assert ctx.ergebnisse["Fase3"].features[0] is teil.feature("Fase3")


def test_loeschen_entfernt_fremde_ergebnisse(aufnahme):
    teil = teil_aus(aufnahme)
    ctx = _ctx(teil, MASS)
    ctx.ergebnisse["Fase3"] = FeatureErgebnis([teil.feature("Fase3")])
    ctx.ergebnisse["Schnitt-Linear1"] = FeatureErgebnis([teil.feature("Schnitt-Linear1")])
    punkt_handler("loeschen")(ctx, {"id": "p1", "typ": "loeschen", "feature": "Fase3", "kinder": ["Verrundung1"]}, aufnahme)
    assert "Fase3" not in ctx.ergebnisse and "Schnitt-Linear1" in ctx.ergebnisse


def test_material_in_allen_konfigurationen(aufnahme, monkeypatch):
    """Sonde Task 6: `SetMaterialPropertyName2("", …)` trifft nur die aktive Konfiguration."""
    monkeypatch.setattr(punkte, "finde_material", lambda db, soll: ("db", "1.4301 (X5CrNi18-10)"))
    teil = teil_aus(aufnahme)
    ctx = kontext(SimpleNamespace(GetMaterialDatabases=("db",)), teil, _spec(), Path("a.yaml"), 0.01)
    assert punkt_handler("material")(ctx, {"id": "p1", "typ": "material", "neu": "1.4301"}, aufnahme) == ["1.4301 (X5CrNi18-10)"]
    assert set(teil.material.values()) == {"1.4301 (X5CrNi18-10)"}


def test_material_laesst_sich_nicht_setzen(aufnahme, monkeypatch):
    monkeypatch.setattr(punkte, "finde_material", lambda db, soll: ("db", "1.4301 (X5CrNi18-10)"))
    teil = teil_aus(aufnahme)
    teil.SetMaterialPropertyName2 = lambda k, d, n: None
    ctx = kontext(SimpleNamespace(GetMaterialDatabases=("db",)), teil, _spec(), Path("a.yaml"), 0.01)
    with pytest.raises(BauFehler) as e:
        punkt_handler("material")(ctx, {"id": "p1", "typ": "material", "neu": "1.4301"}, aufnahme)
    assert e.value.code == MATERIAL_UNBEKANNT


def test_eigenschaft_setzen_datei_und_konfiguration(aufnahme):
    teil = teil_aus(aufnahme)
    _anwenden(teil, {"id": "p1", "typ": "eigenschaft", "name": "Revision", "neu": "B"}, aufnahme)
    _anwenden(teil, {"id": "p2", "typ": "eigenschaft", "name": "Bemerkung", "neu": "x", "konfiguration": "Variante B"}, aufnahme)
    assert teil.eigenschaften[""]["Revision"] == "B" and teil.eigenschaften["Variante B"]["Bemerkung"] == "x"


def test_eigenschaft_entfernen_auch_wenn_es_sie_nicht_gibt(aufnahme):
    """`Delete2` meldet bei fehlender Eigenschaft 1 (Sonde Task 6), das Ziel ist trotzdem erreicht."""
    teil = teil_aus(aufnahme)
    teil.eigenschaften[""] = {"Alt": "1"}
    assert _anwenden(teil, {"id": "p1", "typ": "eigenschaft", "name": "Alt", "neu": None}, aufnahme)[0] == ["Alt"]
    _anwenden(teil, {"id": "p2", "typ": "eigenschaft", "name": "Alt", "neu": None}, aufnahme)
    assert "Alt" not in teil.eigenschaften[""]


def test_eigenschaft_wirkt_nicht(aufnahme):
    teil = teil_aus(aufnahme)
    teil.Extension.CustomPropertyManager = lambda k: SimpleNamespace(
        Add3=lambda *a: 0, GetAll3=lambda n, t, w, a, v: None)
    with pytest.raises(BauFehler, match="Revision"):
        _anwenden(teil, {"id": "p1", "typ": "eigenschaft", "name": "Revision", "neu": "B"}, aufnahme)


def _skript(tmp_path, text):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "p6.py").write_text(text, encoding="utf-8")
    return {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "Endbedingung ändern"}


def test_skript_ohne_umbenennen(tmp_path, aufnahme):
    """Präzisierung 6: Ein Eingriff in ein fremdes Feature darf `None` liefern, kein Name ändert sich."""
    p = _skript(tmp_path, "def bauen(ctx):\n    return None\n")
    teil = teil_aus(aufnahme)
    ctx = kontext(SimpleNamespace(), teil, _spec(p), tmp_path / "aenderung.yaml", 0.01)
    assert punkt_handler("skript")(ctx, p, aufnahme) == []


def test_skript_rueckgabe_behaelt_namen(tmp_path, aufnahme):
    p = _skript(tmp_path, 'def bauen(ctx):\n    return ctx.model.FeatureByName("Fase3")\n')
    teil = teil_aus(aufnahme)
    ctx = kontext(SimpleNamespace(), teil, _spec(p), tmp_path / "aenderung.yaml", 0.01)
    assert punkt_handler("skript")(ctx, p, aufnahme) == ["Fase3"]
    assert teil.feature("Fase3") is not None


def test_handler_skript_des_compilers_bleibt_streng(tmp_path, aufnahme):
    """Teil-Specs: `bauen(ctx)` muss weiter ein Feature liefern, und es heißt nach der ID."""
    from swki.compiler.handler.skript import skript

    (tmp_path / "s.py").write_text("def bauen(ctx):\n    return None\n", encoding="utf-8")
    ctx = SimpleNamespace(spec_pfad=tmp_path / "t.yaml", app=None, model=None)
    with pytest.raises(BauFehler, match="kein Feature"):
        skript(ctx, {"id": "f1", "datei": "s.py"})


def test_neuaufbau_fehler_kommen_aus_dem_bau_nicht_aus_dem_handler(aufnahme):
    """Punkt-Handler melden keine Neuaufbaufehler selbst: Bekannt ist je Konfiguration verschieden, das entscheidet der Bau."""
    a = _aufnahme()
    a["masse"] = [m | {"werte": {"Standard": 40.0, "Variante B": 40.0}} if m["name"] == "D2@Skizze4" else m for m in a["masse"]]
    teil = teil_aus(a)
    teil.fehler["Variante B"] = [("Fase3", 12, False)]
    _anwenden(teil, MASS, a)
    assert REBUILD_FEHLER  # kein BauFehler bis hier
