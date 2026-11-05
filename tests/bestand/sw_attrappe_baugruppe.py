"""Attrappe einer offenen fremden Baugruppe und von ISldWorks für `aufnehmen`, ohne SolidWorks.

UNGEMESSEN: Die Attrappe folgt dem API-Index, nicht einer Messung; S19 kann sie korrigieren. Sie bildet nach, was die Schicht
aushalten muss: `Transform2` steht bis zum Neuaufbau veraltet; `GetComponents` liefert je aktiver Konfiguration, Kinder einer dort
unterdrückten Unterbaugruppe fehlen; `Min/MaximumVariation` sind relativ zu `D1` (S13b D); `FeatureManager.GetFeatures` kennt
auch, was der Baum nicht zeigt (`versteckt`); `pfade_wie_gespeichert`: `GetPathName` einer unterdrückten Komponente nennt den
gespeicherten Pfad (S19c T8.9), die Attrappe tut das nur auf Wunsch, `vom_original` lädt eine aktive von dort (S18g); Grenzen wirken, solange sie nicht unterdrückt sind; eine
Verknüpfung mit altem Fehler lässt `EditRebuild3` scheitern. Unterdrückte Verknüpfungen geben ihre Entitäten nicht mehr her
(`entitaeten_nach_dem_unterdruecken`), so fällt auf, wer sie zu spät liest.

Der Schreibweg (Task 9) ist genauso ungemessen, die Attrappe nimmt nur an, was die API-Hilfe nennt oder was die Handler aushalten
müssen: Eine neue Komponente oder Verknüpfung ist in den übrigen Konfigurationen unterdrückt (wie Features, S18c); ein doppelter
Name bleibt still alt; `ReplaceComponents2` lässt den Handle gültig und ändert `Name2` (Beispiel der API-Hilfe);
`ModifyDefinition` wirkt in der aktiven Konfiguration; alle Rückgaben sagen Erfolg, auch wenn nichts geschah (`wirkungslos`)."""

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
    """IDimension. `mate`: Option 2 und 3 schreiben je Konfiguration in die Verknüpfung."""

    def __init__(self, wert, mate=None):
        self.SystemValue, self.mate = wert, mate
        self.status = 0
        self.aufrufe = []

    def SetSystemValue3(self, wert, option, namen):
        self.aufrufe.append((wert, option, None if namen is None else list(namen.value)))
        if self.status != 0:
            return self.status
        if self.mate is not None and option in (2, 3):
            self.mate.schreibe_d1(wert, self.mate.asm.konfigurationen if option == 2 else namen.value)
            return 0
        self.SystemValue = wert
        return 0


class Bezug:
    """Was `IMateEntity2.Reference` liefert: eine Fläche zum Auswählen. `komp`: Entität im Baugruppenkontext, die Auswahl wird zur
    Seite einer neuen Verknüpfung."""

    def __init__(self, name, komp=None):
        self.name, self.komp, self.Name = name, komp, name

    def _waehle(self, anhaengen):
        if self.komp is not None:
            asm = self.komp.asm
            asm.seiten = [*(asm.seiten if anhaengen else ()), Seite(self.komp, self)]
        return True

    def Select4(self, anhaengen, daten):
        return self._waehle(anhaengen)

    def Select2(self, anhaengen, marke):
        return self._waehle(anhaengen)


class Seite:
    """IMateEntity2."""

    def __init__(self, komp, bezug, typ=2):
        self.ReferenceComponent, self.Reference, self.ReferenceType2 = komp, bezug, typ


class MateDaten:
    """IMate2. `spannen`: (Min, Max) der Variation je Konfiguration, sonst `spanne`."""

    def __init__(self, feature, typ, seiten, ausrichtung, spanne):
        self.feature, self.Type, self.seiten, self.Alignment = feature, typ, seiten, ausrichtung
        self.spanne = spanne
        self.spannen: dict[str, tuple] = {}

    def _spanne(self):
        return self.spannen.get(self.feature.asm.aktiv, self.spanne)

    @property
    def MinimumVariation(self):
        return self._spanne()[0]

    @property
    def MaximumVariation(self):
        return self._spanne()[1]

    @property
    def GetMateEntityCount(self):
        return len(self.seiten)

    def MateEntity(self, i):
        if self.feature.gesperrt():
            raise RuntimeError("Grenze unterdrückt: keine Entitäten")
        return self.seiten[i]


class Definition:
    """IDistanceMateFeatureData bzw. IAngleMateFeatureData: absolute Werte in m bzw. rad."""

    def __init__(self, typ, wert, unten, oben):
        art = "Distance" if typ == 5 else "Angle"
        self.art = art
        setattr(self, art, wert)
        setattr(self, f"Minimum{art}", unten)
        setattr(self, f"Maximum{art}", oben)


class Mate(Knoten):
    """Eine Verknüpfung; `typ` als swMateType_e, Werte in m bzw. rad wie in SolidWorks. `gesteuert`: Ein neuer Wert kommt still
    nicht an, wie ein gesteuertes Maß (S18c)."""

    def __init__(self, asm, name, typ, seiten=(), wert=None, spanne=(0.0, 0.0), ausrichtung=0, code=0, typname="MateCoincident"):
        super().__init__(asm, name, typname)
        self.daten = MateDaten(self, typ, list(seiten), ausrichtung, spanne)
        self.wert_d1 = None if wert is None else Masz(wert, self)
        self.code = code
        self.je_konfiguration: dict[str, float] = {}
        self.unterdrueckungen = []
        self.gesteuert = False
        self.modifiziert = []
        self.drehung_gesperrt = False

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, wert):
        if not any(m is not self and m.Name == wert for m in self.asm.mates):  # wie bei Features: doppelt bleibt still alt (S18c)
            self._name = wert

    def schreibe_d1(self, wert, konfigurationen):
        for k in self.asm.konfigurationen:
            self.je_konfiguration.setdefault(k, self.wert_d1.SystemValue)
        if not self.gesteuert:
            self.je_konfiguration.update(dict.fromkeys(konfigurationen, wert))

    def _d1(self):
        return self.je_konfiguration.get(self.asm.aktiv, self.wert_d1.SystemValue)

    @property
    def GetDefinition(self):
        d1 = self._d1()
        return Definition(self.daten.Type, d1, d1 + self.daten.MinimumVariation, d1 + self.daten.MaximumVariation)

    def ModifyDefinition(self, daten, oben, komponente):
        self.modifiziert.append((self.asm.aktiv, oben, komponente))
        if self.asm.wirkungslos:
            return True
        d1 = self._d1()
        spanne = (getattr(daten, f"Minimum{daten.art}") - d1, getattr(daten, f"Maximum{daten.art}") - d1)
        for k in (self.asm.konfigurationen if self.asm.definition_ueberall else [self.asm.aktiv]):
            self.daten.spannen[k] = spanne
        return True

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
        if self.asm.wirkungslos:
            return True
        for k in (namen.value if option == 3 else [self.asm.aktiv]):
            (self.unterdrueckt.add if aktion == 0 else self.unterdrueckt.discard)(k)
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
        self.fixiert_in: set[str] = set()         # je Konfiguration über `FixComponent`
        self.referenzen: dict[str, str] = {}      # je Konfiguration über `ReferencedConfiguration =`
        self.feature_namen: set[str] = set()      # was `GetModelDoc2.FeatureByName` kennt

    @property
    def GetPathName(self):
        gespeichert = self.asm.pfade_wie_gespeichert
        if gespeichert is not None and (self.asm.aktiv in self.unterdrueckt or self.Name2 in self.asm.vom_original):
            return str(Path(gespeichert) / self.rel)
        return str(self.asm.wurzel / self.rel)

    @property
    def IsFixed(self):
        return self.fixiert or self.asm.aktiv in self.fixiert_in

    @property
    def IsPatternInstance(self):
        return self.muster

    @property
    def ReferencedConfiguration(self):
        return self.referenzen.get(self.asm.aktiv, self.referenz)

    @ReferencedConfiguration.setter
    def ReferencedConfiguration(self, wert):
        self.referenzen[self.asm.aktiv] = wert

    def SetSuppression2(self, zustand):
        if not self.asm.wirkungslos:
            (self.unterdrueckt.add if zustand == UNTERDRUECKT else self.unterdrueckt.discard)(self.asm.aktiv)
        return 2  # swSuppressionChangeOk

    def GetCorrespondingEntity(self, objekt):
        return Bezug(f"{objekt.name} in {self.Name2}", self)

    def FeatureByName(self, name):
        return Bezug(name, self)

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
        return Modell(self.modell, self.feature_namen)

    def GetBox(self, ebenen, skizzen):
        x = self.lagen[self.asm.aktiv][9]
        return (x, 0.0, 0.0, x + 0.01, 0.01, 0.01)

    def Select4(self, anhaengen, daten, popup):
        self.asm.auswahl = self
        return True


class Modell:
    """IModelDoc2 einer Komponente: Ein Teil hat `GetPartBox`, eine Baugruppe nicht."""

    def __init__(self, art, feature_namen=()):
        self.GetType = 1 if art == "teil" else 2
        self.feature_namen = feature_namen
        if art == "teil":
            self.GetPartBox = lambda welt: (0.0, 0.0, 0.0, 0.01, 0.01, 0.01)

    def FeatureByName(self, name):
        return SimpleNamespace(Name=name) if name in self.feature_namen else None


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

    def DeleteSelection2(self, option):
        self.asm.loeschoptionen.append(option)
        if not self.asm.wirkungslos and isinstance(self.asm.auswahl, Komp):
            self.asm.entferne(self.asm.auswahl)
        return True


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
        self.sichtbar = True                            # mit Fenster geöffnet; `App.OpenDoc6` setzt es
        self.bewegt: dict[str, str] = {}
        self.gespeichert = []
        self.auswahl = None
        self.entitaeten_nach_dem_unterdruecken = False
        self.pfade_wie_gespeichert: Path | None = None  # unterdrückt zeigt `GetPathName` den gespeicherten Pfad (S19c T8.9)
        self.vom_original: set[str] = set()             # Komponenten, die aktiv vom gespeicherten Pfad laden (S18g)
        self.versteckt: list[Mate] = []                 # Verknüpfungen, die nur `GetFeatures` kennt, nicht der Baum
        self.wirkungslos = False                        # Schreibaufrufe melden Erfolg und tun nichts
        self.definition_ueberall = False                # `ModifyDefinition` wirkt in allen Konfigurationen
        self.seiten: list[Seite] = []                   # Auswahl für die nächste Verknüpfung
        self.eingefuegt, self.ersetzungen, self.loeschoptionen = [], [], []
        self.bleibt_stehen: set[str] = set()            # Verknüpfungen, die das Löschen ihrer Komponente überleben
        self.verliert: set[str] = set()                 # Verknüpfungen, die `ReplaceComponents2` nicht neu zuordnen kann
        self.bricht: dict[str, int] = {}                # Verknüpfung → Fehlercode nach `ReplaceComponents2`
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

    def alle_mates(self) -> list:
        """Verknüpfungen und Ordner, auch was in Ordnern steckt."""
        return [x for m in self.mates for x in (m, *m.unter)]

    @property
    def FeatureManager(self):
        return SimpleNamespace(GetFeatures=lambda nur_oben: (self.ebene, self.mategruppe, *self.alle_mates(), *self.versteckt))

    def _loese(self):
        self.aufgebaut.add(self.aktiv)
        for m in self.mates:
            if not m.Name.endswith(".antrieb"):
                continue
            grenze = next(g for g in self.alle_mates() if g.Name == m.Name.removesuffix(".antrieb"))
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
        if self.auswahl in self.mates and not self.wirkungslos:
            self.mates.remove(self.auswahl)

    def FixComponent(self):
        self.auswahl.fixiert_in.add(self.aktiv)

    def entferne(self, komp) -> None:
        """Löscht die Komponente samt Kindern und den Verknüpfungen an ihnen."""
        weg = [k for k in self.komponenten if k is komp or k.Name2.startswith(f"{komp.Name2}/")]
        self.komponenten = [k for k in self.komponenten if k not in weg]
        self.glieder = [g for g in self.glieder if g.Name != komp.Name2]
        self.mates = [m for m in self.mates if m.Name in self.bleibt_stehen
                      or not any(s.ReferenceComponent in weg for s in m.daten.seiten)]

    # IAssemblyDoc
    def GetComponents(self, nur_oberste):
        genannt = [k for k in self.komponenten if self.aktiv not in k.nicht_genannt]
        return tuple(k for k in genannt if not nur_oberste or "/" not in k.Name2) or None

    @property
    def InterferenceDetectionManager(self):
        return self.kollisionen if self.sichtbar else None  # ohne Fenster `None` (S19d P.d1, T8.12)

    def AddMate5(self, typ, ausrichtung, flip, d, d_oben, d_unten, _1, _2, w, w_oben, w_unten, _3, sperre, _5, status):
        status.value = 1
        spanne = (d_unten - d, d_oben - d) if typ == 5 else (w_unten - w, w_oben - w) if typ == 6 else (0.0, 0.0)
        m = Mate(self, f"Abstand{len(self.mates) + 100}", typ, self.seiten, wert=d if typ == 5 else w, spanne=spanne,
                 ausrichtung=0 if ausrichtung == 2 else ausrichtung, typname="MateDistanceDim")
        m.drehung_gesperrt = sperre
        m.unterdrueckt |= set(self.konfigurationen) - {self.aktiv}
        self.mates.append(m)
        return m

    def _freier_name(self, stamm: str) -> str:
        nummern = [int(k.Name2.rpartition("-")[2]) for k in self.komponenten if k.Name2.rpartition("-")[0] == stamm]
        return f"{stamm}-{max(nummern, default=0) + 1}"

    def AddComponent5(self, pfad, option, neuer_name, benutze, konfiguration, x, y, z):
        self.eingefuegt.append({"pfad": pfad, "option": option, "neuer_name": neuer_name, "benutze": benutze,
                                "konfiguration": konfiguration, "mitte": (x, y, z)})
        rel = Path(pfad).relative_to(self.wurzel).as_posix()
        k = self.komponente(self._freier_name(Path(pfad).stem), rel, referenz=konfiguration if benutze else "Standard")
        k.unterdrueckt |= set(self.konfigurationen) - {self.aktiv}
        return k

    def ReplaceComponents2(self, datei, konfiguration, alle, wahl, neu_zuordnen):
        self.ersetzungen.append({"datei": datei, "konfiguration": konfiguration, "alle": alle, "wahl": wahl,
                                 "neu_zuordnen": neu_zuordnen})
        if self.wirkungslos:
            return True
        ziel = self.auswahl
        ziele = [k for k in self.komponenten if k.rel == ziel.rel and "/" not in k.Name2] if alle else [ziel]
        rel = Path(datei).relative_to(self.wurzel).as_posix()
        for k in ziele:
            alt, neu = k.Name2, self._freier_name(Path(datei).stem)
            k.Name2, k.rel = neu, rel
            if konfiguration:
                k.referenz = konfiguration
            next(g for g in self.glieder if g.Name == alt).Name = neu
        for m in list(self.mates):
            if any(s.ReferenceComponent in ziele for s in m.daten.seiten):
                if m.Name in self.verliert or not neu_zuordnen:
                    self.mates.remove(m)
                m.code = self.bricht.get(m.Name, m.code)
        return True


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
            self.baugruppe.sichtbar = not self.sichtbarkeit or self.sichtbarkeit[-1] is not False  # `messen.oeffne`
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
