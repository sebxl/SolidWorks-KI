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
    ScaleDecimal = 1.0

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
    """Zeichnung: AddDimension2 legt ein Zeichnungsmaß mit `neu_wert` und den Hilfslinien `neu_linien` an (Vorgabe:
    `_HILFSLINIEN`, wie das Modellmaß); DeleteSelection2 löscht das gewählte Maß."""

    def __init__(self, view, neu_wert=None, gtol=True, neu_linien=None):
        self.view, self.neu_wert, self.neu, self.gtol = view, neu_wert, [], gtol
        self.neu_linien = neu_linien
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
        linien = _HILFSLINIEN if self.neu_linien is None else self.neu_linien
        dd = _DD(self.view, f"RD{len(self.neu) + 1}@{self.view.name}", self.neu_wert, linien, modell=False)
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


def test_kante_am_punkt_gerade_quer_und_kantenende():
    """Runde D (I2): kein IVertex mehr (Eckpunkte liegen live 54–89 mm daneben); am Kantenende wird über den Punkt
    gewählt (Kante ohne Objekt)."""
    senkrecht = _kante((129.06, 176.0), (129.06, 180.5))
    waagrecht = _kante((129.56, 181.0), (189.06, 181.0))
    fremde_ecke = _kante((129.56, 181.0), (129.56, 181.0), punkt=True)  # zufällig im Punkt: wird nicht gewählt
    kanten = [senkrecht, waagrecht, fremde_ecke]
    assert an.kante_am_punkt((129.06, 181.0), "h", kanten) is senkrecht   # Gerade durch den Punkt, quer zur Messung
    ende = an.kante_am_punkt((129.56, 181.0), "h", kanten)                # keine senkrechte Kante: Kantenende
    assert ende is not fremde_ecke and ende.punkt and ende.obj is None and ende.a == (129.56, 181.0)
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
    """I1: Hängt die Rauheit an der Bohrung der Bohrungsangabe, kommt sie an die andere (Runde E: gewählt von der
    gemeinsamen Lagewahl, die Bohrung der Angabe verliert den Gleichstand)."""
    k1, k2 = _kante((86.0, 204.4), (86.0, 204.4), ((87.6, 204.4), 2.0)), _kante((161.0, 204.4), (161.0, 204.4),
                                                                               ((162.6, 204.4), 2.0))
    alt = _AnnLage()
    neu = _AnnLage()
    a = an.Anmerkung("rauheit", "st", ("Ra 0,8",), alt, "haupt", (164.0, 205.8), (0, 0, 1, 1), (20.0, 10.0), (0.0, 0.0),
                     orte=[k1, k2], einhaengen=lambda k, meld=None: (neu, (k.kreis[0][0] + 1.4, k.kreis[0][1] + 1.4)))
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    an.anmerkungen_legen([a], [], drw=drw, besetzt={"st": [(162.6, 204.4)]})
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
    an.anmerkungen_legen([a], [], drw=drw, besetzt={"st": [(87.6, 204.4)]})  # Angabe an k1 → Rauheit an k2
    assert a.instanz() is k2 and belegt == [(164.0, 205.8)]
    a.fixiert = beste
    an.anmerkungen_legen([a], [], drw=drw)
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
    orte = an.orte_der_flaeche([oben, links, rand, mitte, rechts], mitte, {"f1"}, 2, _SCHNITT)
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


# --- Runde D: Review C (I1–I4, M1–M4, M6, M7, M9, M11) ------------------------------------------------------------------


def _kreis_kante(m, r, feature):
    p = (m[0] + r, m[1])
    return an.Kante(object(), p, p, (p[0], p[1], 0.0), (p[0], p[1], 0.0), (m, r), {feature}, radius_mm=r)


def _kreis_strecken(*kreise):
    return [s for k in kreise for s in an._bogen(k.a, k.a, k.kreis[0])]


def _rauheit_an_bohrung(k1, k2, offen, statt=None):
    anker = (k1.kreis[0][0] + k1.kreis[1] * math.cos(math.radians(45)),
             k1.kreis[0][1] + k1.kreis[1] * math.sin(math.radians(45)))
    return an.Anmerkung("rauheit", "b1", ("Ra 0,8",), None, "drauf", statt or anker, (90, 90, 120, 120), (23.7, 11.0),
                        (8.95, 5.5), orte=[k1, k2], offen=offen)


def test_hinweislinie_durch_die_nachbarbohrung_zaehlt():
    """I1 (Probe probe_offen.py): `offen` gilt nur am Ort der Instanz – die Linie quer durch die zweite Bohrung desselben
    Bohrbilds kreuzt eine fremde Kante; die konzentrische Fase der eigenen Bohrung ist frei."""
    k1, k2 = _kreis_kante((100.0, 100.0), 3.0, "b1"), _kreis_kante((115.0, 115.0), 3.0, "mu1")
    fase = _kreis_kante((100.0, 100.0), 4.0, "b1")
    offen = an.offene_kanten([k1, k2, fase], {"b1", "mu1"}, [])
    a = _rauheit_an_bohrung(k1, k2, offen)
    durch_k2 = (125.0 + 8.95, 125.0 + 5.5)                             # Spitze bei (125, 125): Linie durch Bohrung 2
    assert a.verstoesse(durch_k2, kanten=_kreis_strecken(k1, k2, fase)) == {an.V_KANTE: 2}
    frei = (95.0 + 8.95 + 30, 104.0 + 5.5)                             # Spitze rechts der eigenen Fase, fern von k2
    assert an.V_KANTE not in a.verstoesse(frei, kanten=_kreis_strecken(k1, fase))


def test_offen_folgt_der_instanz():
    """I1: Nach dem Umhängen an die zweite Bohrung ist deren Rand offen, der der ersten fremd."""
    k1, k2 = _kreis_kante((100.0, 100.0), 3.0, "b1"), _kreis_kante((115.0, 115.0), 3.0, "mu1")
    fase2 = _kreis_kante((115.0, 115.0), 5.0, "mu1")
    a = _rauheit_an_bohrung(k1, k2, an.offene_kanten([k1, k2, fase2], {"b1", "mu1"}, []))
    assert a._offen_hier() == [k1]
    a.anker = (115.0 + 3.0 * math.cos(math.radians(225)), 115.0 + 3.0 * math.sin(math.radians(225)))
    assert set(map(id, a._offen_hier())) == {id(k2), id(fase2)}


def test_gespiegelter_taschenrand_zaehlt():
    """I1: Durch die eigene Öffnung (erste Kreuzung ab dem Fußpunkt) frei; der Rand der gespiegelten Tasche zählt, und
    nach einer fremden Kante zählt auch der eigene Rand."""
    boden = _kante((110.06, 128.56), (85.06, 128.56), features=["t1"])
    rand2 = _kante((142.06, 122.56), (163.06, 122.56), features=["f1", "s1"])
    offen = an.offene_kanten([boden, _RAND_T1, rand2], {"t1", "s1"}, _SCHNITT)
    assert set(map(id, offen)) == {id(_RAND_T1), id(rand2)}
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0),
                     kante=(boden.a, boden.e), schraffur=[], offen=offen, orte=[boden])
    kanten = [(_RAND_T1.a, _RAND_T1.e), (rand2.a, rand2.e)]
    assert a.verstoesse(_VON_RECHTS_UNTEN, kanten=kanten) == {}         # nur durch die eigene Öffnung
    a.anker = (150.0, 128.56)                                          # Linie von der Mitte des Bodens der Tasche 2 …
    a.orte = [boden]                                                   # … gehört aber zu Tasche 1: Rand 2 ist fremd
    lage = (150.0 + 9.15 + 10.0, 105.0)
    assert a.verstoesse(lage, kanten=kanten).get(an.V_KANTE) == 1
    fremd = ((90.0, 125.0), (110.0, 125.0))                            # vor dem eigenen Rand: beide zählen
    a.anker = (97.5, 128.56)
    assert a.verstoesse(_VON_RECHTS_UNTEN, kanten=kanten + [fremd]).get(an.V_KANTE) == 2


def test_hilfslinie_quer_zur_kante_zaehlt_als_masslinie():
    """M2: Ausgenommen ist eine Maßlinie nur, wo sie auf einer Kante liegt (kollinear); quer über eine Kante
    hinweg bleibt die Kreuzung eine Maßlinie."""
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), None, "drauf", (97.5, 128.56), _UMRISS, (23.5, 10.0), (9.15, 5.0))
    linie = a.hinweislinie(_VON_RECHTS_UNTEN)
    p = (linie[0][0] + (linie[1][0] - linie[0][0]) * 0.5, linie[0][1] + (linie[1][1] - linie[0][1]) * 0.5)
    quer = [((p[0] - 5.0, p[1]), (p[0] + 5.0, p[1]))]                  # waagrechte Hilfslinie durch p
    senkrecht = [((p[0], p[1] - 5.0), (p[0], p[1] + 5.0))]             # Kante quer zur Hilfslinie, durch p
    assert a.verstoesse(_VON_RECHTS_UNTEN, kanten=senkrecht, masslinien=quer).get(an.V_MASSLINIE) == 1
    assert an.V_MASSLINIE not in a.verstoesse(_VON_RECHTS_UNTEN, kanten=quer, masslinien=quer)


def test_naehe_eigene_meldung():
    """M3: „Kante < 3 mm“ und „Ansatz < 4 mm“ sind Nähe, keine Kreuzung: Meldung ANMERKUNG_ZU_NAH."""
    a = an.Anmerkung("bezug", "f1", ("B",), None, "drauf", (75.06, 127.56), _UMRISS, (7.0, 7.0), (0.0, 0.0),
                     kante=((75.06, 122.56), (75.06, 132.56)), lage=(66.56, 127.56))
    nah = [((61.0, 120.0), (61.0, 135.0))]                             # im 3-mm-Saum des Kastens (63,06–70,06)
    assert an.anmerkungen_pruefen([a], kanten=nah) == ["ANMERKUNG_ZU_NAH: f1 bezug „B“ – Kante näher als 3 mm (1)"]


def test_jenseits_nur_nahe_masslinien():
    """M4: Maßlinien einer fernen Ansicht schieben die Lagen nicht hinaus."""
    a = an.Anmerkung("rauheit", "st", ("Ra 0,8",), None, "haupt", (100.0, 100.0), (0, 0, 1, 1), (20.0, 10.0), (0.0, 0.0))
    nah = [((140.0, 95.0), (140.0, 105.0))]                            # 40 mm rechts
    fern = [((300.0, 95.0), (300.0, 105.0))]                           # 200 mm rechts (andere Ansicht)
    assert a._jenseits(nah).get(0) == pytest.approx(40.0 + an.JENSEITS_LUECKE_MM)
    assert a._jenseits(fern) == {}


def test_umhaengen_an_gerade_orte_und_wirkung_gemeldet():
    """M11/M7: Umhängen an eine gleichwertige gerade Kante; der neue Rahmen wird nach Wirkung geprüft (Runde E: im
    Endstand, `anmerkungen_wirkung`)."""
    links = _kante((75.06, 122.56), (85.06, 122.56), features=["f1"])
    rechts = _kante((165.06, 122.56), (175.06, 122.56), features=["f1"])
    zustand = {"beschriftet": True}

    def einhaengen(k, meld=None):
        zustand["beschriftet"] = False                                 # neuer Rahmen: SetFrameValues2 ohne Wirkung
        return _AnnLage(), ((k.a[0] + k.e[0]) / 2, k.a[1])

    def wirkung():
        return [] if zustand["beschriftet"] else ["FORM_LAGE_NICHT_GESETZT: f1 ebenheit 0,02 – Rahmen nicht beschriftet"]

    a = an.Anmerkung("form_lage", "f1", ("0,02",), _AnnLage(), "drauf", (80.06, 122.56), _UMRISS, (16.0, 7.0),
                     (8.0, -3.5), kante=(links.a, links.e), orte=[links, rechts], einhaengen=einhaengen,
                     wirkung=wirkung)
    sperre = [((x, 50.0), (x, 200.0)) for x in range(20, 145, 5)]     # Gitter über der linken Kante
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    meld: list = []
    an.anmerkungen_legen([a], sperre, drw=drw, meldungen=meld)
    assert a.instanz() is rechts and a.kante == (rechts.a, rechts.e) and meld == []
    assert an.anmerkungen_wirkung([a]) == ["FORM_LAGE_NICHT_GESETZT: f1 ebenheit 0,02 – Rahmen nicht beschriftet"]


def test_bezugspunkte_des_neuen_masses_nach_wirkung(monkeypatch):
    """I2: Das neue Zeichnungsmaß misst denselben Wert, setzt aber 40 mm daneben an – Meldung, Modellmaß bleibt."""
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    daneben = [((95.0, 207.5), (95.0, 226.0)), ((110.0, 207.5), (110.0, 226.0))]
    drw = _Drw(v, neu_wert=30.0, neu_linien=daneben)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    namen, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass()])
    assert namen == {} and v.masse == [alt]
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – neues Maß setzt bei (95.0, 206.5), (110.0, 206.5) an statt "
                    "(95.0, 246.5), (110.0, 246.5); Toleranz und Zusatz entfallen"]
    leer = _Drw(v, neu_wert=30.0, neu_linien=[])                       # Hilfslinien nicht lesbar: nie still
    _, meld = an.dauerhaft_machen(leer, None, {"haupt": v}, [_plan_mass()])
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – Hilfslinien des neuen Maßes nicht lesbar; Toleranz und Zusatz "
                    "entfallen"] and v.masse == [alt]
    knapp = [((95.0, 250.0), (95.0, 266.0)), ((110.0, 250.0), (110.0, 266.0))]  # 2,5 mm entlang: Lücke, gleich
    _, meld = an.dauerhaft_machen(_Drw(v, neu_wert=30.0, neu_linien=knapp), None, {"haupt": v}, [_plan_mass()])
    assert meld == []


def test_massstab_nicht_lesbar_gemeldet(monkeypatch):
    """M6: Fällt `ScaleDecimal` aus, ist das eine Meldung, kein stilles 1:1."""
    class _OhneMassstab(_View):
        @property
        def ScaleDecimal(self):
            raise RuntimeError("COM")

    v = _OhneMassstab()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    _, meld = an.dauerhaft_machen(_Drw(v, neu_wert=30.0), None, {"haupt": v}, [_plan_mass()])
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – Maßstab der Ansicht nicht lesbar; Toleranz und Zusatz entfallen"]


class _Sel:
    def __init__(self, obj):
        self.obj = obj

    def GetSelectedObjectCount2(self, mark):
        return 1

    def GetSelectedObjectType3(self, i, mark):
        return an.KANTE

    def GetSelectedObject6(self, i, mark):
        return self.obj


class _Kurve:
    def __init__(self, a_m, e_m):
        self.StartPoint, self.EndPoint = tuple(c / 1000 for c in a_m), tuple(c / 1000 for c in e_m)


class _GewKante:
    def __init__(self, a_m, e_m):
        self.cp = _Kurve(a_m, e_m)

    def GetCurveParams3(self):
        return self.cp


def test_wahl_am_punkt_prueft_die_gewaehlte_kante():
    """M1: Wählt SelectByID2 am Punkt eine andere Kante (Fase 0,25 mm daneben), gilt die Wahl nicht – zurück auf
    SelectEntity der gesuchten Kante."""
    k = _kreis_kante((100.0, 100.0), 3.0, "b1")
    v = _View()
    drw = _Drw(v)
    drw.Extension.SelectByID2 = lambda *a: True
    drw.SelectionManager = _Sel(_GewKante((103.25, 100.0, 0.0), (103.25, 100.0, 0.0)))  # Fasenkreis
    assert an._waehle_am_punkt(drw, v, k, (103.0, 100.0)) and v.auswahl == [k.obj]
    v.auswahl = []
    drw.SelectionManager = _Sel(_GewKante(k.a_m, k.e_m))
    assert an._waehle_am_punkt(drw, v, k, (103.0, 100.0)) and v.auswahl == []  # am Punkt gewählt, kein Rückfall


def test_fremde_texte_eigen_nach_woertern():
    """I3: Eigen ist ein Text nahe der Anmerkung, dessen Wörter in ihren Zeilen stehen – auch getrennt geliefert oder
    mit Symbolzeichen; ein fremdes Wort daneben bleibt fremd."""
    a = an.Anmerkung("form_lage", "t1", ("0,05 A", "2 ×"), None, "drauf", (145.0, 128.56), _UMRISS, (26.0, 12.5),
                     (13.0, -0.75), lage=(67.5, 97.0))
    texte = [("0,05", (59.5, 94.3, 68.0, 100.7)), ("A", (71.0, 94.3, 75.5, 100.7)), ("∥", (52.0, 94.3, 56.0, 100.7)),
             ("2 ×", (50.8, 101.0, 57.5, 107.4)), ("20,00", (58.0, 86.0, 66.0, 92.5)), ("A", (186.5, 227.6, 192.8, 239.2))]
    assert z._fremde_texte(texte, [a]) == [(58.0, 86.0, 66.0, 92.5), (186.5, 227.6, 192.8, 239.2)]


class _Hatch:
    def __init__(self, kanten):
        self.kanten = kanten

    @property
    def Face(self):
        return type("F", (), {"GetEdges": lambda s: tuple(self.kanten)})()


class _KaputteKante:
    def GetCurveParams3(self):
        raise RuntimeError("COM")


class _HatchView:
    def __init__(self, hatches, typ=2, fehler=False):
        self.hatches, self.Type, self.fehler = hatches, typ, fehler
        self.ModelToViewTransform = None

    def GetFaceHatches(self):
        if self.fehler:
            raise RuntimeError("COM")
        return tuple(self.hatches)

    def GetName2(self):
        return "Schnittansicht A-A"


def test_schraffur_ungelesen_gemeldet():
    """I4: GetFaceHatches gescheitert, Schnitt ohne Schraffur, eine Kante unlesbar → Gründe; keine Schraffur in
    einer Projektion ist kein Befund."""
    assert an.schraffur_strecken(None, _HatchView([], fehler=True))[1] == ["GetFaceHatches gescheitert"]
    assert an.schraffur_strecken(None, _HatchView([]))[1] == ["Schnittansicht ohne Schraffur"]
    assert an.schraffur_strecken(None, _HatchView([], typ=4)) == ([], [])
    assert an.schraffur_strecken(None, _HatchView([_Hatch([_KaputteKante()])]))[1] == ["Fläche 1: Kante 1 nicht lesbar"]
    meld: list = []
    cache: dict = {}
    assert an._schraffur(cache, None, {"drauf": _HatchView([])}, "drauf", meld) is None
    assert meld == ["SCHRAFFUR_UNGELESEN: Schnittansicht A-A – Schnittansicht ohne Schraffur"]


def test_ungelesene_schraffur_schliesst_nichts_auf():
    """I4: Ohne gelesene Schraffur ist nichts offen und die Fläche hat nur ihren eigenen Ort."""
    boden = _kante((110.06, 128.56), (85.06, 128.56), features=["t1"])
    boden2 = _kante((165.06, 128.56), (140.06, 128.56), features=["t1"])
    assert an._orte("schnitt", [boden, boden2], boden, {"t1"}, 1, []) == [boden, boden2]
    assert an._orte("schnitt", [boden, boden2], boden, {"t1"}, 1, None) == [boden]


def test_bogen_in_stuecken():
    """M11: Viertelkreis gegen den Uhrzeigersinn in `SCHRAFFUR_BOGEN_STUECKE` Stücken auf dem Kreis."""
    stuecke = an._bogen((10.0, 0.0), (0.0, 10.0), (0.0, 0.0))
    assert len(stuecke) == an.SCHRAFFUR_BOGEN_STUECKE
    assert all(abs(math.dist(p, (0.0, 0.0)) - 10.0) < 1e-9 for s in stuecke for p in s)
    assert stuecke[0][0] == pytest.approx((10.0, 0.0)) and stuecke[-1][1] == pytest.approx((0.0, 10.0))


def test_verdrahtung_kreuzen_und_zu_nah(monkeypatch, tmp_path):
    """M11: `_anmerkungen_kreuzen` zählt fremde PDF-Texte (nicht die eigenen) und die Kanten; `_hinweise_zu_nah`
    misst den Hinweis am PDF gegen fremden Text."""
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    a = an.Anmerkung("form_lage", "f1", ("0,02",), None, "drauf", (124.9, 122.56), _UMRISS, (16.0, 7.0), (8.0, -3.5),
                     kante=((110.06, 122.56), (140.06, 122.56)), lage=(140.0, 105.0))
    linie = a.hinweislinie()
    mitte = ((linie[0][0] + linie[1][0]) / 2, (linie[0][1] + linie[1][1]) / 2)
    schnitt_aa = (mitte[0] - 20.0, mitte[1] - 2.0, mitte[0] + 20.0, mitte[1] + 4.0)
    texte = [("0,02", (113.0, 102.0, 127.0, 108.0)), ("SCHNITT A-A", schnitt_aa)]
    monkeypatch.setattr(z, "texte", lambda p: texte)
    assert z._anmerkungen_kreuzen({}, [], [a], [], pdf) == ["ANMERKUNG_KREUZT: f1 form_lage „0,02“ – Text (1)"]
    h = type("H", (), {"merkmal": "st", "rolle": "haupt", "zeilen": ("2 × Ø8 H7 E", "15 tief"), "lage": (200.0, 185.0),
                       "rechteck": lambda s: (187.3, 177.1, 221.4, 188.1)})()
    texte[:] = [("2 × Ø8 H7 E", (187.3, 181.6, 221.4, 188.1)), ("15 tief", (187.3, 177.1, 200.8, 183.5)),
                ("16,00", (221.2, 183.1, 235.4, 189.5))]
    meld = z._hinweise_zu_nah({}, [h], [], pdf)
    assert len(meld) == 1 and meld[0].startswith("ANGABE_ZU_NAH: st in haupt – Text „2 × Ø8 H7 E“")
    texte[-1] = ("16,00", (230.0, 183.1, 244.2, 189.5))
    assert z._hinweise_zu_nah({}, [h], [], pdf) == []


# --- Runde D, C: gemeinsame Lagewahl der Anmerkungen einer Ansicht ------------------------------------------------------


from dataclasses import dataclass  # noqa: E402


@dataclass
class _FesteLagen(an.Anmerkung):
    """Anmerkung mit vorgegebenen Kandidatenlagen (Rang = Reihenfolge)."""
    lagen: tuple = ()

    def _roh(self, anker=None, weiter=None):
        return list(self.lagen)


def test_gemeinsame_lagewahl_summe_minimal():
    """Runde D (C): Die einzeln beste Lage von a (A0) liegt auf der Hinweislinie von b, dessen einzige Lage B0 ist; a
    hat noch A1 (selbst ein Verstoß). Nacheinander bleibt a auf A0 (an A1 hätte es genauso viele), b kreuzt – gemeinsam
    ist die Summe minimal: a auf A1, b frei."""
    a = _FesteLagen("rauheit", "a", ("Ra 1,6",), _AnnLage(), "drauf", (125.0, 105.0), (0, 0, 1, 1), (20.0, 10.0),
                    (0.0, 0.0), lagen=((115.0, 115.0), (160.0, 90.0)))
    b = _FesteLagen("rauheit", "b", ("Ra 0,8",), _AnnLage(), "drauf", (100.0, 100.0), (0, 0, 1, 1), (20.0, 10.0),
                    (0.0, 0.0), lagen=((130.0, 130.0),))
    sperre = [((155.0, 80.0), (155.0, 100.0))]                          # quer durch A1
    an.anmerkungen_legen([a, b], sperre)
    assert (a.soll, b.soll) == ((160.0, 90.0), (130.0, 130.0))
    assert an.anmerkungen_pruefen([a, b], sperre) == ["ANMERKUNG_KREUZT: a rauheit „Ra 1,6“ – Rechteck auf Linie (1)"]


def test_gemeinsame_lagewahl_je_ansicht_und_fixiert():
    """Runde D (C): Anmerkungen anderer Ansichten und fixierte (beste Runde) gelten als fest; verworfene Lagen nicht."""
    a = _FesteLagen("rauheit", "a", ("Ra 1,6",), _AnnLage(), "drauf", (125.0, 105.0), (0, 0, 1, 1), (20.0, 10.0),
                    (0.0, 0.0), lagen=((115.0, 115.0), (160.0, 90.0)))
    b = _FesteLagen("rauheit", "b", ("Ra 0,8",), _AnnLage(), "drauf", (100.0, 100.0), (0, 0, 1, 1), (20.0, 10.0),
                    (0.0, 0.0), lagen=((130.0, 130.0),))
    b.fixiert = ((130.0, 130.0), None)
    an.anmerkungen_legen([a, b], [])
    assert a.soll == (160.0, 90.0)                                      # weicht der fixierten b aus
    b.fixiert = None
    a.verworfen = [(160.0, 90.0)]
    an.anmerkungen_legen([a, b], [])
    assert a.soll == (115.0, 115.0)                                     # A1 verworfen: A0, auch wenn b kreuzt


def test_gemeinsame_lagewahl_ueber_die_orte():
    """Runde D (C, live SpannplatteZ): ▱ 0,02 an der Unterseite zwischen den Taschen – unter ihr steht „SCHNITT A-A“,
    jede Lage dort kreuzt. Die gemeinsame Wahl schließt die gleichwertigen Orte ein und hängt an die freie linke Kante
    um (neu eingefügt, alte gelöscht)."""
    mitte = _kante((110.06, 122.56), (140.06, 122.56), features=["f1"])
    links = _kante((75.06, 122.56), (85.06, 122.56), features=["f1"])

    def einhaengen(k, meld=None):
        return _AnnLage(), ((k.a[0] + k.e[0]) / 2, k.a[1])

    a = an.Anmerkung("form_lage", "f1", ("0,02",), _AnnLage(), "drauf", (125.06, 122.56), _UMRISS, (16.0, 7.0),
                     (8.0, -3.5), kante=(mitte.a, mitte.e), orte=[mitte, links], einhaengen=einhaengen)
    sperre = [((float(x), 50.0), (float(x), 200.0)) for x in range(84, 205, 5)]  # alles um die Mitte belegt
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    meld: list = []
    an.anmerkungen_legen([a], sperre, drw=drw, meldungen=meld)
    assert a.instanz() is links and a.kante == (links.a, links.e) and meld == []
    assert an.anmerkungen_pruefen([a], sperre) == []
    ohne = an.Anmerkung("form_lage", "f1", ("0,02",), _AnnLage(), "drauf", (125.06, 122.56), _UMRISS, (16.0, 7.0),
                        (8.0, -3.5), kante=(mitte.a, mitte.e), orte=[mitte, links], einhaengen=einhaengen)
    an.anmerkungen_legen([ohne], sperre)                                # ohne Zeichnung: Ort bleibt, Meldung später
    assert ohne.instanz() is mitte and an.anmerkungen_pruefen([ohne], sperre)


def test_zu_nah_je_zeile(monkeypatch, tmp_path):
    """Runde D (Live SpannplatteZ): „Fase 0,5 × 45°“ endet 3,4 mm vor „16,00“, liegt aber 4,8 mm tiefer; die Zeile auf
    der Höhe von „16,00“ endet 6,9 mm davor. Gemessen wird je Zeile, nicht am umschließenden Rechteck."""
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    h = type("H", (), {"merkmal": "st", "rolle": "haupt", "zeilen": ("2 × Ø8 H7 E", "15 tief", "Fase 0,5 × 45°"),
                       "lage": (200.0, 180.0), "rechteck": lambda s: (187.3, 171.9, 217.8, 187.5)})()
    texte = [("2 × Ø8 H7 E", (187.3, 181.0, 214.3, 187.5)), ("15 tief", (187.3, 176.4, 200.8, 182.8)),
             ("Fase 0,5 × 45°", (187.3, 171.9, 217.8, 178.3)), ("16,00", (221.2, 183.1, 235.4, 189.5))]
    monkeypatch.setattr(z, "texte", lambda p: texte)
    assert z._hinweise_zu_nah({}, [h], [], pdf) == []
    texte[-1] = ("16,00", (221.2, 174.0, 235.4, 180.4))                # auf Höhe der Fase-Zeile: zu nah
    assert len(z._hinweise_zu_nah({}, [h], [], pdf)) == 1


# --- Runde E -----------------------------------------------------------------------------------------------------------


def test_fremde_texte_eigene_woerter_einmal_verbraucht():
    """Runde E (I-2): Jedes Wort der eigenen Zeilen deckt höchstens einen PDF-Text, den nächstgelegenen. Das „A“ der
    Schnittlinie 2 mm neben dem Rahmen „0,05 A“ bleibt fremd, die eigene Zelle „A“ eigen."""
    r = an.Anmerkung("form_lage", "t1", ("0,05 A",), None, "drauf", (0, 0), (0, 0, 1, 1), (26.0, 7.0), (13.0, 0.0),
                     lage=(100.0, 100.0))                              # Rechteck 87…113 × 96,5…103,5
    fremd = (115.0, 97.0, 118.0, 103.0)
    texte = [("A", fremd), ("0,05", (95.0, 97.0, 103.0, 103.0)), ("A", (105.0, 97.0, 108.0, 103.0))]
    assert z._fremde_texte(texte, [r]) == [fremd]
    # ohne die eigene Zelle (pymupdf liefert „0,05 A“ in einem Stück) ist das „A“ daneben fremd
    assert z._fremde_texte([("A", fremd), ("0,05 A", (95.0, 97.0, 108.0, 103.0))], [r]) == [fremd]


def test_fremde_texte_fasenmass_unter_der_angabe_bleibt_fremd():
    """Runde E (I-2): Das Fasenmaß „0,5 × 45°“ 2 mm unter der Zeile „Fase 0,5 × 45°“ ist fremd – die Wörter der
    Zeile hat die Zeile selbst verbraucht (ganze Zeilen zuerst)."""
    h = type("H", (), {"zeilen": ("2 × Ø8 H7 E", "15 tief", "Fase 0,5 × 45°"),
                       "rechteck": lambda s: (187.3, 171.9, 217.8, 187.5)})()
    fase = (190.0, 166.0, 210.0, 170.0)
    texte = [("0,5 × 45°", fase), ("2 × Ø8 H7 E", (187.3, 181.0, 214.3, 187.5)),
             ("15 tief", (187.3, 176.4, 200.8, 182.8)), ("Fase 0,5 × 45°", (187.3, 171.9, 217.8, 178.3))]
    assert z._fremde_texte(texte, [h]) == [fase]
    # geschätztes Rechteck (unvermessen, 3 mm daneben): die ganze Zeile gewinnt trotzdem gegen das nähere Fasenmaß
    h.rechteck = lambda: (187.3, 165.0, 217.8, 181.5)
    assert z._fremde_texte(texte, [h]) == [fase]


def test_fremde_texte_je_text_hoechstens_eine_anmerkung():
    """Zwei Rauheiten „Ra 0,8“ nebeneinander und drei PDF-Texte „Ra 0,8“: zwei sind eigen (je der nächste), der dritte
    fremd; Symbolzeichen ohne Wörter bleiben bei Nähe eigen."""
    a = an.Anmerkung("rauheit", "b1", ("Ra 0,8",), None, "drauf", (0, 0), (0, 0, 1, 1), (20.0, 8.0), (0.0, 0.0),
                     lage=(100.0, 100.0))
    b = an.Anmerkung("rauheit", "b2", ("Ra 0,8",), None, "drauf", (0, 0), (0, 0, 1, 1), (20.0, 8.0), (0.0, 0.0),
                     lage=(130.0, 100.0))
    dritte = (112.0, 105.0, 118.0, 107.0)
    texte = [("Ra 0,8", dritte), ("Ra 0,8", (95.0, 97.0, 105.0, 103.0)), ("Ra 0,8", (125.0, 97.0, 135.0, 103.0)),
             ("×", (110.0, 96.0, 111.0, 97.0))]
    assert z._fremde_texte(texte, [a, b]) == [dritte]


def test_paar_ueberspringt_getrennte_huellen_gleichwertig():
    """Runde E (Punkt 6): Liegen die Hüllen zweier Kandidaten (Rechteck samt Linien) weiter als `ANSATZ_ABSTAND_MM`
    auseinander, zählt das Paar nichts – `_paar_kosten` überspringt die Rechnung und kommt auf dasselbe wie `_paar` in
    beide Richtungen; Schraffur und eigenes Symbol rechnet `_paar` gar nicht."""
    import random

    zufall = random.Random(5)
    k1, k2 = _kante((80.0, 100.0), (120.0, 100.0)), _kante((140.0, 100.0), (180.0, 100.0))
    arten = [("rauheit", (20.0, 10.0), (9.0, 5.0), None), ("form_lage", (26.0, 7.0), (13.0, -3.5), None),
             ("bezug", (7.0, 7.0), (0.0, 0.0), (k2.a, k2.e))]
    getrennt = 0
    for _ in range(300):
        art, g, v, kante = zufall.choice(arten)
        a = an.Anmerkung(art, "a", ("x",), None, "drauf", (zufall.uniform(80, 120), 100.0), _UMRISS, g, v,
                         kante=kante, schraffur=_SCHNITT)
        b = an.Anmerkung("rauheit", "b", ("y",), None, "drauf", (zufall.uniform(140, 180), 100.0), _UMRISS,
                         (20.0, 10.0), (9.0, 5.0), schraffur=_SCHNITT)
        la, lb = zufall.choice(a._roh()), zufall.choice(b._roh())
        voll = an._paar(a, la, b, lb) + an._paar(b, lb, a, la)
        assert an._paar_kosten(a, la, an._huelle(a, la), b, lb, an._huelle(b, lb)) == voll
        getrennt += an._getrennt(an._huelle(a, la), an._huelle(b, lb))
        if an._getrennt(an._huelle(a, la), an._huelle(b, lb)):
            assert voll == 0
    assert 30 < getrennt < 290                                       # beide Fälle kommen vor


def test_paar_rechnet_schraffur_und_symbol_nicht(monkeypatch):
    a = an.Anmerkung("rauheit", "a", ("x",), None, "drauf", (100.0, 100.0), _UMRISS, (20.0, 10.0), (9.0, 5.0),
                     schraffur=_SCHNITT)
    monkeypatch.setattr(an.Anmerkung, "_durch_schraffur", lambda *x: pytest.fail("Schraffur gerechnet"))
    monkeypatch.setattr(an.Anmerkung, "_durch_symbol", lambda *x: pytest.fail("Symbol gerechnet"))
    an._paar(a, a._roh()[0], a, a._roh()[1])


def _runden_probe():
    """Probe des Reviewers (Runde D): Rauheit an k1, Bohrungsangabe desselben Merkmals an k1 mit einer Hinweislinie,
    die die Linie einer Lage an k2 quert."""
    k1 = _kante((103.0, 100.0), (103.0, 100.0), ((100.0, 100.0), 3.0))
    k2 = _kante((203.0, 100.0), (203.0, 100.0), ((200.0, 100.0), 3.0))
    umriss = (80.0, 80.0, 220.0, 120.0)
    zaehler = {"einhaengen": 0}

    def einhaengen(k, meld=None):
        zaehler["einhaengen"] += 1
        return _AnnLage(), an.ansatzpunkt(k, [k], [], umriss)

    lage = (150.0, 160.0)

    @dataclass
    class _Fest(an.Anmerkung):
        lagen: tuple = ()

        def _roh(self, anker=None, weiter=None):
            return list(self.lagen)

    a = _Fest("rauheit", "b1", ("Ra 0,8",), _AnnLage(), "drauf", an.ansatzpunkt(k1, [k1], [], umriss), umriss,
              (2.0, 2.0), (0.0, 0.0), orte=[k1, k2], einhaengen=einhaengen, belegt=[], lagen=(lage,))
    p2 = an.ansatzpunkt(k2, [k2], [], umriss)
    m = (p2[0] + (lage[0] - p2[0]) * 0.3, p2[1] + (lage[1] - p2[1]) * 0.3)
    d = (lage[0] - p2[0], lage[1] - p2[1])
    n = (-d[1] / math.hypot(*d), d[0] / math.hypot(*d))
    linie = ((m[0] - 3 * n[0], m[1] - 3 * n[1]), (m[0] + 3 * n[0], m[1] + 3 * n[1]))
    return a, k1, k2, zaehler, (30.0, 35.0, 50.0, 45.0), linie


def test_umhaengen_springt_nicht_je_runde():
    """Runde E (I-3, Probe des Reviewers): Über mehrere Runden der Lesbarkeitsschleife wählt allein `_gemeinsam` den
    Ort – die Hinweislinie der Angabe an k2 zählt, die Rauheit bleibt an k1, keine Einfügung in irgendeiner Runde
    (Runde D: jede Runde k1 → k2 → k1, zwei Einfügungen)."""
    a, k1, _, zaehler, rechteck, linie = _runden_probe()
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    for _ in range(4):
        gelegt = an._rechteck_strecken(rechteck) + [linie]
        an.instanzen_umhaengen(drw, [a], [])                           # ohne fixierte Runde: nichts
        assert a.instanz() is k1
        an.anmerkungen_legen([a], gelegt, [rechteck], [], [], [linie], drw, [], {"b1": [k1.kreis[0]]})
        assert a.instanz() is k1
    assert zaehler["einhaengen"] == 0


def test_umhaengen_hoechstens_einmal_ueber_runden():
    """Runde E (I-3): Ist der heutige Ort gesperrt, wird einmal umgehängt; die folgenden Runden bleiben dort."""
    links = _kante((75.06, 122.56), (85.06, 122.56), features=["f1"])
    rechts = _kante((165.06, 122.56), (175.06, 122.56), features=["f1"])
    zaehler = {"n": 0}

    def einhaengen(k, meld=None):
        zaehler["n"] += 1
        return _AnnLage(), ((k.a[0] + k.e[0]) / 2, k.a[1])

    a = an.Anmerkung("form_lage", "f1", ("0,02",), _AnnLage(), "drauf", (80.06, 122.56), _UMRISS, (16.0, 7.0),
                     (8.0, -3.5), kante=(links.a, links.e), orte=[links, rechts], einhaengen=einhaengen)
    sperre = [((float(x), 50.0), (float(x), 200.0)) for x in range(20, 145, 5)]
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    for _ in range(4):
        an.anmerkungen_legen([a], sperre, drw=drw, meldungen=[])
        assert a.instanz() is rechts
    assert zaehler["n"] == 1


def test_verworfen_bleibt_je_ort():
    """Runde E (I-3): Verwerfungen aus dem PDF bleiben am Ort, auch über das Umhängen; keine Lage kommt zweimal, und
    `verwerfen()` meldet erst False, wenn an allen Orten alles verworfen ist (Runde D: Umhängen leerte die Liste,
    `verwerfen()` meldete immer „umgesetzt“)."""
    k1 = _kante((103.0, 100.0), (103.0, 100.0), ((100.0, 100.0), 3.0))
    k2 = _kante((203.0, 100.0), (203.0, 100.0), ((200.0, 100.0), 3.0))
    umriss = (80.0, 80.0, 220.0, 120.0)
    zaehler = {"n": 0}

    def einhaengen(k, meld=None):
        zaehler["n"] += 1
        return _AnnLage(), an.ansatzpunkt(k, [k], [], umriss)

    a = an.Anmerkung("rauheit", "b1", ("Ra 0,8",), _AnnLage(), "drauf", an.ansatzpunkt(k1, [k1], [], umriss), umriss,
                     (20.0, 10.0), (9.0, 5.0), orte=[k1, k2], einhaengen=einhaengen, belegt=[])
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    gesehen = set()
    for runde in range(200):
        an.anmerkungen_legen([a], [], drw=drw, meldungen=[])
        schluessel = (a.ort_nr(a.instanz()), a.soll)
        assert schluessel not in gesehen, runde
        gesehen.add(schluessel)
        if not a.verwerfen():
            break
    assert len(gesehen) == 2 * len(a._roh()) and {o for o, _ in gesehen} == {0, 1}
    assert zaehler["n"] <= 2


def test_rahmen_nach_umhaengen_beschriftet_keine_meldung(monkeypatch):
    """Runde E (M7-Rest): Der erste Rahmen bleibt unbeschriftet, der umgehängte ist beschriftet – keine Meldung
    „Rahmen nicht beschriftet“, weder aus `form_lage_setzen` noch im Endstand."""
    v = _View("Zeichenansicht2")
    k1 = _kante((103.0, 100.0), (103.0, 100.0), ((100.0, 100.0), 3.0), features=["b1"])
    k2 = _kante((203.0, 100.0), (203.0, 100.0), ((200.0, 100.0), 3.0), features=["b1"])
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: [k1, k2])
    monkeypatch.setattr(an, "schraffur_strecken", lambda mu, view: ([], []))

    class _Gt:
        def __init__(self, wirkt):
            self.wirkt, self.sym, self.werte = wirkt, (), ()

        def SetFrameSymbols2(self, i, symbol, *rest):
            self.sym = (symbol,)
            return False

        def SetFrameValues2(self, i, *werte):
            self.werte = werte if self.wirkt else ()
            return False

        def GetFrameSymbols2(self, i):
            return self.sym

        def GetFrameValues(self, i):
            return self.werte

        def GetAnnotation(self):
            return _AnnLage()

    gts = [_Gt(False), _Gt(True)]
    drw = _Drw(v)
    drw.InsertGtol = lambda: gts.pop(0)
    drw.Extension.DeleteSelection2 = lambda o: True
    fl = FormLage("b1", "position", "<IGTOL-POSI>", "0,05", ("A",), False)
    m = Mass("b1:form_lage:0", "form_lage", "form_lage", 0.0, "b1", text="0,05", achse=2, modus="flach", form_lage=fl)
    anm: list = []
    meld = an.form_lage_setzen(drw, None, {"drauf": v}, [m], {"drauf": 2}, {"b1": "bohrung"}, anmerkungen=anm)
    assert meld == [] and len(anm) == 1 and an.anmerkungen_wirkung(anm)    # erster Rahmen: unbeschriftet
    a = anm[0]
    heute = a.instanz()
    mx = heute.kreis[0][0]
    sperre = [((mx + dx, 0.0), (mx + dx, 300.0)) for dx in range(-60, 61, 4)]  # alles um den heutigen Ort belegt
    an.anmerkungen_legen(anm, sperre, drw=drw, meldungen=meld)
    assert a.instanz() is not heute and meld == [] and an.anmerkungen_wirkung(anm) == []


def test_lage_der_letzten_runde_bleibt_kandidat():
    """Runde E (live SpannplatteZ): Nach dem Umhängen setzt die Hinweislinie anders an, als die Probe am Ort annahm; die
    gewählte Lage liegt dann nicht mehr unter den Lagen um den wirklichen Ansatz. Sie bleibt am heutigen Ort Kandidat
    (sonst wählte die nächste Runde eine schlechtere Lage: Ra 1,6 mit Hinweislinie durch das eigene Symbol)."""
    a = an.Anmerkung("rauheit", "t1", ("Ra 1,6",), _AnnLage(), "drauf", (100.0, 100.0), _UMRISS, (20.0, 10.0),
                     (9.0, 5.0))
    frei = (150.0, 40.0)
    assert all(math.dist(frei, lage) > 1 for lage in a._roh())
    sperre = [((0.0, 50.0 + y), (300.0, 50.0 + y)) for y in range(0, 100, 3)]  # alle Lagen um den Anker belegt
    assert a.bewerten(frei, sperre) == 0 and min(a.bewerten(lage, sperre) for lage in a._roh()) > 0
    a.soll = frei
    an.anmerkungen_legen([a], sperre)
    assert a.soll == frei
    a.verwerfen()                                                     # verworfen: kein Kandidat mehr
    an.anmerkungen_legen([a], sperre)
    assert a.soll != frei


# --- Gesamtreview (b): Umhängen -------------------------------------------------------------------------------------

def _zwei_orte(einhaengen):
    links = _kante((75.06, 122.56), (85.06, 122.56), features=["f1"])
    rechts = _kante((165.06, 122.56), (175.06, 122.56), features=["f1"])
    a = an.Anmerkung("form_lage", "f1", ("0,02",), _AnnLage(), "drauf", (80.06, 122.56), _UMRISS, (16.0, 7.0),
                     (8.0, -3.5), kante=(links.a, links.e), orte=[links, rechts], einhaengen=einhaengen)
    drw = _Drw(_View())
    drw.Extension.DeleteSelection2 = lambda o: True
    return a, links, rechts, drw


def test_umhaengen_leert_die_gewaehlte_lage():
    """`soll` gehört zum alten Ort; nach dem Umhängen wäre es dort ein falscher Kandidat."""
    a, _, rechts, drw = _zwei_orte(lambda k, meld=None: (_AnnLage(), ((k.a[0] + k.e[0]) / 2, k.a[1])))
    a.soll = (90.0, 140.0)
    assert an._umhaengen(drw, a, rechts, []) is True
    assert a.instanz() is rechts and a.soll is None


def test_fixierte_lage_verfaellt_wenn_umhaengen_scheitert():
    """Scheitert das Umhängen an den Ort der besten Runde, gilt deren Lage nicht am alten Anker."""
    a, links, rechts, drw = _zwei_orte(lambda k, meld=None: None)
    a.fixiert = ((170.0, 140.0), rechts)
    meld: list = []
    an.instanzen_umhaengen(drw, [a], meld)
    assert a.instanz() is links and a.fixiert is None
    assert any(m.startswith("ANMERKUNG_NICHT_UMGEHAENGT") for m in meld)
