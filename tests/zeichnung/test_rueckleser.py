"""Reine Teile des Rücklesers (Plan Z1.4 Task 4b): Toleranz, Maßart, Instanzzahl, Blattformat, Sichtbarkeit."""

from pathlib import Path

import pytest

from swki.zeichnung import rueckleser as rl
from swki.zeichnung.anforderungen_setzen import Kante
from swki.zeichnung.ist import Ist, IstToleranz
from swki.zeichnung.zeichnen import ZeichnungFehler


def _gerade(a, e):
    return Kante(None, a, e, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def _kreis(m, r):
    return Kante(None, (m[0] + r, m[1]), (m[0] + r, m[1]), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), kreis=(m, r))


# --- Toleranz ---------------------------------------------------------------------------------------------------------

def test_toleranz_symmetrisch_mit_vorzeichen():
    """Review Task 3 (M2): ±0,02 ergibt oben 0,02, unten −0,02 in mm."""
    t = rl.toleranz(4, -2e-05, 2e-05, "", "")
    assert t.typ == "symmetrisch" and abs(t.oben - 0.02) < 1e-9 and abs(t.unten + 0.02) < 1e-9


def test_toleranz_arten():
    assert rl.toleranz(0, 0.0, 0.0, "", "") == IstToleranz("keine", None, None, None)
    assert rl.toleranz(2, -5e-05, 1e-04, "", "").typ == "bilateral"
    assert rl.toleranz(3, -5e-05, 1e-04, "", "").typ == "grenz"
    bohrung = rl.toleranz(7, 0.0, 2.1e-05, "H7", "")
    assert bohrung.typ == "passung" and bohrung.passung == "H7"
    assert rl.toleranz(7, 2e-06, 1.8e-05, "", "k6").passung == "k6"
    assert rl.toleranz(8, 0.0, 2.1e-05, "H7", "").passung == "H7"


def test_toleranz_unbekannt_nie_keine():
    """Ein unbekannter swTolType darf nie „keine“ werden (sonst ginge Z-TOL-3 verloren)."""
    for typ in (1, 5, 6, 9, 10, 11, 99):
        t = rl.toleranz(typ, 0.0, 0.0, "", "")
        assert t.typ not in ("keine", "bilateral", "grenz", "symmetrisch", "passung") and str(typ) in t.typ


def test_passung_ohne_text_bleibt_passung():
    assert rl.toleranz(7, 0.0, 0.0, "", "").passung is None


# --- Maßart -----------------------------------------------------------------------------------------------------------

def test_massart():
    assert rl.massart(2, "", " 200,00 ") == "laenge"
    assert rl.massart(11, "4 × ", " 4 × 30,00 (= 120) ") == "laenge"
    assert rl.massart(2, "<MOD-DIAM>", " <MOD-DIAM>50,00 ") == "durchmesser"   # Längsschnitt der Buchse
    assert rl.massart(6, "", " <MOD-DIAM>8,00 ") == "durchmesser"
    assert rl.massart(15, "", "") == "durchmesser"
    assert rl.massart(5, "R", " R4,00 ") == "radius"
    assert rl.massart(14, "", "") == "radius"
    assert rl.massart(3, "", " 90° ") == "winkel"
    assert rl.massart(1, "", "") is None and rl.massart(10, "", "") is None


def test_praefix_mit_durchmesser_aus_der_anzeige():
    """Ein Ø-Maß zeigt das Zeichen auch ohne Präfixtext (Z-DRE-1 prüft, was das Rücklesen sieht)."""
    assert rl.praefix("durchmesser", "", " <MOD-DIAM>8,00 ") == "Ø"
    assert rl.praefix("durchmesser", "<MOD-DIAM>", " <MOD-DIAM>50,00 ") == "<MOD-DIAM>"
    assert rl.praefix("durchmesser", "2 × ", " 2 × Ø8,00 ") == "2 × Ø"
    assert rl.praefix("durchmesser", "", " 8,00 ") == ""
    assert rl.praefix("laenge", "4 × ", " 4 × 30,00 ") == "4 × "


# --- Instanzzahl, Blatt, Rauheitstext ---------------------------------------------------------------------------------

def test_anzahl_ueber_dem_rahmen():
    assert rl.anzahl("2 ×") == 2 and rl.anzahl(" 12 × ") == 12 and rl.anzahl("3x") == 3
    assert rl.anzahl("") is None and rl.anzahl(None) is None and rl.anzahl("ALLE") is None


def test_format_und_massstab():
    assert rl.format_name(420.0, 297.0) == "A3quer" and rl.format_name(210.0, 297.0) == "A4"
    assert rl.format_name(594.0, 420.0) == "594×420"
    assert rl.massstab_text(1.0, 2.0) == "1:2" and rl.massstab_text(2.0, 1.0) == "2:1"
    assert rl.massstab_text(1.0, 2.5) == "1:2,5"


def test_rauheitstext_feld_c_weicht_ab():
    """Nachtrag: Text in Feld c (Fertigungsverfahren) statt Feld a ist „weicht ab“."""
    assert rl.rauheitstext("Ra 0,8", "") == "Ra 0,8"
    assert rl.rauheitstext("Ra 0,8", "geschliffen") == "Ra 0,8 (Feld c: geschliffen)"
    assert rl.rauheitstext("", "Ra 0,8") == "(Feld c: Ra 0,8)"


# --- Sichtbarkeit (`verdeckt`) ---------------------------------------------------------------------------------------

def test_verdeckt_beide_punkte_auf_kanten():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0)), _gerade((50.0, 0.0), (50.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((50.0, 21.0), (50.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (50.0, 20.0)], "h", linien, kanten, [], 1.0) is False


def test_verdeckt_punkt_ohne_kante():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((30.0, 21.0), (30.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (30.0, 20.0)], "h", linien, kanten, [], 1.0) is True


def test_verdeckt_mittellinie_zaehlt():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0))]
    mitte = [((30.0, -3.0), (30.0, 23.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((30.0, 11.0), (30.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (30.0, 10.0)], "h", linien, kanten, mitte, 0.5) is False


def test_verdeckt_virtuelle_fasenecke():
    """Dieselbe Streckenregel wie `kante_am_punkt`: 0,5 mm über das Kantenende hinaus (Fase 0,5 × 45°, 1:1) ist
    sichtbar; mit nur 0,1 mm Toleranz entstünde ein falscher Mangel „ohne sichtbaren Bezug“."""
    kanten = [_gerade((0.0, 0.0), (0.0, 19.5)), _gerade((40.0, 0.0), (40.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((40.0, 21.0), (40.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (40.0, 20.0)], "h", linien, kanten, [], 1.0) is False
    assert rl.verdeckt([(0.0, 21.5), (40.0, 20.0)], "h", linien, kanten, [], 1.0) is True


def _tasche_r4():
    """Live 28.11. (SpannplatteZ, Einzelheit Z 1:1): Ecke der Tasche 50 × 30 mit R4 – gerade Kanten enden 4 mm vor der
    gedachten scharfen Ecke (306,88 | 209,44), der Bogen verbindet ihre Enden."""
    return [_gerade((306.88, 235.44), (306.88, 213.44)), _gerade((310.88, 209.44), (352.88, 209.44)),
            Kante(None, (306.88, 213.44), (310.88, 209.44), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  kreis=((310.88, 213.44), 4.0)),
            _gerade((356.88, 213.44), (356.88, 235.44)),
            Kante(None, (352.88, 209.44), (356.88, 213.44), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  kreis=((352.88, 213.44), 4.0))]


def test_verdeckt_gedachte_scharfe_ecke():
    """Maß 50 der gerundeten Tasche setzt an der gedachten scharfen Ecke an: Schnittpunkt der Geraden zweier
    sichtbarer Kanten, deren Enden ein sichtbarer Bogen (oder eine Fasenkante) verbindet – sichtbarer Bezug
    (wie `mittellinien.ohne_kante`, „gedachte scharfe Ecke“, Live 19.11.)."""
    kanten = _tasche_r4()
    linien = [((306.88, 208.44), (306.88, 193.44)), ((356.88, 208.44), (356.88, 193.44))]
    assert rl.verdeckt([(306.88, 209.44), (356.88, 209.44)], "h", linien, kanten, [], 1.0) is False
    assert rl.virtuelle_ecke((306.88, 209.44), kanten) and rl.virtuelle_ecke((356.88, 209.44), kanten)


def test_keine_gedachte_ecke_ohne_verbindung():
    """Zwei Geraden schneiden sich im Punkt, aber nichts Sichtbares verbindet ihre Enden: kein Bezug (sonst wäre
    jeder Schnittpunkt zweier Kantenverlängerungen sichtbar)."""
    kanten = [k for k in _tasche_r4() if not k.kreis]
    assert not rl.virtuelle_ecke((306.88, 209.44), kanten)
    linien = [((306.88, 208.44), (306.88, 193.44)), ((356.88, 208.44), (356.88, 193.44))]
    assert rl.verdeckt([(306.88, 209.44), (356.88, 209.44)], "h", linien, kanten, [], 1.0) is True


def test_verdeckt_kreismitte():
    kanten = [_kreis((10.0, 10.0), 4.0), _gerade((0.0, 0.0), (0.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((10.0, 15.0), (10.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (10.0, 10.0)], "h", linien, kanten, [], 1.0) is False


# --- gedachte scharfe Ecke: nur gebrochene Ecken (Review 4b, M1) ------------------------------------------------------

def _trapez():
    """Probe des Reviews (trapez.py): Trapez mit Deckkante; die Verlängerungen der Seiten treffen sich 80 mm über der
    Deckkante – dort ist keine gedachte scharfe Ecke, die Deckkante ist eine Fläche, keine Fase."""
    return [_gerade((0.0, 0.0), (10.0, 20.0)), _gerade((100.0, 0.0), (90.0, 20.0)), _gerade((0.0, 0.0), (100.0, 0.0)),
            _gerade((10.0, 20.0), (90.0, 20.0))]


def test_trapez_spitze_keine_gedachte_ecke():
    kanten = _trapez()
    assert not rl.virtuelle_ecke((50.0, 100.0), kanten)
    linien = [((50.0, 101.0), (50.0, 110.0)), ((100.0, 1.0), (100.0, 110.0))]
    assert rl.verdeckt([(50.0, 100.0), (100.0, 0.0)], "h", linien, kanten, [], 1.0) is True


def test_gedachte_ecke_einer_fase():
    """Fase 1 × 45° an einer rechtwinkligen Ecke: die Fasenkante verbindet die Enden – gedachte scharfe Ecke."""
    kanten = [_gerade((0.0, 0.0), (0.0, 19.0)), _gerade((1.0, 20.0), (40.0, 20.0)), _gerade((0.0, 19.0), (1.0, 20.0))]
    assert rl.virtuelle_ecke((0.0, 20.0), kanten)


def test_lange_verbindung_keine_gedachte_ecke():
    """Eine gerade Verbindung weiter als `mittellinien.ECKE_MM` von der Ecke (Rechteck mit 10 mm abgeschnittener Ecke)
    ist eine Fläche des Teils, keine gebrochene Kante – auch wenn sie im Verhältnis kurz genug für eine Fase wäre."""
    kanten = [_gerade((0.0, 0.0), (0.0, 10.0)), _gerade((10.0, 20.0), (40.0, 20.0)), _gerade((0.0, 10.0), (10.0, 20.0))]
    assert not rl.virtuelle_ecke((0.0, 20.0), kanten)


def test_bogen_muss_tangential_sein():
    """Ein Bogen zählt nur als Verrundung, wenn er beide Geraden in ihren Enden berührt (Mitte im Abstand r von
    beiden Geraden); ein beliebiger Bogen zwischen den Enden ist keine gebrochene Ecke."""
    kanten = [k for k in _tasche_r4() if not k.kreis]
    schief = Kante(None, (306.88, 213.44), (310.88, 209.44), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                   kreis=((330.0, 230.0), 30.5))
    assert not rl.virtuelle_ecke((306.88, 209.44), kanten + [schief])


# --- Sichtbarkeit linearer Maße (Review 4b, M3) ----------------------------------------------------------------------

def test_linear_ohne_hilfslinien_wird_gemeldet():
    """Jedes lineare Maß (auch ein Ø-Maß des Längsschnitts) ohne lesbare Hilfslinien: `verdeckt` None und eine
    Meldung – nie still ungeprüft."""
    for art in ("laenge", "durchmesser"):
        assert rl.lage_des_masses(2, art, None, [], [], 1.0) == (None, None, None, True), art
    assert rl.lage_des_masses(6, "durchmesser", None, [], [], 1.0) == (None, None, None, False)  # kein Linearmaß
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0)), _gerade((50.0, 0.0), (50.0, 20.0))]
    h = ("h", [((0.0, 21.0), (0.0, 30.0)), ((50.0, 21.0), (50.0, 30.0))], [(0.0, 20.0), (50.0, 20.0)])
    assert rl.lage_des_masses(2, "durchmesser", h, kanten, [], 1.0) == (None, None, False, False)
    assert rl.lage_des_masses(2, "laenge", h, kanten, [], 1.0) == ("h", ((0.0, 20.0), (50.0, 20.0)), False, False)


# --- COM-Teile mit Attrappen (Review 4b, I2, M4, M5) ---------------------------------------------------------------

class _Feature:
    def __init__(self, name):
        self.Name = name


class _Flaeche:
    def __init__(self, name):
        self._f = _Feature(name)

    def GetFeature(self):
        return self._f


class _KanteCom:
    def __init__(self, *namen):
        self._fl = [_Flaeche(n) for n in namen]

    def GetTwoAdjacentFaces2(self):
        return self._fl


class _Ann:
    def __init__(self, typen=(), objekte=(), fehler=False):
        self._typen, self._objekte, self._fehler = list(typen), list(objekte), fehler

    def GetAttachedEntityTypes(self):
        if self._fehler:
            raise RuntimeError("COM")
        return self._typen

    def GetAttachedEntities3(self):
        return self._objekte


class _Rauheit:
    def __init__(self, text, ann, naechstes=None):
        self._text, self._ann, self._n = text, ann, naechstes

    def GetText(self, feld):
        return self._text if feld == rl.SF_FELD_A else ""

    def GetAnnotation(self):
        return self._ann

    def GetNext(self):
        return self._n


class _Rahmen:
    def __init__(self, fehler=False):
        self._fehler = fehler

    def GetFrameValues(self, _):
        if self._fehler:
            raise RuntimeError("COM")
        return ["0,05", "", "A", "", ""]

    def GetFrameSymbols2(self, _):
        return ["<IGTOL-PARA>"]

    def GetText(self, _):
        return ""

    def GetAnnotation(self):
        return _Ann([rl.KANTE], [_KanteCom("t1")])

    def GetNextGTOL(self):
        return None


class _Notiz:
    def __init__(self, text):
        self._text = text

    def GetText(self):
        return self._text

    def GetAnnotation(self):
        return _Ann()


class _Ansicht:
    def __init__(self, notizen=(), rahmen=None, rauheit=None):
        self._notizen, self._rahmen, self._rauheit = list(notizen), rahmen, rauheit

    def GetNotes(self):
        return self._notizen

    def GetFirstGTOL(self):
        return self._rahmen

    def GetFirstDatumTag(self):
        return None

    def GetFirstSFSymbol(self):
        return self._rauheit


def test_anforderung_ohne_kante_wird_gemeldet():
    """Review 4b (I2): Rauheit ohne angehängte Kante (Ausnahme, Fläche statt Kante) ist RUECKLESEN_UNVOLLSTAENDIG; ein
    Sammelhinweis ohne Anhängung bleibt still."""
    meldungen = []
    an_kante = _Rauheit("Ra 0,8", _Ann([rl.KANTE], [_KanteCom("st", "st_fase")]))
    an_flaeche = _Rauheit("Ra 1,6", _Ann([2], [object()]), an_kante)
    fehler = _Rauheit("Ra 3,2", _Ann(fehler=True), an_flaeche)
    aus = rl._angaben(_Ansicht([_Notiz("ISO 8015")], rauheit=fehler), "Zeichenansicht1", meldungen)
    assert [(a.art, a.text, a.features) for a in aus] == [
        ("hinweis", "ISO 8015", ()), ("rauheit", "Ra 3,2", ()), ("rauheit", "Ra 1,6", ()),
        ("rauheit", "Ra 0,8", ("st", "st_fase"))]
    assert meldungen == ["RUECKLESEN_UNVOLLSTAENDIG: Zeichenansicht1 – rauheit „Ra 3,2“ ohne angehängte Kante",
                         "RUECKLESEN_UNVOLLSTAENDIG: Zeichenansicht1 – rauheit „Ra 1,6“ ohne angehängte Kante"]


def test_angaben_com_fehler_wird_gemeldet():
    """Review 4b (M4): ein unlesbarer Toleranzrahmen ist eine Meldung, kein roher COM-Fehler; der Rest wird gelesen."""
    meldungen = []
    rauheit = _Rauheit("Ra 0,8", _Ann([rl.KANTE], [_KanteCom("st")]))
    aus = rl._angaben(_Ansicht(rahmen=_Rahmen(fehler=True), rauheit=rauheit), "v", meldungen)
    assert [a.art for a in aus] == ["rauheit"]
    assert meldungen == ["RUECKLESEN_UNVOLLSTAENDIG: v – Toleranzrahmen nicht lesbar (RuntimeError)"]
    meldungen = []
    aus = rl._angaben(_Ansicht(rahmen=_Rahmen()), "v", meldungen)
    assert [(a.art, a.symbol, a.wert, a.bezug, a.features) for a in aus] == [
        ("form_lage", "<IGTOL-PARA>", "0,05", ("A",), ("t1",))] and meldungen == []


class _Dok:
    def __init__(self, pfad):
        self.GetPathName = pfad
        self.GetTitle = pfad.replace("\\", "/").rsplit("/", 1)[-1]


class _App:
    """SolidWorks-Attrappe: `OpenDoc6` lädt `laedt` (Zeichnung zuerst), `CloseDoc` schließt nach Titel."""

    def __init__(self, offen=(), laedt=("C:/arbeit/z.SLDDRW", "C:/arbeit/teil.SLDPRT"), oeffnen_fehler=None,
                 schliessen_scheitert=()):
        self.docs = [_Dok(p) for p in offen]
        self.laedt, self.oeffnen_fehler, self.scheitert = laedt, oeffnen_fehler, set(schliessen_scheitert)
        self.geschlossen = []

    @property
    def GetDocuments(self):
        return list(self.docs)

    def OpenDoc6(self, pfad, typ, optionen, konfiguration, fehler, warnungen):
        neu = [_Dok(p) for p in self.laedt]
        self.docs += neu
        if self.oeffnen_fehler:
            raise self.oeffnen_fehler
        return neu[0]

    def CloseDoc(self, titel):
        if titel in self.scheitert:
            raise RuntimeError("COM")
        self.geschlossen.append(titel)
        self.docs = [d for d in self.docs if d.GetTitle != titel]


def _leeres_ist(meldungen=()):
    return Ist("A3quer", "1:1", (), (), (), {}, "", tuple(meldungen))


def _code(aufruf) -> str:
    with pytest.raises(ZeichnungFehler) as e:
        aufruf()
    return e.value.daten["code"]


def test_schliesst_nur_selbst_geladenes(monkeypatch):
    """Review 4b (M4): geschlossen werden Zeichnung und Teil, die `OpenDoc6` geladen hat – nicht ein Dokument, das
    während des Lesens dazukam (jemand anderes, oder ein spät nachgeladenes Teil), und nicht, was vorher offen war.
    Was während des Lesens dazukam, wird gemeldet, nie still."""
    app = _App(offen=("C:/anders/offen.SLDPRT",))
    monkeypatch.setattr(rl, "_lies", lambda *a: _leeres_ist())
    ist = rl.lies_zeichnung(Path("C:/arbeit/z.SLDDRW"), {}, app=app)
    assert app.geschlossen == ["z.SLDDRW", "teil.SLDPRT"] and ist.meldungen == ()
    assert [d.GetTitle for d in app.docs] == ["offen.SLDPRT"]

    app = _App(offen=("C:/anders/offen.SLDPRT",))

    def lies(app_, drw, rollen):
        app_.docs.append(_Dok("C:/anders/fremd.SLDPRT"))
        return _leeres_ist()

    monkeypatch.setattr(rl, "_lies", lies)
    ist = rl.lies_zeichnung(Path("C:/arbeit/z.SLDDRW"), {}, app=app)
    assert app.geschlossen == ["z.SLDDRW", "teil.SLDPRT"]
    assert [d.GetTitle for d in app.docs] == ["offen.SLDPRT", "fremd.SLDPRT"]
    assert ist.meldungen == ("RUECKLESEN_NICHT_GESCHLOSSEN: fremd.SLDPRT kam während des Lesens dazu – offen gelassen "
                             "(nicht sicher selbst geladen)",)


def test_oeffnen_scheitert_schliesst_trotzdem():
    app = _App(oeffnen_fehler=RuntimeError("COM"))
    assert _code(lambda: rl.lies_zeichnung(Path("C:/arbeit/z.SLDDRW"), {}, app=app)) == "ZEICHNUNG_NICHT_GEOEFFNET"
    assert app.docs == []


def test_lesefehler_wird_zeichnungfehler(monkeypatch):
    app = _App()

    def lies(*_):
        raise RuntimeError("COM")

    monkeypatch.setattr(rl, "_lies", lies)
    assert _code(lambda: rl.lies_zeichnung(Path("C:/arbeit/z.SLDDRW"), {}, app=app)) == "RUECKLESEN_FEHLER"
    assert app.docs == []


def test_schliessen_scheitert_wird_gemeldet(monkeypatch):
    app = _App(schliessen_scheitert=("teil.SLDPRT",))
    monkeypatch.setattr(rl, "_lies", lambda *a: _leeres_ist(("X: y",)))
    ist = rl.lies_zeichnung(Path("C:/arbeit/z.SLDDRW"), {}, app=app)
    assert ist.meldungen[0] == "X: y" and len(ist.meldungen) == 2
    assert ist.meldungen[1].startswith("RUECKLESEN_NICHT_GESCHLOSSEN: teil.SLDPRT")


def test_schon_offen_ohne_gross_klein_und_trenner():
    app = _App(offen=("C:\\Arbeit\\Z.slddrw",))
    assert _code(lambda: rl.lies_zeichnung(Path("c:/arbeit/z.SLDDRW"), {}, app=app)) == "ZEICHNUNG_SCHON_OFFEN"
    assert app.geschlossen == [] and len(app.docs) == 1


class _Blatt:
    def GetProperties2(self):
        return [12, 13, 1.0, 1.0, True, 0.42, 0.297]

    def GetName(self):
        return "Blatt1"


class _Zeichnung:
    def __init__(self, blaetter):
        self._blaetter = blaetter

    def GetCurrentSheet(self):
        return _Blatt()

    def GetSheetNames(self):
        return self._blaetter

    def GetFirstView(self):
        return None


def test_blatt_nicht_erfunden_und_mehrere_blaetter_gemeldet(monkeypatch):
    """Review 4b (M5): „Blatt“ kommt nur aus den Eigenschaften der Zeichnung (Get6), nie vom Rückleser; (M4) bei
    mehreren Blättern wird nur das aktuelle gelesen – das wird gemeldet."""
    monkeypatch.setattr(rl, "mathutil", lambda app: None)
    monkeypatch.setattr(rl, "lies_eigenschaften", lambda drw: {"Benennung": "X"})
    ist = rl._lies(None, _Zeichnung(["Blatt1"]), {})
    assert ist.eigenschaften == {"Benennung": "X"} and ist.format_ == "A3quer" and ist.meldungen == ()
    ist = rl._lies(None, _Zeichnung(["Blatt1", "Blatt2"]), {})
    assert ist.meldungen == ("RUECKLESEN_UNVOLLSTAENDIG: Blatt1 – Zeichnung hat 2 Blätter, gelesen nur das aktuelle",)


def test_toleranz_beide_passungswerte_gesetzt():
    """Gesamtreview M3: Bohrung und Welle gesetzt („H7/g6“) ist ein anderer Typ als „H7“ – nicht still die Bohrung."""
    assert rl.toleranz(7, 0.0, 2.1e-05, "H7", "g6").passung == "H7/g6"
    assert rl.toleranz(7, 0.0, 2.1e-05, "H7", "  ").passung == "H7"
    from swki.zeichnung.ist import IstMass
    from swki.zeichnung.massplan import Mass
    from swki.zeichnung.pruefen import _toleranz_ok
    from swki.zeichnung.toleranzangaben import Toleranz

    m = Mass("a", "neu", "durchmesser", 20.0, "f1", toleranz=Toleranz("H7", None, None, False))
    ist = IstMass("x", "haupt", "durchmesser", 20.0, "Ø", "", False, rl.toleranz(7, 0.0, 2.1e-05, "H7", "g6"), None,
                  None, None)
    assert _toleranz_ok(ist, m) is False
