"""Zeichnungsableitung Z1.3 Stufe 4 Task 5: Anforderungen in die Zeichnung, ohne SolidWorks (Fake-COM).

Meldungswege (Plan Task 5 Step 1): Punkt ohne Kante, neuer Wert weicht ab, Rauheitskante fehlt, Rahmen nicht erzeugt;
`toleranz_setzen` (Passung → Typ 7, Abmaße → SetValues, Hülle → Suffix <MOD-EP>)."""

import math

import pytest

from swki.zeichnung import anforderungen_setzen as an
from swki.zeichnung import zeichnen as z
from swki.zeichnung.lesbarkeit import Befund
from swki.zeichnung.massplan import Mass
from swki.zeichnung.toleranzangaben import FormLage, Toleranz

# --- Fake-COM ---------------------------------------------------------------------------------------------------------


class _Tol:
    """Wie live (27.11.): die Setter melden False, die Wirkung ist trotzdem da."""

    def __init__(self):
        self.Type, self.FitDisplayStyle, self.passung, self.werte = 0, 3, ("", ""), (0.0, 0.0)

    def SetFitValues(self, bohrung, welle):
        self.passung = (bohrung, welle)
        return False

    def SetValues(self, unten, oben):
        self.werte = (unten, oben)
        return False

    def GetHoleFitValue(self):
        return self.passung[0]

    def GetShaftFitValue(self):
        return self.passung[1]

    def GetMinValue(self):
        return self.werte[0]

    def GetMaxValue(self):
        return self.werte[1]


class _Dim:
    def __init__(self, name, wert_mm, modell=True):
        self.FullName, self.wert, self.modell, self.Tolerance = f"{name}@Teil.Part", wert_mm, modell, _Tol()

    def GetSystemValue3(self, welche, konfig):
        return (self.wert / 1000,) if self.modell else None

    def GetSystemValue2(self, konfig):
        return self.wert / 1000


class _Daten:
    def __init__(self, linien):
        self.linien = linien

    def GetLineCount(self):
        return len(self.linien)

    def GetLineAtIndex3(self, k):
        (ax, ay), (ex, ey) = self.linien[k]
        return (0, 0, 0, 0, ax / 1000, ay / 1000, 0, ex / 1000, ey / 1000, 0)  # Anfang [4:6], Ende [7:9]


class _Ann:
    def __init__(self, dd, lage=(100.0, 120.0)):
        self.dd, self.lage = dd, lage

    def GetPosition(self):
        return (self.lage[0] / 1000, self.lage[1] / 1000, 0.0)

    def Select2(self, append, mark):
        self.dd.view.gewaehlt = self.dd
        return True


class _DD:
    def __init__(self, view, name, wert_mm, linien, modell=True):
        self.view, self.dim, self.daten = view, _Dim(name, wert_mm, modell), _Daten(linien)
        self.Type2, self.texte = 2, {}
        self.ann = _Ann(self)

    def GetDimension2(self, i):
        return self.dim

    def GetDisplayData(self):
        return self.daten

    def GetAnnotation(self):
        return self.ann

    def GetText(self, teil):
        return self.texte.get(teil, "")

    def SetText(self, teil, text):
        self.texte[teil] = text
        return True


class _View:
    def __init__(self, name="Zeichenansicht1"):
        self.masse, self.gewaehlt, self.name, self.auswahl = [], None, name, []

    def GetDisplayDimensions(self):
        return tuple(self.masse)

    def GetName2(self):
        return self.name

    def SelectEntity(self, obj, anhaengen):
        self.auswahl = (self.auswahl if anhaengen else []) + [obj]
        return True


class _Drw:
    """Zeichnung: AddDimension2 legt ein Zeichnungsmaß mit `neu_wert` an; DeleteSelection2 löscht das gewählte Maß."""

    def __init__(self, view, neu_wert=None, gtol=True):
        self.view, self.neu_wert, self.neu, self.gtol = view, neu_wert, [], gtol
        drw = self

        def loeschen(s, o):
            if drw.view.gewaehlt in drw.view.masse:
                drw.view.masse.remove(drw.view.gewaehlt)
            return True

        self.Extension = type("E", (), {"DeleteSelection2": loeschen,
                                         "SelectByID2": lambda s, *a: False})()  # Punktwahl scheitert: SelectEntity

    def ClearSelection2(self, alle):
        self.view.gewaehlt = None

    def ActivateView(self, name):
        return True

    def AddDimension2(self, x, y, zz):
        if self.neu_wert is None:
            return None
        dd = _DD(self.view, f"RD{len(self.neu) + 1}@{self.view.name}", self.neu_wert, [], modell=False)
        self.neu.append(dd)
        self.view.masse.append(dd)
        return dd

    def InsertGtol(self):
        return None if not self.gtol else object()


def _kante(a, e, kreis=None, features=(), punkt=False):
    return an.Kante(object(), a, e, (a[0], a[1], 0.0), (e[0], e[1], 0.0), kreis, set(features), punkt)


def _plan_mass(name="D3@m1", praefix="4 × ", suffix=" (= 120)", toleranz=None):
    return Mass(name, "modell", "abstand", 30.0, "m1", name=name, praefix=praefix, suffix=suffix, toleranz=toleranz)


# Hilfslinien eines waagrechten Maßes zwischen zwei Kreismitten (95, 245) und (110, 245): Anfang 1 mm über dem Kreis
# (Radius 1,5 auf dem Blatt) plus Lücke, wie live am D3@m1 (27.11.)
_HILFSLINIEN = [((95.0, 247.5), (95.0, 266.0)), ((110.0, 247.5), (110.0, 266.0))]
_KREISE = [_kante((93.5, 245.0), (93.5, 245.0), ((95.0, 245.0), 1.5)),
           _kante((108.5, 245.0), (108.5, 245.0), ((110.0, 245.0), 1.5))]


def test_punkt_ohne_kante_gemeldet_modellmass_bleibt(monkeypatch):
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    drw = _Drw(v, neu_wert=30.0)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE[:1])
    namen, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass()])
    assert namen == {} and v.masse == [alt] and drw.neu == []
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – keine sichtbare Kante am Bezugspunkt (110.0, 246.5); "
                    "Toleranz und Zusatz entfallen"]


def test_neuer_wert_weicht_ab_neues_geloescht(monkeypatch):
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    drw = _Drw(v, neu_wert=30.5)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    namen, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass()])
    assert namen == {} and v.masse == [alt]
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – neues Maß misst 30.5 statt 30.0; Toleranz und Zusatz entfallen"]


def test_zeichnungsmass_ersetzt_modellmass(monkeypatch):
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    drw = _Drw(v, neu_wert=30.0)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    namen, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass(), _plan_mass("D1@f1", "", "")])
    assert meld == [] and namen == {"D3@m1": "RD1@Zeichenansicht1"} and v.masse == drw.neu
    assert v.auswahl == [_KREISE[0].obj, _KREISE[1].obj]          # beide Kreise gewählt
    assert an.zusaetze_setzen({"haupt": v}, [_plan_mass()], namen) == []
    assert drw.neu[0].texte == {1: "4 × ", 2: " (= 120)"}


def test_kante_am_punkt_gerade_quer_und_eckpunkt():
    senkrecht = _kante((129.06, 176.0), (129.06, 180.5))
    waagrecht = _kante((129.56, 181.0), (189.06, 181.0))
    ecke = _kante((129.56, 181.0), (129.56, 181.0), punkt=True)
    kanten = [senkrecht, waagrecht, ecke]
    assert an.kante_am_punkt((129.06, 181.0), "h", kanten) is senkrecht   # Gerade durch den Punkt, quer zur Messung
    assert an.kante_am_punkt((129.56, 181.0), "h", kanten) is ecke        # keine senkrechte Kante: Eckpunkt
    assert an.kante_am_punkt((150.0, 181.0), "v", kanten) is waagrecht
    assert an.kante_am_punkt((140.0, 170.0), "h", kanten) is None


def test_kreis_ueber_hilfslinie_nicht_bei_konzentrischen_kreisen():
    """Live 27.11. (Fase der Buchse in der Stirnansicht): Hilfslinien setzen an zwei konzentrischen Kreisen an, die
    Mitte liegt nicht auf ihnen – kein Kreis, das Maß bleibt Modellmaß."""
    kreis = _kante((275.9, 176.0), (275.9, 176.0), ((275.94, 191.0), 15.0))
    assert an.kante_am_punkt((275.94, 176.0), "v", [kreis], ((274.94, 176.0), (239.0, 176.0))) is None
    assert an.kante_am_punkt((95.0, 246.5), "h", _KREISE, _HILFSLINIEN[0]) is _KREISE[0]


def test_toleranz_passung_bohrung_mit_huelle():
    dd = _DD(_View(), "RD1@Zeichenansicht1", 20.0, [], modell=False)
    dd.texte[2] = " (= 120)"
    assert an.toleranz_setzen(dd, Toleranz("H7", None, None, True))
    tol = dd.dim.Tolerance
    assert (tol.Type, tol.passung, tol.FitDisplayStyle) == (7, ("H7", ""), 3)
    assert dd.texte[2] == " <MOD-EP> (= 120)"                       # Ⓔ vor dem vorhandenen Suffix
    assert an.toleranz_setzen(dd, Toleranz("H7", None, None, True)) and dd.texte[2] == " <MOD-EP> (= 120)"


def test_toleranz_passung_welle_und_abmasse():
    dd = _DD(_View(), "RD2", 32.0, [], modell=False)
    assert an.toleranz_setzen(dd, Toleranz("k6", None, None, False))
    assert dd.dim.Tolerance.passung == ("", "k6") and dd.texte == {}
    sym = _DD(_View(), "RD3", 150.0, [], modell=False)
    assert an.toleranz_setzen(sym, Toleranz(None, 0.02, -0.02, False))
    assert sym.dim.Tolerance.Type == 4 and sym.dim.Tolerance.werte == pytest.approx((-0.00002, 0.00002))
    bilat = _DD(_View(), "RD4", 8.0, [], modell=False)
    assert an.toleranz_setzen(bilat, Toleranz(None, 0.1, -0.05, False))
    assert bilat.dim.Tolerance.Type == 2 and bilat.dim.Tolerance.werte == pytest.approx((-0.00005, 0.0001))
    assert an.toleranz_setzen(bilat, None)


def test_toleranz_ohne_wirkung_gemeldet():
    dd = _DD(_View(), "RD5", 20.0, [], modell=False)
    dd.dim.Tolerance.SetFitValues = lambda b, w: True          # meldet Erfolg, setzt aber nichts
    assert not an.toleranz_setzen(dd, Toleranz("H7", None, None, False))


def _rauheit(merkmal="t1"):
    return Mass(f"{merkmal}:rauheit", "rauheit", "rauheit", 0.0, merkmal, text="Ra 1,6", achse=1, modus="quer")


def test_rauheitskante_fehlt_gemeldet(monkeypatch):
    v = _View()
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [_kante((0, 0), (50, 0), features={"f1"})])
    anm = []
    meld = an.rauheit_setzen(_Drw(v), None, {"haupt": v, "drauf": v}, [_rauheit()], {"haupt": 1, "drauf": 2},
                             {"t1": "schnitt"}, anmerkungen=anm)
    assert meld == ["RAUHEIT_NICHT_GESETZT: t1 Ra 1,6 – keine passende Kante in drauf"] and anm == []


def test_rauheit_ohne_passende_ansicht_gemeldet(monkeypatch):
    v = _View()
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: pytest.fail("keine Ansicht passt"))
    meld = an.rauheit_setzen(_Drw(v), None, {"haupt": v}, [_rauheit()], {"haupt": 1}, {"t1": "schnitt"})
    assert meld == ["RAUHEIT_NICHT_GESETZT: t1 Ra 1,6 – keine Ansicht mit passender Blickachse (y, quer)"]


def test_rahmen_nicht_erzeugt_gemeldet(monkeypatch):
    v = _View()
    boden = an.Kante(object(), (0, 10), (50, 10), (-80, 8, -15), (-30, 8, -15), None, {"t1"})
    oben = an.Kante(object(), (0, 0), (50, 0), (-80, 20, -15), (-30, 20, -15), None, {"t1", "f1"})
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [boden, oben])
    fl = FormLage("t1", "parallelitaet", "<IGTOL-PARA>", "0,05", ("A",), False)
    m = Mass("t1:form_lage:0", "form_lage", "form_lage", 0.0, "t1", text="0,05", achse=1, modus="quer", form_lage=fl)
    meld = an.form_lage_setzen(_Drw(v, gtol=False), None, {"drauf": v}, [m], {"drauf": 2}, {"t1": "schnitt"})
    assert meld == ["FORM_LAGE_NICHT_GESETZT: t1 parallelitaet 0,05 – Kante in drauf nicht auswählbar oder "
                    "InsertGtol abgelehnt"]
    assert v.auswahl == [boden.obj]                                  # Taschenboden: kleinste Lage auf der Achse


def test_bezug_ohne_flaechenrichtung_gemeldet():
    m = Mass("bezug:A", "bezug", "bezug", 0.0, "f1", text="A", anker={"feature": "f1", "nahe": [0, 0, 0]})
    assert an.bezuege_setzen(object(), None, {}, [m], {}) == [
        "BEZUG_NICHT_GESETZT: A – Anker {'feature': 'f1', 'nahe': [0, 0, 0]} ohne Flächenrichtung"]


def test_endkante_oben_und_unten():
    unten = an.Kante(object(), (0, 10), (100, 10), (-100, 0, 60), (100, 0, 60), None, {"f1"})
    oben = an.Kante(object(), (0, 0), (100, 0), (-100, 20, 60), (100, 20, 60), None, {"f1"})
    seite = an.Kante(object(), (0, 0), (0, 10), (-100, 0, 60), (-100, 20, 60), None, {"f1"})
    assert an.endkante([unten, oben, seite], {"f1"}, 1, -1) is unten
    assert an.endkante([unten, oben, seite], {"f1"}, 1, 1) is oben
    assert an.endkante([unten, oben, seite], {"t1"}, 1, 1) is None


def test_bezugskasten_lagen_nach_aussen():
    a = an.Anmerkung("bezug", "f1", ("A",), None, "drauf", (50.0, 10.0), (0.0, 0.0, 100.0, 10.0), (7.0, 7.0),
                     (0.0, 0.0), kante=((0.0, 10.0), (100.0, 10.0)))
    lagen = a.kandidaten([])
    assert lagen[0] == pytest.approx((50.0, 10.0 + 6.0 + 3.5))     # oberhalb der oberen Kante, Mitte der Kante
    assert all(y > 10.0 for _, y in lagen)


def test_befund_gehoert_zur_anmerkung_nur_in_der_naehe():
    a = an.Anmerkung("bezug", "f1", ("A",), None, "drauf", (50.0, 10.0), (0.0, 0.0, 100.0, 10.0), (7.0, 7.0),
                     (0.0, 0.0), lage=(50.0, 19.5))
    assert z._hinweis_zu(Befund("linie_durch_text", "A", (48.0, 17.0, 52.0, 22.0)), [a]) is a
    assert z._hinweis_zu(Befund("linie_durch_text", "A", (150.0, 17.0, 154.0, 22.0)), [a]) is None  # Schnitt „A-A“


def test_umbrechen_und_aufteilung():
    haerte = "einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm (550 HV1)"
    assert an.umbrechen([haerte]) == ["einsatzgehärtet und angelassen (60 ± 2) HRC,", "CHD = (0,8 +0,4/0) mm (550 HV1)"]
    assert " ".join(an.umbrechen([haerte])) == haerte                # Z1.4 vergleicht whitespace-normalisiert
    # allgemeine Rauheit rechts neben der ersten kurzen Zeile, kein eigener Platz im Band (Live 27.11.: A3 1:2 → A4 1:5)
    zeilen = ["Allgemeintoleranzen ISO 2768-1:1989 – m", "Tolerierung ISO 8015:2011"]
    assert an.sammel_aufteilung(zeilen) == (zeilen, 1) and an.sammel_zeilenzahl(zeilen) == 2
    lang = ["x" * 60, "y" * 60]
    assert an.sammel_aufteilung(lang) == (lang, 2) and an.sammel_zeilenzahl(lang) == 3  # passt nirgends: eine Zeile mehr


def test_sammel_pruefen_ueberlauf_und_fehlend():
    band = (230.0, 65.0, 410.0, 100.0)
    texte = [("Tolerierung ISO 8015:2011", (231.0, 93.0, 288.0, 99.5)), ("Maßgebend ist die Zeichnung", (231.0, 60.0, 298.0, 66.0)),
             ("Oberflächen ohne Angabe: Ra 3,2", (330.0, 88.0, 408.0, 95.0))]
    assert an.sammel_pruefen(texte, ["Tolerierung ISO 8015:2011"], band) == []
    meld = an.sammel_pruefen(texte, ["Maßgebend ist die Zeichnung", "Halbzeug: Flach"], band)
    assert meld[0].startswith("SAMMELANGABE_UEBERLAUF: „Maßgebend ist die Zeichnung“")
    assert meld[1] == "SAMMELANGABE_FEHLT: „Halbzeug: Flach“ nicht im PDF"
    assert an.sammel_pruefen(texte[:1], [], band) == ["SAMMELANGABE_FEHLT: „Oberflächen ohne Angabe: Ra 3,2“ nicht im PDF"]


def test_notiztext_huelle_als_symbol():
    """Live 27.11.: „Ⓔ“ lässt auch einen Hinweis verschwinden; <MOD-EP> erscheint, pymupdf liest „E“."""
    notiz, zeilen = z._notiztext("2 × Ø8 H7 Ⓔ – 15 tief\nFase 0,5 × 45°")
    assert notiz == "2 × Ø8 H7 <MOD-EP> – 15 tief\nFase 0,5 × 45°"
    assert zeilen == ("2 × Ø8 H7 E – 15 tief", "Fase 0,5 × 45°")


# --- Nachbesserung A (Review Task 5) -----------------------------------------------------------------------------------


def test_kollineare_ferne_kante_zaehlt_nicht():
    """I2: Kante quer zur Messrichtung zählt nur, wenn der Bezugspunkt auf der Strecke liegt – höchstens 1 mm über ihr
    Ende hinaus (virtuelle Ecke einer Fase, Buchse f3) –, nicht 15 mm weiter auf derselben Geraden (live D3@m1)."""
    fern = _kante((110.0, 218.9), (110.0, 229.9))
    assert an.kante_am_punkt((110.0, 246.5), "h", [fern]) is None
    nah = _kante((110.0, 240.0), (110.0, 250.0))
    assert an.kante_am_punkt((110.0, 246.5), "h", [fern, nah]) is nah


def test_kante_gewinnt_vor_kreis():
    """M1: Trifft am Punkt eine Kante und über die Hilfslinie ein Kreis, gewinnt die Kante."""
    kante = _kante((95.0, 240.0), (95.0, 250.0))
    assert an.kante_am_punkt((95.0, 246.5), "h", _KREISE + [kante], _HILFSLINIEN[0]) is kante


def test_mittenbezug_ohne_kante_gemeldet(monkeypatch):
    """I2: Bezug mitte/ursprung ohne Kante – die Meldung nennt den Bezug."""
    v = _View()
    v.masse.append(_DD(v, "D1@x", 47.0, _HILFSLINIEN))
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [])
    m = Mass("D1@x", "modell", "lage", 47.0, "k1", name="D1@x", bezug="mitte", suffix=" (x)")
    _, meld = an.dauerhaft_machen(_Drw(v, neu_wert=47.0), None, {"haupt": v}, [m])
    assert meld == ["MASS_NICHT_DAUERHAFT: D1@x – Bezug mitte ohne sichtbare Kante am Bezugspunkt (95.0, 246.5), "
                    "(110.0, 246.5); Toleranz und Zusatz entfallen"]


def test_neues_mass_nicht_geloescht_gemeldet(monkeypatch):
    """M2: Weicht der Wert ab und lässt sich das neue Maß nicht löschen, steht es doppelt – Meldung."""
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    drw = _Drw(v, neu_wert=30.5)
    drw.Extension.DeleteSelection2 = lambda o: True                # meldet Erfolg, löscht nichts
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    _, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass()])
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – neues Maß misst 30.5 statt 30.0; neues Maß nicht gelöscht, "
                    "steht doppelt; Toleranz und Zusatz entfallen"]


class _AnnVersatz:
    """Annotation, deren zurückgelesene Lage um 2 mm von der gesetzten abweicht (Bezugskasten rückt)."""

    def __init__(self):
        self.p = (0.0, 0.0)

    def SetPosition2(self, x, y, zz):
        self.p = (x + 0.002, y)
        return True

    def GetPosition(self):
        return (*self.p, 0.0)


def test_verwerfen_merkt_die_soll_lage():
    """I3: verworfen wird die gewählte Lage, nicht die zurückgelesene; danach kommt eine andere."""
    a = an.Anmerkung("rauheit", "st", ("Ra 0,8",), _AnnVersatz(), "haupt", (100.0, 100.0), (0.0, 0.0, 50.0, 50.0),
                     (23.0, 16.0), (9.0, 8.0))
    an.anmerkungen_legen([a], [])
    soll = a.soll
    assert a.lage != soll and a.verwerfen() and a.verworfen == [soll]
    an.anmerkungen_legen([a], [])
    assert a.soll != soll
    assert len(a._roh()) == len(an.ANM_ABSTAENDE_MM) * len(an.ANM_RICHTUNGEN_GRAD)  # nicht fest 16 (M4)


def test_rauheit_ohne_ansicht_ehrlich_gemeldet():
    """M4: Ohne Ansicht passender Blickachse heißt die Meldung so, nicht „keine passende Kante“."""
    m = Mass("t1:rauheit", "rauheit", "rauheit", 0.0, "t1", text="Ra 1,6", achse=None, modus=None)
    assert an.rauheit_setzen(_Drw(_View()), None, {"haupt": _View()}, [m], {"haupt": 1}, {"t1": "schnitt"}) == [
        "RAUHEIT_NICHT_GESETZT: t1 Ra 1,6 – keine Ansicht mit passender Blickachse (Achse unbekannt)"]


# --- Nachbesserung B (Review Task 5) -----------------------------------------------------------------------------------


def _lade_ref(pfad):
    from pathlib import Path
    from swki.spec.laden import lade_spec
    return lade_spec(Path(__file__).resolve().parents[1] / "referenz" / pfad)


def test_instanzen_aus_spec():
    """I4: Stifte 2, Taschenboden t1 2 (s1 spiegelt), Platte 1, M6-Reihe 5."""
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    assert [an.instanzen(spec, f) for f in ("st", "t1", "f1", "g1")] == [2, 2, 1, 5]


def test_ansatzpunkt_meidet_belegte_und_andere_kanten():
    """C2: Ansatz auf der Kante, nicht im Kantenende, nicht dort, wo schon eine Hinweislinie ansetzt."""
    boden = _kante((85.0, 128.6), (110.0, 128.6))
    wand = _kante((97.5, 128.6), (97.5, 122.6))                     # trifft den Boden in der Mitte
    p = an.ansatzpunkt(boden, [boden, wand], [])
    assert p == pytest.approx((85.0 + 0.35 * 25.0, 128.6))           # 50 % liegt auf der Wand
    q = an.ansatzpunkt(boden, [boden, wand], [p])
    assert math.dist(p, q) >= an.ANSATZ_ABSTAND_MM


def test_lage_ohne_kreuzung_der_masslinie_bevorzugt():
    """C2: Hinweislinie kreuzt keine Maßlinie (Bezug B lief über das 12,00); Kasten 3 mm von fremden Kanten."""
    a = an.Anmerkung("bezug", "f1", ("B",), None, "drauf", (60.0, 127.0), (60.0, 122.0, 160.0, 132.0), (7.0, 7.0),
                     (0.0, 0.0), kante=((60.0, 122.0), (60.0, 132.0)))
    masslinie = [((50.0, 120.0), (50.0, 140.0))]                    # senkrechte Hilfslinie links der Kante
    erste = a.kandidaten(masslinien=masslinie)[0]
    assert a.bewerten(erste, masslinien=masslinie) == 0
    assert a.bewerten((40.0, 127.0), masslinien=masslinie) >= 1


def test_umhaengen_an_bohrung_ohne_angabe():
    """I1: Hängt die Rauheit an der Bohrung der Bohrungsangabe, kommt sie an die andere."""
    k1, k2 = _kante((86.0, 204.4), (86.0, 204.4), ((87.6, 204.4), 2.0)), _kante((161.0, 204.4), (161.0, 204.4),
                                                                               ((162.6, 204.4), 2.0))
    alt = type("Ann", (), {"Select2": lambda s, a, m: True})()
    neu = object()
    a = an.Anmerkung("rauheit", "st", ("Ra 0,8",), alt, "haupt", (164.0, 205.8), (0, 0, 1, 1), (20.0, 10.0), (0.0, 0.0),
                     orte=[k1, k2], einhaengen=lambda k, meld=None: (neu, (k.kreis[0][0] + 1.4, k.kreis[0][1] + 1.4)))
    hinweis = type("H", (), {"merkmal": "st", "kreis": ((162.6, 204.4), 2.0), "rechteck": lambda s: None})()
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    an.instanzen_umhaengen(drw, [a], [hinweis])
    assert a.ann is neu and a.anker == pytest.approx((89.0, 205.8))


def test_radiusmass_ueber_kreiskante(monkeypatch):
    """I5: R-Modellmaß (Typ 5) mit Zusatz wird über die Kreiskante allein ein Zeichnungsmaß."""
    v = _View()
    alt = _DD(v, "D1@r1", 4.0, [((20.0, 20.0), (13.4, 13.4)), ((13.4, 13.4), (12.0, 12.0))])  # Ende in der Mitte
    alt.Type2 = 5
    v.masse.append(alt)
    bogen = _kante((8.0, 12.0), (12.0, 8.0), ((12.0, 12.0), 2.0))
    bogen.radius_mm = 4.0
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [bogen])
    m = Mass("D1@r1", "modell", "radius", 4.0, "r1", name="D1@r1", suffix=" (x)")
    namen, meld = an.dauerhaft_machen(_Drw(v, neu_wert=4.0), None, {"haupt": v}, [m])
    assert meld == [] and namen == {"D1@r1": "RD1@Zeichenansicht1"} and v.auswahl == [bogen.obj]


def test_befund_an_fremdem_text_gehoert_zur_kreuzenden_hinweislinie():
    """Live 28.11.: Die Hinweislinie des Rahmens lief durch „SCHNITT A-A“ – der Befund gehört dem Rahmen, nicht den
    Maßreihen."""
    a = an.Anmerkung("form_lage", "t1", ("0,05 A",), None, "drauf", (105.0, 128.6), (60.0, 122.0, 160.0, 132.0),
                     (26.0, 7.0), (13.0, -3.5), lage=(135.0, 100.0))
    assert z._hinweis_zu(Befund("linie_durch_text", "SCHNITT A-A", (104.0, 109.0, 147.0, 121.0)), [a]) is a
    assert z._hinweis_zu(Befund("linie_durch_text", "SCHNITT A-A", (204.0, 109.0, 247.0, 121.0)), [a]) is None


def test_kantenende_ohne_eckpunkt_wird_punkt():
    """Live 28.11. (Buchse f2 im Schnitt): Bezugspunkt am Ende einer Kante, aber keine IVertex – Wahl am Punkt."""
    wand = _kante((129.06, 178.5), (129.06, 183.0))
    k = an.kante_am_punkt((129.06, 178.5), "v", [wand])
    assert k is not None and k.punkt and k.obj is None and k.a == (129.06, 178.5)


# --- Nachbesserung C -------------------------------------------------------------------------------------------------


def test_kreismitte_vor_verlaengerter_wand():
    """I2-Rest (Nachweis kante_1mm.py): Eine kollineare Wand, die 0,8 mm vor der Kreismitte endet, verliert gegen den
    Kreis mit der Mitte im Punkt; allein gilt sie nur innerhalb 1 mm × Maßstab."""
    p = (110.0, 246.5)
    kreis = _kante((112.0, 246.5), (112.0, 246.5), ((110.0, 246.5), 2.0), ["bohrung"])
    wand = _kante((110.0, 236.0), (110.0, 245.7), features=["tasche"])
    assert an.kante_am_punkt(p, "h", [kreis, wand]) is kreis
    assert an.kante_am_punkt(p, "h", [wand]) is wand                   # 0,8 mm bei 1:1
    assert an.kante_am_punkt(p, "h", [wand], massstab=0.5) is None     # 1:2 → 0,5 mm auf dem Blatt
    auf = _kante((110.0, 240.0), (110.0, 250.0))
    assert an.kante_am_punkt(p, "h", [kreis, wand, auf]) is auf        # auf der Strecke: Kante vor Kreis


def test_ersetze_rund_nimmt_den_naechsten_kreis(monkeypatch):
    """Zwei Kreise gleichen Radius berühren Linien des Maßes; gewählt wird der nächste, nicht der erste."""
    v = _View()
    alt = _DD(v, "D1@r1", 4.0, [((20.0, 20.0), (13.4, 13.4)), ((13.4, 13.4), (12.0, 12.0))])
    alt.Type2 = 5
    v.masse.append(alt)
    fern = _kante((28.0, 12.0), (32.0, 8.0), ((32.0, 12.0), 2.0))
    nah = _kante((8.0, 12.0), (12.0, 8.0), ((12.0, 12.0), 2.0))
    fern.radius_mm = nah.radius_mm = 4.0
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [fern, nah])
    alt.daten.linien.append(((30.2, 12.0), (30.25, 12.0)))             # streift den fernen Rand (0,2 mm)
    m = Mass("D1@r1", "modell", "radius", 4.0, "r1", name="D1@r1", suffix=" (x)")
    an.dauerhaft_machen(_Drw(v, neu_wert=4.0), None, {"haupt": v}, [m])
    assert v.auswahl == [nah.obj]


def test_ansatzpunkt_rueckfall_gemeldet():
    """Ist kein Ansatzpunkt frei, kommt der erste – mit Meldung, einmal."""
    boden = _kante((85.0, 128.6), (95.0, 128.6))
    belegt = [(85.0 + t * 10.0, 128.6) for t in an.ANSATZ_TEILUNG]
    meld: list = []
    for _ in range(2):
        p = an.ansatzpunkt(boden, [boden], belegt, None, meld, "t1 Ra 1,6")
    assert p == pytest.approx((90.0, 128.6))
    assert meld == ["ANSATZ_NICHT_FREI: t1 Ra 1,6 – kein Ansatzpunkt der Kante frei (belegt oder an einer anderen "
                    "Kante), Hinweislinie am ersten"]


class _AnnLage:
    def __init__(self):
        self.p = (0.0, 0.0)

    def SetPosition2(self, x, y, zz):
        self.p = (x, y)
        return True

    def GetPosition(self):
        return (*self.p, 0.0)

    def Select2(self, a, m):
        return True


def test_wiederherstellen_haengt_zurueck():
    """I3-Rest: `stand()` umfasst die Instanz. Hat das Umhängen nach der besten Runde die Bohrung gewechselt, hängt die
    Wiederherstellung zurück, statt die alte Lage an die neue Bohrung zu setzen; der alte Ansatz verlässt `belegt`."""
    k1 = _kante((86.0, 204.4), (86.0, 204.4), ((87.6, 204.4), 2.0))
    k2 = _kante((161.0, 204.4), (161.0, 204.4), ((162.6, 204.4), 2.0))
    belegt: list = []

    def einhaengen(k, meld=None):
        ansatz = (k.kreis[0][0] + 1.4, k.kreis[0][1] + 1.4)
        belegt.append(ansatz)
        return _AnnLage(), ansatz

    ann, anker = einhaengen(k1)
    a = an.Anmerkung("rauheit", "st", ("Ra 0,8",), ann, "haupt", anker, (0, 0, 1, 1), (20.0, 10.0), (0.0, 0.0),
                     orte=[k1, k2], einhaengen=einhaengen, belegt=belegt)
    an.anmerkungen_legen([a], [])
    beste = a.stand()
    assert beste == (a.soll, k1)
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    hinweis = type("H", (), {"merkmal": "st", "kreis": ((87.6, 204.4), 2.0), "rechteck": lambda s: None})()
    an.instanzen_umhaengen(drw, [a], [hinweis])                        # Angabe an k1 → Rauheit an k2
    assert a.instanz() is k2 and belegt == [(164.0, 205.8)]
    a.fixiert = beste
    an.instanzen_umhaengen(drw, [a], [])
    an.anmerkungen_legen([a], [])
    assert a.instanz() is k1 and a.soll == beste[0] and belegt == [(89.0, 205.8)]


# Schnitt A-A der SpannplatteZ (Live 28.11., dump): Platte 75–175 × 122,56–132,56, Taschen von unten bis 128,56
_SCHNITT = [((75.06, 122.56), (75.06, 132.56)), ((75.06, 132.56), (175.06, 132.56)), ((175.06, 132.56), (175.06, 122.56)),
            ((175.06, 122.56), (165.06, 122.56)), ((165.06, 122.56), (165.06, 128.56)),
            ((165.06, 128.56), (140.06, 128.56)), ((140.06, 128.56), (140.06, 122.56)),
            ((140.06, 122.56), (110.06, 122.56)), ((110.06, 122.56), (110.06, 128.56)),
            ((110.06, 128.56), (85.06, 128.56)), ((85.06, 128.56), (85.06, 122.56)), ((85.06, 122.56), (75.06, 122.56))]
_RAND_T1 = _kante((87.06, 122.56), (108.06, 122.56), features=["f1", "t1"])  # Rand der Taschenöffnung, hinter dem Schnitt
_UMRISS = (75.06, 122.56, 175.06, 132.56)
_VON_RECHTS_UNTEN = (129.15, 105.0)  # Rauheit (23,5 × 10, Versatz 9,15/5): Spitze (120, 100), Linie unter 128° zum Boden


def test_hinweislinie_durch_kontur_und_schraffur_zaehlt():
    """(c): Ebenheit an der Unterseite – nach oben kreuzt die Linie die Oberkante und läuft durch die Schraffur, nach
    unten ist sie frei."""
    a = an.Anmerkung("form_lage", "f1", ("0,02",), None, "drauf", (124.9, 122.56), _UMRISS, (16.0, 7.0), (8.0, -3.5),
                     kante=((110.06, 122.56), (140.06, 122.56)), schraffur=_SCHNITT)
    oben, unten = (120.0, 145.0), (140.0, 105.0)
    assert a.verstoesse(oben, kanten=_SCHNITT) == {an.V_KANTE: 1, an.V_SCHRAFFUR: 1, an.V_SYMBOL: 1}  # Ecke
    assert a.verstoesse(unten, kanten=_SCHNITT) == {}
    assert a.kandidaten(kanten=_SCHNITT)[0][1] < 122.56


def test_taschenboden_von_unten_durch_die_oeffnung():
    """(c): Ra am Taschenboden – von unten über den Rand der eigenen Öffnung zählt nicht, von oben Kante und
    Schraffur."""
    boden = _kante((110.06, 128.56), (85.06, 128.56), features=["t1"])
    offen = an.offene_kanten([boden, _RAND_T1], {"t1"}, _SCHNITT)
    assert offen == [_RAND_T1]
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0),
                     kante=(boden.a, boden.e), schraffur=_SCHNITT, offen=offen)
    kanten = _SCHNITT + [(_RAND_T1.a, _RAND_T1.e)]
    assert a.bewerten(_VON_RECHTS_UNTEN, kanten=kanten) == 0
    assert a.verstoesse((110.0, 145.0), kanten=kanten) == {an.V_KANTE: 1, an.V_SCHRAFFUR: 1}


def test_rauheit_hinweislinie_durch_das_eigene_symbol():
    """Live 28.11.: Ra 1,6 von unten – kommt die Linie von oben an die Spitze, läuft sie durch Dreieck und Text."""
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0))
    assert a.verstoesse((80.0, 105.0)) == {an.V_SYMBOL: 1}            # Spitze links unten, Linie von rechts oben
    assert a.verstoesse(_VON_RECHTS_UNTEN) == {}                       # Spitze rechts unten, Linie von links oben


def test_bezug_auf_der_verlaengerung():
    """(b), ISO 5459: Bezug B an der linken Kante des Schnitts – daneben kreuzt jede Lage das 12,00; frei ist der Kasten
    auf der Verlängerung über oder unter dem Teil (Spike Stufe 4 i: SolidWorks zieht die Verlängerung selbst)."""
    a = an.Anmerkung("bezug", "f1", ("B",), None, "drauf", (75.06, 127.56), _UMRISS, (7.0, 7.0), (0.0, 0.0),
                     kante=((75.06, 122.56), (75.06, 132.56)))
    masslinien = [((64.12, 106.84), (64.12, 134.91)), ((109.06, 122.56), (63.12, 122.56)),
                  ((109.06, 128.56), (63.12, 128.56))]
    lagen = a.kandidaten(kanten=_SCHNITT, masslinien=masslinien, hindernisse=masslinien)
    beste = lagen[0]
    assert a.bewerten(beste, hindernisse=masslinien, kanten=_SCHNITT, masslinien=masslinien) == 0
    fuss = a.fusspunkt(beste)
    assert fuss[0] == pytest.approx(75.06) and not 122.56 <= fuss[1] <= 132.56
    assert a.verlaengerung(beste) is not None and a.verlaengerung(beste)[1] == pytest.approx(fuss)
    assert all(a.bewerten(lage, hindernisse=masslinien, kanten=_SCHNITT, masslinien=masslinien) > 0
               for lage in lagen if 122.56 <= a.fusspunkt(lage)[1] <= 132.56)


def test_kreuzung_nach_der_letzten_runde_gemeldet():
    """(a): Was nach der letzten Runde kreuzt, steht als ANMERKUNG_KREUZT da (Lage zurückgelesen, gegen die anderen)."""
    a = an.Anmerkung("bezug", "f1", ("B",), None, "drauf", (75.06, 127.56), _UMRISS, (7.0, 7.0), (0.0, 0.0),
                     kante=((75.06, 122.56), (75.06, 132.56)), lage=(56.56, 127.56))
    b = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0),
                     lage=_VON_RECHTS_UNTEN)
    masslinien = [((64.12, 106.84), (64.12, 134.91))]
    assert an.anmerkungen_pruefen([a, b], masslinien=masslinien) == [
        "ANMERKUNG_KREUZT: f1 bezug „B“ – Maßlinie (1)"]


def test_hinweis_haelt_abstand_zu_masszahl():
    """Punkt 4: „2 × Ø8 H7 Ⓔ –“ endete 0,6 mm vor „16,00“ – in Zeilenrichtung zählt erst eine Schrifthöhe Abstand
    als frei, quer dazu 1 mm."""
    from swki.zeichnung.angaben import hinweis_lagen_bewertet

    kreis, umriss, groesse = ((100.0, 100.0), 2.0), (0.0, 0.0, 101.0, 101.0), (30.0, 6.0)
    lage = next(l for w, l in hinweis_lagen_bewertet(kreis, umriss, [], groesse) if w[2] == 0)

    def zahl(x0, y0):
        return z._rechteck_strecken((x0, y0, x0 + 14.0, y0 + 4.0))

    def wert(nah):
        return next(w for w, l in hinweis_lagen_bewertet(kreis, umriss, [], groesse, nah) if l == lage)[0]

    rechts, oben = lage[0] + groesse[0] / 2, lage[1] + groesse[1] / 2
    assert wert(zahl(rechts + 0.6, lage[1] - 2.0)) == 1
    assert wert(zahl(rechts + 4.0, lage[1] - 2.0)) == 0
    assert wert(zahl(lage[0] - 7.0, oben + 0.6)) == 1                  # darüber, 0,6 mm
    assert wert(zahl(lage[0] - 7.0, oben + 1.5)) == 0


def test_orte_der_flaeche_im_schnitt():
    """(b): Die Unterseite zeigt sich im Schnitt dreimal (links, zwischen, rechts der Taschen); der Rand der
    Taschenöffnung hinter dem Schnitt gehört nicht dazu."""
    def kante(a, e, features):
        return an.Kante(object(), a, e, (a[0], 0.0, a[1]), (e[0], 0.0, e[1]), None, set(features))

    mitte = kante((110.06, 122.56), (140.06, 122.56), ["Schnitt1", "f1"])
    links = kante((75.06, 122.56), (85.06, 122.56), ["Schnitt1", "f1"])
    rechts = kante((165.06, 122.56), (175.06, 122.56), ["Schnitt1", "f1"])
    rand = kante((87.06, 122.56), (108.06, 122.56), ["f1", "t1"])
    oben = kante((75.06, 132.56), (175.06, 132.56), ["Schnitt1", "f1"])
    orte = an.orte_der_flaeche([oben, links, rand, mitte, rechts], mitte, {"f1"}, 2, -1, _SCHNITT)
    assert orte[0] is mitte and set(map(id, orte[1:])) == {id(links), id(rechts)}


def test_hilfslinie_auf_der_kante_zaehlt_als_kante():
    """Die Hilfslinie des 12,00 liegt auf dem Rand der Taschenöffnung: wo die Hinweislinie über die (erlaubte) Öffnung
    läuft, zählt sie nicht zusätzlich als Maßlinie."""
    boden = _kante((110.06, 128.56), (85.06, 128.56), features=["t1"])
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0),
                     kante=(boden.a, boden.e), schraffur=_SCHNITT, offen=[_RAND_T1])
    kanten = _SCHNITT + [(_RAND_T1.a, _RAND_T1.e)]
    hilfslinie = [((109.06, 122.56), (63.12, 122.56))]
    assert a.verstoesse(_VON_RECHTS_UNTEN, kanten=kanten, masslinien=hilfslinie) == {}
    assert a.verstoesse(_VON_RECHTS_UNTEN, masslinien=hilfslinie) == {an.V_MASSLINIE: 1}


def test_fremder_text_gleichen_wortlauts_bleibt_fremd():
    """Bezug „A“ machte die Kennbuchstaben „A“ der Schnittlinie unsichtbar: eigen ist ein Text nur nahe seiner
    Anmerkung."""
    a = an.Anmerkung("bezug", "f1", ("A",), None, "drauf", (125.0, 132.6), _UMRISS, (7.0, 7.0), (0.0, 0.0),
                     kante=((75.06, 132.56), (175.06, 132.56)), lage=(125.06, 142.06))
    nah, fern = (123.6, 139.0, 126.5, 145.0), (186.5, 227.6, 192.8, 239.2)
    assert z._fremde_texte([("A", nah), ("A", fern), ("20,00", (58.1, 228.7, 64.5, 242.9))], [a]) == [
        fern, (58.1, 228.7, 64.5, 242.9)]


def test_umriss_ohne_eckpunkte():
    """Eckpunkte landen live neben der Ansicht (IVertex.GetPoint): der Umriss zählt nur Kanten."""
    kanten = [_kante((75.0, 122.5), (175.0, 122.5)), _kante((75.0, 132.5), (175.0, 132.5)),
              _kante((137.6, 68.8), (137.6, 68.8), punkt=True)]
    assert an._umriss(kanten) == (75.0, 122.5, 175.0, 132.5)


def test_zu_nah_am_pdf_rechteck():
    """Punkt 4, Endprüfung: „2 × Ø8 H7 E –“ (187,3–221,4) gegen „16,00“ (221,2–235,4) – zu nah; 4 mm weiter frei."""
    hinweis = (187.3, 181.6, 221.4, 188.1)
    assert z.zu_nah(hinweis, z._rechteck_strecken((221.2, 183.1, 235.4, 189.5))) > 0
    assert z.zu_nah(hinweis, z._rechteck_strecken((225.0, 183.1, 239.2, 189.5))) == 0


def test_hinweislinie_auf_der_kante_und_durch_das_massende_zaehlt():
    """Live 28.11.: Der Rahmen hing links an der Unterseite, seine Hinweislinie lag auf Unterkante und Hilfslinie und
    lief genau durch das Ende der Maßlinie 12,00 – das ist kein freier Weg."""
    links = ((75.06, 122.56), (85.06, 122.56))
    a = an.Anmerkung("form_lage", "f1", ("0,02",), None, "drauf", (79.0, 122.56), _UMRISS, (16.0, 7.0), (8.0, -3.5),
                     kante=links)
    lage = (47.0, 122.56)                                              # Rahmen links, Hinweislinie waagrecht
    masslinien = [((64.12, 106.84), (64.12, 122.56)), ((109.06, 122.56), (63.12, 122.56))]
    v = a.verstoesse(lage, kanten=_SCHNITT, masslinien=masslinien)
    assert v.get(an.V_MASSLINIE, 0) >= 1 and v.get(an.V_KANTE, 0) >= 1


def test_rahmen_hinweislinie_durch_das_eigene_rechteck():
    """Live 28.11.: Die Hinweislinie des Rahmens lief von oben rechts zur linken Schmalseite durch „2 ×“."""
    a = an.Anmerkung("form_lage", "t1", ("0,05 A", "2 ×"), None, "drauf", (145.0, 128.56), _UMRISS, (26.0, 12.5),
                     (13.0, 6.25 - 7.0))
    assert a.verstoesse((150.0, 90.0)) == {an.V_SYMBOL: 1}            # Anker über dem Rahmen, Linie zur linken Seite
    assert a.verstoesse((185.0, 90.0)) == {}                           # Rahmen rechts unten, Linie zur linken Seite
