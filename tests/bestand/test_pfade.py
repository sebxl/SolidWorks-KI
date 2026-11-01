"""Pfadschutz (Spec §8.1a): SolidWorks darf nie still eine Datei außerhalb des Bestands- oder Lauf-Ordners laden. Attrappen."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.bestand import pfade
from swki.bestand.ablage import ist_virtuell
from swki.bestand.fehler import BESTAND_PFAD_FREMD, BestandFehler
from swki.pruefung import messen


class Komp:
    def __init__(self, pfad, virtuell=False, unterdrueckt=False):
        self.pfad, self.virtuell, self.unterdrueckt = str(pfad), virtuell, unterdrueckt

    @property
    def GetPathName(self):
        return self.pfad

    @property
    def IsVirtual(self):
        return self.virtuell


class Dok:
    """Ein offenes Dokument (Teil oder Baugruppe). Ein Teil hat kein `GetComponents`, wie in SolidWorks."""

    def __init__(self, pfad, komponenten=None):
        self.pfad = Path(pfad)
        self.gespeichert = []
        if komponenten is not None:
            # nur `False` liefert alle Ebenen
            self.GetComponents = lambda nur_oberste: tuple(komponenten) if not nur_oberste else ()

    @property
    def GetPathName(self):
        return str(self.pfad)

    @property
    def GetTitle(self):
        return self.pfad.name

    def Save3(self, optionen, fehler, warnungen):
        self.gespeichert.append(optionen)
        return True


class App:
    def __init__(self, wurzel, abhaengig=None, vorher_offen=(), nachgeladen=(), komponenten=None):
        self.wurzel = wurzel
        self.abhaengig = abhaengig  # Pfade der Abhängigkeiten oder None (keine)
        self.offen = [Dok(p) for p in vorher_offen]
        self.nachgeladen = [Dok(p) for p in nachgeladen]
        self.komponenten = komponenten
        self.aufrufe = []
        self.geoeffnet = []
        self.geschlossen = []
        self.dok = None

    def GetDocumentDependencies2(self, pfad, traverse, suche, nur_lesen):
        self.aufrufe.append((pfad, traverse, suche, nur_lesen))
        if self.abhaengig is None:
            return None
        return tuple(x for p in self.abhaengig for x in (Path(p).name, str(p)))

    def OpenDoc6(self, pfad, typ, optionen, konfiguration, fehler, warnungen):
        self.geoeffnet.append((pfad, typ, optionen))
        endung = Path(pfad).suffix.lower()
        self.dok = Dok(pfad, self.komponenten if endung == ".sldasm" else None)
        self.offen += [self.dok, *self.nachgeladen]
        return self.dok

    def DocumentVisible(self, sichtbar, typ):
        pass

    @property
    def GetDocuments(self):
        return tuple(self.offen) or None

    def CloseDoc(self, titel):
        self.geschlossen.append(titel)


@pytest.fixture
def wurzel(tmp_path):
    ordner = tmp_path / "auftrag" / "lauf-3"
    ordner.mkdir(parents=True)
    return ordner


def _e(pfad, name=None, virtuell=False):
    return {"name": name or Path(str(pfad)).name, "pfad": str(pfad), "virtuell": virtuell}


# --- fremde_pfade: rein ----------------------------------------------------------------------------------------------

def test_alles_im_ordner_ist_leer(wurzel):
    eintraege = [_e(wurzel / "a.SLDPRT"), _e(wurzel / "unter" / "b.SLDASM")]
    assert pfade.fremde_pfade(eintraege, wurzel) == []


def test_datei_ausserhalb_wird_genannt(wurzel, tmp_path):
    fremd = _e(tmp_path / "kunde" / "orig.SLDPRT")
    assert pfade.fremde_pfade([_e(wurzel / "a.SLDPRT"), fremd], wurzel) == [fremd]


def test_gross_kleinschreibung_zaehlt_nicht(wurzel):
    eintrag = _e(str(wurzel).upper() + "\\A.SLDPRT")
    assert pfade.fremde_pfade([eintrag], Path(str(wurzel).lower())) == []


def test_nachbarordner_mit_gleichem_praefix_ist_fremd(wurzel):
    nachbar = _e(wurzel.parent / "lauf-30" / "a.SLDPRT")  # beginnt mit "…\lauf-3", liegt aber nicht darin
    assert pfade.fremde_pfade([nachbar], wurzel) == [nachbar]


def test_der_ordner_selbst_ist_nicht_fremd_und_punkte_werden_aufgeloest(wurzel):
    assert pfade.fremde_pfade([_e(wurzel / "unter" / ".." / "a.SLDPRT")], wurzel) == []
    assert pfade.fremde_pfade([_e(wurzel / ".." / "a.SLDPRT")], wurzel) != []


def test_virtuelle_komponente_ist_nicht_fremd(wurzel, tmp_path):
    virtuell = _e(tmp_path / "irgendwo" / "Baugruppe.SLDASM^Teil1", virtuell=True)
    assert pfade.fremde_pfade([virtuell], wurzel) == []
    assert ist_virtuell(virtuell["pfad"]) and not ist_virtuell(wurzel / "a.SLDPRT")


def test_leerer_pfad_ist_kein_fund(wurzel):
    assert pfade.fremde_pfade([_e("", name="Teil1")], wurzel) == []


# --- Vorprüfung --------------------------------------------------------------------------------------------------------

def test_vorpruefung_loest_nach_suchregeln_auf_und_nennt_nur_echte_referenzen(wurzel):
    app = App(wurzel, abhaengig=[wurzel / "a.SLDPRT", wurzel.parent / "Asm.SLDASM^Teil9"])
    assert pfade.aufgeloeste_referenzen(app, wurzel / "Asm.SLDASM") == [str(wurzel / "a.SLDPRT")]
    assert app.aufrufe == [(str(wurzel / "Asm.SLDASM"), True, True, False)]


def test_vorpruefung_ohne_referenz(wurzel):
    assert pfade.aufgeloeste_referenzen(App(wurzel), wurzel / "Teil.SLDPRT") == []


def test_vorpruefung_oeffnet_nicht(wurzel, tmp_path):
    app = App(wurzel, abhaengig=[tmp_path / "kunde" / "orig.SLDPRT"])
    with pytest.raises(BestandFehler) as e:
        pfade.oeffne_in(app, wurzel / "Asm.SLDASM", wurzel)
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD
    assert e.value.daten["pfade"] == [str(tmp_path / "kunde" / "orig.SLDPRT")]
    assert app.geoeffnet == [] and app.geschlossen == []


# --- Nach dem Laden ----------------------------------------------------------------------------------------------------

def test_unterdrueckte_komponente_wird_mitgeprueft(wurzel, tmp_path):
    fremd = tmp_path / "kunde" / "orig.SLDPRT"
    komponenten = [Komp(wurzel / "a.SLDPRT"), Komp(fremd, unterdrueckt=True)]
    app = App(wurzel, komponenten=komponenten)  # die Vorprüfung sieht nichts, erst das Laden zeigt es
    with pytest.raises(BestandFehler) as e:
        pfade.oeffne_in(app, wurzel / "Asm.SLDASM", wurzel)
    assert e.value.daten["pfade"] == [str(fremd)]


def test_komponenten_aller_ebenen_und_hauptdokument_werden_gelesen(wurzel):
    app = App(wurzel, komponenten=[Komp(wurzel / "a.SLDPRT"), Komp(wurzel / "Unter.SLDASM")])
    model = app.OpenDoc6(str(wurzel / "Asm.SLDASM"), 2, 0, "", None, None)
    geladen = pfade.geladene_pfade(app, model, set())
    namen = ("Asm.SLDASM", "a.SLDPRT", "Unter.SLDASM")
    assert {x["pfad"] for x in geladen} == {str(wurzel / n) for n in namen}
    assert len(geladen) == 3  # das Hauptdokument steht auch in GetDocuments, zählt aber einmal


def test_schon_offenes_fremdes_dokument_ist_kein_fund(wurzel, tmp_path):
    fremd = tmp_path / "kunde" / "Offen.SLDPRT"
    app = App(wurzel, vorher_offen=[fremd], komponenten=[Komp(wurzel / "a.SLDPRT")])
    model = pfade.oeffne_in(app, wurzel / "Asm.SLDASM", wurzel)
    assert model is app.dok
    assert app.geschlossen == []


def test_neu_geladenes_fremdes_dokument_ist_ein_fund(wurzel, tmp_path):
    fremd = tmp_path / "kunde" / "Nachgeladen.SLDPRT"
    app = App(wurzel, nachgeladen=[fremd], komponenten=[])
    with pytest.raises(BestandFehler) as e:
        pfade.oeffne_in(app, wurzel / "Asm.SLDASM", wurzel)
    assert e.value.daten["pfade"] == [str(fremd)]


def test_teil_ohne_komponenten_geht_durch(wurzel):
    app = App(wurzel)
    model = pfade.oeffne_in(app, wurzel / "Teil.SLDPRT", wurzel)  # ein Teil hat kein GetComponents
    assert model.GetPathName == str(wurzel / "Teil.SLDPRT")
    assert not hasattr(model, "GetComponents")
    assert app.geschlossen == []


def test_fund_schliesst_ohne_speichern(wurzel, tmp_path):
    fremd = tmp_path / "kunde" / "orig.SLDPRT"
    app = App(wurzel, komponenten=[Komp(fremd), Komp(wurzel / "a.SLDPRT")])
    with pytest.raises(BestandFehler) as e:
        pfade.oeffne_in(app, wurzel / "Asm.SLDASM", wurzel)
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD
    assert e.value.daten["pfade"] == [str(fremd)]
    assert app.geschlossen == ["Asm.SLDASM"]  # genau einmal
    assert app.dok.gespeichert == []


def test_oeffnen_mit_voller_last_und_nur_lesen(wurzel):
    app = App(wurzel)
    pfade.oeffne_in(app, wurzel / "Teil.SLDPRT", wurzel, sichtbar=False)
    _, typ, optionen = app.geoeffnet[0]
    assert typ == messen.SW_DOC_PART
    assert optionen == messen.SW_OPEN_SILENT | messen.SW_OPEN_READONLY | messen.SW_OPEN_VOLL


def test_nur_lesen_laesst_sich_abschalten(wurzel):
    app = App(wurzel)
    pfade.oeffne_in(app, wurzel / "Teil.SLDPRT", wurzel, nur_lesen=False)
    assert app.geoeffnet[0][2] == messen.SW_OPEN_SILENT | messen.SW_OPEN_VOLL


def test_pruefungseintrag_pfade(wurzel, tmp_path):
    fremd = tmp_path / "kunde" / "orig.SLDPRT"
    app = App(wurzel, komponenten=[Komp(wurzel / "a.SLDPRT"), Komp(fremd)])
    model = app.OpenDoc6(str(wurzel / "Asm.SLDASM"), 2, 0, "", None, None)
    e = pfade.pruefe_geladen(app, model, wurzel, set())
    assert e["id"] == "pfade" and e["ok"] is False and e["fremd"] == [str(fremd)]
    ordentlich = App(wurzel, komponenten=[Komp(wurzel / "a.SLDPRT")])
    gut = pfade.pruefe_geladen(ordentlich, ordentlich.OpenDoc6(str(wurzel / "Asm.SLDASM"), 2, 0, "", None, None), wurzel, set())
    assert gut["id"] == "pfade" and gut["ok"] is True and gut["fremd"] == [] and gut["geladen"] >= 2


def test_offene_dokumente_ohne_dokumente(wurzel):
    assert pfade.offene_dokumente(App(wurzel)) == set()
    assert len(pfade.offene_dokumente(App(wurzel, vorher_offen=[wurzel / "a.SLDPRT"]))) == 1


def test_oeffne_voll_setzt_nur_das_bit(wurzel):
    """`oeffne` ohne `voll` bleibt wie bisher."""
    calls = []
    app = SimpleNamespace(OpenDoc6=lambda *a: calls.append(a) or SimpleNamespace(), DocumentVisible=lambda *a: None)
    messen.oeffne(app, wurzel / "T.SLDPRT")
    messen.oeffne(app, wurzel / "T.SLDPRT", voll=True)
    assert calls[0][2] == messen.SW_OPEN_SILENT and calls[1][2] == messen.SW_OPEN_SILENT | messen.SW_OPEN_VOLL
