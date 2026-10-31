"""Geometrie vorher/nachher (Spec Bestandsdateien §7.2): die zweite Hälfte des Präzisionsschutzes.

`koerper_differenz` zieht je Konfiguration die Körper beider Dokumente gegenseitig voneinander ab, nur an Kopien, in denselben
Modellkoordinaten (eine Verschiebung ist hier ein Fehler). `bewerte_bereiche` ist rein: Jede Abweichung über der Toleranz muss
vollständig in einem Bereich liegen, jeder Punkt, der Geometrie ändern soll, muss eine Abweichung in seinem Bereich haben.

Wege aus S18d, an unsichtbaren Dokumenten (docs/bestandsdateien/ergebnisse.md):
- Unveränderte Geometrie ist leer, ohne Splitter; `Operations2` liefert dann `(None, 0)`, verbraucht aber beide Körper.
- Jedes Ziel minus alle Werkzeuge statt Paaren nach Lage: Getrennte Körper liefern das Ziel unverändert, Code 0, auch wenn sich die
  Hüllquader überlappen (Sonde Task 8). Ein Körper auf nur einer Seite ist so von selbst als Ganzes eine Abweichung, und ein
  Körper, den ein Schnitt zerteilt, braucht kein Sonderfall.
- `Copy2(True)`, so gemessen. Kein STL-Rückfall: 0,03 mm Rauschen bei gleicher Geometrie, am unsichtbaren Dokument stürzt SolidWorks
  ab. Ein Fehlercode heißt `DifferenzFehler`, für diese Konfiguration also nicht nachgewiesen (`ok: None`).

Die Toleranz entscheidet über die Dicke (`dicke`), nicht über die Ausdehnung: Der Körper einer um 5 µm verschobenen Fläche ist exakt
und 60 × 20 mm groß. Maßstab ist der Grundsatz aus `vergleich`: Ein Fehlalarm kostet eine Rückfrage, ein falsches `ok` die Datei des
Kollegen.

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  IBody2.Copy2(1), .Operations2(3: SWBODYCUT 15902, Ausgabe swBodyOperationError_e, mit Typinfo als Rohzahl, Rückgabe (Ergebnis,
    Code)), .GetBodyBox(0), .GetMassProperties(1: Volumen [3], Fläche [4])
  IPartDoc.GetBodies2(2), IFeature.GetFaces(0), IFace2.GetBox(0)
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import reduce

from swki.bestand.spec import GEOMETRIE_TYPEN
from swki.bestand.sw_bestand import _schalte
from swki.cli import SwkiFehler
from swki.compiler.topologie import koerper
from swki.kaufteile.sw_kaufteil import flaechenkoerper
from swki.pruefung.bewertung import eintrag
from swki.verbindung import in_mm, in_mm3

SW_BODY_CUT = 15902        # swBodyOperationType_e.SWBODYCUT
TOL_VOLUMEN = 0.01         # mm³: Rauschen der Massenberechnung, wie im Bau
_TOL_VOLUMEN_ANTEIL = 1e-6
# Ein `skript`-Punkt kann Geometrie ändern, muss aber nicht (Punkt-Typen, die keine Wirkung schulden)
WIRKUNG_TYPEN = GEOMETRIE_TYPEN - {"skript"}


class DifferenzFehler(SwkiFehler):
    """Die Differenz liefert keine Aussage: Für diese Konfiguration ist nichts nachgewiesen."""


@dataclass
class Abweichung:
    art: str  # "entfernt" (nur vorher) | "hinzu" (nur nachher)
    box: list[float]  # [xmin, ymin, zmin, xmax, ymax, zmax] mm, Modellkoordinaten
    volumen: float  # mm³
    flaeche: float | None = None  # Oberfläche in mm²; ohne sie zählt nur der Hüllquader


def dicke(a: Abweichung) -> float:
    """Obere Schätzung der größten Dicke in mm; unter der Toleranz zählt die Abweichung nicht.

    Die kleinste Box-Kante ist sicher, denn dünner als sie ist der Körper überall, trifft aber nur achsparallele Schichten: Die Sichel
    einer versetzten Bohrung ist 4 mm breit. `2·V/A` ist die mittlere Dicke einer dünnen Schicht, die größte kann darüber liegen
    (S18d, Bohrung 20 µm versetzt: Sichel 12,7 µm im Mittel, 20 µm an der stärksten Stelle; Keil: das Doppelte). Darum zählt die doppelte
    mittlere Dicke. Eine gleichmäßige schräge Schicht oder ein Ring gilt so schon ab 5 µm als Abweichung, das ist ein Fehlalarm, kein
    falsches `ok`. Grenze: Eine dünne Schicht, die mit einem Buckel zusammenhängt, verdünnt dessen Mittel, gemessen ist so etwas nicht."""
    kante = min(a.box[i + 3] - a.box[i] for i in range(3))
    return min(kante, 4 * a.volumen / a.flaeche) if a.flaeche else kante


def _vereine(a: list[float], b: list[float]) -> list[float]:
    return [min(a[i], b[i]) for i in range(3)] + [max(a[i], b[i]) for i in range(3, 6)]


def _innen(box: list[float], bereich: list[float], toleranz: float) -> bool:
    return all(box[i] >= bereich[i] - toleranz and box[i + 3] <= bereich[i + 3] + toleranz for i in range(3))


def _beruehrt(box: list[float], bereich: list[float], toleranz: float) -> bool:
    return all(box[i] <= bereich[i + 3] + toleranz and box[i + 3] >= bereich[i] - toleranz for i in range(3))


def _gilt_in(punkt: dict, konfiguration: str) -> bool:
    k = punkt.get("konfigurationen", "alle")
    return k == "alle" or konfiguration in k


def _bereiche(spec: dict, feature_boxen: dict[str, list[float]]) -> list[tuple[int, list[dict], list[float]]]:
    """(Index, Punkte, Hüllquader) je Bereich. Ein `features`-Bereich ist ein Hüllquader über alle seine Features (Spec §7.2: Ein
    gelöschter Schnitt samt Fase ist ein Differenzkörper). Hat keines Flächen, kann er nichts erklären und entfällt."""
    punkte = {p["id"]: p for p in spec["punkte"]}
    aus = []
    for i, b in enumerate(spec["bereiche"]):
        boxen = [[*b["box"]["min"], *b["box"]["max"]]] if "box" in b else [feature_boxen[n] for n in b["features"] if n in feature_boxen]
        if boxen:
            aus.append((i, [punkte[pid] for pid in b["punkte"] if pid in punkte], reduce(_vereine, boxen)))
    return aus


def _lage(box: list[float]) -> str:
    return ", ".join(f"{achse} {box[i]:g}…{box[i + 3]:g}" for i, achse in enumerate("xyz"))


def _in_konfiguration(k: str, liste: list[Abweichung] | str, bereiche: list, toleranz: float) -> dict:
    """Ein Bereich gilt nur in den Konfigurationen seiner Punkte: Sonst erlaubte ein Punkt für Standard dieselbe Stelle in Variante B."""
    if isinstance(liste, str):
        return eintrag("bereich", None, konfiguration=k, ist=[], knoten=[], hinweis=f"Differenz in {k} nicht nachgewiesen: {liste}")
    passend = [(i, box) for i, punkte, box in bereiche if any(_gilt_in(p, k) for p in punkte)]
    ist = [{"art": a.art, "box": a.box, "volumen": a.volumen, "flaeche": a.flaeche, "dicke": round(dicke(a), 6),
            "bereich": next((i for i, box in passend if _innen(a.box, box, toleranz)), None),
            "unter_toleranz": dicke(a) < toleranz} for a in liste]
    draussen = [x for x in ist if x["bereich"] is None and not x["unter_toleranz"]]
    if draussen:
        return eintrag("bereich", False, konfiguration=k, ist=ist, knoten=[], hinweis="; ".join(
            f"{x['art']} {x['volumen']:g} mm³ bei {_lage(x['box'])} liegt in keinem Bereich ({k})" for x in draussen))
    return eintrag("bereich", True, konfiguration=k, ist=ist, knoten=[])


def _schuldet_wirkung(p: dict) -> bool:
    """Spec §7.2: „wenn der Punkt Geometrie ändern sollte“. Bezugsgeometrie hat kein Volumen."""
    return p["typ"] in WIRKUNG_TYPEN and not (p["typ"] == "feature" and p["feature"]["typ"] == "referenz")


def _wirkung(p: dict, abweichungen: dict, bereiche: list, toleranz: float) -> dict:
    """Eine Abweichung irgendwo im Bereich genügt, auch unter der Toleranz, und nur in einer der Konfigurationen des Punkts:
    `unterdruecken` in `alle` hat in einer Konfiguration, in der das Feature schon unterdrückt ist, nichts zu tun."""
    pid, boxen = f"punkt:{p['id']}", [box for _, punkte, box in bereiche if p in punkte]
    eigene = {k: a for k, a in abweichungen.items() if _gilt_in(p, k)}
    if any(_beruehrt(a.box, box, toleranz) for liste in eigene.values() if not isinstance(liste, str) for a in liste for box in boxen):
        return eintrag(pid, True, knoten=[p["id"]])
    if offen := [k for k, a in eigene.items() if isinstance(a, str)]:
        return eintrag(pid, None, knoten=[p["id"]], hinweis=f"Wirkung nicht nachgewiesen, Differenz fehlt in {', '.join(offen)}")
    return eintrag(pid, False, knoten=[p["id"]], hinweis=f"Punkt {p['id']}: keine Abweichung in seinem Bereich, er hat nichts bewirkt")


def _volumen_delta(soll_block: dict, abweichungen: dict, prozent: float) -> dict:
    """Nachher minus vorher, summiert aus den Differenzkörpern, je Konfiguration mit Abweichungen: Eine Konfiguration, die kein Punkt
    berührt, bleibt gleich. Hat keine eine Abweichung, zählt 0 überall."""
    soll = soll_block["soll"]
    tol = max(abs(soll) * soll_block.get("toleranz_prozent", prozent) / 100, TOL_VOLUMEN)
    offen = [k for k, a in abweichungen.items() if isinstance(a, str)]
    ist = {k: round(sum(x.volumen if x.art == "hinzu" else -x.volumen for x in a), 6) for k, a in abweichungen.items()
           if a and k not in offen}
    if not ist and not offen:
        ist = dict.fromkeys(abweichungen, 0.0)
    daten = {"ist": ist, "soll": soll, "tol": tol, "knoten": []}
    if falsch := [k for k, v in ist.items() if abs(v - soll) > tol]:
        return eintrag("volumen_delta", False, **daten, hinweis="; ".join(f"{ist[k]:g} statt {soll:g} mm³ ({k})" for k in falsch))
    if offen:
        return eintrag("volumen_delta", None, **daten, hinweis=f"Differenz fehlt in {', '.join(offen)}")
    return eintrag("volumen_delta", True, **daten)


def bewerte_bereiche(spec: dict, abweichungen: dict[str, list[Abweichung] | str], feature_boxen: dict[str, list[float]],
                     toleranz: float = 0.01, volumen_prozent: float = 0.5) -> list[dict]:
    """Einträge `bereich` je Konfiguration (mit `konfiguration`; `ist` nennt jede Abweichung mit Lage, Volumen, zugeordnetem Bereich),
    `punkt:<id>` je Punkt, der Geometrie ändern soll, und `volumen_delta`, wenn die Spec es nennt. `abweichungen` trägt statt der Liste
    einen Fehlertext, wo die Differenz scheiterte; solche Einträge bleiben `ok: None`. `volumen_prozent`: Vorgabe für
    `toleranz_prozent`."""
    bereiche = _bereiche(spec, feature_boxen)
    aus = [_in_konfiguration(k, liste, bereiche, toleranz) for k, liste in abweichungen.items()]
    aus += [_wirkung(p, abweichungen, bereiche, toleranz) for p in spec["punkte"] if _schuldet_wirkung(p)]
    if (delta := spec.get("pruefung", {}).get("volumen_delta")) is not None:
        aus.append(_volumen_delta(delta, abweichungen, volumen_prozent))
    return aus


# ---------------------------------------------------------------------------------------------------------------- COM

@contextmanager
def _aktive_zurueck(modelle: list) -> Iterator[None]:
    aktiv = [(m, m.ConfigurationManager.ActiveConfiguration.Name) for m in modelle]
    try:
        yield
    finally:
        for m, k in aktiv:
            _schalte(m, k)


def _zeige(model, konfiguration: str) -> None:
    """Wie `lies_bestand`: umschalten, zurücklesen, neu aufbauen. Körper und Features danach neu holen (S18c)."""
    _schalte(model, konfiguration)
    model.EditRebuild3


def _minus(ziele: list, werkzeuge: list) -> list:
    """Alle Ziele minus alle Werkzeuge, nur an Kopien (S18d: `Operations2` verbraucht beide Körper, auch wenn nichts getroffen wird)."""
    rest = [k.Copy2(True) for k in ziele]
    for werkzeug in werkzeuge:
        neu = []
        for ziel in rest:
            ergebnis, code = ziel.Operations2(SW_BODY_CUT, werkzeug.Copy2(True), 0)
            if code:
                raise DifferenzFehler(f"Operations2 meldet swBodyOperationError_e {code}")
            neu.extend(ergebnis or ())
        rest = neu
    return rest


def _box_mm(roh) -> list[float]:
    """Zwei Ecken in Metern → [xmin, ymin, zmin, xmax, ymax, zmax] in mm."""
    c = [in_mm(x) for x in roh]
    return [min(c[i], c[i + 3]) for i in range(3)] + [max(c[i], c[i + 3]) for i in range(3)]


def _abweichung(art: str, k) -> Abweichung:
    m = k.GetMassProperties(1.0)  # Dichte egal
    return Abweichung(art, [round(c, 6) for c in _box_mm(k.GetBodyBox())], round(in_mm3(m[3]), 6), round(m[4] * 1e6, 6))


def _volumen(liste: list) -> float:
    return sum(in_mm3(k.GetMassProperties(1.0)[3]) for k in liste)


def _pruefe_bilanz(vorher: list, nachher: list, aus: list[Abweichung]) -> None:
    """Rückgaben nicht glauben (S18c): Eine leere Differenz wäre das falsche `ok` schlechthin, die Volumen sagen es unabhängig davon."""
    alt, neu = _volumen(vorher), _volumen(nachher)
    summe = sum(a.volumen if a.art == "hinzu" else -a.volumen for a in aus)
    if abs(neu - alt - summe) > max(TOL_VOLUMEN, _TOL_VOLUMEN_ANTEIL * max(alt, neu)):
        raise DifferenzFehler(f"Differenzkörper ergeben {summe:g} mm³, das Volumen änderte sich um {neu - alt:g} mm³")


def koerper_differenz(app, model_vorher, model_nachher, konfiguration: str) -> list[Abweichung]:
    """Differenz beider Dokumente in einer Konfiguration, die aktive steht danach wieder da, auch nach einem Fehler.
    `DifferenzFehler`: Fehlercode, Flächenkörper (`Operations2` sähe sie nicht, das Ergebnis wäre leer) oder Volumenbilanz."""
    modelle = [model_vorher, model_nachher]
    with _aktive_zurueck(modelle):
        for m in modelle:
            _zeige(m, konfiguration)
            if flaechenkoerper(m):
                raise DifferenzFehler("Flächenkörper lassen sich nicht vergleichen, nur Volumenkörper")
        vorher, nachher = koerper(model_vorher), koerper(model_nachher)
        aus = ([_abweichung("entfernt", k) for k in _minus(vorher, nachher)]
               + [_abweichung("hinzu", k) for k in _minus(nachher, vorher)])
        _pruefe_bilanz(vorher, nachher, aus)
    return aus


def _feature_boxen(model, namen: set[str]) -> dict[str, list[float]]:
    """Hüllquader (mm) der Flächen je Feature in der aktiven Konfiguration; unterdrückte Features und Skizzen haben keine."""
    aus = {}
    for name in namen:
        feature = model.FeatureByName(name)
        boxen = [_box_mm(f.GetBox) for f in (feature.GetFaces or ())] if feature is not None else []
        if boxen:
            aus[name] = reduce(_vereine, boxen)
    return aus


def alle_feature_boxen(modelle: list, konfigurationen: list[str], namen: set[str]) -> dict[str, list[float]]:
    """Spec §7.2: Hüllquader der Flächen vorher und nachher, über alle Konfigurationen: Unterdrückte Features haben nur dort Flächen, wo
    sie aktiv sind, gelöschte nur vorher, neue nur nachher."""
    aus: dict[str, list[float]] = {}
    if not namen:
        return aus
    with _aktive_zurueck(modelle):
        for k in konfigurationen:
            for m in modelle:
                _zeige(m, k)
                for name, box in _feature_boxen(m, namen).items():
                    aus[name] = _vereine(aus[name], box) if name in aus else box
    return aus
