"""Zeichnungsableitung Z1.3 Stufe 1: zeichnen.py ohne SolidWorks – Laufwahl und Ansichtserzeugung mit Fake-COM
(Review I1, I5)."""

import math

import pytest

from swki.zeichnung import zeichnen as z
from swki.zeichnung.ansichten import Ansicht
from swki.zeichnung.massplan import Mass


def _lauf(n, bestanden):
    return {"lauf": n, "bestanden": bestanden, "bau": "ok", "code_maengel": 0, "pruefer": "bestanden" if bestanden else None}


def test_letzter_bestandener_lauf(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, True), _lauf(2, False)])
    assert z.waehle_lauf(None, None) == (1, [])


def test_kein_bestandener_lauf_fehler(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, False)])
    with pytest.raises(z.ZeichnungFehler) as e:
        z.waehle_lauf(None, None)
    assert e.value.daten["code"] == "ZEICHNUNG_LAUF_NICHT_BESTANDEN" and "--lauf" in str(e.value)


def test_ausdruecklicher_lauf_mit_meldung(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, False)])
    lauf, meldungen = z.waehle_lauf(None, 1)
    assert lauf == 1 and any("nicht bestanden" in m for m in meldungen)


class _View:
    def __init__(self, name):
        self.GetName2, self.GetOutline, self.Position, self.ScaleDecimal, self.Angle = name, (0.1, 0.1, 0.2, 0.15), (0.15, 0.125), 1.0, 0


class _Drw:
    def __init__(self):
        self.n, self.schnitte = 0, 0
        self.Extension = type("E", (), {"SelectByID2": lambda *a: True})()
        self.SketchManager = type("S", (), {"CreateLine": lambda *a: object()})()

    def _neu(self):
        self.n += 1
        return _View(f"Zeichenansicht{self.n}")

    def CreateDrawViewFromModelView3(self, *a):
        return self._neu()

    def CreateUnfoldedViewAt3(self, *a):
        return self._neu()

    def CreateSectionViewAt5(self, *a):
        self.schnitte += 1
        v = self._neu()
        v.GetName2 = "Schnittansicht A-A"
        return v

    def ActivateView(self, name):
        return True


def test_fraesteil_schnitt_nicht_unterstuetzt_wird_gemeldet():
    drw = _Drw()
    views, schnitt, meldungen = z._erzeuge(drw, None, z.Path("t.sldprt"),
                                           [Ansicht("haupt", "*Oben"), Ansicht("drauf", None, schnitt=True)])
    assert set(views) == {"haupt", "drauf"} and schnitt is None and drw.schnitte == 0
    assert any("SCHNITT_NICHT_UNTERSTUETZT" in m for m in meldungen)


def test_drehteil_laengsschnitt_aus_stirn():
    drw = _Drw()
    views, schnitt, meldungen = z._erzeuge(drw, None, z.Path("t.sldprt"),
                                           [Ansicht("seite", "*Oben"), Ansicht("haupt", None, schnitt=True)])
    assert schnitt == "Schnittansicht A-A" and drw.schnitte == 1 and meldungen == []


def test_zeichnungsname_kurz():
    """Schriftfeld: das ISO-Muster zeigt den Dateinamen groß (Nutzer 17.11.2026: Titel zu groß)."""
    assert z.zeichnungsname({"name": "Buchse"}) == "Buchse"
    assert z.zeichnungsname({"name": "Buchse", "eigenschaften": {"Zeichnungsnummer": "Z-1044-01"}}) == "Z-1044-01"


# --- Stufe 3 Task 4: Angaben und Textzusätze ------------------------------------------------------------------------



class _KantenView:
    """Ansicht ohne sichtbare Kreiskanten; jeder Zugriff auf die Zeichnung wäre ein Fehler."""

    def __init__(self):
        self.ModelToViewTransform, self.ScaleDecimal = object(), 1.0

    def GetVisibleEntities2(self, leer, typ):
        return ()


def _angabe(achse):
    return Mass("g1:angabe", "angabe", "angabe", 0.0, "g1", text="5 × M6 – 10 tief", achse=achse, modus="flach")


def test_angabe_ohne_passende_ansicht_gemeldet():
    """Review Focus 1: keine Ansicht blickt entlang der Achse der Angabe → Meldung, kein Absturz, kein Hinweis."""
    views = {"haupt": _KantenView(), "seite": _KantenView()}
    hinweise = []
    meld = z._angaben_setzen(object(), None, views, [_angabe(2)], {"haupt": 1, "seite": 0}, hinweise=hinweise)
    assert meld == ["ANGABE_OHNE_ANSICHT: g1"] and hinweise == []


def test_angabe_ohne_kreiskante_gemeldet():
    views = {"haupt": _KantenView()}
    meld = z._angaben_setzen(object(), None, views, [_angabe(1)], {"haupt": 1})
    assert meld == ["ANGABE_OHNE_ANSICHT: g1"]


def test_angabe_ohne_achse_gemeldet():
    meld = z._angaben_setzen(object(), None, {"haupt": _KantenView()}, [_angabe(None)], {"haupt": 1})
    assert meld == ["ANGABE_OHNE_ANSICHT: g1"]


class _ZusatzDim:
    def __init__(self, name):
        self.FullName, self.texte = f"{name}@Teil.Part", {}

    def GetDimension2(self, i):
        return self

    def SetText(self, teil, text):
        self.texte[teil] = text
        return True


def test_zusaetze_an_passenden_anzeigemassen():
    teilung, fase, andere = _ZusatzDim("D3@m1"), _ZusatzDim("D1@fa1"), _ZusatzDim("D1@t1_skizze")
    view = type("V", (), {"GetDisplayDimensions": lambda s: (teilung, fase, andere)})()
    plan = [Mass("D3@m1", "modell", "abstand", 30.0, "m1", name="D3@m1", praefix="4 × ", suffix=" (= 120)"),
            Mass("D1@fa1", "modell", "fase", 1.0, "fa1", name="D1@fa1", suffix=" × 45°"),
            Mass("D1@t1_skizze", "modell", "laenge", 20.0, "t1", name="D1@t1_skizze"),
            _angabe(1)]
    z._zusaetze_setzen({"haupt": view}, plan)
    assert teilung.texte == {1: "4 × ", 2: " (= 120)"}
    assert fase.texte == {2: " × 45°"}            # kein leeres Präfix (würde z. B. <MOD-DIAM> löschen)
    assert andere.texte == {}


def test_planzahlen_trennen_masse_und_angaben():
    """Ruling A: `masse.plan` zählt nur Maße (modell/neu), Angaben getrennt."""
    plan = [Mass("a", "modell", "laenge", 1.0, "f1", name="a"), Mass("b", "neu", "durchmesser", 2.0, "f1"),
            _angabe(1)]
    assert z._planzahlen(plan) == (2, 1)


class _Ann:
    def __init__(self, x_mm, y_mm):
        self.GetPosition = (x_mm / 1000, y_mm / 1000, 0.0)


def _hinweis(lage=(150.0, 260.0)):
    h = z._Hinweis("g1", ("5 × M6 – 10 tief", "Senkung Ø6 × 90°"), _Ann(168.0, 255.2), "haupt",
                   [(None, ((146.0, 240.0), 1.5))], 0,
                   (111.0, 190.0, 211.0, 250.0), (40.0, 11.0), (20.0, -4.1), lage=lage)
    h.verworfen.append((1.0, 2.0))
    return h


def test_hinweis_am_pdf_vermessen():
    """Live 19.11.: INote.GetExtent taugte nicht – Größe und Versatz aus den Zeilen im PDF."""
    h = _hinweis()
    pdf = [("5 × M6 – 10 tief", (168.0, 250.2, 201.3, 256.6)), ("Senkung Ø6 × 90°", (168.0, 245.7, 207.8, 252.1)),
           ("5 × M6 – 10 tief", (20.0, 20.0, 50.0, 25.0))]
    assert z._hinweise_vermessen([h], pdf) == [h]
    assert h.groesse == pytest.approx((39.8, 10.9)) and h.versatz == pytest.approx((19.9, -4.05))
    assert h.vermessen and h.verworfen == []
    assert z._hinweise_vermessen([h], pdf) == []  # nur einmal


def test_hinweis_ohne_zeile_im_pdf_behaelt_schaetzung():
    h = _hinweis()
    assert z._hinweise_vermessen([h], [("5 × M6 – 10 tief", (168.0, 250.2, 201.3, 256.6))]) == []
    assert h.groesse == (40.0, 11.0) and h.vermessen


def test_befund_gehoert_zum_hinweis():
    h = _hinweis()
    assert z._hinweis_zu(z.Befund("linie_durch_text", "Senkung Ø6 × 90°", (168, 246, 208, 252)), [h]) is h
    assert z._hinweis_zu(z.Befund("text_ueber_text", "30,00", (160, 250, 170, 255), "5 × M6 – 10 tief"), [h]) is h
    assert z._hinweis_zu(z.Befund("linie_durch_text", "30,00", (160, 250, 170, 255)), [h]) is None
    assert z._hinweis_zu(z.Befund("text_ueber_text", "5 × M6 – 10 tief", (168, 250, 201, 256), "Senkung Ø6 × 90°"),
                         [h]) is None  # zwei Zeilen desselben Hinweises


class _NotizAnn:
    def __init__(self, drw):
        self.drw, self.lage = drw, None

    def SetPosition2(self, x, y, z):
        self.lage = (x * 1000, y * 1000)
        return True

    def Select2(self, append, mark):
        self.drw.gewaehlt = self
        return True


class _NotizDrw:
    """Zeichnung mit Kreispunkt-Wahl (SelectByID2 → Ansicht und Kreiskante), InsertNote und Löschen."""

    def __init__(self):
        self.notizen, self.gewaehlt, self.punkte = [], None, []
        drw = self
        kreis = type("K", (), {"IsCircle": True})()
        kante = type("Ka", (), {"GetCurve": kreis})()
        self.SelectionManager = type("SM", (), {"GetSelectedObjectCount2": lambda s, m: 2,
                                                "GetSelectedObjectType3": lambda s, i, m: (12, 1)[i - 1],
                                                "GetSelectedObject6": lambda s, i, m: kante})()
        self.Extension = type("E", (), {
            "SelectByID2": lambda s, n, typ, x, y, *a: drw.punkte.append((x * 1000, y * 1000)) or True,
            "DeleteSelection2": lambda s, o: drw.notizen.remove(drw.gewaehlt) or True})()

    def ActivateView(self, name):
        return True

    def ClearSelection2(self, alle):
        self.gewaehlt = None

    def InsertNote(self, text):
        ann = _NotizAnn(self)
        self.notizen.append(ann)
        return type("N", (), {"GetAnnotation": ann})()


def test_hinweis_wechselt_auf_freie_bohrung_und_setzt_am_kreis_zum_text_an():
    """Live 19.11. (Spannplatte): an der zuerst gewählten Bohrung keine freie Lage, an einer anderen der Reihe schon;
    Hinweislinie setzt am Kreis zum Text hin an (nicht quer durch die Bohrung)."""
    drw = _NotizDrw()
    alt = _NotizAnn(drw)
    drw.notizen.append(alt)
    view = type("V", (), {"GetName2": "Zeichenansicht1"})()
    kreise = [("k0", ((146.0, 240.0), 1.5)), ("k1", ((191.0, 240.0), 1.5))]
    h = z._Hinweis("g1", ("5 × M6 – 10 tief", "Senkung Ø6 × 90°"), alt, "haupt", kreise, 0,
                   (111.0, 190.0, 211.0, 250.0), (40.0, 11.0), (20.0, -4.1), text="5 × M6 – 10 tief\nSenkung Ø6 × 90°",
                   view=view, winkel=225.0)
    sperre = z._rechteck_strecken((100.0, 180.0, 175.0, 300.0))  # alles um die erste Bohrung belegt
    gelegt = z._hinweise_legen(drw, [h], {}, sperre)
    assert h.instanz == 1 and drw.notizen == [h.ann] and h.ann is not alt
    assert h.lage[0] > 191 and h.lage[1] > 240 and gelegt
    (px, py), = drw.punkte
    assert math.dist((px, py), (191.0, 240.0)) == pytest.approx(1.5) and px > 191 and py > 240
    assert h.ann.lage == pytest.approx((h.lage[0] - 20.0, h.lage[1] + 4.1))
