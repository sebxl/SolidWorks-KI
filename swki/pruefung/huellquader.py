"""Soll-Hüllquader aus der Spezifikation (`pruefung.huellquader: auto`), ohne SolidWorks. Längen in mm.

Den Hüllquader bestimmen die Aufsätze (extrusion, rotation, Muster und Spiegelungen davon). Annahme wie bei
`volumen: auto`: Schnitte, Bohrungen, Verrundungen und Fasen liegen im Material und verkleinern ihn nicht. Schnitte
werden trotzdem verfolgt, weil spätere Skizzen auf ihren Flächen liegen können (Taschenboden).
"""

import math

from swki.formschraege import extrusionsrichtung, schraege, skizzennormale
from swki.pruefung.geometrie import _umriss
from swki.spec.ausdruck import auswerten
from swki.spec.konturen import eckradien

Box = list[float]  # [xmin, ymin, zmin, xmax, ymax, zmax]

_ACHSE_DER_EBENE = {"vorne": 2, "oben": 1, "rechts": 0}
_ACHSE = {"x": 0, "y": 1, "z": 2}
_AUFSATZ, _SCHNITT = "aufsatz", "schnitt"


class _Offen(Exception):
    """Hüllquader nicht analytisch berechenbar; der Text sagt warum."""


def _bogen_extrema(mitte, r: float, a0: float, sweep: float) -> list[tuple[float, float]]:
    """Punkte eines Bogens (Mitte, Radius, Startwinkel, Überstreichung gegen den Uhrzeigersinn, rad), die den Umriss
    bestimmen: Anfang, Ende und jede Achsrichtung, die der Bogen überstreicht."""
    punkte = [(mitte[0] + r * math.cos(a0), mitte[1] + r * math.sin(a0)),
              (mitte[0] + r * math.cos(a0 + sweep), mitte[1] + r * math.sin(a0 + sweep))]
    for k in range(4):
        w = k * math.pi / 2
        if (w - a0) % (2 * math.pi) <= sweep + 1e-12:
            punkte.append((mitte[0] + r * math.cos(w), mitte[1] + r * math.sin(w)))
    return punkte


def _polygon_punkte(polygon: dict, p: dict) -> list[tuple[float, float]]:
    """Randpunkte eines Polygons mit Eckradien: scharfe Ecken, sonst Tangentenpunkte und Bogenextrema der Rundung."""
    pts = [(auswerten(u, p), auswerten(v, p)) for u, v in polygon["punkte"]]
    radien, n, ergebnis = eckradien(polygon, p), len(pts), []
    for k, (b, r) in enumerate(zip(pts, radien)):
        if r == 0:
            ergebnis.append(b)
            continue
        a, c = pts[k - 1], pts[(k + 1) % n]
        e1 = (a[0] - b[0], a[1] - b[1])
        e2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        e1, e2 = (e1[0] / l1, e1[1] / l1), (e2[0] / l2, e2[1] / l2)
        phi = math.acos(max(-1.0, min(1.0, e1[0] * e2[0] + e1[1] * e2[1])))
        t = r / math.tan(phi / 2)
        winkelhalb = (e1[0] + e2[0], e1[1] + e2[1])
        lw = math.hypot(*winkelhalb)
        d = r / math.sin(phi / 2)
        mitte = (b[0] + winkelhalb[0] / lw * d, b[1] + winkelhalb[1] / lw * d)
        t1, t2 = (b[0] + e1[0] * t, b[1] + e1[1] * t), (b[0] + e2[0] * t, b[1] + e2[1] * t)
        a1, a2 = math.atan2(t1[1] - mitte[1], t1[0] - mitte[0]), math.atan2(t2[1] - mitte[1], t2[0] - mitte[0])
        sweep = (a2 - a1) % (2 * math.pi)
        if sweep > math.pi:   # der Rundungsbogen ist immer der kurze
            a1, sweep = a2, 2 * math.pi - sweep
        ergebnis += _bogen_extrema(mitte, r, a1, sweep)
    return ergebnis


def _kontur_punkte(kontur: dict, p: dict) -> list[tuple[float, float]]:
    punkte = [(auswerten(kontur["start"][0], p), auswerten(kontur["start"][1], p))]
    for s in kontur["segmente"]:
        roh = s["linie"] if "linie" in s else s["bogen"]
        ende = (auswerten(roh[0], p), auswerten(roh[1], p))
        if "bogen" in s:
            m = (auswerten(s["mitte"][0], p), auswerten(s["mitte"][1], p))
            a0 = math.atan2(punkte[-1][1] - m[1], punkte[-1][0] - m[0])
            sweep = (math.atan2(ende[1] - m[1], ende[0] - m[0]) - a0) % (2 * math.pi)
            punkte += _bogen_extrema(m, math.hypot(ende[0] - m[0], ende[1] - m[1]), a0, sweep)
        punkte.append(ende)
    return punkte


def profil_umriss(element: dict, p: dict) -> tuple[float, float, float, float] | None:
    """Genauer achsparalleler Umriss (umin, vmin, umax, vmax) eines geschlossenen Skizzenelements, auch mit Eckradien
    und Bögen; None für Elemente ohne Fläche (mittellinie)."""
    if "polygon" in element or "kontur" in element:
        pts = _polygon_punkte(element["polygon"], p) if "polygon" in element else _kontur_punkte(element["kontur"], p)
        return min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)
    return _umriss(element, p)


def _skizzen_umriss(elemente: list, p: dict) -> tuple[float, float, float, float]:
    umrisse = [u for u in (profil_umriss(e, p) for e in elemente) if u is not None]
    return (min(u[0] for u in umrisse), min(u[1] for u in umrisse),
            max(u[2] for u in umrisse), max(u[3] for u in umrisse))


def _in_ebene(orientierung: str, achse_u: tuple[float, float], achse_v: tuple[float, float]) -> dict[int, tuple]:
    """Bereiche der beiden Modellachsen in der Skizzenebene aus den (u, v)-Bereichen (Zuordnung wie im Skill:
    vorne X=u, Y=v · oben X=u, Z=−v · rechts Z=−u, Y=v)."""
    if orientierung == "vorne":
        return {0: achse_u, 1: achse_v}
    if orientierung == "oben":
        return {0: achse_u, 2: (-achse_v[1], -achse_v[0])}
    return {2: (-achse_u[1], -achse_u[0]), 1: achse_v}


def _box(bereiche: dict[int, tuple]) -> Box:
    return [bereiche[i][0] for i in range(3)] + [bereiche[i][1] for i in range(3)]


def _flaechenlage(anker: dict, koerper: dict) -> tuple[int, float]:
    """Achse und Koordinate der Fläche {feature, flaeche: "±a"} eines früheren Features: beim
    Aufsatz die äußerste Fläche in dieser Richtung, beim Schnitt die Fläche, die ins Freie zeigt (Taschenboden)."""
    if "feature" not in anker:
        raise _Offen("Fläche über {nahe} (Lage erst im Modell bekannt)")
    if anker["feature"] not in koerper:
        raise _Offen(f"Fläche von {anker['feature']} (kein Aufsatz oder Schnitt mit bekannter Lage)")
    box, art = koerper[anker["feature"]]
    vorzeichen, achse = (1 if anker["flaeche"][0] == "+" else -1), _ACHSE[anker["flaeche"][1]]
    aussen = (vorzeichen > 0) == (art == _AUFSATZ)
    return achse, box[achse + 3] if aussen else box[achse]


def _skizzenebene(ebene, koerper: dict, p: dict) -> tuple[str, float]:
    """Orientierung (Standardebene mit gleicher (u, v)-Zuordnung) und Lage der Skizzenebene auf ihrer Normalenachse."""
    if isinstance(ebene, str):
        return ebene, 0.0
    if "versatz" in ebene:
        return ebene["versatz"]["ebene"], auswerten(ebene["versatz"]["abstand"], p)
    achse, lage = _flaechenlage(ebene, koerper)
    return {v: k for k, v in _ACHSE_DER_EBENE.items()}[achse], lage


def _extrusion(f: dict, koerper: dict, p: dict) -> Box:
    ebene = f["skizze"]["ebene"]
    orientierung, lage = _skizzenebene(ebene, koerper, p)
    normale = skizzennormale(ebene)
    achse = _ACHSE_DER_EBENE[orientierung]
    ende = f["ende"]
    r = extrusionsrichtung(normale, f["typ"], ende.get("umkehren", False))[achse]
    if ende["typ"] == "blind":
        t = auswerten(ende["tiefe"], p)
        entlang, weg = sorted((lage, lage + r * t)), t
    elif ende["typ"] == "mittig":
        t = auswerten(ende["tiefe"], p)
        entlang, weg = (lage - t / 2, lage + t / 2), t / 2
    elif ende["typ"] in ("bis_flaeche", "versatz_von_flaeche"):
        f_achse, ziel = _flaechenlage(ende["flaeche"], koerper)
        if f_achse != achse:
            raise _Offen(f"{f['id']}: Zielfläche nicht quer zur Extrusionsrichtung")
        if ende["typ"] == "versatz_von_flaeche":
            ziel -= r * auswerten(ende["abstand"], p)   # der Versatz geht zur Skizze hin
        entlang, weg = sorted((lage, ziel)), abs(ziel - lage)
    else:
        raise _Offen(f"{f['id']}: ende {ende['typ']}")
    umin, vmin, umax, vmax = _skizzen_umriss(f["skizze"]["elemente"], p)
    s = schraege(f)
    if s is not None and s["querschnitt"] == "groesser":   # der Querschnitt wächst bis zum Ende um weg · tan(Winkel)
        if any(not ({"kreis", "rechteck", "langloch"} & set(e)) for e in f["skizze"]["elemente"]):
            raise _Offen(f"{f['id']}: Formschräge groesser an Polygon oder Kontur (spitze Ecken wachsen stärker)")
        d = weg * math.tan(math.radians(auswerten(s["winkel"], p)))
        umin, vmin, umax, vmax = umin - d, vmin - d, umax + d, vmax + d
    bereiche = _in_ebene(orientierung, (umin, umax), (vmin, vmax))
    bereiche[achse] = entlang
    return _box(bereiche)


def _rotation(f: dict, koerper: dict, p: dict) -> Box:
    if auswerten(f.get("winkel", 360), p) != 360:
        raise _Offen(f"{f['id']}: Rotation unter 360°")
    orientierung, lage = _skizzenebene(f["skizze"]["ebene"], koerper, p)
    elemente = f["skizze"]["elemente"]
    linie = next(e["mittellinie"] for e in elemente if "mittellinie" in e)
    (u0, v0), (u1, v1) = [(auswerten(a, p), auswerten(b, p)) for a, b in (linie["von"], linie["bis"])]
    umin, vmin, umax, vmax = _skizzen_umriss([e for e in elemente if "mittellinie" not in e], p)
    if abs(v1 - v0) < 1e-9:      # Achse parallel zu u: Radius quer in v
        radius = max(abs(vmax - v0), abs(vmin - v0))
        bereiche = _in_ebene(orientierung, (umin, umax), (v0 - radius, v0 + radius))
    elif abs(u1 - u0) < 1e-9:    # Achse parallel zu v: Radius quer in u
        radius = max(abs(umax - u0), abs(umin - u0))
        bereiche = _in_ebene(orientierung, (u0 - radius, u0 + radius), (vmin, vmax))
    else:
        raise _Offen(f"{f['id']}: Mittellinie nicht parallel zu u oder v")
    bereiche[_ACHSE_DER_EBENE[orientierung]] = (lage - radius, lage + radius)
    return _box(bereiche)


def _verschoben(box: Box, achse: int, weg: float) -> Box:
    neu = list(box)
    neu[achse] += weg
    neu[achse + 3] += weg
    return neu


def _vereinigt(boxen: list[Box]) -> Box:
    return [min(b[i] for b in boxen) for i in range(3)] + [max(b[i] for b in boxen) for i in range(3, 6)]


def _quellen(f: dict, koerper: dict) -> list[tuple[Box, str]]:
    """Boxen der gemusterten bzw. gespiegelten Features; Features ohne Box (Bohrungen, Schnitte ohne bekannte Lage)
    tragen zum Hüllquader nichts bei – Aufsätze ohne Box hat huellquader_auto schon abgelehnt."""
    return [koerper[q] for q in f["features"] if q in koerper]


def _muster_linear(f: dict, koerper: dict, p: dict) -> list[tuple[Box, str]]:
    ergebnis = []
    for box, art in _quellen(f, koerper):
        boxen = [box]
        for r in (f["richtung1"], f.get("richtung2")):
            if r is None:
                continue
            schritt = auswerten(r["abstand"], p) * (-1 if r.get("umkehren") else 1)
            boxen = [_verschoben(b, _ACHSE[r["achse"]], k * schritt) for b in boxen for k in range(r["anzahl"])]
        ergebnis.append((_vereinigt(boxen), art))
    return ergebnis


def _spiegeln(f: dict, koerper: dict, p: dict) -> list[tuple[Box, str]]:
    ebene = f["ebene"]
    if isinstance(ebene, str) or "versatz" in ebene:
        orientierung, lage = _skizzenebene(ebene, koerper, p)
        achse = _ACHSE_DER_EBENE[orientierung]
    else:
        achse, lage = _flaechenlage(ebene, koerper)
    ergebnis = []
    for box, art in _quellen(f, koerper):
        gespiegelt = list(box)
        gespiegelt[achse], gespiegelt[achse + 3] = 2 * lage - box[achse + 3], 2 * lage - box[achse]
        ergebnis.append((_vereinigt([box, gespiegelt]), art))
    return ergebnis


def _koerper(spec: dict, p: dict, bis: str | None = None) -> dict[str, tuple[Box, str]]:
    """Feature-ID → (Box, Art) für Aufsätze und Schnitte mit bekannter Lage, bis vor das Feature `bis`; wirft _Offen,
    wenn ein Aufsatz nicht berechenbar ist."""
    koerper: dict[str, tuple[Box, str]] = {}
    for f in spec["features"]:
        typ = f["typ"]
        if f["id"] == bis:
            break
        if typ in ("extrusion", "schnitt", "rotation"):
            schnitt = typ == "schnitt" or (typ == "rotation" and f.get("schnitt", False))
            try:
                box = (_rotation if typ == "rotation" else _extrusion)(f, koerper, p)
            except _Offen:
                if schnitt:
                    continue   # Schnitt ohne bekannte Lage: zählt nicht; nur Flächen auf ihm bleiben offen
                raise
            koerper[f["id"]] = (box, _SCHNITT if schnitt else _AUFSATZ)
        elif typ in ("muster_linear", "spiegeln"):
            teile = (_muster_linear if typ == "muster_linear" else _spiegeln)(f, koerper, p)
            for art in (_AUFSATZ, _SCHNITT):
                boxen = [b for b, a in teile if a == art]
                if boxen:   # gemischte Muster: die Aufsätze zählen für den Hüllquader
                    koerper[f["id"]] = (_vereinigt(boxen), art)
                    break
        elif typ == "muster_kreis":
            if any(koerper.get(q, (None, _SCHNITT))[1] == _AUFSATZ for q in f["features"]):
                raise _Offen(f"{f['id']}: Kreismuster von Aufsätzen")
        elif typ == "verzahnung":
            raise _Offen(f"{f['id']}: Verzahnung (die Box hängt von der Lage der Zähne ab)")
        elif typ == "skript":
            raise _Offen(f"{f['id']}: Skript")
    return koerper


def huellquader_auto(spec: dict) -> tuple[list[float] | None, str]:
    """Kanten [X, Y, Z] des Hüllquaders aus der Spezifikation (mm) und "analytisch", sonst (None, Grund)."""
    try:
        koerper = _koerper(spec, spec.get("parameter", {}))
    except _Offen as e:
        return None, str(e)
    aufsaetze = [b for b, art in koerper.values() if art == _AUFSATZ]
    if not aufsaetze:
        return None, "kein Aufsatz"
    box = _vereinigt(aufsaetze)
    return [round(box[i + 3] - box[i], 6) for i in range(3)], "analytisch"


def seitenpunkt(spec: dict, fid: str, richtung: str) -> list[float] | None:
    """Punkt mitten auf der Seitenfläche eines Features mit Formschräge, deren äußere Normale ungefähr `richtung`
    ("+x" … "-z", quer zur Extrusion) zeigt – als Vorschlag für {nahe: [x, y, z]}; None, wenn nicht berechenbar.
    Liegt auf halber Tiefe (bei mittig auf halber Tiefe der Seite in Extrusionsrichtung – in der Skizzenebene stoßen
    die beiden geschrägten Hälften aneinander), quer dazu in der Mitte des Profils."""
    p = spec.get("parameter", {})
    f = next(x for x in spec["features"] if x["id"] == fid)
    try:
        orientierung, lage = _skizzenebene(f["skizze"]["ebene"], _koerper(spec, p, bis=fid), p)
        ende = f["ende"]
        if ende["typ"] not in ("blind", "mittig"):
            return None
        achse = _ACHSE_DER_EBENE[orientierung]
        r = extrusionsrichtung(skizzennormale(f["skizze"]["ebene"]), f["typ"], ende.get("umkehren", False))[achse]
        tiefe = auswerten(ende["tiefe"], p) / (2 if ende["typ"] == "blind" else 4)
        s = schraege(f)
        d = tiefe * math.tan(math.radians(auswerten(s["winkel"], p))) * (-1 if s["querschnitt"] == "kleiner" else 1)
        umin, vmin, umax, vmax = _skizzen_umriss(f["skizze"]["elemente"], p)
    except (_Offen, KeyError, StopIteration):
        return None
    bereiche = _in_ebene(orientierung, (umin - d, umax + d), (vmin - d, vmax + d))
    bereiche[achse] = (lage + r * tiefe, lage + r * tiefe)
    ziel = _ACHSE[richtung[1]]
    if ziel == achse:
        return None
    punkt = [(lo + hi) / 2 for lo, hi in (bereiche[i] for i in range(3))]
    punkt[ziel] = bereiche[ziel][1] if richtung[0] == "+" else bereiche[ziel][0]
    return [round(c, 3) + 0.0 for c in punkt]
