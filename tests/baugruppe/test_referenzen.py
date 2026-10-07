from pathlib import Path

import pytest

from swki.baugruppe import referenzen, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.referenzen import flaeche_der_instanz, loese_im_teil
from swki.compiler.anker import AnkerFehler, Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext


class _Feature:
    def __init__(self, name):
        self.Name = name


def _ctx(ergebnisse=None) -> Kontext:
    return Kontext(None, None, {"parameter": {}}, Path("teil.yaml"), 0.1, ergebnisse=ergebnisse or {})


def _ebene(y, normale=(0.0, 1.0, 0.0), abstand=None):
    return Flaeche("ebene", (0.0, y, 0.0), normale=normale, abstand=abstand, objekt=f"ebene{y}")


def test_flaeche_der_instanz_naechste():
    kandidaten = [_ebene(26.4, abstand=3.0), _ebene(26.4, abstand=60.1), _ebene(0, (0.0, -1.0, 0.0), abstand=26.0)]
    assert flaeche_der_instanz(kandidaten, "+y").objekt == "ebene26.4"


def test_flaeche_der_instanz_mehrdeutig_und_fehlend():
    with pytest.raises(AnkerFehler) as e:
        flaeche_der_instanz([_ebene(1, abstand=3.0), _ebene(2, abstand=3.0)], "+y")
    assert e.value.code == "REFERENZ_MEHRDEUTIG"
    with pytest.raises(AnkerFehler) as e:
        flaeche_der_instanz([_ebene(1, abstand=3.0)], "-y")
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


def test_standardebene(monkeypatch):
    ebenen = [_Feature("Ebene vorne"), _Feature("Ebene oben"), _Feature("Ebene rechts")]
    monkeypatch.setattr(referenzen.sw, "standardebenen", lambda model: ebenen)
    ref = loese_im_teil(_ctx(), {"ebene": "oben"})
    assert ref.ist_feature and ref.objekt is ebenen[1]
    assert (ref.geometrie.art, ref.geometrie.punkt, ref.geometrie.richtung) == ("ebene", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def test_referenz_fehlt():
    with pytest.raises(AnkerFehler) as e:
        loese_im_teil(_ctx(), {"referenz": "TRENNEBENE"})
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


def test_bohrungsachse_der_instanz(monkeypatch):
    zylinder = [Flaeche("zylinder", (-30.0, 0.0, 0.0), achse=(0.0, -1.0, 0.0), radius=3.4, objekt="z1"),
                Flaeche("zylinder", (30.0, 0.0, 0.0), achse=(0.0, -1.0, 0.0), radius=3.4, objekt="z2")]
    monkeypatch.setattr(referenzen, "flaechen", lambda feature: zylinder)
    ctx = _ctx({"f2": FeatureErgebnis([_Feature("f2")], punkte=[(-30.0, 20.0, 0.0), (30.0, 20.0, 0.0)])})
    ref = loese_im_teil(ctx, {"feature": "f2", "instanz": 2, "achse": True})
    assert not ref.ist_feature and ref.objekt == "z2"
    assert ref.geometrie.art == "achse" and ref.geometrie.richtung == (0.0, -1.0, 0.0)


def test_instanz_zu_gross():
    ctx = _ctx({"f2": FeatureErgebnis([_Feature("f2")], punkte=[(0.0, 20.0, 0.0)])})
    with pytest.raises(AnkerFehler) as e:
        loese_im_teil(ctx, {"feature": "f2", "instanz": 2, "achse": True})
    assert "nur 1 Instanzen" in str(e.value)


@pytest.mark.parametrize(("typ", "ausrichtung", "erwartet"), [
    ("deckungsgleich", "gleich", [0]), ("parallel", "entgegengesetzt", [1]), ("konzentrisch", None, [2])])
def test_ausrichtungen(typ, ausrichtung, erwartet):
    v = Verknuepfung("v1", "v1", typ, {}, {}, ausrichtung, None, False)
    assert sw_baugruppe.ausrichtungen(v) == erwartet


def test_umgekehrte():
    gesetzt = {"v1": 0, "v2": 1, "v3": 0}
    assert sw_baugruppe.umgekehrte(gesetzt, {"v1": 1, "v2": 1, "v3": 1}) == ["v1", "v3"]  # Reihenfolge von gesetzt
    assert sw_baugruppe.umgekehrte(gesetzt, {"v1": 0, "v2": 1, "v3": 0}) == []
    assert sw_baugruppe.umgekehrte(gesetzt, {"v1": 0, "v3": 0}) == []  # fehlender Name zählt nicht
    assert sw_baugruppe.umgekehrte({}, {"v1": 1}) == []


# --- verknuepfe mit Attrappen (kein SolidWorks) ---------------------------------------------------------------------

class _Spezifisch:
    def __init__(self, ausrichtung):
        self.Alignment = ausrichtung


class _MateFeature:
    def __init__(self, ausrichtung=0):
        self.Name = "Mate1"
        self.GetSpecificFeature2 = _Spezifisch(ausrichtung)


class _Asm:
    def __init__(self):
        self.mates: list[_MateFeature] = []
        self.codes: list[int] = []
        self.geloescht: list[str] = []
        self.neu_ausrichtung = 0

    def AddMate5(self, typ, code, *rest):  # noqa: N802 (SolidWorks-Name)
        self.codes.append(code)
        rest[-1].value = 1  # ErrorStatus
        mate = _MateFeature(code if code != sw_baugruppe.NAECHSTE else self.neu_ausrichtung)
        self.mates.append(mate)
        return mate


@pytest.fixture
def asm(monkeypatch):
    a = _Asm()
    monkeypatch.setattr(sw_baugruppe, "verknuepfungen", lambda _asm: list(a.mates))
    monkeypatch.setattr(sw_baugruppe, "waehle", lambda *args: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 0)
    monkeypatch.setattr(sw_baugruppe, "_loesche", lambda _asm, feature: (a.mates.remove(feature), a.geloescht.append(feature.Name)))
    monkeypatch.setattr(sw_baugruppe.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    return a


def _v(vid, typ, ausrichtung):
    return Verknuepfung(vid, vid, typ, {}, {}, ausrichtung, None, False)


def test_verknuepfe_traegt_ausdrueckliche_ausrichtung_ein(asm):
    gesetzt: dict[str, int] = {}
    feature = sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "entgegengesetzt"), None, None, {}, gesetzt)
    assert feature.Name == "v1" and asm.codes == [1] and gesetzt == {"v1": 1}


def test_verknuepfe_ohne_angabe_ein_versuch_und_nicht_in_gesetzt(asm):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v2", "konzentrisch", None), None, None, {}, gesetzt)
    assert asm.codes == [sw_baugruppe.NAECHSTE] and gesetzt == {}


def test_verknuepfe_erkennt_umgekehrte_ausrichtung(asm):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    asm.mates[0].GetSpecificFeature2.Alignment = 1  # SolidWorks kehrt v1 beim Anlegen von v2 still um
    with pytest.raises(BauFehler) as e:
        sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    assert e.value.code == "VERKNUEPFUNG_FEHLER" and str(e.value) == "v2 kehrt die Ausrichtung von v1 um"
    assert asm.geloescht == ["v2"] and len(asm.mates) == 1 and gesetzt == {"v1": 0}


def test_verknuepfe_ohne_gesetzt_prueft_nicht(asm):
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {})
    asm.mates[0].GetSpecificFeature2.Alignment = 1
    sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {})
    assert asm.geloescht == []


def test_verknuepfe_fehlerstatus_wird_geloescht_und_gemeldet(asm, monkeypatch):
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 7)
    with pytest.raises(BauFehler) as e:
        sw_baugruppe.verknuepfe(asm, _v("v1", "parallel", "gleich"), None, None, {}, {})
    assert e.value.code == "VERKNUEPFUNG_FEHLER" and str(e.value) == "v1 (parallel): Fehlercode 7"
    assert asm.geloescht == ["v1"] and asm.mates == []


def test_verknuepfe_fremde_ausnahme_loescht_die_neue_verknuepfung(asm, monkeypatch):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)

    def kaputt(feature):
        raise RuntimeError("Alignment nicht lesbar")

    monkeypatch.setattr(sw_baugruppe, "ausrichtung_von", kaputt)
    with pytest.raises(BauFehler) as e:
        sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    assert e.value.code == "VERKNUEPFUNG_FEHLER"
    assert str(e.value) == "v2 (deckungsgleich): RuntimeError: Alignment nicht lesbar"
    assert asm.geloescht == ["v2"] and [m.Name for m in asm.mates] == ["v1"] and gesetzt == {"v1": 0}


def _loesche_wirft(asm_, feature):
    raise OSError("Löschen kaputt")


def test_verknuepfe_loeschfehler_verdeckt_fremde_ursache_nicht(asm, monkeypatch):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)

    def kaputt(feature):
        raise RuntimeError("Alignment nicht lesbar")

    monkeypatch.setattr(sw_baugruppe, "ausrichtung_von", kaputt)
    monkeypatch.setattr(sw_baugruppe, "_loesche", _loesche_wirft)
    with pytest.raises(BauFehler) as e:
        sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    assert e.value.code == "VERKNUEPFUNG_FEHLER"
    assert str(e.value) == "v2 (deckungsgleich): RuntimeError: Alignment nicht lesbar"


def test_verknuepfe_loeschfehler_verdeckt_die_umkehr_nicht(asm, monkeypatch):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    asm.mates[0].GetSpecificFeature2.Alignment = 1  # v1 wird beim Anlegen von v2 still umgekehrt
    monkeypatch.setattr(sw_baugruppe, "_loesche", _loesche_wirft)
    with pytest.raises(BauFehler, match="v2 kehrt die Ausrichtung von v1 um") as e:
        sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    assert e.value.code == "VERKNUEPFUNG_FEHLER"


def test_verknuepfe_prueft_die_ausrichtung_vor_der_gleichung(asm):
    from types import SimpleNamespace

    gleichungen: list[str] = []
    asm.GetEquationMgr = SimpleNamespace(Add2=lambda index, text, loesen: gleichungen.append(text) or 0)
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    asm.mates[0].GetSpecificFeature2.Alignment = 1  # v1 wird beim Anlegen von v2 still umgekehrt
    v2 = Verknuepfung("v2", "v2", "abstand", {}, {}, "gleich", "=S", False)
    with pytest.raises(BauFehler, match="v2 kehrt die Ausrichtung von v1 um"):
        sw_baugruppe.verknuepfe(asm, v2, None, None, {"S": 5}, gesetzt)
    assert gleichungen == [] and asm.geloescht == ["v2"]  # keine verwaiste Gleichung "D1@v2"


def _gewinde_ctx(monkeypatch):
    """Attrappen-Kontext eines Kaufteils: Gewindegruppe `flansch` (M5, Normale −y) mit zwei Positionen; je Position ein
    Kernloch (Ø 4,134) und, bei Position 1, eine größere koaxiale Fläche (Ø 5,0, z. B. Senkung); dazu eine fremde Fläche
    ohne Achse durch die Positionen. Die Körper zählen die Flächenabfragen."""
    pos1, pos2 = (21.2, 0.0, 21.2), (-21.2, 0.0, 21.2)
    y = (0.0, -1.0, 0.0)
    flaechen = [Flaeche("zylinder", pos1, achse=y, radius=2.067, objekt="kern1"),
                Flaeche("zylinder", pos1, achse=y, radius=2.5, objekt="weit1"),
                Flaeche("zylinder", pos2, achse=y, radius=2.067, objekt="kern2"),
                Flaeche("zylinder", (0.0, 0.0, 0.0), achse=y, radius=1.0, objekt="fremd"),
                Flaeche("ebene", (0.0, 0.0, 0.0), normale=y, objekt="plan")]
    abfragen = []

    class _Koerper:
        def GetFaces(self):
            abfragen.append(1)
            return [f.objekt for f in flaechen]

    monkeypatch.setattr(referenzen, "koerper", lambda model: [_Koerper()])
    monkeypatch.setattr(referenzen, "flaeche_aus", lambda face: next(f for f in flaechen if f.objekt == face))
    gruppe = {"groesse": "M5", "gewindetiefe": 8, "tiefe": 10, "normale": [0, -1, 0],
              "positionen": [list(pos1), list(pos2)]}
    ctx = Kontext(None, object(), {"parameter": {}, "gewinde": {"flansch": gruppe}}, Path("kaufteil.sldprt"), 0.1)
    return ctx, abfragen


def test_gewinde_referenz_waehlt_instanz_und_kleinsten_radius(monkeypatch):
    ctx, _ = _gewinde_ctx(monkeypatch)
    r1 = loese_im_teil(ctx, {"gewinde": "flansch", "instanz": 1})
    r2 = loese_im_teil(ctx, {"gewinde": "flansch", "instanz": 2})
    assert (r1.objekt, r2.objekt) == ("kern1", "kern2")  # kleinster Radius gewinnt (nicht die Senkung weit1)
    assert not r1.ist_feature
    assert r1.geometrie.art == "achse" and r1.geometrie.richtung == (0.0, -1.0, 0.0)
    assert r2.geometrie.punkt == (-21.2, 0.0, 21.2)


def test_gewinde_referenz_sammelt_flaechen_je_kontext_einmal(monkeypatch):
    ctx, abfragen = _gewinde_ctx(monkeypatch)
    for i in (1, 2, 1):
        loese_im_teil(ctx, {"gewinde": "flansch", "instanz": i})
    assert len(abfragen) == 1


def test_gewinde_referenz_ohne_passende_flaeche(monkeypatch):
    ctx, _ = _gewinde_ctx(monkeypatch)
    ctx.spec["gewinde"]["flansch"]["positionen"][1] = [50.0, 0.0, 50.0]
    with pytest.raises(AnkerFehler) as e:
        loese_im_teil(ctx, {"gewinde": "flansch", "instanz": 2})
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"
