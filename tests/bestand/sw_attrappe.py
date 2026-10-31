"""Attrappe eines offenen fremden Teils für Punkte und Bau ohne SolidWorks.

Sie bildet nach, was S18c und die Sonde aus Task 6 gemessen haben, denn genau daran scheitert der Bau sonst still:
Werte, Reihenfolge und Fehler gelten je Konfiguration; ein gesteuertes Maß meldet Status 0 und springt beim Neuaufbau zurück;
ein doppelter Name bleibt ohne Ausnahme alt; `ReorderFeature` wirkt nur in der aktiven Konfiguration, ein unmöglicher Zug
liefert False und beschädigt sie; Löschen nimmt Kinder und aufgenommene Skizzen mit; ein neues Feature ist in den übrigen
Konfigurationen unterdrückt."""

from types import SimpleNamespace


class Feat:
    def __init__(self, teil, name, typ="Cut", unter=()):
        self.teil, self._name, self.typ, self.unter = teil, name, typ, list(unter)
        self.unterdrueckt: set[str] = set()
        self._bruder = None
        for a, b in zip(self.unter, self.unter[1:]):
            a._bruder = b

    @property
    def GetTypeName2(self):
        return self.typ

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, wert):
        if not any(f._name == wert for f in self.teil.alle()):  # S18c: doppelt → still alt
            self._name = wert

    @property
    def GetNextFeature(self):
        kette = self.teil.ordnung[self.teil.aktiv]
        i = kette.index(self)
        return kette[i + 1] if i + 1 < len(kette) else None

    @property
    def GetFirstSubFeature(self):
        return self.unter[0] if self.unter else None

    @property
    def GetNextSubFeature(self):
        return self._bruder

    @property
    def GetFaces(self):
        return ()

    def Select2(self, anhaengen, marke):
        self.teil.auswahl = self
        return True

    def SetSuppression2(self, aktion, option, namen):
        self.teil.unterdrueckungen.append((self._name, aktion, option))
        for k in (namen.value if option == 3 else [self.teil.aktiv] if option == 1 else self.teil.konfigurationen):
            (self.unterdrueckt.add if aktion == 0 else self.unterdrueckt.discard)(k)
            for u in self.unter:
                (u.unterdrueckt.add if aktion == 0 else u.unterdrueckt.discard)(k)
        return True

    def IsSuppressed2(self, option, namen):
        # Live gemessen: Dokumentreihenfolge, egal wie die Namen geordnet sind (Nachträge aus Task 5)
        return tuple(k in self.unterdrueckt for k in self.teil.konfigurationen if k in namen.value)


class Dim:
    def __init__(self, teil, werte, einfrieren=False):
        self.teil, self.werte, self.einfrieren = teil, dict(werte), einfrieren
        self.gesetzt = []
        self.status = 0
        self.fest = dict(werte)

    def GetSystemValue3(self, option, namen):
        return (self.werte[self.teil.aktiv],)

    def SetSystemValue3(self, wert, option, namen):
        self.gesetzt.append((wert, option, None if namen is None else list(namen.value)))
        if self.status == 0:
            for k in (namen.value if option == 3 else self.teil.konfigurationen):
                self.werte[k] = wert
        return self.status

    def neuaufbau(self):
        if self.einfrieren:  # gesteuert: der Neuaufbau nimmt den Wert still zurück (S18c)
            self.werte = dict(self.fest)


class Gleichungen:
    def __init__(self, zeilen):
        self.zeilen = [dict(z) for z in zeilen]  # {"text", "global", "wert"}
        self.gesetzt = []

    @property
    def GetCount(self):
        return len(self.zeilen)

    def Equation(self, i):
        return self.zeilen[i]["text"]

    def GlobalVariable(self, i):
        return self.zeilen[i]["global"]

    def Value(self, i):
        return self.zeilen[i]["wert"]

    def SetEquationAndConfigurationOption(self, i, text, option, namen):
        self.gesetzt.append((i, text, option, namen))
        self.zeilen[i]["text"] = text
        rechts = text.split("=", 1)[1].strip()
        if rechts.replace(".", "", 1).isdigit():
            self.zeilen[i]["wert"] = float(rechts)
        return i  # S18c: kein Status


class Eigenschaften:
    def __init__(self, werte):
        self.werte = werte

    def Add3(self, name, typ, wert, option):
        self.werte[name] = wert
        return 0

    def Delete2(self, name):
        return 0 if self.werte.pop(name, None) is not None else 1

    def GetAll3(self, namen, typen, werte, aufgeloest, verknuepft):
        namen.value, werte.value = tuple(self.werte), tuple(self.werte.values())


class Erweiterung:
    def __init__(self, teil):
        self.teil = teil

    @property
    def GetWhatsWrongCount(self):
        return len(self.teil.fehler.get(self.teil.aktiv, []))

    def GetWhatsWrong(self, features, codes, warnungen):
        zeilen = self.teil.fehler.get(self.teil.aktiv, [])
        features.value = tuple(SimpleNamespace(Name=f) for f, _, _ in zeilen)
        codes.value = tuple(c for _, c, _ in zeilen)
        warnungen.value = tuple(w for _, _, w in zeilen)

    def DeleteSelection2(self, option):
        teil = self.teil
        weg = {teil.auswahl}
        if option & 1:
            offen = [teil.auswahl.Name]
            while offen:
                for n in teil.loescht_mit.get(offen.pop(), ()):
                    weg.add(teil.feature(n))
                    offen.append(n)
        if option & 2:
            weg |= {u for f in list(weg) for u in f.unter}
        for k in teil.ordnung:
            teil.ordnung[k] = [f for f in teil.ordnung[k] if f not in weg]
        return True

    def ReorderFeature(self, name, ziel, ort):
        """Wirkt nur in der aktiven Konfiguration (Sonde Task 6); ein unmöglicher Zug liefert False, die Konfiguration bleibt
        beschädigt (S18c3)."""
        teil = self.teil
        kette = teil.ordnung[teil.aktiv]
        f = teil.feature(name)
        if name in teil.reorder_unmoeglich:
            kette.remove(f)
            kette.insert(0, f)
            return False
        block = [x for x in kette if x is f or x in f.unter]
        rest = [x for x in kette if x not in block]
        i = rest.index(teil.feature(ziel)) + 1
        teil.ordnung[teil.aktiv] = rest[:i] + block + rest[i:]
        return True

    def CustomPropertyManager(self, k):
        return Eigenschaften(self.teil.eigenschaften.setdefault(k, {}))

    @property
    def CreateMassProperty2(self):
        teil = self.teil
        return SimpleNamespace(UseSystemUnits=True, Volume=teil.volumen.get(teil.aktiv, 0.0) * 1e-9, CenterOfMass=(0, 0, 0))

    @property
    def GetLicenseType(self):
        return self.teil.lizenz


class Teil:
    def __init__(self, pfad=None, konfigurationen=("Standard", "Variante B"), aktiv=None):
        self.pfad = pfad
        self.konfigurationen = list(konfigurationen)
        self.aktiv = aktiv or self.konfigurationen[0]
        self.ordnung: dict[str, list[Feat]] = {k: [] for k in self.konfigurationen}
        self.masse: dict[str, Dim] = {}
        self.gleichungen = Gleichungen([])
        self.fehler: dict[str, list] = {}
        self.volumen: dict[str, float] = dict.fromkeys(self.konfigurationen, 1000.0)
        self.eigenschaften: dict[str, dict] = {}
        self.material = dict.fromkeys(self.konfigurationen, "1.0038")
        self.loescht_mit: dict[str, list[str]] = {}
        self.reorder_unmoeglich: set[str] = set()
        self.unterdrueckungen = []
        self.auswahl = None
        self.bei_neuaufbau = None
        self.gespeichert = []  # aktive Konfiguration je Save3
        self.geschlossen = False
        self.lizenz = 2
        self.Extension = Erweiterung(self)

    def neues_feature(self, name, typ="Cut", unter=()):
        f = Feat(self, name, typ, unter)
        for k in self.konfigurationen:
            self.ordnung[k].append(f)
        return f

    def alle(self):
        kette = next(iter(self.ordnung.values()))
        return [*kette, *(u for f in kette for u in f.unter if u not in kette)]

    def feature(self, name):
        return next((f for f in self.alle() if f.Name == name), None)

    # IModelDoc2
    @property
    def FirstFeature(self):
        kette = self.ordnung[self.aktiv]
        return kette[0] if kette else None

    def FeatureByName(self, name):
        return self.feature(name)

    @property
    def GetConfigurationNames(self):
        return tuple(self.konfigurationen)

    def ShowConfiguration2(self, k):
        self.aktiv = k
        return True

    @property
    def ConfigurationManager(self):
        return SimpleNamespace(ActiveConfiguration=SimpleNamespace(Name=self.aktiv))

    @property
    def EditRebuild3(self):
        for d in self.masse.values():
            d.neuaufbau()
        if self.bei_neuaufbau is not None:
            self.bei_neuaufbau(self)
        return not any(not w for _, _, w in self.fehler.get(self.aktiv, []))

    def Parameter(self, name):
        return self.masse.get(name)

    @property
    def GetEquationMgr(self):
        return self.gleichungen

    def ClearSelection2(self, alle):
        self.auswahl = None

    def GetBodies2(self, typ, sichtbar):
        return ()

    def GetPartBox(self, welt):
        return (0.0,) * 6

    def GetMaterialPropertyName2(self, k, datenbank):
        return self.material[k or self.aktiv]

    def SetMaterialPropertyName2(self, k, datenbank, name):
        self.material[k or self.aktiv] = name

    @property
    def GetPathName(self):
        return str(self.pfad)

    @property
    def GetTitle(self):
        return self.pfad.name

    def Save3(self, optionen, fehler, warnungen):
        self.gespeichert.append(self.aktiv)
        self.pfad.write_bytes(b"gespeichert")
        return True


def teil_aus(aufnahme: dict, pfad=None) -> Teil:
    """Ein Teil im Stand einer Aufnahme: Baum, Maße, Gleichungen, Fehler, Volumen. Skizzen unter ihren Features wie in
    SolidWorks: Sie stehen in der Kette und zugleich als Unterfeature."""
    teil = Teil(pfad, aufnahme["konfigurationen"], aufnahme["aktiv"])
    daten = {f["name"]: f for f in aufnahme["features"]}
    feats = {n: Feat(teil, n, f["typ"]) for n, f in daten.items()}
    for n, f in daten.items():
        unter = [feats[e] for e in f["eltern"] if daten[e]["typ"] == "ProfileFeature"]
        feats[n].unter = unter
        for k, u in f["unterdrueckt"].items():
            if u:
                feats[n].unterdrueckt.add(k)
    for k in teil.konfigurationen:
        teil.ordnung[k] = [feats[n] for n in aufnahme["reihenfolge"][k]]
    for m in aufnahme["masse"]:
        teil.masse[m["name"]] = Dim(teil, {k: (v or 0.0) / 1000 for k, v in m["werte"].items()})
    teil.gleichungen = Gleichungen([{"text": g["text"], "global": g["global"],
                                     "wert": aufnahme["variablen"].get(g["links"], 0.0)} for g in aufnahme["gleichungen"]])
    teil.loescht_mit = {n: f["kinder"] for n, f in daten.items()}
    for e in aufnahme["neuaufbau"]:
        teil.fehler.setdefault(e["konfiguration"], []).append((e["feature"], e["code"], e["warnung"]))
    teil.volumen = {k: g["volumen"] for k, g in aufnahme["geometrie"].items()}
    return teil
