"""Maße in der Zeichnung (Z1.3 Stufe 2; Design §6.1/§6.2, Plan 2026-11-17 Stufe 2 Task 5).

Ablauf `bemasse`: Modellmaße mit `InsertModelAnnotations4` (HiddenFeatureDims=True, Spike Z1.0) in alle Ansichten
einfügen → je Plan-Maß die Ansichten, in denen SolidWorks es zeigt (Kandidaten) → `ordne_zu` mit Obergrenze → bei
Bedarf eine weitere Ansicht (höchstens zwei Runden) → Duplikate und Nicht-Plan-Maße in der Zeichnung löschen (die
Teildatei bleibt unverändert). Neue Maße (Drehteil: Ø, Längen) gehen in die Hauptansicht und werden über Kanten gesetzt.

API (swki api methode, SW 2025): IView.GetDisplayDimensions (0, 2009); IDisplayDimension.GetDimension2 (1, 2008),
GetAnnotation, SetText (2; swDimensionTextPrefix = 1); IAnnotation.Select2 (2); IModelDocExtension.DeleteSelection2
(1, 2006); IModelDoc2.AddDimension2 (3); IView.GetVisibleEntities2 (2, 2014; swViewEntityType_Edge = 1), SelectEntity (2); ICurve.LineParams;
IModelDocExtension.AlignDimensions (2, 2011; swAlignDimensionType_AutoArrange = 0), SelectByID2 (9);
IDrawingDoc.InsertModelAnnotations4 (8, 2024; swInsertDimensionsMarkedForDrawing = 32768), ActivateView (1).
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import win32com.client.dynamic

from swki.verbindung import callout_leer
from swki.zeichnung.massplan import Mass
from swki.zeichnung.zuordnung import ordne_zu

MARKIERTE_MASSE = 32768 | 131072  # swInsertDimensionsMarkedForDrawing | swInsertHoleWizardLocationDimensions
KANTE = 1                # swViewEntityType_e.swViewEntityType_Edge
SILHOUETTE = 4           # swViewEntityType_e.swViewEntityType_SilhouetteEdge
PRAEFIX = 1              # swDimensionTextParts_e.swDimensionTextPrefix
AUTO_ANORDNEN = 0        # swAlignDimensionType_e.swAlignDimensionType_AutoArrange
DURCHMESSER = "<MOD-DIAM>"
MASSABSTAND_M = 0.008    # Abstand neuer Maße untereinander (R-Kap. 4: 7 mm, Widerspruch 5 mm; Hausregel bis Z1.5)
_TOL = 1e-6

EINZELHEIT_MIN = 3  # so viele Maße braucht ein Merkmal, damit sich eine Einzelheit lohnt


@dataclass
class Ergebnis:
    je_ansicht: dict[str, list[str]]
    neu: dict[str, list[str]] = field(default_factory=dict)
    gesetzt: int = 0
    geloescht: int = 0
    meldungen: list[str] = field(default_factory=list)


def _ruf(obj, name, *args):
    x = getattr(obj, name)
    if args:
        return x(*args)
    return x if isinstance(x, win32com.client.dynamic.CDispatch) or not callable(x) else x()


def kurzname(dd) -> str:
    """'D3@t1_skizze@Teil.Part' → 'D3@t1_skizze' (Maßprotokoll-Name ohne Dokument)."""
    return _ruf(dd.GetDimension2(0), "FullName").rsplit("@", 1)[0]


def _anzeige(view) -> list:
    return list(_ruf(view, "GetDisplayDimensions") or ())


def _einfuegen(drw, view, alle: bool) -> None:
    """Bei `alle=False` fügt SolidWorks laut Hilfe nur in die *ausgewählte* Ansicht ein – Auswahl dann stehen lassen
    (Review I5; im Live-Lauf mit erzwungener Zusatzansicht noch ungeprüft)."""
    name = _ruf(view, "GetName2")
    drw.ClearSelection2(True)
    _ruf(drw, "Extension").SelectByID2(name, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
    drw.ActivateView(name)
    if alle:
        drw.ClearSelection2(True)
    drw.InsertModelAnnotations4(0, MARKIERTE_MASSE, alle, False, True, False, False, False)


def kandidaten(views: dict, plan: list[Mass]) -> dict[str, list[str]]:
    namen = {m.name: m.id for m in plan if m.name}
    kand = {m.id: [] for m in plan}
    for rolle, v in views.items():
        for dd in _anzeige(v):
            mid = namen.get(kurzname(dd))
            if mid is not None and rolle not in kand[mid]:
                kand[mid].append(rolle)
    return kand


def _nach_blickachse(kand: dict[str, list[str]], plan: list[Mass], achsen: dict[str, int]) -> dict[str, list[str]]:
    """Nutzer 18.11.2026: SolidWorks fügt Skizzenmaße in jede parallele Ansicht ein, auch wo das Merkmal nicht sichtbar
    ist. Ein Maß mit bekannter Achse bleibt nur in Ansichten, deren Blickachse passt (flach: gleich, quer: verschieden)."""
    aus = {}
    for m in plan:
        if m.achse is None or m.modus is None:
            aus[m.id] = kand[m.id]
            continue
        aus[m.id] = [r for r in kand[m.id] if r not in achsen or (achsen[r] == m.achse) == (m.modus == "flach")]
    return aus


def _loesche(drw, dd) -> None:
    """Live Z1.3 Stufe 2 (spikes/z1_diag_loeschen.py): `Select3(…, callout_leer())` wählt nichts aus, `EditDelete` wirkt
    dann nicht; `Select2(False, 0)` + `DeleteSelection2(0)` entfernt das Maß aus der Ansicht."""
    drw.ClearSelection2(True)
    _ruf(dd, "GetAnnotation").Select2(False, 0)
    _ruf(drw, "Extension").DeleteSelection2(0)


def bemasse(drw, views: dict, plan: list[Mass], rollen: list[str], max_je: int, weitere: list[str],
            neue_ansicht: Callable[[str], object] | None, vorzug: dict[str, str] | None = None,
            blickachsen: dict[str, int] | None = None,
            einzelheit: Callable[[str, list[str]], object] | None = None, ausser: set[str] | None = None) -> Ergebnis:
    """`rollen`: Vorrang der vorhandenen Ansichten (Hauptansicht zuerst); `weitere`: Rollen, die bei Bedarf als
    Projektion entstehen (`neue_ansicht(rolle)` erzeugt sie). Bleibt eine Ansicht über der Obergrenze, lagert
    `einzelheit(rolle, maßnamen)` das Merkmal mit den meisten Maßen dort in eine Einzelheit aus (Nutzer 18.11.2026;
    `ausser`: Merkmale, die nie ausgelagert werden, z. B. der Grundkörper). Liefert Zuordnung, neue Maße je Ansicht und
    Meldungen."""
    modell = [m for m in plan if m.quelle == "modell"]
    neu = [m.id for m in plan if m.quelle == "neu"]
    rollen, weitere, zusatz = list(rollen), list(weitere), set()
    achsen, vorzug = dict(blickachsen or {}), dict(vorzug or {})
    if modell:
        _einfuegen(drw, views[rollen[0]], True)
    for _runde in range(3):
        z = ordne_zu(_nach_blickachse(kandidaten(views, modell), modell, achsen), rollen, max_je, vorzug,
                     zusatz, {rollen[0]: len(neu)})
        if not (z.weitere_ansicht and weitere and neue_ansicht):
            break
        rolle = weitere.pop(0)
        views[rolle] = neue_ansicht(rolle)
        rollen.append(rolle)
        zusatz.add(rolle)
        _einfuegen(drw, views[rolle], False)
    if einzelheit and any(len(ms) > max_je for ms in z.je_ansicht.values()):
        dicht = max(z.je_ansicht, key=lambda r: len(z.je_ansicht[r]))
        zahl = Counter(m.merkmal for m in modell if m.id in z.je_ansicht[dicht] and m.merkmal not in (ausser or set()))
        if zahl and zahl.most_common(1)[0][1] >= EINZELHEIT_MIN:
            merkmal = zahl.most_common(1)[0][0]
            det = einzelheit(dicht, [m.name for m in modell if m.merkmal == merkmal])
            if det is None:
                z.meldungen.append(f"EINZELHEIT_NICHT_ERZEUGT: {merkmal} in {dicht}")
            else:
                views["einzelheit"], achsen["einzelheit"] = det, achsen.get(dicht)
                rollen.append("einzelheit")
                zusatz.add("einzelheit")
                _einfuegen(drw, det, False)
                vorzug.update({m.id: "einzelheit" for m in modell if m.merkmal == merkmal})
                z = ordne_zu(_nach_blickachse(kandidaten(views, modell), modell, achsen), rollen, max_je, vorzug,
                             zusatz, {rollen[0]: len(neu)})
                z.meldungen.append(f"EINZELHEIT: {merkmal} aus {dicht} ausgelagert "
                                   f"({len(z.je_ansicht['einzelheit'])} Maße)")
    erg = Ergebnis(z.je_ansicht, meldungen=list(z.meldungen))
    vorher = sum(len(_anzeige(v)) for v in views.values())
    ids = {m.name: m.id for m in modell}
    for rolle, v in views.items():
        behalten, gesehen = set(z.je_ansicht.get(rolle, [])), set()
        for dd in _anzeige(v):
            mid = ids.get(kurzname(dd))
            if mid in behalten and mid not in gesehen:
                gesehen.add(mid)
            else:
                _loesche(drw, dd)
        erg.gesetzt += len(gesehen)
    erg.geloescht = vorher - sum(len(_anzeige(v)) for v in views.values())  # Wirkung zählen, nicht Versuche
    if vorher - erg.gesetzt != erg.geloescht:
        erg.meldungen.append(f"MASS_NICHT_GELOESCHT: {vorher - erg.gesetzt - erg.geloescht} Modellmaße blieben stehen")
    if neu:
        erg.neu = {rollen[0]: neu}
        if len(neu) > max_je:
            erg.meldungen.append(f"ANSICHT_VOLL: {len(neu)} neue Maße in {rollen[0]} (Obergrenze {max_je} Maße je "
                                 "Ansicht; Drehteile haben in Stufe 2 keine weitere Ansicht)")
    return erg


# --- neue Maße über Kanten (Drehteil) --------------------------------------------------------------------------------

def _linien(view) -> list[tuple[object, tuple, tuple]]:
    """Sichtbare gerade Kanten der Ansicht: (Kante, Punkt mm, Richtung) in Modellkoordinaten."""
    aus = []
    for typ in (KANTE, SILHOUETTE):  # ungeschnittene Zylinder zeigen ihre Mantellinien als Silhouetten (Review I6)
        for k in list(view.GetVisibleEntities2(callout_leer(), typ) or ()):
            try:
                c = _ruf(k, "GetCurve")
                if not _ruf(c, "IsLine"):
                    continue
                px, py, pz, dx, dy, dz = list(_ruf(c, "LineParams"))[:6]
            except Exception:  # noqa: BLE001 – COM: Kante ohne Kurve oder ohne LineParams überspringen
                continue
            aus.append((k, (px * 1000, py * 1000, pz * 1000), (dx, dy, dz)))
    return aus


def _dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def _quer(p, achse) -> tuple:
    """Anteil von p senkrecht zur Achse (durch den Ursprung)."""
    s = _dot(p, achse)
    return tuple(x - s * a for x, a in zip(p, achse))


def setze_neu(drw, view, mass: Mass, achse: tuple, platz_m: tuple[float, float]) -> bool:
    """Ø: zwei Kanten parallel zur Achse im Abstand r auf entgegengesetzten Seiten; Länge: zwei Kanten quer zur Achse
    an den Lagen `von`/`bis`. Danach `AddDimension2` an `platz_m` (Blattkoordinaten, m)."""
    linien = _linien(view)
    g = mass.geometrie or {}
    if mass.art == "durchmesser":
        r = g["radius"]
        par = [(k, _quer(p, achse)) for k, p, d in linien if abs(abs(_dot(d, achse)) - 1) < 1e-6
               and abs(math.dist(_quer(p, achse), (0, 0, 0)) - r) < 1e-3]
        paar = next(((a, b) for i, a in enumerate(par) for b in par[i + 1:] if _dot(a[1], b[1]) < 0), None)
        kanten = [paar[0][0], paar[1][0]] if paar else None
    else:
        def an(lage):
            return next((k for k, p, d in linien if abs(_dot(d, achse)) < 1e-6 and abs(_dot(p, achse) - lage) < 1e-3), None)
        kanten = [an(g["von"]), an(g["bis"])]
        kanten = kanten if all(kanten) else None
    if not kanten:
        return False
    drw.ClearSelection2(True)
    view.SelectEntity(kanten[0], False)
    view.SelectEntity(kanten[1], True)
    dd = drw.AddDimension2(platz_m[0], platz_m[1], 0)
    if dd is None:
        return False
    if mass.art == "durchmesser":
        dd.SetText(PRAEFIX, DURCHMESSER)
    return True


def ordne_masse_an(drw, view) -> bool:
    """Alle Maße der Ansicht auswählen und von SolidWorks automatisch anordnen lassen."""
    dds = _anzeige(view)
    if not dds:
        return True
    drw.ClearSelection2(True)
    for dd in dds:
        _ruf(dd, "GetAnnotation").Select2(True, 0)
    ok = bool(_ruf(drw, "Extension").AlignDimensions(AUTO_ANORDNEN, MASSABSTAND_M))
    drw.ClearSelection2(True)
    return ok
