"""Zeichnungsableitung Z1.3 Stufe 4 Task 5: Anforderungen in die Zeichnung, ohne SolidWorks (Fake-COM).

Meldungswege (Plan Task 5 Step 1): Punkt ohne Kante, neuer Wert weicht ab, Rauheitskante fehlt, Rahmen nicht erzeugt;
`toleranz_setzen` (Passung → Typ 7, Abmaße → SetValues, Hülle → Suffix <MOD-EP>)."""

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

        self.Extension = type("E", (), {"DeleteSelection2": loeschen})()

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
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – keine sichtbare Kante am Bezugspunkt (110.0, 246.5)"]


def test_neuer_wert_weicht_ab_neues_geloescht(monkeypatch):
    v = _View()
    alt = _DD(v, "D3@m1", 30.0, _HILFSLINIEN)
    v.masse.append(alt)
    drw = _Drw(v, neu_wert=30.5)
    monkeypatch.setattr(an, "sichtbare_kanten", lambda mu, view: _KREISE)
    namen, meld = an.dauerhaft_machen(drw, None, {"haupt": v}, [_plan_mass()])
    assert namen == {} and v.masse == [alt]
    assert meld == ["MASS_NICHT_DAUERHAFT: D3@m1 – neues Maß misst 30.5 statt 30.0"]


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
    assert meld == ["FORM_LAGE_NICHT_GESETZT: t1 parallelitaet 0,05 – InsertGtol abgelehnt"]
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
                    "(110.0, 246.5)"]


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
                    "steht doppelt"]


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
    assert len(a._roh()) == 16                                       # nicht mehr fest 16 (M4), sondern die Lagen


def test_rauheit_ohne_ansicht_ehrlich_gemeldet():
    """M4: Ohne Ansicht passender Blickachse heißt die Meldung so, nicht „keine passende Kante“."""
    m = Mass("t1:rauheit", "rauheit", "rauheit", 0.0, "t1", text="Ra 1,6", achse=None, modus=None)
    assert an.rauheit_setzen(_Drw(_View()), None, {"haupt": _View()}, [m], {"haupt": 1}, {"t1": "schnitt"}) == [
        "RAUHEIT_NICHT_GESETZT: t1 Ra 1,6 – keine Ansicht mit passender Blickachse (Achse unbekannt)"]
