"""Baugruppen in SolidWorks lesen und fahren (Spec Bestandsdateien §8.1–§8.4, Plan Etappe 2 Task 8), Format `bestand.json` einer
Baugruppe. Liest Bestandskopie und Lauf gleich und ändert nur den Speicher, gespeichert wird hier nie.

UNGEMESSEN: Diese Schicht steht gegen den API-Index und Attrappen, Spike S19 kann sie korrigieren. Belegt sind nur `D1` und die
Variationen relativ zu `D1` (S13b D), `GetDocumentDependencies2` und das Öffnen (S18). Offen für S19: wie sich Grenzen erkennen
lassen, was `MateEntity(i).Reference` liefert, die Typnamen im Baum, ein Ordner unter den Verknüpfungen, `GetPathName` und
`GetComponents` bei Unterdrücktem, `IsFixed` in Unterbaugruppen (die API-Hilfe nennt nur die oberste Ebene).

Grundsatz: Was sich nicht lesen lässt, fehlt (bzw. `None`), `vergleich_baugruppe` macht daraus `ok: None`. Ausnahme ist die
unterdrückte Komponente: Sie hat kein Soll, trägt aber in jedem Feld je Konfiguration einen Eintrag, sonst wäre eine
unveränderte Baugruppe nie bewiesen. `kollisionen` ist `[]` nur nach erfolgreichem Lesen, `GetInterferenceCount` trennt „keine“
von „nicht gelesen“.

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  IAssemblyDoc.GetComponents(1), .InterferenceDetectionManager
  IInterferenceDetectionMgr.GetInterferenceCount(0), .GetInterferences(0), .TreatCoincidenceAsInterference, .Done(0)
  IInterference.Components, .Volume
  IComponent2.Name2, .GetPathName(0), .IsVirtual, .IsPatternInstance(0), .Solving (swComponentSolvingOption_e, Teil −1),
    .IsFixed(0), .GetConstrainedStatus(0: swConstrainedStatus_e), .ReferencedConfiguration, .Transform2,
    .GetSuppression2(0: swComponentSuppressionState_e swComponentSuppressed 0)
  IFeature.GetSpecificFeature2(0), .GetErrorCode2(1), .Parameter(1), .IsSuppressed2(2), .GetTypeName2(0)
  IMate2.Type (swMateType_e), .Alignment (swMateAlign_e), .GetMateEntityCount(0), .MateEntity(1), .MinimumVariation,
    .MaximumVariation
  IMateEntity2.Reference, .ReferenceComponent, .ReferenceType2 (swSelectType_e swSelDATUMPLANES 4, swSelDATUMAXES 5,
    swSelDATUMPOINTS 6)
  IModelDoc2.ForceRebuild3(1), .GetType(0: swDocumentTypes_e), .FeatureManager; IFeatureManager.GetFeatures(1: False alle Ebenen)
Typnamen laut Index zu IFeature.GetTypeName2: Reference, ReferencePattern, MateGroup, Mate…; ob die Baugruppe sie so meldet,
klärt S19f."""

import math
from dataclasses import replace
from pathlib import Path, PureWindowsPath

from swki.baugruppe import sw_baugruppe
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.baugruppe.sw_bewegung import SwMechanik
from swki.bestand.bewegung_bestand import SW_ABSTAND, SW_WINKEL, als_verknuepfung
from swki.bestand.folgen import vergleichsname
from swki.bestand.sw_bestand import (SW_EINHEITENSYSTEM, baum_features, datei_referenzen, eigenschaften_von, feature_eintrag,
                                     gleichungen_von, gleichungsdatei, ist_ordner, leite_masse, lies_masse, schalte, unterdrueckt,
                                     whats_wrong)
from swki.compiler.fehler import REBUILD_FEHLER, BauFehler
from swki.pruefung.messen import skizzenstatus
from swki.verbindung import in_mm, in_mm3
from swki.verbindung import wert as primitiv

VERKNUEPFUNG_UNERREICHT = "VERKNUEPFUNG_UNERREICHT"  # Warnung der Aufnahme: Der Baum erreicht nicht jede Verknüpfung
SW_UNTERDRUECKT = 0  # swComponentSuppressionState_e.swComponentSuppressed
SW_MATE_UNBEKANNT = 7  # swMateType_e.swMateUNKNOWN: Ersatz, wenn eine überall unterdrückte Verknüpfung nichts hergibt
AUSRICHTUNG_UNBEKANNT = -1  # kein swMateAlign_e: nur als Ersatz, in Bestand und Lauf gleich
SW_BEZUGSGEOMETRIE = frozenset({4, 5, 6})  # swSelectType_e: Ebene, Achse, Punkt sind Features, wählbar mit Select2
GLIEDER = frozenset({"Reference", "ReferencePattern"})  # IFeature.GetTypeName2 von Komponenten und Komponentenmustern, laut Index
MATE_VORSILBE = "Mate"   # MateGroup und alle Verknüpfungen (MateCoincident, MateDistanceDim …), laut Index


def _versuch(lesen):
    """Wert von `lesen()`, `None`, wenn SolidWorks ihn nicht hergibt (etwa an einer unterdrückten Komponente)."""
    try:
        return lesen()
    except Exception:
        return None


def ist_glied(typ: str) -> bool:
    return typ in GLIEDER or typ.startswith(MATE_VORSILBE)


def baum_ohne_glieder(model) -> list:
    """`baum_features` ohne Komponenten und Verknüpfungen: Die stehen in `komponenten` und `verknuepfungen`."""
    return baum_features(model, ist_glied)


def _je_konfiguration(asm, konfigurationen: list[str], lies) -> None:
    """`lies(k)` je Konfiguration nach dem Neuaufbau. `ForceRebuild3` statt `EditRebuild3`: Lage und Status stehen sonst über
    Unterbaugruppen veraltet (Diagnose 4b, Task 13), und ein geändertes Teil neben einer ungespeicherten Baugruppe zeigte die
    alte Lage. Die aktive Konfiguration steht danach wieder, auch nach einem Fehler."""
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    try:
        for k in konfigurationen:
            schalte(asm, k)
            asm.ForceRebuild3(False)
            lies(k)
    finally:
        schalte(asm, aktiv)


# --- Komponenten -------------------------------------------------------------------------------------------------------

def _rel(pfad: str, wurzel: Path, namen: dict[str, str]) -> str:
    """Pfad relativ zum Ordner der Baugruppe. Liegt er außerhalb (virtuelle Komponente unter Temp, gespeicherter Pfad einer
    unterdrückten, API-Hilfe `GetPathName`), zählt der Name; `namen` (Name klein → rel) ordnet ihn der Aufnahme zu, Dateinamen
    sind dort eindeutig."""
    p = PureWindowsPath(pfad)
    try:
        return p.relative_to(PureWindowsPath(wurzel)).as_posix()
    except ValueError:
        return namen.get(p.name.lower(), p.name)


def _komponente_stand(komp, k: str, e: dict, wurzel: Path, namen: dict[str, str]) -> None:
    """Eine Komponente in der aktiven Konfiguration `k` nach `e`."""
    e["gesehen"].add(k)
    if e["datei"] is None:
        e["datei"] = _versuch(lambda: _rel(primitiv(komp.GetPathName), wurzel, namen))
    if e["virtuell"] is None:
        e["virtuell"] = _versuch(lambda: bool(primitiv(komp.IsVirtual)))
    if e["muster"] is None:
        e["muster"] = _versuch(lambda: bool(primitiv(komp.IsPatternInstance)))
    if e["loesen"] is None:
        e["loesen"] = _versuch(lambda: int(primitiv(komp.Solving)))
    zustand = _versuch(lambda: primitiv(komp.GetSuppression2))
    weg = None if zustand is None else zustand == SW_UNTERDRUECKT
    werte = {"fixiert": _versuch(lambda: bool(primitiv(komp.IsFixed))),
             "status": _versuch(lambda: int(primitiv(komp.GetConstrainedStatus))),
             "konfigurationen": _versuch(lambda: komp.ReferencedConfiguration), "unterdrueckt": weg}
    for feld, wert in werte.items():
        if wert is not None:
            e[feld][k] = wert
    if weg:
        e["transform"][k] = None
    elif (t := _versuch(lambda: sw_baugruppe.transform(komp))) is not None:
        e["transform"][k] = t


def _leere_komponente() -> dict:
    return {"datei": None, "konfiguration": None, "konfigurationen": {}, "virtuell": None, "muster": None, "loesen": None,
            "fixiert": {},
            "unterdrueckt": {}, "status": {}, "transform": {}, "gesehen": set()}


def _vervollstaendige(roh: dict[str, dict], konfigurationen: list[str], aktiv: str) -> dict[str, dict]:
    """Was `GetComponents` in einer Konfiguration nicht nennt (Kind einer dort unterdrückten Unterbaugruppe), zählt als
    unterdrückt. Eine unterdrückte Komponente bekommt Einträge in allen Feldern: der in einer anderen Konfiguration gelesene
    Wert, sonst ein fester Ersatz, gleich in Bestand und Lauf. Bei einer aktiven bleibt die Lücke, sie heißt nicht gelesen."""
    for e in roh.values():
        for k in konfigurationen:
            if k not in e["gesehen"]:
                e["unterdrueckt"][k], e["transform"][k] = True, None
            if e["unterdrueckt"].get(k):
                for feld, ersatz in (("fixiert", False), ("status", 0), ("konfigurationen", "")):
                    e[feld].setdefault(k, next(iter(e[feld].values()), ersatz))
        e["konfiguration"] = e["konfigurationen"].get(aktiv)
        del e["gesehen"]
    return roh


def lies_komponenten(asm, konfigurationen: list[str], dateien=()) -> dict:
    """Alle Ebenen (`Name2` mit `/`) je Konfiguration nach dem Neuaufbau; unterdrückt: `transform` `null`. `dateien`: relative
    Pfade der Aufnahme, sie ordnen einen Pfad außerhalb der Kopie zu."""
    roh: dict[str, dict] = {}
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    _je_konfiguration(asm, konfigurationen, _komponenten_leser(asm, roh, dateien))
    return _vervollstaendige(roh, konfigurationen, aktiv)


def _komponenten_leser(asm, roh: dict[str, dict], dateien):
    wurzel = Path(primitiv(asm.GetPathName)).parent
    namen = {PureWindowsPath(rel).name.lower(): rel for rel in dateien}

    def lies(k: str) -> None:
        for komp in asm.GetComponents(False) or ():
            _komponente_stand(komp, k, roh.setdefault(komp.Name2, _leere_komponente()), wurzel, namen)

    return lies


# --- Verknüpfungen -----------------------------------------------------------------------------------------------------

def _partner(mate) -> list:
    """Komponentennamen der Entitäten; `None` an einer Stelle ist eine Ebene oder Achse der Hauptbaugruppe (`ReferenceComponent`
    ohne Komponente, S19a)."""
    aus = []
    for i in range(int(primitiv(mate.GetMateEntityCount))):
        komp = mate.MateEntity(i).ReferenceComponent
        aus.append(None if komp is None else komp.Name2 or None)
    return aus


def _zahlen(feature, mate, typ: int) -> dict | None:
    """`{wert, min, max}` in mm bzw. Grad; `None` in einem Feld: trägt keinen Wert. Abstand und Winkel haben das Maß `D1`
    (aktueller Wert), die Variationen sind relativ dazu (S13b D); eine Grenze zeigt sich an einer Variation ungleich 0. Nicht
    lesbar: `None`."""
    if typ not in (SW_ABSTAND, SW_WINKEL):
        return {"wert": None, "min": None, "max": None}
    try:
        roh, unten, oben = feature.Parameter(sw_baugruppe.MASS_NAME).SystemValue, mate.MinimumVariation, mate.MaximumVariation
    except Exception:
        return None
    einheit = in_mm if typ == SW_ABSTAND else math.degrees
    grenze = bool(unten) or bool(oben)
    return {"wert": round(einheit(roh), 6), "min": round(einheit(roh + unten), 6) if grenze else None,
            "max": round(einheit(roh + oben), 6) if grenze else None}


def _verknuepfung_stand(f, k: str, e: dict) -> None:
    """Eine Verknüpfung in der aktiven Konfiguration `k` nach `e`. Unterdrückt gibt sie womöglich nichts her: Das bleibt
    ungelesen."""
    if (weg := _versuch(lambda: unterdrueckt(f, k))) is not None:
        e["unterdrueckt"][k] = weg
    if (code := _versuch(lambda: sw_baugruppe.fehlercode(f))) is not None:
        e["fehler"][k] = code
    mate = _versuch(lambda: f.GetSpecificFeature2)
    if mate is None:
        return
    if e["typ"] is None:
        e["typ"] = _versuch(lambda: int(mate.Type))
    if e["ausrichtung"] is None:
        e["ausrichtung"] = _versuch(lambda: int(mate.Alignment))
    if e["partner"] is None:
        e["partner"] = _versuch(lambda: _partner(mate))
    if e["typ"] is not None and (zahlen := _zahlen(f, mate, e["typ"])) is not None:
        e["werte"][k] = zahlen


def _leere_verknuepfung(gesteuert: bool) -> dict:
    return {"typ": None, "ausrichtung": None, "wert": None, "min": None, "max": None, "werte": {}, "grenze": None,
            "gesteuert": gesteuert,
            "partner": None, "fehler": {}, "unterdrueckt": {}}


def _gesteuerte(gleichungen: list[dict]) -> set[str]:
    return {vergleichsname(g["links"]) for g in gleichungen}


def _verknuepfungen_leser(asm, roh: dict[str, dict], gesteuert: set[str]):
    def lies(k: str) -> None:
        for f in sw_baugruppe.verknuepfungen(asm):
            name = f.Name
            e = roh.setdefault(name, _leere_verknuepfung(vergleichsname(f"{sw_baugruppe.MASS_NAME}@{name}") in gesteuert))
            _verknuepfung_stand(f, k, e)

    return lies


def _ersetze_unterdrueckte(e: dict, konfigurationen: list[str]) -> None:
    """Wie `_vervollstaendige`: Eine unterdrückte Verknüpfung hat kein Soll, trägt aber je Konfiguration Einträge, sonst wäre
    eine unveränderte Baugruppe nie bewiesen. Werte aus einer anderen Konfiguration, sonst „trägt keinen Wert“. Ist sie überall
    unterdrückt und gab nichts her, stehen Ersatzwerte da, die nichts behaupten; in beiden Ständen sind sie gleich, aktiviert
    jemand sie, weicht alles ab."""
    leer = {"wert": None, "min": None, "max": None}
    for k in konfigurationen:
        if e["unterdrueckt"].get(k):
            e["werte"].setdefault(k, next(iter(e["werte"].values()), leer))
            e["fehler"].setdefault(k, 0)
    if all(e["unterdrueckt"].get(k) for k in konfigurationen):
        for feld, ersatz in (("typ", SW_MATE_UNBEKANNT), ("ausrichtung", AUSRICHTUNG_UNBEKANNT), ("partner", [])):
            if e[feld] is None:
                e[feld] = ersatz


def _werte_der_aktiven(roh: dict[str, dict], konfigurationen: list[str], aktiv: str) -> dict[str, dict]:
    """Unterdrückte ergänzt; `wert`, `min`, `max` der aktiven Konfiguration; `grenze`: in einer gelesenen Konfiguration trägt sie
    Grenzen."""
    for e in roh.values():
        _ersetze_unterdrueckte(e, konfigurationen)
        e.update(e["werte"].get(aktiv, {}))
        if e["werte"]:
            e["grenze"] = any(z["min"] is not None or z["max"] is not None for z in e["werte"].values())
    return roh


def lies_verknuepfungen(asm, konfigurationen: list[str]) -> dict:
    """Verknüpfungen je Konfiguration nach dem Neuaufbau, Format `bestand.json`."""
    roh: dict[str, dict] = {}
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    _je_konfiguration(asm, konfigurationen, _verknuepfungen_leser(asm, roh, _gesteuerte(gleichungen_von(asm)[0])))
    return _werte_der_aktiven(roh, konfigurationen, aktiv)


def gegenprobe_verknuepfungen(asm, gelesen) -> list[dict]:
    """Warnungen, wenn der Baumweg nicht jede Verknüpfung erreicht: `IFeatureManager.GetFeatures(False)` nennt alle Features des
    Dokuments in beliebiger Reihenfolge, ohne Struktur. Der Vergleich sähe eine fehlende nie, Bestand und Lauf läsen gleich; so
    ist es auch dann nicht still, wenn S19f eine andere Baumform zeigt als angenommen. Nicht lesbar ist selbst eine Warnung."""
    try:
        typen = {f.Name: f.GetTypeName2 for f in asm.FeatureManager.GetFeatures(False) or ()}
    except Exception as e:
        return [{"code": VERKNUEPFUNG_UNERREICHT, "verknuepfungen": None,
                 "meldung": f"Gegenprobe der Verknüpfungen nicht lesbar ({type(e).__name__}: {e}), Vollständigkeit nicht belegt"}]
    fehlen = sorted(n for n, typ in typen.items()
                    if typ.startswith(MATE_VORSILBE) and typ != "MateGroup" and not ist_ordner(typ) and n not in gelesen)
    if not fehlen:
        return []
    return [{"code": VERKNUEPFUNG_UNERREICHT, "verknuepfungen": fehlen,
             "meldung": f"Verknüpfungen, die der Baum nicht erreicht, sind weder gelesen noch gefahren: {', '.join(fehlen)}"}]


# --- Kollision ----------------------------------------------------------------------------------------------------------

def lies_kollisionen(asm) -> list[dict] | None:
    """Überlappungen `{paar, volumen}` der aktiven Konfiguration, Berührung zählt nicht; `None`, wenn sie nicht gelesen sind:
    `GetInterferences` liefert auch dann nichts, wenn es gescheitert ist, nur der Zähler trennt das von „keine“."""
    try:
        idm = asm.InterferenceDetectionManager
        try:
            idm.TreatCoincidenceAsInterference = False
            anzahl = int(primitiv(idm.GetInterferenceCount))
            liste = list(idm.GetInterferences or ())
            if len(liste) != anzahl:
                return None
            return [{"paar": sorted(k.Name2 for k in (i.Components or ())), "volumen": round(in_mm3(i.Volume), 3)} for i in liste]
        finally:
            sw_baugruppe.rufe(idm, "Done")
    except Exception:
        return None


# --- Die ganze Baugruppe ---------------------------------------------------------------------------------------------------

def lies_baugruppe(app, asm, dateien=(), kollision: bool = True) -> dict:
    """Aufnahme einer offenen Baugruppe im Format `bestand.json` ohne `datei`, `dateien`, `bewegungen`, `sw_jahr` (setzt der
    Aufrufer). Die Felder von `eigenschaften` bis `geometrie` sind die von Etappe 1, `features`, `reihenfolge` und `masse`
    lassen Komponenten und Verknüpfungen aus; Material und Geometrie hat die Baugruppe nicht. Liest in einem Durchgang je
    Konfiguration, die aktive steht vorn und ist danach wieder aktiv, gespeichert wird nichts. `kollision=False`: `kollisionen`
    bleibt `None` (Aufrufer misst sie extra oder braucht sie nicht, Unterbaugruppe)."""
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    konfigurationen = [aktiv] + [k for k in asm.GetConfigurationNames if k != aktiv]
    tabelle = bool(asm.Extension.HasDesignTable)
    gleichungen, variablen = gleichungen_von(asm)
    d: dict = {"version": 2, "art": "baugruppe", "konfigurationen": konfigurationen, "aktiv": aktiv,
               "einheitensystem": asm.Extension.GetUserPreferenceInteger(SW_EINHEITENSYSTEM, 0), "tabelle": tabelle,
               "eigenschaften": {"datei": eigenschaften_von(asm, ""),
                                 "konfiguration": {k: eigenschaften_von(asm, k) for k in konfigurationen}},
               "externe_referenzen": datei_referenzen(asm) + gleichungsdatei(asm), "gleichungen": gleichungen,
               "variablen": variablen,
               "skizzen": skizzenstatus(asm), "material": "", "materialien": {}, "geometrie": {}, "messung": {}}
    komponenten, verknuepfungen, neuaufbau, reihenfolge, masse = {}, {}, [], {}, {}
    lies_komp = _komponenten_leser(asm, komponenten, dateien)
    lies_mate = _verknuepfungen_leser(asm, verknuepfungen, _gesteuerte(gleichungen))

    def lies(k: str) -> None:
        neuaufbau.extend({"konfiguration": k, **f} for f in whats_wrong(asm))
        features = baum_ohne_glieder(asm)
        if k == aktiv:
            d["features"] = [feature_eintrag(f, konfigurationen, tabelle) for f in features]
        reihenfolge[k] = [f.Name for f in features]
        lies_masse(features, k, konfigurationen, masse)
        lies_komp(k)
        lies_mate(k)

    _je_konfiguration(asm, konfigurationen, lies)
    return d | {"reihenfolge": reihenfolge, "masse": leite_masse(list(masse.values()), gleichungen), "neuaufbau": neuaufbau,
                "komponenten": _vervollstaendige(komponenten, konfigurationen, aktiv),
                "verknuepfungen": _werte_der_aktiven(verknuepfungen, konfigurationen, aktiv),
                "kollisionen": lies_kollisionen(asm) if kollision else None,
                "warnungen": gegenprobe_verknuepfungen(asm, verknuepfungen)}


# --- Mechanik -----------------------------------------------------------------------------------------------------------------

def _entitaeten(feature) -> list[tuple[object, bool]]:
    """Die Entitäten einer Grenze wie `sw_baugruppe.in_baugruppe`: (Objekt, ist Feature). Für `treibe` an denselben Flächen
    (S19b)."""
    mate = feature.GetSpecificFeature2
    seiten = [mate.MateEntity(i) for i in range(int(primitiv(mate.GetMateEntityCount)))]
    return [(s.Reference, primitiv(s.ReferenceType2) in SW_BEZUGSGEOMETRIE) for s in seiten]


class BestandMechanik(SwMechanik):
    """Die Mechanik an einer Bestandskopie oder einem Lauf. Eine Kollision, die sich nicht lesen lässt, bricht die Fahrt ab
    (laut, `fahre_bestand`): `sw_baugruppe.interferenzen` machte daraus still „keine“, und ein bestandenes `bewegung_kollision`
    hieße nichts. Ein Antrieb, der sich nicht anlegen lässt, kostet dagegen nur seine Grenze (§8.4, Ruling Task 6 präzisiert);
    Fehler ohne Bezug zu einer Grenze bleiben laut."""

    def halte(self, b, wert: float) -> None:
        if b.name in self.antriebe:
            super().halte(b, wert)
            return
        try:
            super().halte(b, wert)
        except StellungFehler:
            raise
        except Exception as e:  # jeder Fehler beim Anlegen, auch COM: `verknuepfe` hat seine Verknüpfung schon wieder gelöscht
            raise StellungFehler(b.name, wert, f"Antrieb nicht angelegt: {e}") from e

    def interferenzen(self) -> list[dict]:
        gelesen = lies_kollisionen(self.asm)
        if gelesen is None:
            raise BauFehler(REBUILD_FEHLER, "Kollision in der Fahrt nicht lesbar", schritt="kollision")
        return gelesen


def mechanik_fuer(app, asm, grenzen: dict, aufnahme: dict, ordner: Path | None) -> SwMechanik:
    """Mechanik der Grenzen (Name → Eintrag aus `verknuepfungen`) an der offenen Baugruppe: nur oberste Ebene, nur nicht
    unterdrückte Komponenten. Die Entitäten werden hier gelesen, vor `fahre`, das die Grenzen unterdrückt; gibt eine sie nicht
    her, fällt nur diese Grenze heraus (`StellungFehler` beim Anlegen des Antriebs). Die Verknüpfungsfehler der Aufnahme gehen
    als `bekannte_fehler` mit: Alte Fehler stoppen die Fahrt nicht, neue schon. `ordner`: Bilder der Fahrt, `None` ohne
    Fenster."""
    handles = {f.Name: f for f in sw_baugruppe.verknuepfungen(asm)}
    entitaeten: dict[str, list | str] = {}
    verknuepfungen = {}
    for name, v in grenzen.items():
        if v.get("typ") not in (SW_ABSTAND, SW_WINKEL):
            continue  # `fahre_bestand` vermerkt sie als nicht fahrbar
        try:
            entitaeten[name] = _entitaeten(handles[name])
        except Exception as e:
            entitaeten[name] = f"{type(e).__name__}: {e}"
        roh = als_verknuepfung(name, v)
        verknuepfungen[name] = replace(roh, a={**roh.a, "grenze": name}, b={**roh.b, "grenze": name})

    def entitaet(seite: dict) -> tuple[object, bool]:
        name, gelesen = seite["grenze"], entitaeten[seite["grenze"]]
        if isinstance(gelesen, str) or seite["index"] >= len(gelesen):
            grund = gelesen if isinstance(gelesen, str) else f"Entität {seite['index']} fehlt"
            raise StellungFehler(name, float(grenzen[name].get("min") or 0.0), f"Entitäten der Grenze nicht lesbar: {grund}")
        return gelesen[seite["index"]]

    komponenten = {k.Name2: k for k in sw_baugruppe.komponenten(asm) if primitiv(k.GetSuppression2) != SW_UNTERDRUECKT}
    aktiv = aufnahme["aktiv"]
    bekannt = {n for n, v in (aufnahme.get("verknuepfungen") or {}).items() if (v.get("fehler") or {}).get(aktiv)}
    bekannt |= {e["feature"] for e in aufnahme.get("neuaufbau") or [] if e["konfiguration"] == aktiv and not e["warnung"]}
    return BestandMechanik(app, asm, verknuepfungen, entitaet, komponenten, ordner, bekannt)
