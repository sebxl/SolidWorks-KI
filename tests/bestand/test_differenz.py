"""Geometrie-Differenz (Spec Bestandsdateien §7.2): Bereiche rein, `koerper_differenz` an Attrappen, die nachbilden, was S18d und
die Sonde aus Task 8 gemessen haben: `Operations2` verbraucht beide Körper, gleiche Körper liefern `(None, 0)`, getrennte Körper
das Ziel unverändert."""

from types import SimpleNamespace

import pytest

from swki.bestand.differenz import (Abweichung, DifferenzFehler, alle_feature_boxen, bewerte_bereiche, dicke, koerper_differenz)

SPEC_BOX = {"punkte": [{"id": "p1", "typ": "mass"}],
            "bereiche": [{"punkte": ["p1"], "box": {"min": [-50, 0, 0], "max": [-20, 40, 20]}}]}
IM_BEREICH = [-40, 10, 10, -30, 20, 20]
DRAUSSEN = [10, 10, 10, 20, 20, 20]


def alle_ok(eintraege: list[dict]) -> bool:
    return all(e["ok"] is True for e in eintraege)


def bereich(eintraege: list[dict]) -> list[dict]:
    return [e for e in eintraege if e["id"] == "bereich"]


def test_abweichung_im_bereich_ok():
    a = {"Standard": [Abweichung("entfernt", IM_BEREICH, 500.0)]}
    e = bewerte_bereiche(SPEC_BOX, a, {})
    assert alle_ok(e)
    assert bereich(e)[0]["ist"][0] | {"dicke": None} == {
        "art": "entfernt", "box": IM_BEREICH, "volumen": 500.0, "flaeche": None, "dicke": None, "bereich": 0,
        "unter_toleranz": False}


def test_abweichung_ausserhalb_ist_mangel():
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0), Abweichung("entfernt", DRAUSSEN, 12.5)]}
    [e] = bereich(bewerte_bereiche(SPEC_BOX, a, {}))
    assert e["ok"] is False and e["konfiguration"] == "Standard" and e["knoten"] == []
    assert "12.5" in e["hinweis"] and "Standard" in e["hinweis"] and "10" in e["hinweis"] and "entfernt" in e["hinweis"]
    assert [x["bereich"] for x in e["ist"]] == [0, None]


@pytest.mark.parametrize("ueber, ok", [(0.005, True), (0.02, False)])
def test_box_grenze_mit_toleranz(ueber, ok):
    a = {"Standard": [Abweichung("hinzu", [-40, 10, 10, -20 + ueber, 20, 20], 500.0)]}
    assert bereich(bewerte_bereiche(SPEC_BOX, a, {}))[0]["ok"] is ok


def test_splitter_unter_toleranz_zaehlt_nicht():
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0), Abweichung("hinzu", [10, 10, 10, 10.005, 10.005, 10.005], 1e-7)]}
    [e] = bereich(bewerte_bereiche(SPEC_BOX, a, {}))
    assert e["ok"] is True and [x["unter_toleranz"] for x in e["ist"]] == [False, True]


def test_verschobene_flaeche_5_um_ist_unter_toleranz():
    """S18d: Der Körper ist exakt, 50 × 60 × 20 mm groß wäre er nur als Box; zählen darf nur die Dicke."""
    flach = Abweichung("hinzu", [50.0, -30.0, 0.0, 50.005, 30.0, 20.0], 5.99, 2396.0)
    assert dicke(flach) == pytest.approx(0.005)
    assert bereich(bewerte_bereiche(SPEC_BOX, {"Standard": [flach]}, {}))[0]["ok"] is True
    grob = Abweichung("hinzu", [50.0, -30.0, 0.0, 50.05, 30.0, 20.0], 59.9, 2400.0)
    assert bereich(bewerte_bereiche(SPEC_BOX, {"Standard": [grob]}, {}))[0]["ok"] is False


@pytest.mark.parametrize("versatz", [0.02, 0.012])
def test_bohrung_versetzt_bleibt_ueber_toleranz(versatz):
    """S18d, Sichel: Box 4 × 8 × 20, im Mittel nur 2/π des Versatzes dick. 12 µm liegen über der Toleranz, auch wenn das Mittel darunter
    bleibt: `2·V/A` allein reicht nicht."""
    sichel = Abweichung("entfernt", [35.98, 11.0, 0.0, 39.99, 19.0, 20.0], 8.0 * versatz * 20, 2 * 3.14159 * 4 * 20)
    assert dicke(sichel) > 0.01
    assert bereich(bewerte_bereiche(SPEC_BOX, {"Standard": [sichel]}, {}))[0]["ok"] is False


def test_bereich_features_aus_boxen():
    spec = {"punkte": [{"id": "p1", "typ": "unterdruecken"}], "bereiche": [{"punkte": ["p1"], "features": ["Fase1", "Tasche"]}]}
    boxen = {"Fase1": [0, 0, 18, 10, 10, 20], "Tasche": [0, 0, 10, 10, 10, 18]}
    a = {"Standard": [Abweichung("hinzu", [0, 0, 12, 10, 10, 20.005], 200.0)]}
    assert alle_ok(bewerte_bereiche(spec, a, boxen))  # ein Hüllquader über die Features des Bereichs (Spec §7.2)
    draussen = {"Standard": [Abweichung("hinzu", [0, 0, 12, 10, 10, 20.5], 200.0)]}
    assert bereich(bewerte_bereiche(spec, draussen, boxen))[0]["ok"] is False


def test_feature_bereich_ohne_box_nimmt_nichts_auf():
    """Hat das Feature keine Flächen, kann der Bereich nichts erklären: Mangel, kein stilles Bestehen."""
    spec = {"punkte": [{"id": "p1", "typ": "skript"}], "bereiche": [{"punkte": ["p1"], "features": ["Skizze1"]}]}
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
    assert bereich(bewerte_bereiche(spec, a, {}))[0]["ok"] is False


def test_bereich_gilt_nur_in_den_konfigurationen_seiner_punkte():
    spec = {"punkte": [{"id": "p1", "typ": "mass", "konfigurationen": ["Standard"]}], "bereiche": SPEC_BOX["bereiche"]}
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0)], "Variante B": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
    e = {x["konfiguration"]: x["ok"] for x in bereich(bewerte_bereiche(spec, a, {}))}
    assert e == {"Standard": True, "Variante B": False}


def test_ein_eintrag_je_konfiguration():
    a = {"Standard": [], "Variante B": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
    assert [x["konfiguration"] for x in bereich(bewerte_bereiche(SPEC_BOX, a, {}))] == ["Standard", "Variante B"]


def test_punkt_ohne_wirkung_ist_mangel():
    e = bewerte_bereiche(SPEC_BOX, {"Standard": []}, {})
    [m] = [x for x in e if x["ok"] is False]
    assert m["id"] == "punkt:p1" and m["knoten"] == ["p1"] and "keine Abweichung" in m["hinweis"]


def test_punkt_mit_wirkung_unter_toleranz_oder_in_einer_konfiguration_genuegt():
    """Fase in Variante B schon unterdrückt: `alle` wirkt nur in Standard. Auch ein Punkt von 5 µm hat gewirkt."""
    klein = Abweichung("hinzu", [-40, 10, 10, -39.995, 20, 20], 0.5)
    assert alle_ok(bewerte_bereiche(SPEC_BOX, {"Standard": [klein], "Variante B": []}, {}))


def test_wirkung_zaehlt_nur_in_den_konfigurationen_des_punkts():
    spec = {"punkte": [{"id": "p1", "typ": "mass", "konfigurationen": ["Standard"]}], "bereiche": SPEC_BOX["bereiche"]}
    a = {"Standard": [], "Variante B": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
    assert [x["ok"] for x in bewerte_bereiche(spec, a, {}) if x["id"] == "punkt:p1"] == [False]


@pytest.mark.parametrize("punkt", [{"id": "p1", "typ": "skript"}, {"id": "p1", "typ": "material"}, {"id": "p1", "typ": "eigenschaft"},
                                   {"id": "p1", "typ": "feature", "feature": {"typ": "referenz"}}])
def test_punkte_ohne_pflicht_zur_wirkung(punkt):
    spec = {"punkte": [punkt], "bereiche": SPEC_BOX["bereiche"]}
    assert alle_ok(bewerte_bereiche(spec, {"Standard": []}, {}))


def test_fehlercode_ist_nicht_nachgewiesen():
    e = bewerte_bereiche(SPEC_BOX, {"Standard": "Operations2 meldet Fehler 3"}, {})
    assert [(x["id"], x["ok"]) for x in e] == [("bereich", None), ("punkt:p1", None)]
    assert "Operations2 meldet Fehler 3" in e[0]["hinweis"] and e[0]["ist"] == []


def test_fehlercode_uebersteht_keinen_nachweis_der_wirkung_anderswo():
    """Die Wirkung ist in Variante B nachgewiesen, der Bereich in Standard bleibt offen."""
    e = bewerte_bereiche(SPEC_BOX, {"Standard": "Fehler", "Variante B": [Abweichung("hinzu", IM_BEREICH, 5.0)]}, {})
    assert [(x["id"], x["ok"]) for x in e] == [("bereich", None), ("bereich", True), ("punkt:p1", True)]


def _mit_delta(soll, **mehr) -> dict:
    return SPEC_BOX | {"pruefung": {"volumen_delta": {"soll": soll, **mehr}}}


def test_volumen_delta():
    """Vorzeichen: nachher minus vorher."""
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 800.0), Abweichung("entfernt", IM_BEREICH, 300.0)]}
    [e] = [x for x in bewerte_bereiche(_mit_delta(500), a, {}) if x["id"] == "volumen_delta"]
    assert e["ok"] is True and e["ist"] == {"Standard": 500.0} and e["soll"] == 500
    [e] = [x for x in bewerte_bereiche(_mit_delta(-500), a, {}) if x["id"] == "volumen_delta"]
    assert e["ok"] is False and "Standard" in e["hinweis"]


def test_volumen_delta_toleranz():
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 504.0)]}
    def ok(**mehr):
        return next(x["ok"] for x in bewerte_bereiche(_mit_delta(500, **mehr), a, {}) if x["id"] == "volumen_delta")
    assert ok(toleranz_prozent=1) is True and ok(toleranz_prozent=0.5) is False
    assert ok() is False  # Vorgabe 0,5 % aus den Toleranzen


def test_volumen_delta_nur_wo_sich_etwas_geaendert_hat():
    """Ein Punkt in einer Konfiguration: die übrigen bleiben gleich, ihr Delta 0 ist kein Mangel."""
    a = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0)], "Variante B": []}
    [e] = [x for x in bewerte_bereiche(_mit_delta(500), a, {}) if x["id"] == "volumen_delta"]
    assert e["ok"] is True and e["ist"] == {"Standard": 500.0}


def test_volumen_delta_ohne_jede_abweichung_ist_mangel():
    [e] = [x for x in bewerte_bereiche(_mit_delta(500), {"Standard": [], "Variante B": []}, {}) if x["id"] == "volumen_delta"]
    assert e["ok"] is False and e["ist"] == {"Standard": 0.0, "Variante B": 0.0}


def test_volumen_delta_ohne_differenz_nicht_nachgewiesen():
    a = {"Standard": "Fehler", "Variante B": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
    [e] = [x for x in bewerte_bereiche(_mit_delta(500), a, {}) if x["id"] == "volumen_delta"]
    assert e["ok"] is None


# ------------------------------------------------------------------------------------------------- Körper-Attrappen

CUT = 15902


def zellen(x0, y0, z0, x1, y1, z1) -> frozenset:
    return frozenset((x, y, z) for x in range(x0, x1) for y in range(y0, y1) for z in range(z0, z1))


class Koerper:
    """Volumen in Würfeln von 1 mm. Wie IBody2: Ergebnis von `Operations2` ist `(Ergebnis, Code)`, beide Körper sind danach
    verbraucht."""

    fehlercode = 0

    def __init__(self, inhalt, original=True):
        self.inhalt, self.original, self.verbraucht = inhalt, original, False

    def Copy2(self, ids):
        assert ids is True and not self.verbraucht  # S18d: gemessen mit True
        return Koerper(self.inhalt, original=False)

    def Operations2(self, art, werkzeug, code):
        assert art == CUT and code == 0
        assert not (self.original or werkzeug.original), "nur an Kopien (S18d)"
        assert not (self.verbraucht or werkzeug.verbraucht)
        self.verbraucht = werkzeug.verbraucht = True
        if Koerper.fehlercode:
            return None, Koerper.fehlercode
        rest = self.inhalt - werkzeug.inhalt
        return ((Koerper(rest, original=False),) if rest else None), 0

    def GetMassProperties(self, dichte):
        n = len(self.inhalt) * 1e-9
        return [0.0, 0.0, 0.0, n, 6 * n * 1e3, n * dichte]

    def GetBodyBox(self):
        xs = [[z[i] for z in self.inhalt] for i in range(3)]
        return [min(a) / 1000 for a in xs] + [(max(a) + 1) / 1000 for a in xs]


class Modell:
    def __init__(self, je_konfiguration: dict, flaechen=(), aktiv="Standard", feature_flaechen=None):
        self.bodies, self.flaechen, self.feature_flaechen = je_konfiguration, flaechen, feature_flaechen or {}
        self.aktiv, self.schalter, self.neuaufbau = aktiv, [], 0
        self.ConfigurationManager = SimpleNamespace(ActiveConfiguration=None)
        self._setze()

    def _setze(self):
        self.ConfigurationManager.ActiveConfiguration = SimpleNamespace(Name=self.aktiv)

    def ShowConfiguration2(self, k):
        self.aktiv = k
        self.schalter.append(k)
        self._setze()
        return True

    @property
    def EditRebuild3(self):
        self.neuaufbau += 1
        return True

    def GetBodies2(self, typ, sichtbar):
        assert sichtbar is False
        return tuple(self.bodies[self.aktiv]) if typ == 0 else tuple(self.flaechen)

    def FeatureByName(self, name):
        faces = self.feature_flaechen.get(self.aktiv, {}).get(name)
        return None if faces is None else SimpleNamespace(GetFaces=tuple(SimpleNamespace(GetBox=b) for b in faces))


@pytest.fixture(autouse=True)
def kein_fehlercode():
    Koerper.fehlercode = 0
    yield
    Koerper.fehlercode = 0


def _modelle(vorher, nachher, **mehr):
    return (Modell({"Standard": [Koerper(z) for z in vorher], "Variante B": [Koerper(z) for z in vorher]}, **mehr),
            Modell({"Standard": [Koerper(z) for z in nachher], "Variante B": [Koerper(z) for z in nachher]}, **mehr))


PLATTE = zellen(0, 0, 0, 10, 10, 4)
LOCH = zellen(2, 2, 2, 4, 4, 4)


def test_gleiche_koerper_sind_leer():
    a, b = _modelle([PLATTE], [PLATTE])
    assert koerper_differenz(None, a, b, "Standard") == []


def test_beide_richtungen_mit_mm():
    a, b = _modelle([PLATTE], [(PLATTE - LOCH) | zellen(0, 0, 4, 1, 1, 5)])
    [e, h] = koerper_differenz(None, a, b, "Standard")
    assert (e.art, e.box, e.volumen) == ("entfernt", [2.0, 2.0, 2.0, 4.0, 4.0, 4.0], 8.0)
    assert (h.art, h.box, h.volumen) == ("hinzu", [0.0, 0.0, 4.0, 1.0, 1.0, 5.0], 1.0)
    assert e.flaeche == pytest.approx(48.0)


def test_nur_auf_einer_seite_ist_der_ganze_koerper():
    """Sonde Task 8: getrennte Körper liefern das Ziel unverändert, auch wenn sich die Hüllquader überlappen."""
    zweiter = zellen(20, 0, 0, 22, 2, 2)
    a, b = _modelle([PLATTE], [PLATTE, zweiter])
    [h] = koerper_differenz(None, a, b, "Standard")
    assert (h.art, h.volumen) == ("hinzu", 8.0)
    [e] = koerper_differenz(None, b, a, "Standard")
    assert (e.art, e.volumen) == ("entfernt", 8.0)


def test_koerper_zerfaellt_ohne_paarung():
    """Ein Schnitt trennt den Körper: Vorher einer, nachher zwei, entfernt ist nur der Schnitt."""
    links, rechts = zellen(0, 0, 0, 4, 10, 4), zellen(5, 0, 0, 10, 10, 4)
    a, b = _modelle([links | rechts | zellen(4, 0, 0, 5, 10, 4)], [links, rechts])
    [e] = koerper_differenz(None, a, b, "Standard")
    assert (e.art, e.volumen) == ("entfernt", 40.0)


def test_originale_bleiben_unberuehrt():
    a, b = _modelle([PLATTE], [PLATTE - LOCH])
    koerper_differenz(None, a, b, "Standard")
    assert not any(k.verbraucht for m in (a, b) for k in m.bodies["Standard"])


def test_schaltet_beide_und_stellt_die_aktive_wieder_her():
    a, b = _modelle([PLATTE], [PLATTE - LOCH])
    koerper_differenz(None, a, b, "Variante B")
    assert a.schalter == b.schalter == ["Variante B", "Standard"]
    assert a.aktiv == b.aktiv == "Standard" and a.neuaufbau and b.neuaufbau


def test_fehlercode_wirft_und_stellt_die_aktive_wieder_her():
    a, b = _modelle([PLATTE], [PLATTE - LOCH])
    Koerper.fehlercode = 3
    with pytest.raises(DifferenzFehler, match="3"):
        koerper_differenz(None, a, b, "Variante B")
    assert a.aktiv == b.aktiv == "Standard"


def test_flaechenkoerper_sind_nicht_vergleichbar():
    """Ein reines Flächenmodell hätte keine Volumenkörper, die Differenz wäre leer und falsch."""
    a, b = _modelle([PLATTE], [PLATTE], flaechen=[object()])
    with pytest.raises(DifferenzFehler, match="Flächenkörper"):
        koerper_differenz(None, a, b, "Standard")


def test_bilanz_faengt_stilles_leeres_ergebnis():
    """Rückgaben nicht glauben (S18c): Liefert `Operations2` nichts, obwohl das Volumen sich geändert hat, ist nichts bewiesen."""

    class Leer(Koerper):
        def Copy2(self, ids):
            return Leer(self.inhalt, original=False)

        def Operations2(self, art, werkzeug, code):
            return None, 0

    a = Modell({"Standard": [Leer(PLATTE)]})
    b = Modell({"Standard": [Leer(PLATTE - LOCH)]})
    with pytest.raises(DifferenzFehler, match="Volumen"):
        koerper_differenz(None, a, b, "Standard")


def test_feature_boxen_vereinen_vorher_nachher_und_konfigurationen():
    a = Modell({"Standard": [], "Variante B": []}, feature_flaechen={"Standard": {"Fase1": [(0.0, 0.0, 0.018, 0.01, 0.01, 0.02)]}})
    b = Modell({"Standard": [], "Variante B": []}, feature_flaechen={
        "Variante B": {"Fase1": [(0.0, 0.0, 0.0, 0.001, 0.001, 0.001)], "Neu": [(0.04, 0.0, 0.0, 0.05, 0.001, 0.001)]},
        "Standard": {"Leer": []}})
    boxen = alle_feature_boxen([a, b], ["Standard", "Variante B"], {"Fase1", "Neu", "Leer", "Fehlt"})
    assert boxen == {"Fase1": pytest.approx([0.0, 0.0, 0.0, 10.0, 10.0, 20.0]), "Neu": pytest.approx([40.0, 0.0, 0.0, 50.0, 1.0, 1.0])}
    assert a.aktiv == b.aktiv == "Standard"


def test_feature_boxen_ohne_namen_schalten_nicht():
    a = Modell({"Standard": []})
    assert alle_feature_boxen([a], ["Standard", "Variante B"], set()) == {} and a.schalter == []
