"""Aufnahme ohne SolidWorks: Reihenfolge von `aufnehmen` mit Attrappen, Ableitung von zustand/quelle/gruppe, aktive
Konfiguration nach dem Lesen (Plan Review Focus 4), Zusammenfassung, `zeige` bis vor das Öffnen."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.bestand import befehle, sw_bestand
from swki.bestand.ablage import bestand_ordner, lade_aufnahme
from swki.bestand.fehler import (BESTAND_NICHT_LESBAR, BESTAND_REFERENZ, BESTAND_REFERENZ_EXTERN, BESTAND_UNBEKANNT,
                                 BESTAND_VERSION_NEUER, BestandFehler)
from swki.bestand.sw_bestand import leite_masse, links_von, lies_bestand, massname, whats_wrong
from swki.cli import main
from swki.konfig import Rechner
from tests.bestand.beispiel_aufnahme import AUFNAHME


class App:
    """ISldWorks für `aufnehmen`: Version und Abhängigkeiten ohne Öffnen."""

    def __init__(self, versionen=("18000[2025/268]",), abhaengig=None):
        self.versionen, self.abhaengig = versionen, abhaengig
        self.GetLatestSupportedFileVersion = 18000
        self.geschlossen, self.gefragt = [], []

    def VersionHistory(self, pfad):
        self.gefragt.append(pfad)
        return self.versionen

    def GetDocumentDependencies2(self, pfad, tief, suche, nur_lesen):
        assert (tief, suche, nur_lesen) == (True, False, False)
        self.gefragt.append(pfad)
        return self.abhaengig

    def CloseDoc(self, titel):
        self.geschlossen.append(titel)


GELESEN = {"version": 1, "konfigurationen": ["Standard", "Variante B"], "aktiv": "Standard", "material": "1.0038",
           "eigenschaften": {"datei": {}, "konfiguration": {}}, "externe_referenzen": [], "gleichungen": [],
           "variablen": {}, "features": [], "reihenfolge": {}, "skizzen": {}, "masse": [], "neuaufbau": [],
           "geometrie": {}, "tabelle": False, "einheitensystem": 5}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """Original, Rechner, Attrappen für verbinde, oeffne, lies_bestand, screenshots."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    original = tmp_path / "kunde" / "Lagerdeckel.SLDPRT"
    original.parent.mkdir()
    original.write_bytes(b"inhalt")
    u = SimpleNamespace(r=r, original=original, app=App(), geoeffnet=[], gelesen=dict(GELESEN), bilder=[], lesefehler=None)

    def oeffne(app, pfad, sichtbar=True, nur_lesen=False):
        u.geoeffnet.append({"pfad": pfad, "sichtbar": sichtbar, "nur_lesen": nur_lesen})
        return SimpleNamespace(GetTitle=pfad.name)

    def lies(app, model):
        if u.lesefehler is not None:
            raise u.lesefehler
        return u.gelesen

    def screenshots(app, model, ordner):
        u.bilder.append(ordner)
        return {"iso": str(ordner / "iso.png")}

    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    monkeypatch.setattr(befehle, "verbinde", lambda jahr: u.app)
    monkeypatch.setattr(befehle, "oeffne", oeffne)
    monkeypatch.setattr(befehle, "lies_bestand", lies)
    monkeypatch.setattr(befehle, "screenshots", screenshots)
    return u


def test_version_neuer_bricht_vor_dem_oeffnen_ab(umgebung):
    umgebung.app.versionen = ("17000[2024/100]", "19000[2026/300]")
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(umgebung.original, "a1")
    assert e.value.daten["code"] == BESTAND_VERSION_NEUER
    assert umgebung.geoeffnet == [] and not bestand_ordner(umgebung.r, "a1", 1).exists()


def test_version_aelter_steht_in_der_aufnahme(umgebung):
    umgebung.app.versionen = ("16000[2023/100]",)
    assert befehle.aufnehmen(umgebung.original, "a1")["version_aelter"] is True
    assert lade_aufnahme(umgebung.r, "a1", 1)["datei"]["version_aelter"] is True


def test_version_unlesbar_ist_nicht_lesbar(umgebung):
    umgebung.app.versionen = None
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(umgebung.original, "a1")
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and umgebung.geoeffnet == []


def test_externe_referenzen_lehnt_ab(umgebung):
    umgebung.app.abhaengig = ("Basis", "D:\\Kunde\\Basis.SLDPRT")
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(umgebung.original, "a1")
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN
    assert e.value.daten["referenzen"] == ["D:\\Kunde\\Basis.SLDPRT"]
    assert umgebung.geoeffnet == [] and not bestand_ordner(umgebung.r, "a1", 1).exists()


def test_externe_referenz_erst_im_offenen_dokument_lehnt_ab(umgebung):
    """S18: GetDocumentDependencies2 ist nur am abgeleiteten Teil gemessen; was die Datei selbst nennt, zählt mit."""
    umgebung.gelesen["externe_referenzen"] = ["D:\\Kunde\\Anderes.SLDPRT"]
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(umgebung.original, "a1")
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN
    assert umgebung.app.geschlossen and not (bestand_ordner(umgebung.r, "a1", 1) / "bestand.json").exists()


def test_original_fehlt_ohne_solidworks(umgebung):
    umgebung.original.unlink()
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(umgebung.original, "a1")
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and umgebung.app.gefragt == []


def test_oeffnet_nur_die_kopie_nur_lesend(umgebung):
    befehle.aufnehmen(umgebung.original, "a1")
    ordner = bestand_ordner(umgebung.r, "a1", 1)
    assert umgebung.geoeffnet and all(g["nur_lesen"] and g["pfad"].parent == ordner for g in umgebung.geoeffnet)
    assert umgebung.geoeffnet[0]["sichtbar"] is False  # S18: unsichtbar spart 2,3 GB; nur die Bilder brauchen ein Fenster
    assert umgebung.bilder == [ordner / "bilder"]


def test_schliesst_auch_bei_fehler(umgebung):
    umgebung.lesefehler = RuntimeError("COM weg")
    with pytest.raises(RuntimeError):
        befehle.aufnehmen(umgebung.original, "a1")
    assert umgebung.app.geschlossen == ["Lagerdeckel.SLDPRT"]
    assert not (bestand_ordner(umgebung.r, "a1", 1) / "bestand.json").exists()


def test_gescheiterte_aufnahme_wird_nachgeholt(umgebung):
    umgebung.lesefehler = RuntimeError("COM weg")
    with pytest.raises(RuntimeError):
        befehle.aufnehmen(umgebung.original, "a1")
    umgebung.lesefehler = None
    aus = befehle.aufnehmen(umgebung.original, "a1")
    assert aus["aufnahme"] == 1 and lade_aufnahme(umgebung.r, "a1", 1)["aktiv"] == "Standard"


def test_gleiche_datei_liest_nichts_neu(umgebung):
    befehle.aufnehmen(umgebung.original, "a1")
    umgebung.geoeffnet.clear()
    aus = befehle.aufnehmen(umgebung.original, "a1")
    assert umgebung.geoeffnet == [] and aus["aufnahme"] == 1 and aus["neu"] is False


def test_aufnahme_traegt_datei_und_jahr(umgebung):
    befehle.aufnehmen(umgebung.original, "a1")
    a = lade_aufnahme(umgebung.r, "a1", 1)
    assert a["sw_jahr"] == 2025 and a["datei"]["name"] == "Lagerdeckel.SLDPRT"
    assert a["datei"]["original"] == str(umgebung.original) and a["datei"]["versionen"] == ["18000[2025/268]"]
    assert a["datei"]["version_aelter"] is False and len(a["datei"]["sha256"]) == 64 and a["tabelle"] is False


def test_zusammenfassung_kompakt():
    a = json.loads(json.dumps(AUFNAHME))
    a["skizzen"] = {"Skizze1": 3, "Skizze5": 2, "Rippe/Skizze5": 2}
    a["neuaufbau"] = [{"konfiguration": "Standard", "feature": "Fase3", "code": 12, "warnung": False}]
    aus = befehle.zusammenfassung("a1", 2, a, Path("C:/arbeit/a1/bestand-2"), neu=True)
    assert aus["auftrag"] == "a1" and aus["aufnahme"] == 2 and aus["konfigurationen"] == ["Standard", "Variante B"]
    assert aus["zaehler"] == {"konfigurationen": 2, "features": 7, "masse": 8, "gleichungen": 3, "variablen": 1, "neuaufbau": 1}
    assert aus["skizzen_offen"] == {"Skizze5": 2} and aus["neuaufbau"] == a["neuaufbau"]
    masse = {m["name"]: m for m in aus["masse"]}
    assert masse["D1@Skizze1"] == {"name": "D1@Skizze1", "wert": 100.0, "zustand": "gesteuert"}
    assert masse["D5@Skizze5"]["wert"] == {"Standard": 12.0, "Variante B": 15.0}  # je Konfiguration nur, wenn verschieden
    assert masse["D2@Skizze4"]["wert"] == 40.0                                    # None zählt nicht als abweichend
    assert {"name": "Bohrung2", "typ": "Cut"} in aus["features"]
    text = json.dumps(aus, ensure_ascii=False)
    assert "punkte" not in text and "eigenschaften" not in text and "quelle" not in text


# ------------------------------------------------------------------------------------------- Ableitung (rein)


def _roh(name, driven=2, tabelle=False, verknuepft=None):
    return {"name": name, "feature": name.split("@")[-1], "werte": {"Standard": 1.0}, "einheit": "mm", "punkte": [],
            "driven": driven, "tabelle": tabelle, "verknuepft": verknuepft}


def _gl(text, ist_global=False):
    return {"index": 0, "text": text, "links": links_von(text), "global": ist_global}


def _je_name(roh, gleichungen):
    return {m["name"]: m for m in leite_masse(roh, gleichungen)}


def test_links_von():
    assert links_von('"D1@Skizze1" = "L" * 2') == "D1@Skizze1"
    assert links_von('"L"= 100') == "L"
    assert links_von("kaputt") == "kaputt"


def test_massname_schneidet_nur_das_letzte_ab():
    assert massname("D1@Skizze1@Lagerdeckel.Part") == "D1@Skizze1"
    assert massname("Bohrung_D@Skizze3@Teil8.Part") == "Bohrung_D@Skizze3"


def test_treibend_ist_der_normalfall():
    m = _je_name([_roh("D2@Skizze4")], [])["D2@Skizze4"]
    assert (m["zustand"], m["quelle"], m["gruppe"]) == ("treibend", None, None)
    assert set(m) == {"name", "feature", "werte", "einheit", "zustand", "quelle", "gruppe", "punkte"}


def test_linke_seite_ist_gesteuert_trotz_driven_state_1():
    """S18b: DrivenState ist 1 bei Gleichung und Referenzmaß; nur die Gleichung trennt die beiden."""
    gl = [_gl('"L"= 100', True), _gl('"D1@Skizze1" = "L"'), _gl('"D3@Skizze2" = "D1@Skizze1" + 5')]
    m = _je_name([_roh("D1@Skizze1", driven=1), _roh("D3@Skizze2", driven=1), _roh("D5@Skizze2", driven=1)], gl)
    assert (m["D1@Skizze1"]["zustand"], m["D1@Skizze1"]["quelle"]) == ("gesteuert", {"art": "variable", "name": "L"})
    assert (m["D3@Skizze2"]["zustand"], m["D3@Skizze2"]["quelle"]) == ("gesteuert", {"art": "gleichung", "name": "D3@Skizze2"})
    assert (m["D5@Skizze2"]["zustand"], m["D5@Skizze2"]["quelle"]) == ("getrieben", None)


def test_ausdruck_mit_variable_ist_gleichung():
    gl = [_gl('"L"= 100', True), _gl('"D1@Skizze1" = "L" * 2')]
    assert _je_name([_roh("D1@Skizze1", driven=1)], gl)["D1@Skizze1"]["quelle"] == {"art": "gleichung", "name": "D1@Skizze1"}


def test_jedes_mass_links_ist_gesteuert_auch_mit_driven_state_2():
    """`zustand` ist die einzige Quelle für MASS_GESTEUERT: DrivenState darf eine Gleichung nie aufheben."""
    assert _je_name([_roh("D1@Skizze1", driven=2)], [_gl('"D1@Skizze1" = 5')])["D1@Skizze1"]["zustand"] == "gesteuert"


@pytest.mark.parametrize("links", ["D1@Skizze1@Lagerdeckel.Part", "d1@skizze1"])
def test_linke_seite_mit_dateiname_oder_anderer_schreibweise(links):
    m = _je_name([_roh("D1@Skizze1", driven=1)], [_gl(f'"{links}" = 5')])["D1@Skizze1"]
    assert m["zustand"] == "gesteuert" and m["quelle"] == {"art": "gleichung", "name": links}


def test_tabellenmass_ist_gesteuert():
    m = _je_name([_roh("D1@Tasche", driven=2, tabelle=True)], [])["D1@Tasche"]
    assert (m["zustand"], m["quelle"]) == ("gesteuert", {"art": "tabelle", "name": None})


def test_verknuepfte_masse_sind_treibend_mit_gruppe():
    """Plan Präzisierung 1: kein führendes Maß, jedes Mitglied setzt alle."""
    m = _je_name([_roh("Bohrung_D@Skizze3", verknuepft="Bohrung_D"), _roh("Bohrung_D@Skizze4", verknuepft="Bohrung_D")], [])
    assert {x["gruppe"] for x in m.values()} == {"Bohrung_D"} and {x["zustand"] for x in m.values()} == {"treibend"}


def test_gleichung_auf_einem_mitglied_steuert_die_ganze_gruppe():
    """Sonst setzt ein mass-Punkt auf den Partner still einen Wert, den der Neuaufbau zurückdreht (S18c)."""
    gl = [_gl('"Bohrung_D@Skizze3" = 8')]
    m = _je_name([_roh("Bohrung_D@Skizze3", driven=1, verknuepft="Bohrung_D"),
                  _roh("Bohrung_D@Skizze4", verknuepft="Bohrung_D")], gl)
    assert m["Bohrung_D@Skizze4"]["zustand"] == "gesteuert" and m["Bohrung_D@Skizze4"]["quelle"] == m["Bohrung_D@Skizze3"]["quelle"]


def test_ableitung_passt_zur_attrappe_der_validierung():
    """Die Formen von `quelle`, die `swki.bestand.spec._quelle_text` auswertet, kommen so auch aus der Ableitung."""
    arten = {m["quelle"]["art"] for m in AUFNAHME["masse"] if m["quelle"]}
    gl = [_gl('"L"= 100', True), _gl('"D1@Skizze1" = "L"'), _gl('"D3@Skizze2" = "D1@Skizze1" + 5')]
    m = _je_name([_roh("D1@Skizze1", 1), _roh("D3@Skizze2", 1), _roh("D8@Skizze9", 2, tabelle=True)], gl)
    assert {x["quelle"]["art"] for x in m.values()} == arten


# ------------------------------------------------------------------------------------------- Lesen mit Attrappe


class Eigenschaften:
    def GetAll3(self, *ausgaben):
        pass


class Erweiterung:
    GetWhatsWrongCount = 0
    HasDesignTable = False

    def CustomPropertyManager(self, konfiguration):
        return Eigenschaften()

    def ListExternalFileReferences(self, *ausgaben):
        pass

    def GetUserPreferenceInteger(self, was, option):
        return 5

    @property
    def CreateMassProperty2(self):
        return self.modell.masse()


class Modell:
    """IModelDoc2 ohne Features: genug, um das Umschalten der Konfigurationen zu prüfen."""

    FirstFeature = None
    EditRebuild3 = True

    def __init__(self, aktiv="Variante B", fehler_in=None):
        self.aktiv, self.fehler_in, self.geschaltet = aktiv, fehler_in, []
        self.GetConfigurationNames = ("Standard", "Variante B", "Variante C")
        self.Extension = Erweiterung()
        self.Extension.modell = self
        self.GetEquationMgr = SimpleNamespace(GetCount=0)

    @property
    def ConfigurationManager(self):
        return SimpleNamespace(ActiveConfiguration=SimpleNamespace(Name=self.aktiv))

    def ShowConfiguration2(self, name):
        self.geschaltet.append(name)
        self.aktiv = name
        return True

    def masse(self):
        if self.aktiv == self.fehler_in:
            raise RuntimeError("COM weg")
        return SimpleNamespace(UseSystemUnits=True, Volume=1e-6, CenterOfMass=(0.0, 0.0, 0.0))

    def GetBodies2(self, art, nur_sichtbare):
        return ()

    def GetPartBox(self, immer):
        return (0.0, 0.0, 0.0, 0.01, 0.01, 0.01)

    def GetMaterialPropertyName2(self, konfiguration, datenbank):
        return "1.0038"


@pytest.fixture
def byref(monkeypatch):
    monkeypatch.setattr(sw_bestand, "byref_variant", lambda: SimpleNamespace(value=None))
    monkeypatch.setattr(sw_bestand, "byref_long", lambda: SimpleNamespace(value=0))
    monkeypatch.setattr(sw_bestand, "byref_str", lambda: SimpleNamespace(value=""))


def test_aktive_konfiguration_bleibt_und_steht_vorn(byref):
    model = Modell(aktiv="Variante B")
    d = lies_bestand(None, model)
    assert model.aktiv == "Variante B" and d["aktiv"] == "Variante B"
    assert d["konfigurationen"] == ["Variante B", "Standard", "Variante C"]  # Spec §5.2: aktive zuerst
    assert set(d["geometrie"]) == set(d["reihenfolge"]) == {"Standard", "Variante B", "Variante C"}
    assert d["tabelle"] is False and d["neuaufbau"] == [] and "datei" not in d and "sw_jahr" not in d


def test_material_je_konfiguration_und_der_aktiven(byref):
    """Das Material gilt je Konfiguration (Sonde Task 6); `material` bleibt der Wert der aktiven."""
    model = Modell(aktiv="Variante B")
    model.GetMaterialPropertyName2 = lambda k, d: {"Standard": "1.0038"}.get(k, "1.4301")
    d = lies_bestand(None, model)
    assert d["material"] == "1.4301"
    assert d["materialien"] == {"Variante B": "1.4301", "Standard": "1.0038", "Variante C": "1.4301"}


def test_aktive_konfiguration_bleibt_im_fehlerfall(byref):
    model = Modell(aktiv="Variante B", fehler_in="Standard")
    with pytest.raises(RuntimeError):
        lies_bestand(None, model)
    assert model.aktiv == "Variante B" and model.geschaltet[-1] == "Variante B"


def test_konfiguration_laesst_sich_nicht_schalten(byref):
    """Rückgaben nicht glauben (S18c): gelesen wird nur, was wirklich aktiv ist."""
    model = Modell(aktiv="Variante B")
    model.ShowConfiguration2 = lambda name: True  # bleibt stehen
    with pytest.raises(BestandFehler) as e:
        lies_bestand(None, model)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR


def test_neuaufbau_traegt_die_konfiguration(byref, monkeypatch):
    monkeypatch.setattr(sw_bestand, "whats_wrong", lambda m: [{"feature": "Rippe", "code": 1, "warnung": False}]
                        if m.aktiv == "Standard" else [])
    d = lies_bestand(None, Modell(aktiv="Variante B"))
    assert d["neuaufbau"] == [{"konfiguration": "Standard", "feature": "Rippe", "code": 1, "warnung": False}]


def test_whats_wrong(monkeypatch):
    werte = iter([(SimpleNamespace(Name="Fase1"),), (12,), (True,)])
    monkeypatch.setattr(sw_bestand, "byref_variant", lambda: SimpleNamespace(value=next(werte)))
    model = SimpleNamespace(Extension=SimpleNamespace(GetWhatsWrongCount=1, GetWhatsWrong=lambda f, c, w: None))
    assert whats_wrong(model) == [{"feature": "Fase1", "code": 12, "warnung": True}]
    assert whats_wrong(SimpleNamespace(Extension=SimpleNamespace(GetWhatsWrongCount=0))) == []


def test_unterdrueckung_je_konfiguration_einzeln_gefragt():
    """Live gemessen: IsSuppressed2 liefert in Dokumentreihenfolge, die Reihenfolge der übergebenen Namen zählt nicht."""
    class Feature:
        Name, GetTypeName2, GetParents, GetChildren, GetFirstSubFeature = "Fase1", "Chamfer", None, None, None

        def IsSuppressed2(self, art, namen):
            return tuple(u for k, u in (("Standard", False), ("Variante B", True)) if k in namen.value)

    d = sw_bestand._feature_eintrag(Feature(), ["Variante B", "Standard"], False)
    assert d["unterdrueckt"] == {"Variante B": True, "Standard": False}
    assert d["unter"] == []


def test_unterfeatures_stehen_beim_feature():
    """Der Vergleich erkennt daran, welche neuen Features zu einem feature-Punkt gehören (Bohrungsassistent: Skizzen, Gewinde)."""
    class Sub:
        def __init__(self, name, nach=None):
            self.Name, self.GetNextSubFeature = name, nach

    class Feature:
        Name, GetTypeName2, GetParents, GetChildren = "Bohrung", "HoleWzd", None, None
        GetFirstSubFeature = Sub("Skizze6", Sub("Bohrungsgewinde1"))

        def IsSuppressed2(self, art, namen):
            return (False,)

    assert sw_bestand._feature_eintrag(Feature(), ["Standard"], False)["unter"] == ["Skizze6", "Bohrungsgewinde1"]


def test_externe_referenzen_paare():
    app = App(abhaengig=("Basis", "D:\\A\\Basis.SLDPRT", "Zweite", "D:\\A\\Zweite.SLDPRT"))
    assert sw_bestand.externe_referenzen(app, Path("x.SLDPRT")) == ["D:\\A\\Basis.SLDPRT", "D:\\A\\Zweite.SLDPRT"]
    assert sw_bestand.externe_referenzen(App(abhaengig=None), Path("x.SLDPRT")) == []


# ------------------------------------------------------------------------------------------- zeige


@pytest.fixture
def aufgenommen(umgebung, monkeypatch):
    umgebung.gelesen = {**GELESEN, **json.loads(json.dumps({k: AUFNAHME[k] for k in ("masse", "features")}))}
    befehle.aufnehmen(umgebung.original, "a1")
    umgebung.geoeffnet.clear()
    umgebung.gezeigt = []
    monkeypatch.setattr(befehle, "zeige_mass", lambda app, model, m, pfad: umgebung.gezeigt.append(("mass", m["name"], pfad)))
    monkeypatch.setattr(befehle, "zeige_feature", lambda app, model, n, pfad: umgebung.gezeigt.append(("feature", n, pfad)))
    return umgebung


def test_zeige_mass_nur_lesend_in_die_bilder_der_aufnahme(aufgenommen):
    aus = befehle.zeige("a1", "D2@Skizze4", None)
    ordner = bestand_ordner(aufgenommen.r, "a1", 1)
    assert [g["nur_lesen"] for g in aufgenommen.geoeffnet] == [True] and aufgenommen.geoeffnet[0]["pfad"].parent == ordner
    art, name, pfad = aufgenommen.gezeigt[0]
    assert (art, name) == ("mass", "D2@Skizze4") and pfad.parent == ordner / "bilder" and aus["bild"] == str(pfad)
    assert "@" not in pfad.name  # SaveAs3: swFileNameContainsAtSign
    assert aufgenommen.app.geschlossen == ["Lagerdeckel.SLDPRT"] * 3  # lesen, Bilder, zeige


def test_zeige_feature(aufgenommen):
    befehle.zeige("a1", None, "Bohrung2")
    assert aufgenommen.gezeigt[0][:2] == ("feature", "Bohrung2")


def test_zeige_schliesst_auch_bei_fehler(aufgenommen, monkeypatch):
    def scheitert(*a):
        raise RuntimeError("COM weg")

    monkeypatch.setattr(befehle, "zeige_mass", scheitert)
    aufgenommen.app.geschlossen.clear()
    with pytest.raises(RuntimeError):
        befehle.zeige("a1", "D2@Skizze4", None)
    assert aufgenommen.app.geschlossen == ["Lagerdeckel.SLDPRT"]


@pytest.mark.parametrize(("mass", "feature"), [("D9@Gibtsnicht", None), (None, "Gibtsnicht")])
def test_zeige_unbekannt_oeffnet_nichts(aufgenommen, mass, feature):
    with pytest.raises(BestandFehler) as e:
        befehle.zeige("a1", mass, feature)
    assert e.value.daten["code"] == BESTAND_REFERENZ and aufgenommen.geoeffnet == []


def test_zeige_ohne_aufnahme(umgebung):
    with pytest.raises(BestandFehler) as e:
        befehle.zeige("a9", "D2@Skizze4", None)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_zeige_waehlt_konfiguration_ohne_unterdrueckung():
    """Im aktiven Stand unterdrückt: das Bild zeigte sonst nichts, ohne dass es auffällt."""
    a = {"aktiv": "Standard", "konfigurationen": ["Standard", "Variante B"],
         "features": [{"name": "Fase1", "unterdrueckt": {"Standard": True, "Variante B": False}},
                      {"name": "Skizze1", "unterdrueckt": {"Standard": False, "Variante B": False}}]}
    assert befehle.sichtbar_in(a, "Fase1") == "Variante B"
    assert befehle.sichtbar_in(a, "Skizze1") == "Standard"
    assert befehle.sichtbar_in(a, "fehlt") == "Standard"


def test_cli_verdrahtet(umgebung, capsys):
    assert main(["bestand", "aufnehmen", str(umgebung.original), "--auftrag", "a1"]) == 0
    assert json.loads(capsys.readouterr().out)["aufnahme"] == 1
    assert main(["bestand", "zeige", "a1"]) == 1  # --mass oder --feature ist Pflicht
    assert main(["bestand", "zeige", "a1", "--mass", "x", "--feature", "y"]) == 1
