"""SolidWorks-Grundfunktionen für Baugruppen (Late Binding, Spike S12; Konstanten aus dem API-Index).

Nullargumentige Member ohne "()"; nullargumentige Aktionen (FixComponent, EditDelete, Done) über rufe(), das sie als
Methode markiert – so ist es egal, ob pywin32 sie beim Attributzugriff schon ausführen würde (S9a) oder nicht (S5)."""

import math
from pathlib import Path

from swki.baugruppe.fehler import KOMPONENTE_FEHLER, VERKNUEPFUNG_FEHLER
from swki.compiler import sw
from swki.compiler.anker import AnkerFehler
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, GLEICHUNG_FEHLER, REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.spec.ausdruck import auswerten, ist_ausdruck, sw_ausdruck
from swki.verbindung import byref_bool, byref_long, grad, in_mm, in_mm3, mm, r8_array

MATE_TYP = {"deckungsgleich": 0, "konzentrisch": 1, "senkrecht": 2, "parallel": 3, "abstand": 5, "winkel": 6}  # swMateType_e
AUSRICHTUNG = {"gleich": 0, "entgegengesetzt": 1}  # swMateAlign_e ALIGNED / ANTI_ALIGNED (Spike S12 Zeile 5)
NAECHSTE = 2  # swMateAlign_e.swMateAlignCLOSEST (Spike S12 Zeile 5)
SW_MATE_OK = 1  # swAddMateError_e.swAddMateError_NoError
MARKE = 1  # Auswahlmarke für AddMate5 (Spike S6/S12)
MASS_NAME = "D1"  # Maß einer Abstands-/Winkelverknüpfung (Spike S12 Zeile 8)
IDENTITAET = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
_TOL_LAGE = 1e-9


def ausrichtungen(v) -> list[int]:
    """Ausrichtung der Verknüpfung als Liste mit genau einem Versuch: die angegebene; ohne Angabe (nur konzentrisch)
    NAECHSTE (swMateAlignCLOSEST) – SolidWorks behält dann die schon festgelegte Richtung (Spike S12 Zeile 5)."""
    if v.ausrichtung:
        return [AUSRICHTUNG[v.ausrichtung]]
    return [NAECHSTE]


def umgekehrte(gesetzt: dict[str, int], ist: dict[str, int]) -> list[str]:
    """Namen aus `gesetzt`, deren Ausrichtung in `ist` abweicht (Reihenfolge von `gesetzt`). SolidWorks kehrt die
    Ausrichtung einer früheren Verknüpfung still um, wenn eine spätere widerspricht (Spike S12 Zeile 5); fehlt ein
    Name in `ist`, zählt er nicht als umgekehrt."""
    return [name for name, soll in gesetzt.items() if name in ist and ist[name] != soll]


def rufe(objekt, name: str):
    """Nullargumentige COM-Methode sicher aufrufen."""
    objekt._FlagAsMethod(name)
    return getattr(objekt, name)()


def neue_baugruppe(app, vorlage: Path):
    asm = app.NewDocument(str(vorlage), 0, 0, 0)
    if asm is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"NewDocument mit {vorlage} fehlgeschlagen", schritt="dokument")
    return asm


def fuege_ein(app, asm, pfad: Path, box_mm: list[float]):
    """Komponente mit Ursprung im Baugruppenursprung, ohne Drehung. AddComponent5 setzt das Zentrum der Bounding-Box
    (Spike S6) – deshalb das Boxzentrum übergeben; liegt der Ursprung trotzdem nicht im Nullpunkt, Identität setzen."""
    mitte = [mm((box_mm[i] + box_mm[i + 3]) / 2) for i in range(3)]
    komp = asm.AddComponent5(str(pfad), 0, "", False, "", *mitte)
    if komp is None:
        raise BauFehler(KOMPONENTE_FEHLER, f"AddComponent5 {pfad.name} fehlgeschlagen", schritt="einfuegen")
    t = komp.Transform2.ArrayData
    if any(abs(t[i] - IDENTITAET[i]) > _TOL_LAGE for i in range(12)):
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(IDENTITAET)))
    return komp


def fixiere(asm, komp) -> None:
    sw.auswahl_leeren(asm)
    if not komp.Select4(False, asm.SelectionManager.CreateSelectData, False):
        raise BauFehler(KOMPONENTE_FEHLER, f"{komp.Name2}: Auswahl zum Fixieren fehlgeschlagen", schritt="fixieren")
    rufe(asm, "FixComponent")
    sw.auswahl_leeren(asm)
    if not komp.IsFixed:
        raise BauFehler(KOMPONENTE_FEHLER, f"{komp.Name2} ließ sich nicht fixieren", schritt="fixieren")


def in_baugruppe(komp, ref) -> tuple[object, bool]:
    """Entität im Baugruppenkontext: Bezugs-/Standardgeometrie über IComponent2.FeatureByName, Flächen über
    GetCorrespondingEntity (Spike S12 Zeile 3)."""
    objekt = komp.FeatureByName(ref.objekt.Name) if ref.ist_feature else komp.GetCorrespondingEntity(ref.objekt)
    if objekt is None:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{komp.Name2}: Referenz im Baugruppenkontext nicht gefunden")
    return objekt, ref.ist_feature


def waehle(asm, entitaet: tuple[object, bool], anhaengen: bool) -> None:
    objekt, ist_feature = entitaet
    if ist_feature:
        ok = objekt.Select2(anhaengen, MARKE)
    else:
        daten = asm.SelectionManager.CreateSelectData
        daten.Mark = MARKE
        ok = objekt.Select4(anhaengen, daten)
    if not ok:
        raise BauFehler(VERKNUEPFUNG_FEHLER, "Auswahl für die Verknüpfung fehlgeschlagen", schritt="auswahl")


def verknuepfungen(asm) -> list:
    """Verknüpfungs-Features (Unterfeatures des Ordners vom Typ MateGroup) in Baumreihenfolge."""
    f = asm.FirstFeature
    while f is not None and f.GetTypeName2 != "MateGroup":
        f = f.GetNextFeature
    ergebnis, unter = [], (f.GetFirstSubFeature if f is not None else None)
    while unter is not None:
        ergebnis.append(unter)
        unter = unter.GetNextSubFeature
    return ergebnis


def fehlercode(feature) -> int:
    return int(feature.GetErrorCode2(byref_bool()))


def _loesche(asm, feature) -> None:
    sw.auswahl_leeren(asm)
    feature.Select2(False, 0)
    rufe(asm, "EditDelete")
    sw.auswahl_leeren(asm)


def _loesche_still(asm, feature) -> None:
    """Wie _loesche, aber ohne Ausnahme: in einem Fehlerzweig darf das Aufräumen die Ursache nicht verdecken."""
    try:
        _loesche(asm, feature)
    except Exception:
        pass


def ausrichtung_von(feature) -> int:
    """Ausrichtung einer Verknüpfung (swMateAlign_e) aus IMate2.Alignment."""
    return int(feature.GetSpecificFeature2.Alignment)


class _Umkehr(BauFehler):
    """Eine spätere Verknüpfung hat die Ausrichtung einer früheren umgekehrt."""


def _pruefe_ausrichtungen(asm, v, gesetzt: dict[str, int]) -> None:
    features = {f.Name: f for f in verknuepfungen(asm)}
    ist = {name: ausrichtung_von(features[name]) for name in gesetzt if name in features}
    if umgekehrt := umgekehrte(gesetzt, ist):
        raise _Umkehr(VERKNUEPFUNG_FEHLER, f"{v.id} kehrt die Ausrichtung von {', '.join(umgekehrt)} um",
                      schritt="verknuepfung")


def verknuepfe(asm, v, a: tuple[object, bool], b: tuple[object, bool], parameter: dict,
               gesetzt: dict[str, int] | None = None):
    """Verknüpfung v anlegen (AddMate5, ein Versuch), als v.id benennen, neu aufbauen, Wert ggf. per Gleichung an die
    Parameter binden. Jede Ausnahme nach dem Anlegen löscht die neue Verknüpfung wieder.

    `gesetzt` (Verknüpfungs-ID → ausdrücklich festgelegte swMateAlign_e-Ausrichtung) reicht der Aufrufer durch alle
    Verknüpfungen: SolidWorks kehrt die Ausrichtung einer früheren Verknüpfung still um, wenn eine spätere widerspricht
    (Spike S12 Zeile 5; kein Status, kein Fehlercode). Nach dem Anlegen wird die Ausrichtung aller dort genannten
    Verknüpfungen zurückgelesen; ist eine umgekehrt, wird v wieder gelöscht und VERKNUEPFUNG_FEHLER gemeldet. Bei Erfolg
    wird v mit ausdrücklicher Ausrichtung eingetragen; Verknüpfungen ohne Angabe (NAECHSTE) bleiben draußen, ihre
    Richtung ist frei."""
    wert = auswerten(v.wert, parameter) if v.wert is not None else 0.0
    abstand = mm(wert) if v.typ == "abstand" else 0.0
    winkel = grad(wert) if v.typ == "winkel" else 0.0
    [code] = ausrichtungen(v)
    vorher = len(verknuepfungen(asm))
    sw.auswahl_leeren(asm)
    waehle(asm, a, False)
    waehle(asm, b, True)
    status = byref_long()
    mate = asm.AddMate5(MATE_TYP[v.typ], code, False, abstand, abstand, abstand, 1, 1, winkel, winkel, winkel,
                        False, v.drehung_sperren, 0, status)
    sw.auswahl_leeren(asm)
    alle = verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    try:
        if neu is None or status.value != SW_MATE_OK:
            raise BauFehler(VERKNUEPFUNG_FEHLER, f"AddMate5 meldet Status {status.value}", schritt="verknuepfung")
        neu.Name = v.id
        sw.rebuild(asm)
        if fc := fehlercode(neu):
            raise BauFehler(VERKNUEPFUNG_FEHLER, f"Fehlercode {fc}", schritt="verknuepfung")
        if gesetzt:
            _pruefe_ausrichtungen(asm, v, gesetzt)  # vor der Gleichung: bei einer Umkehr bleibt keine Gleichung stehen
        if ist_ausdruck(v.wert):
            if asm.GetEquationMgr.Add2(-1, f'"{MASS_NAME}@{v.id}" = {sw_ausdruck(v.wert)}', True) < 0:
                raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {v.id} = {v.wert} abgelehnt", schritt="gleichung")
            sw.rebuild(asm)
    except _Umkehr:
        _loesche_still(asm, neu)
        raise
    except Exception as e:  # auch fremde Ausnahmen (z. B. COM beim Rücklesen): die neue Verknüpfung nicht stehen lassen
        if neu is not None:
            _loesche_still(asm, neu)
        meldung = str(e) if isinstance(e, BauFehler) else f"{type(e).__name__}: {e}"
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): {meldung}", schritt="verknuepfung") from e
    if gesetzt is not None and v.ausrichtung:
        gesetzt[v.id] = AUSRICHTUNG[v.ausrichtung]
    return neu


def komponenten(asm) -> list:
    return list(asm.GetComponents(True) or ())


def transform(komp) -> list[float]:
    return list(komp.Transform2.ArrayData)


def status(komp) -> int:
    return int(komp.GetConstrainedStatus)


def ist_fixiert(komp) -> bool:
    return bool(komp.IsFixed)


def interferenzen(asm) -> list[tuple[list[str], float]]:
    """Überlappungen als ([Name2 der Komponenten], Volumen in mm³); Berührung zählt nicht (Spec 3b §9.3)."""
    idm = asm.InterferenceDetectionManager
    try:
        idm.TreatCoincidenceAsInterference = False
        return [([k.Name2 for k in (i.Components or ())], in_mm3(i.Volume)) for i in (idm.GetInterferences or ())]
    finally:
        rufe(idm, "Done")


def huellquader(asm) -> list[float]:
    """[xmin, ymin, zmin, xmax, ymax, zmax] in mm (IAssemblyDoc.GetBox, ohne Bezugsgeometrie)."""
    return [in_mm(x) for x in asm.GetBox(0)]


def masse_kg(asm) -> float:
    mp = asm.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return float(mp.Mass)


def aufloesen(asm) -> None:
    """Leichtgewichtige Komponenten auflösen (nach OpenDoc6), damit Kollision und Geometrie vollständig sind."""
    asm.ResolveAllLightWeightComponents(False)


def verknuepfungswerte(asm) -> dict[str, float]:
    """Wert jeder Abstands- (mm) und Winkelverknüpfung (Grad) nach Feature-Namen."""
    werte = {}
    for f in verknuepfungen(asm):
        typ = f.GetSpecificFeature2.Type
        if typ in (MATE_TYP["abstand"], MATE_TYP["winkel"]) and (mass := f.Parameter(MASS_NAME)) is not None:
            werte[f.Name] = in_mm(mass.SystemValue) if typ == MATE_TYP["abstand"] else math.degrees(mass.SystemValue)
    return werte
