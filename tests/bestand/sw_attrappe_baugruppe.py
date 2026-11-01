"""Attrappe einer offenen fremden Baugruppe und von ISldWorks für `aufnehmen`, ohne SolidWorks.

UNGEMESSEN: Die Attrappe folgt dem API-Index, nicht einer Messung; S19 kann sie korrigieren. Sie bildet nach, was die Schicht
aushalten muss: `Transform2` steht bis zum Neuaufbau veraltet; `GetComponents` liefert je aktiver Konfiguration, Kinder einer
dort unterdrückten Unterbaugruppe fehlen; `Min/MaximumVariation` sind relativ zu `D1` (S13b D); Grenzen wirken, solange sie
nicht unterdrückt sind; eine Verknüpfung mit altem Fehler lässt `EditRebuild3` scheitern. Unterdrückte Verknüpfungen geben ihre
Entitäten nicht mehr her (`entitaeten_nach_dem_unterdruecken`), so fällt auf, wer sie zu spät liest."""

import os
from pathlib import Path
from types import SimpleNamespace

from tests.bestand.sw_attrappe import Eigenschaften, Gleichungen

EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
UNTERDRUECKT, VOLL_GELADEN = 0, 3  # swComponentSuppressionState_e


def lage(x_m: float = 0.0) -> list[float]:
    t = list(EINS)
    t[9] = x_m
    return t


class Knoten:
    """IFeature im Baum (Ebene, Komponente, Ordner); `unter`: Unterfeatures."""

    GetParents = GetChildren = None
    GetFirstDisplayDimension = None

    def __init__(self, asm, name, typ, unter=()):
        self.asm, self.Name, self.GetTypeName2, self.unter = asm, name, typ, list(unter)
        self.unterdrueckt: set[str] = set()
        self._bruder = None
        for a, b in zip(self.unter, self.unter[1:]):
            a._bruder = b

    @property
    def GetNextFeature(self):
        kette = self.asm.baum
        i = kette.index(self)
        return kette[i + 1] if i + 1 < len(kette) else None

    @property
    def GetFirstSubFeature(self):
        return self.unter[0] if self.unter else None

    @property
    def GetNextSubFeature(self):
        return self._bruder

    def IsSuppressed2(self, option, namen):
        return tuple(k in self.unterdrueckt for k in namen.value)

    def Select2(self, anhaengen, marke):
        self.asm.auswahl = self
        return True


class Masz:
    def __init__(self, wert):
        self.SystemValue = wert

    def SetSystemValue3(self, wert, option, namen):
        self.SystemValue = wert
        return 0


class Bezug:
    """Was `IMateEntity2.Reference` liefert: eine Fläche zum Auswählen."""

    def __init__(self, name):
        self.name = name

    def Select4(self, anhaengen, daten):
        return True


class Seite:
    """IMateEntity2."""

    def __init__(self, komp, bezug, typ=2):
        self.ReferenceComponent, self.Reference, self.ReferenceType2 = komp, bezug, typ


class MateDaten:
    """IMate2."""

    def __init__(self, feature, typ, seiten, ausrichtung, spanne):
        self.feature, self.Type, self.seiten, self.Alignment = feature, typ, seiten, ausrichtung
        self.MinimumVariation, self.MaximumVariation = spanne

    @property
    def GetMateEntityCount(self):
        return len(self.seiten)

    def MateEntity(self, i):
        if self.feature.gesperrt():
            raise RuntimeError("Grenze unterdrückt: keine Entitäten")
        return self.seiten[i]


class Mate(Knoten):
    """Eine Verknüpfung; `typ` als swMateType_e, Werte in m bzw. rad wie in SolidWorks."""

    def __init__(self, asm, name, typ, seiten=(), wert=None, spanne=(0.0, 0.0), ausrichtung=0, code=0, typname="MateCoincident"):
        super().__init__(asm, name, typname)
        self.daten = MateDaten(self, typ, list(seiten), ausrichtung, spanne)
        self.wert_d1 = None if wert is None else Masz(wert)
        self.code = code
        self.je_konfiguration: dict[str, float] = {}
        self.unterdrueckungen = []

    def gesperrt(self):
        return self.asm.entitaeten_nach_dem_unterdruecken is False and self.asm.aktiv in self.unterdrueckt

    @property
    def GetSpecificFeature2(self):
        return self.daten

    def GetErrorCode2(self, warnung):
        return self.code

    def Parameter(self, name):
        if name != "D1" or self.wert_d1 is None:
            return None
        if self.asm.aktiv in self.je_konfiguration:
            self.wert_d1.SystemValue = self.je_konfiguration[self.asm.aktiv]
        return self.wert_d1

    def SetSuppression2(self, aktion, option, namen):
        self.unterdrueckungen.append(aktion)
        (self.unterdrueckt.add if aktion == 0 else self.unterdrueckt.discard)(self.asm.aktiv)
        return True


class Komp:
    """IComponent2. `lagen`: Stand je Konfiguration nach dem Neuaufbau; `veraltet`: was `Transform2` davor zeigt."""

    def __init__(self, asm, name, rel, fixiert=False, virtuell=False, muster=False, status=3, loesen=-1, modell="teil",
                 referenz="Standard"):
        self.asm, self.Name2, self.rel = asm, name, rel
        self.fixiert, self.IsVirtual, self.muster, self.status, self.Solving = fixiert, virtuell, muster, status, loesen
        self.modell, self.referenz = modell, referenz
        self.unterdrueckt: set[str] = set()
        self.nicht_genannt: set[str] = set()
        self.lagen = {k: lage() for k in asm.konfigurationen}
        self.veraltet: dict[str, list[float]] = {}

    @property
    def GetPathName(self):
        return str(self.asm.wurzel / self.rel)

    @property
    def IsFixed(self):
        return self.fixiert

    @property
    def IsPatternInstance(self):
        return self.muster

    @property
    def ReferencedConfiguration(self):
        return self.referenz

    @property
    def GetConstrainedStatus(self):
        return self.status

    @property
    def GetSuppression2(self):
        return UNTERDRUECKT if self.asm.aktiv in self.unterdrueckt else VOLL_GELADEN

    @property
    def Transform2(self):
        k = self.asm.aktiv
        if k in self.unterdrueckt:
            return None
        return SimpleNamespace(ArrayData=self.veraltet.get(k, self.lagen[k]) if k not in self.asm.aufgebaut else self.lagen[k])

    @property
    def GetModelDoc2(self):
        if self.modell is None or self.asm.aktiv in self.unterdrueckt:
            return None
        return Modell(self.modell)

    def GetBox(self, ebenen, skizzen):
        x = self.lagen[self.asm.aktiv][9]
        return (x, 0.0, 0.0, x + 0.01, 0.01, 0.01)

    def Select4(self, anhaengen, daten, popup):
        self.asm.auswahl = self
        return True


class Modell:
    """IModelDoc2 einer Komponente: Ein Teil hat `GetPartBox`, eine Baugruppe nicht."""

    def __init__(self, art):
        self.GetType = 1 if art == "teil" else 2
        if art == "teil":
            self.GetPartBox = lambda welt: (0.0, 0.0, 0.0, 0.01, 0.01, 0.01)


class Interferenz:
    def __init__(self, komponenten, volumen_mm3):
        self.Components = tuple(SimpleNamespace(Name2=n) for n in komponenten)
        self.Volume = volumen_mm3 * 1e-9


class Kollisionen:
    """IInterferenceDetectionMgr. `liste` None: `GetInterferences` liefert nichts, obwohl `anzahl` mehr sagt."""

    def __init__(self, anzahl=0, liste=()):
        self.anzahl, self.liste = anzahl, liste
        self.TreatCoincidenceAsInterference = True
        self.fertig = 0

    @property
    def GetInterferenceCount(self):
        return self.anzahl

    @property
    def GetInterferences(self):
        return self.liste

    def _FlagAsMethod(self, name):
        pass

    def Done(self):
        self.fertig += 1


class Erweiterung:
    def __init__(self, asm):
        self.asm = asm
        self.HasDesignTable = False

    @property
    def GetWhatsWrongCount(self):
        return len(self.asm.fehler.get(self.asm.aktiv, []))

    def GetWhatsWrong(self, features, codes, warnungen):
        zeilen = self.asm.fehler.get(self.asm.aktiv, [])
        features.value = tuple(SimpleNamespace(Name=f) for f, _ in zeilen)
        codes.value = tuple(c for _, c in zeilen)
        warnungen.value = tuple(False for _ in zeilen)

    def CustomPropertyManager(self, k):
        return Eigenschaften(self.asm.eigenschaften.setdefault(k, {}))

    def ListExternalFileReferences(self, *ausgaben):
        pass

    def GetUserPreferenceInteger(self, was, option):
        return 5

    @property
    def GetLastFeatureAdded(self):
        return self.asm.mates[-1] if self.asm.mates else None


class Baugruppe:
    """IModelDoc2 und IAssemblyDoc in einem. `bewegt`: Grenze → Komponente, die der Antrieb in x verschiebt."""

    def __init__(self, wurzel: Path, name="Haupt.SLDASM", konfigurationen=("Standard",), aktiv=None):
        self.wurzel, self.name = Path(wurzel), name
        self.konfigurationen = list(konfigurationen)
        self.aktiv = aktiv or self.konfigurationen[0]
        self.komponenten: list[Komp] = []
        self.glieder: list[Knoten] = []
        self.mates: list[Mate] = []
        self.ebene = Knoten(self, "Ebene vorne", "RefPlane")
        self.mategruppe = Knoten(self, "Verknüpfungen", "MateGroup")
        self.gleichungen = Gleichungen([], self)
        self.gleichungen.LinkToFile, self.gleichungen.FilePath = False, ""
        self.fehler: dict[str, list] = {}
        self.eigenschaften: dict[str, dict] = {}
        self.aufgebaut: set[str] = set()
        self.neuaufbauten = []
        self.kollisionen = Kollisionen()
        self.bewegt: dict[str, str] = {}
        self.gespeichert = []
        self.auswahl = None
        self.entitaeten_nach_dem_unterdruecken = False
        self.Extension = Erweiterung(self)
        self.SelectionManager = SimpleNamespace(CreateSelectData=SimpleNamespace(Mark=0))

    # Aufbau der Attrappe
    def komponente(self, name, rel, **felder) -> Komp:
        k = Komp(self, name, rel, **felder)
        self.komponenten.append(k)
        if "/" not in name:
            self.glieder.append(Knoten(self, name, "Reference"))  # Komponenten stehen als Features im Baum (Typname laut Index)
        return k

    def mate(self, name, typ, seiten=(), **felder) -> Mate:
        m = Mate(self, name, typ, seiten, **felder)
        self.mates.append(m)
        return m

    def seite(self, name) -> Seite:
        return Seite(self.komp(name), Bezug(f"Fläche von {name}"))

    def komp(self, name) -> Komp:
        return next(k for k in self.komponenten if k.Name2 == name)

    # IModelDoc2
    @property
    def baum(self):
        self.mategruppe.unter = self.mates
        for a, b in zip(self.mates, [*self.mates[1:], None]):
            a._bruder = b
        return [self.ebene, *self.glieder, self.mategruppe]

    @property
    def FirstFeature(self):
        return self.baum[0]

    @property
    def GetConfigurationNames(self):
        return tuple(self.konfigurationen)

    def ShowConfiguration2(self, k):
        self.aktiv = k
        return True

    @property
    def ConfigurationManager(self):
        return SimpleNamespace(ActiveConfiguration=SimpleNamespace(Name=self.aktiv))

    def _loese(self):
        self.aufgebaut.add(self.aktiv)
        for m in self.mates:
            if not m.Name.endswith(".antrieb"):
                continue
            grenze = next(g for g in self.mates if g.Name == m.Name.removesuffix(".antrieb"))
            wert = m.wert_d1.SystemValue
            mitte = grenze.wert_d1.SystemValue
            unten, oben = mitte + grenze.daten.MinimumVariation, mitte + grenze.daten.MaximumVariation
            wirkt = self.aktiv not in grenze.unterdrueckt
            m.code = 47 if wirkt and not unten - 1e-9 <= wert <= oben + 1e-9 else 0
            if m.code == 0:
                self.komp(self.bewegt[grenze.Name]).lagen[self.aktiv] = lage(wert)

    @property
    def EditRebuild3(self):
        self._loese()
        return not self.fehler.get(self.aktiv)

    def ForceRebuild3(self, nur_oben):
        self.neuaufbauten.append(self.aktiv)
        self._loese()
        return True

    @property
    def GetEquationMgr(self):
        return self.gleichungen

    def ClearSelection2(self, alle):
        self.auswahl = None

    def GetMaterialPropertyName2(self, k, datenbank):
        return ""

    @property
    def GetPathName(self):
        return str(self.wurzel / self.name)

    @property
    def GetTitle(self):
        return self.name

    def Save3(self, optionen, fehler, warnungen):
        self.gespeichert.append(self.aktiv)
        return True

    def _FlagAsMethod(self, name):
        pass

    def EditDelete(self):
        if self.auswahl in self.mates:
            self.mates.remove(self.auswahl)

    # IAssemblyDoc
    def GetComponents(self, nur_oberste):
        genannt = [k for k in self.komponenten if self.aktiv not in k.nicht_genannt]
        return tuple(k for k in genannt if not nur_oberste or "/" not in k.Name2) or None

    @property
    def InterferenceDetectionManager(self):
        return self.kollisionen

    def AddMate5(self, typ, ausrichtung, flip, d, d_oben, d_unten, _1, _2, w, w_oben, w_unten, _3, _4, _5, status):
        status.value = 1
        m = Mate(self, f"Abstand{len(self.mates) + 100}", typ, wert=d if typ == 5 else w, typname="MateDistanceDim")
        self.mates.append(m)
        return m


class Einzeldatei:
    """Ein offenes Teil oder eine Unterbaugruppe beim Lesen je Datei."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)

    @property
    def GetPathName(self):
        return str(self.pfad)

    @property
    def GetTitle(self):
        return self.pfad.name

    def GetComponents(self, nur_oberste):
        return ()


class App:
    """ISldWorks. `referenzen`: gespeicherte Pfade der Hauptbaugruppe; `baugruppe`: was beim Öffnen von `Haupt.SLDASM` offen
    ist."""

    def __init__(self, original: Path, referenzen: list[Path], baugruppe: Baugruppe | None = None):
        self.original, self.referenzen, self.baugruppe = Path(original), [Path(p) for p in referenzen], baugruppe
        self.versionen: dict[str, tuple] = {}
        self.abhaengig: dict[str, list[str]] = {}  # Dateiname → eigene Referenzen
        self.GetLatestSupportedFileVersion = 18000
        self.GetProcessID = os.getpid()
        self.geoeffnet, self.ereignisse, self.offen, self.sichtbarkeit = [], [], [], []

    def VersionHistory(self, pfad):
        return self.versionen.get(Path(pfad).name, ("18000[2025/268]",))

    def _kopie_von(self, ziel: Path, pfad: Path) -> Path:
        try:
            return Path(pfad).parent / ziel.relative_to(self.original.parent)
        except ValueError:
            return Path(pfad).parent / ziel.name

    def GetDocumentDependencies2(self, pfad, tief, suche, nur_lesen):
        if suche and Path(pfad).name == self.original.name:
            self.wurzel_kopie = Path(pfad).parent
        if Path(pfad).name != self.original.name:
            eigene = [Path(p) for p in self.abhaengig.get(Path(pfad).name, ())]
            eigene = [self._kopie_von(p, self.wurzel_kopie / "x") for p in eigene] if suche else eigene
            return tuple(x for p in eigene for x in (p.name, str(p))) or None
        ziele = [self._kopie_von(p, Path(pfad)) if suche else p for p in self.referenzen]
        return tuple(x for p in ziele for x in (p.name, str(p))) or None

    def OpenDoc6(self, pfad, typ, optionen, konfiguration, fehler, warnungen):
        self.geoeffnet.append(Path(pfad))
        self.ereignisse.append(("offen", Path(pfad).name))
        if Path(pfad).name == self.original.name and self.baugruppe is not None:
            self.baugruppe.wurzel = Path(pfad).parent
            self.baugruppe.aufgebaut.clear()
            dok = self.baugruppe
        else:
            dok = Einzeldatei(pfad)
        self.offen.append(dok)
        return dok

    def DocumentVisible(self, sichtbar, typ):
        self.sichtbarkeit.append(sichtbar)

    @property
    def GetDocuments(self):
        return tuple(self.offen) or None

    def CloseDoc(self, titel):
        self.ereignisse.append(("zu", titel))
        self.offen = [d for d in self.offen if d.GetTitle != titel]


def muster_baugruppe(wurzel: Path, konfigurationen=("Standard",)) -> Baugruppe:
    """Grund-1 fixiert, Schlitten-1 an der Grenze Hub (0 bis 25 mm, steht auf 10), elf Schrauben, Unter-1 mit Welle-1, Abstand
    mit Wert, Verknüpfung an einer Ebene der Hauptbaugruppe."""
    asm = Baugruppe(wurzel, konfigurationen=konfigurationen)
    asm.komponente("Grund-1", "teile/Grund.SLDPRT", fixiert=True)
    asm.komponente("Schlitten-1", "teile/Schlitten.SLDPRT", status=2)
    for n in range(1, 12):
        asm.komponente(f"Schraube-{n}", "teile/Schraube.SLDPRT")
    asm.komponente("Unter-1", "Unter.SLDASM", modell="baugruppe", loesen=0)
    asm.komponente("Unter-1/Welle-1", "teile/Welle.SLDPRT")
    asm.mate("Hub", 5, [asm.seite("Schlitten-1"), asm.seite("Grund-1")], wert=0.010, spanne=(-0.010, 0.015),
             typname="MateDistanceDim")
    asm.mate("Abstand1", 5, [asm.seite("Schraube-1"), asm.seite("Grund-1")], wert=0.003, typname="MateDistanceDim")
    asm.mate("Deckungsgleich1", 0, [asm.seite("Grund-1"), Seite(None, Bezug("Ebene vorne"), 4)])
    asm.bewegt["Hub"] = "Schlitten-1"
    asm.komp("Schlitten-1").lagen = {k: lage(0.010) for k in asm.konfigurationen}
    return asm
