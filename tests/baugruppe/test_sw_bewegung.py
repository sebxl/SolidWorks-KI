"""Stufe 4a: SolidWorks-Schicht mit Attrappen – Grenzverknüpfung an AddMate5, Gleichung der Grenze, treibende
Verknüpfung, Stellen, Unterdrücken, Hüllquader, Grundstellung beim Bau."""

import math
from types import SimpleNamespace

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung, verknuepfungen
from swki.baugruppe.bewegung import Bewegung
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.sw_bewegung import SwMechanik
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import schreibe


class _Mass:
    def __init__(self):
        self.gesetzt = []

    def SetSystemValue3(self, wert, konfiguration, namen):  # noqa: N802 (SolidWorks-Name)
        self.gesetzt.append((wert, konfiguration, namen))


class _Mate:
    def __init__(self, name="Mate1"):
        self.Name = name
        self.GetSpecificFeature2 = SimpleNamespace(Alignment=0)
        self.masse: dict[str, _Mass] = {}
        self.unterdrueckt: list[tuple] = []
        self.suppression_ok = True

    def Parameter(self, name):  # noqa: N802 (SolidWorks-Name)
        return self.masse.setdefault(name, _Mass())

    def SetSuppression2(self, zustand, konfiguration, namen):  # noqa: N802 (SolidWorks-Name)
        self.unterdrueckt.append((zustand, konfiguration, namen))
        return self.suppression_ok


class _Asm:
    def __init__(self):
        self.mates: list[_Mate] = []
        self.aufrufe: list[tuple] = []
        self.gleichungen: list[str] = []
        self.GetEquationMgr = SimpleNamespace(Add2=lambda index, text, loesen: self.gleichungen.append(text) or 0)

    def AddMate5(self, *args):  # noqa: N802 (SolidWorks-Name)
        self.aufrufe.append(args[:-1])
        args[-1].value = 1  # ErrorStatus
        mate = _Mate()
        self.mates.append(mate)
        return mate


@pytest.fixture
def asm(monkeypatch):
    a = _Asm()
    monkeypatch.setattr(sw_baugruppe, "verknuepfungen", lambda _asm: list(a.mates))
    monkeypatch.setattr(sw_baugruppe, "waehle", lambda *args: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 0)
    monkeypatch.setattr(sw_baugruppe.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    return a


def _grenze(vid="g1", typ="grenze_abstand", oben="=HUB"):
    return Verknuepfung(vid, vid, typ, {}, {}, "gleich", None, False, 0, oben)


def _bindung(vid, parameter):
    name = sw_baugruppe.GRENZ_MASSE.get("max")
    return [f'"{name}@{vid}" = "{parameter}"'] if name else []


def test_grenze_abstand_an_addmate5(asm):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _grenze(), None, None, {"HUB": 100}, gesetzt)
    assert asm.aufrufe == [(5, 0, False, 0.0, pytest.approx(0.1), 0.0, 1, 1, 0.0, 0.0, 0.0, False, False, 0)]
    assert asm.gleichungen == _bindung("g1", "HUB") and gesetzt == {"g1": 0}


def test_grenze_winkel_an_addmate5(asm):
    sw_baugruppe.verknuepfe(asm, _grenze("g2", "grenze_winkel", "=SCHWENK"), None, None, {"SCHWENK": 90}, {})
    assert asm.aufrufe == [(6, 0, False, 0.0, 0.0, 0.0, 1, 1, 0.0, pytest.approx(math.pi / 2), 0.0, False, False, 0)]
    assert asm.gleichungen == _bindung("g2", "SCHWENK")


def test_treibe_legt_eine_abstandsverknuepfung_an(asm):
    feature = sw_baugruppe.treibe(asm, _grenze(), None, None, 25.0)
    assert feature.Name == "g1.antrieb" and asm.gleichungen == []
    assert asm.aufrufe == [(5, 0, False, pytest.approx(0.025), pytest.approx(0.025), pytest.approx(0.025), 1, 1, 0.0,
                            0.0, 0.0, False, False, 0)]


def test_stelle(asm, monkeypatch):
    feature = sw_baugruppe.treibe(asm, _grenze("g2", "grenze_winkel", "=SCHWENK"), None, None, 0.0)
    assert sw_baugruppe.stelle(asm, feature, "winkel", 45.0) is None
    assert feature.masse["D1"].gesetzt == [(pytest.approx(math.pi / 4), 1, None)]

    def kaputt(model):
        raise BauFehler("REBUILD_FEHLER", "g2: Code 5", schritt="rebuild")

    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", kaputt)
    assert "g2: Code 5" in sw_baugruppe.stelle(asm, feature, "winkel", 100.0)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda f: 7 if f is feature else 0)
    assert sw_baugruppe.stelle(asm, feature, "winkel", 100.0) == "Verknüpfungsfehler: g2.antrieb"


def test_loesche_prueft_das_verschwinden(asm, monkeypatch):
    feature = sw_baugruppe.treibe(asm, _grenze(), None, None, 25.0)
    monkeypatch.setattr(sw_baugruppe, "_loesche", lambda a, f: None)  # Select2/EditDelete ins Leere
    with pytest.raises(BauFehler, match="Verknüpfung g1.antrieb nicht gelöscht"):
        sw_baugruppe.loesche(asm, feature)
    monkeypatch.setattr(sw_baugruppe, "_loesche", lambda a, f: a.mates.remove(f))
    sw_baugruppe.loesche(asm, feature)
    assert asm.mates == []


def test_kiste_aus_teilebox_und_lage():
    # Drehung 90° um +z (x → y, y → −x), Verschiebung (100, 0, 0) mm = 0,1 m; Teilebox 10 × 20 × 30 mm
    t = [0.0, 1.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.1, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    assert sw_baugruppe.kiste(t, [0, 0, 0, 10, 20, 30]) == pytest.approx([80, 0, 0, 100, 10, 30])


def test_unterdruecke_grenze(asm, monkeypatch):
    aufbauten = []
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: aufbauten.append(model))
    feature = _Mate()
    sw_baugruppe.unterdruecke(asm, feature, True)
    sw_baugruppe.unterdruecke(asm, feature, False)
    assert feature.unterdrueckt == [(0, 1, None), (1, 1, None)] and aufbauten == [asm, asm]

    feature.suppression_ok = False
    with pytest.raises(BauFehler, match="Grenze Mate1 nicht unterdrückt"):
        sw_baugruppe.unterdruecke(asm, feature, True)

    # SwMechanik findet die Grenze über den Verknüpfungsnamen, ohne auf die Schreibung zu achten
    grenze = _Mate("G1")
    asm.mates.append(grenze)
    mech = SwMechanik(None, asm, {}, None, {})
    mech.unterdruecke(Bewegung("Hub", "g1", "abstand", "schieber", 0.0, 100.0, 8), True)
    assert grenze.unterdrueckt == [(0, 1, None)]


class _Mech:
    """Attrappe von SwMechanik für bau._grundstellung; fehler_name: dort scheitert halte()."""
    letzte = None
    fehler_name: str | None = None

    def __init__(self, *args):
        self.args = args
        self.aufrufe: list[tuple] = []
        _Mech.letzte = self

    def halte(self, b, wert):
        self.aufrufe.append(("halte", b.name, wert))
        if b.name == _Mech.fehler_name:
            raise StellungFehler(b.name, wert, "Verknüpfungsfehler: g2.antrieb")

    def loese(self, b):
        self.aufrufe.append(("loese", b.name))


def _baulauf(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    b = bau.Baulauf(None, bg, "A", tmp_path, lade_standard(), Protokoll("A", "bewegungsprobe.yaml", 1, 2025),
                    asm=object())
    return b, verknuepfungen(bg.spec, bg.quellen)


def test_grundstellung_haelt_alle_und_loest_rueckwaerts(tmp_path, monkeypatch):
    _Mech.fehler_name = None
    monkeypatch.setattr(bau, "SwMechanik", _Mech)
    b, alle = _baulauf(tmp_path)
    assert bau._grundstellung(b, alle) is None
    assert _Mech.letzte.aufrufe == [("halte", "Hub", 0.0), ("halte", "Schwenk", 0.0), ("loese", "Schwenk"),
                                    ("loese", "Hub")]
    assert set(_Mech.letzte.args[2]) == {"g1", "g2"}
    assert [(k.id, k.typ, k.status) for k in b.protokoll.knoten] == [
        ("grundstellung:Hub", "grundstellung", "ok"), ("grundstellung:Schwenk", "grundstellung", "ok")]


def test_grundstellung_fehler(tmp_path, monkeypatch):
    _Mech.fehler_name = "Schwenk"
    monkeypatch.setattr(bau, "SwMechanik", _Mech)
    b, alle = _baulauf(tmp_path)
    fehler = bau._grundstellung(b, alle)
    assert fehler.code == "GRUNDSTELLUNG_FEHLER" and "Grundstellung Schwenk" in str(fehler)
    assert _Mech.letzte.aufrufe[-2:] == [("loese", "Schwenk"), ("loese", "Hub")]
    assert [k.status for k in b.protokoll.knoten] == ["ok", "fehler"]
