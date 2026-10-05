"""Stufe 4b: SolidWorks-Schicht der Kopplungen mit Attrappen – CreateMate, Rücklesen, Unterdrückung, Zahnphase und
Kopplung beim Bau (Spec 4b §5.4)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung, verknuepfungen
from swki.baugruppe.fehler import ZAHNPHASE_FEHLER
from swki.baugruppe.kopplung import in_baugruppe, phasenfehler, verzahnung_der_seite
from swki.baugruppe.modell import Baugruppe
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from tests.baugruppe.beispiel_kopplung import TEILE, quellen, spec


class _Mate:
    def __init__(self, typ: int):
        self.Name = "Mate1"
        self.GetSpecificFeature2 = SimpleNamespace(Type=typ)


class _Asm:
    def __init__(self):
        self.mates: list[_Mate] = []
        self.daten: list[SimpleNamespace] = []
        self.anlegen = True

    def CreateMateData(self, typ):  # noqa: N802 (SolidWorks-Name)
        self.daten.append(SimpleNamespace(typ=typ))
        return self.daten[-1]

    def CreateMate(self, daten):  # noqa: N802 (SolidWorks-Name)
        if not self.anlegen:
            return None
        self.mates.append(_Mate(daten.typ))
        return self.mates[-1]


@pytest.fixture
def asm(monkeypatch):
    a = _Asm()
    a.auswahl = []
    monkeypatch.setattr(sw_baugruppe, "verknuepfungen", lambda _asm: list(a.mates))
    monkeypatch.setattr(sw_baugruppe, "waehle", lambda asm_, ent, anhaengen, marke=1: a.auswahl.append((ent, marke)))
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 0)
    monkeypatch.setattr(sw_baugruppe, "dispatch_array", list)
    monkeypatch.setattr(sw_baugruppe.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    return a


def _v(vid: str, typ: str) -> Verknuepfung:
    return Verknuepfung(vid, vid, typ, {}, {}, None, None, False)


def test_kopple_zahnrad(asm):
    feature = sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, True)
    [d] = asm.daten
    assert d.typ == 10 and d.EntitiesToMate == ["A", "B"] and d.Reverse is True
    assert d.GearRatioNumerator == pytest.approx(0.1) and d.GearRatioDenominator == pytest.approx(0.05)
    assert feature.Name == "k2" and asm.auswahl == []


def test_kopple_zahnstange_mit_vorauswahl(asm):
    sw_baugruppe.kopple(asm, _v("k1", "zahnstange"), ("Ritzel", False), ("Stange", False), 40.0, 0.0, False)
    [d] = asm.daten
    assert d.typ == 13 and d.DiameterType == 0 and d.DiameterVal == pytest.approx(0.04) and d.Reverse is False
    assert asm.auswahl == [(("Stange", False), 64), (("Ritzel", False), 128)]


def test_kopple_ohne_verknuepfung(asm):
    asm.anlegen = False
    with pytest.raises(BauFehler, match="k2 \\(zahnrad\\): CreateMate legt keine Verknüpfung an"):
        sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, False)


def test_kopple_mit_fehlercode_loescht_wieder(asm, monkeypatch):
    geloescht = []
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 47)
    monkeypatch.setattr(sw_baugruppe, "_loesche_still", lambda asm_, f: geloescht.append(f.Name))
    with pytest.raises(BauFehler, match="Fehlercode 47"):
        sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, False)
    assert geloescht == ["k2"]


def test_lies_kopplung():
    zahnrad = SimpleNamespace(GetSpecificFeature2=SimpleNamespace(Type=10),
                              GetDefinition=SimpleNamespace(GearRatioNumerator=0.1, GearRatioDenominator=0.05, Reverse=0))
    assert sw_baugruppe.lies_kopplung(zahnrad) == {"zaehler": 100.0, "nenner": 50.0, "umkehren": False}
    stange = SimpleNamespace(GetSpecificFeature2=SimpleNamespace(Type=13),
                             GetDefinition=SimpleNamespace(DiameterVal=0.04, DiameterType=0, Reverse=True))
    assert sw_baugruppe.lies_kopplung(stange) == {"durchmesser": 40.0, "art": 0, "umkehren": True}


def test_ist_unterdrueckt():
    assert sw_baugruppe.ist_unterdrueckt(SimpleNamespace(IsSuppressed=True)) is True


# --- Bau: Zahnphase und Kopplung ---------------------------------------------------------------------------------

EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _lage(x, y, z=0.0) -> list[float]:
    return EINS[:9] + [x / 1000, y / 1000, z / 1000] + EINS[12:]


@pytest.fixture
def baulauf(monkeypatch, tmp_path):
    s = spec()
    bg = Baugruppe(Path(tmp_path / "trieb.yaml"), s, quellen(), {f"{k}.yaml": t for k, t in TEILE.items()})
    lagen = {"zahnstange": _lage(0, 0), "ritzelwelle": _lage(37.3, 20.0), "antriebswelle": _lage(112.3, 20.0)}
    b = bau.Baulauf(object(), bg, "A", tmp_path, {}, Protokoll("A", "trieb.yaml", 1, 2025), asm=object())
    b.komponenten = {k: SimpleNamespace(name=k, Name2=k) for k in lagen}
    monkeypatch.setattr(sw_baugruppe, "transform", lambda komp: list(lagen[komp.name]))
    monkeypatch.setattr(sw_baugruppe, "setze_lage", lambda app, asm, komp, t: lagen.__setitem__(komp.name, t))
    b.lagen = lagen
    return b


def _kopplung(b, vid: str) -> Verknuepfung:
    return next(v for v in verknuepfungen(b.bg.spec, b.bg.quellen) if v.id == vid)


def _fehler(b, v) -> float:
    a, g = (in_baugruppe(verzahnung_der_seite(b.bg.quellen, s), b.lagen[s["komponente"]]) for s in (v.a, v.b))
    return phasenfehler(a, g)


def test_zahnphase_dreht_seite_a_in_die_luecke(baulauf):
    for vid in ("k1", "k2"):
        v = _kopplung(baulauf, vid)
        bau._zahnphase(baulauf, v)
        assert _fehler(baulauf, v) == pytest.approx(0.0, abs=1e-9)
    assert [k.id for k in baulauf.protokoll.knoten] == ["zahnphase:k1", "zahnphase:k2"]
    assert baulauf.lagen["zahnstange"] == _lage(0, 0)  # Seite b bleibt


def test_zahnphase_nicht_erreicht(baulauf, monkeypatch):
    monkeypatch.setattr(sw_baugruppe, "setze_lage", lambda app, asm, komp, t: None)  # SolidWorks dreht nicht
    v = _kopplung(baulauf, "k1")
    assert abs(_fehler(baulauf, v)) > bau.TOL_PHASE  # Vorbedingung: die Ausgangslage ist nicht in Phase
    with pytest.raises(BauFehler) as e:
        bau._zahnphase(baulauf, v)
    assert e.value.code == ZAHNPHASE_FEHLER and "Zahnphase k1" in str(e.value)


def test_kopple_mit_teilkreisen_und_richtung(baulauf, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(bau, "_entitaet_kopplung", lambda b, seite: seite["komponente"])
    monkeypatch.setattr(sw_baugruppe, "kopple", lambda *args: aufrufe.append(args[1:]) or SimpleNamespace(Name="k"))
    bau._kopple(baulauf, _kopplung(baulauf, "k2"))
    bau._kopple(baulauf, _kopplung(baulauf, "k1"))
    assert [a[1:] for a in aufrufe] == [("antriebswelle", "ritzelwelle", 100.0, 50.0, False),
                                       ("ritzelwelle", "zahnstange", 40.0, 0.0, False)]
