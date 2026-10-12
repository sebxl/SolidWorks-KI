"""Reine Geometrie für die Prüfung: Abstände zwischen Punkten, Achsen und Ebenen; analytisches Sollvolumen.

Alle Längen in mm.
"""

import math
from dataclasses import dataclass

from swki.compiler.anker import Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.formschraege import schraege, volumen_feature
from swki.spec.ausdruck import auswerten
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import bohrspitze_grad, norm_von, normmasse
from swki.verzahnung import aus_feature

_PARALLEL = 1.0 - 1e-6


@dataclass
class Messgeometrie:
    art: str  # "punkt" | "achse" | "ebene"
    punkt: Vektor
    richtung: Vektor | None = None  # Achse: Richtung; Ebene: Normale (Einheitsvektoren)


class NichtMessbar(ValueError):
    pass


def abstand(a: Messgeometrie, b: Messgeometrie) -> float:
    """Kürzester Abstand; Achsen/Ebenen müssen zueinander parallel sein, sonst NichtMessbar."""
    if a.art == "punkt" and b.art == "punkt":
        return laenge(differenz(a.punkt, b.punkt))
    if a.art == "punkt" or b.art == "punkt":
        p, g = (a, b) if a.art == "punkt" else (b, a)
        if g.art == "achse":
            return punkt_achse_abstand(p.punkt, g.punkt, g.richtung)
        return abs(skalar(differenz(p.punkt, g.punkt), g.richtung))
    if a.art == "achse" and b.art == "achse":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Achsen sind nicht parallel")
        return punkt_achse_abstand(a.punkt, b.punkt, b.richtung)
    if a.art == "ebene" and b.art == "ebene":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Ebenen sind nicht parallel")
        return abs(skalar(differenz(a.punkt, b.punkt), a.richtung))
    achse, ebene = (a, b) if a.art == "achse" else (b, a)
    if abs(skalar(achse.richtung, ebene.richtung)) > 1e-6:
        raise NichtMessbar("Achse ist nicht parallel zur Ebene")
    return abs(skalar(differenz(achse.punkt, ebene.punkt), ebene.richtung))


def _punkte(roh, p: dict) -> list[tuple[float, float]]:
    return [(auswerten(x, p), auswerten(y, p)) for x, y in roh]


def _polygon_flaeche(pts) -> float:
    """Vorzeichenbehaftete Fläche (Gaußsche Trapezformel): > 0 gegen den Uhrzeigersinn."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2


def _eckkorrektur(a, b, c, r: float) -> float:
    """Flächenänderung durch Eckradius r an Ecke b (Nachbarn a, c) eines gegen den Uhrzeigersinn umlaufenden
    Polygons: an konvexen Ecken wird Material weggenommen, an konkaven hinzugefügt."""
    if r == 0:
        return 0.0
    v1, v2 = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    phi = math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2)))))
    betrag = r * r / math.tan(phi / 2) - r * r * (math.pi - phi) / 2  # Drachen aus Tangenten − Kreissektor
    links = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) > 0
    return -betrag if links else betrag


def _polygon_mit_radien(pts, radien) -> float:
    if _polygon_flaeche(pts) < 0:
        pts, radien = pts[::-1], radien[::-1]
    n = len(pts)
    return _polygon_flaeche(pts) + sum(_eckkorrektur(pts[k - 1], pts[k], pts[(k + 1) % n], radien[k]) for k in range(n))


def _kontur_flaeche(kontur: dict, p: dict) -> float:
    """Fläche einer geschlossenen Kontur (Greenscher Satz; Bögen gegen den Uhrzeigersinn)."""
    pts = kontur_punkte(kontur, p)
    summe = 0.0
    for k, s in enumerate(kontur["segmente"]):
        (xa, ya), (xb, yb) = pts[k], pts[k + 1]
        if "linie" in s:
            summe += (xa * yb - xb * ya) / 2
            continue
        mx, my = auswerten(s["mitte"][0], p), auswerten(s["mitte"][1], p)
        r = math.hypot(xa - mx, ya - my)
        winkel = (math.atan2(yb - my, xb - mx) - math.atan2(ya - my, xa - mx)) % (2 * math.pi)
        summe += (r * r * winkel + mx * (yb - ya) - my * (xb - xa)) / 2
    return abs(summe)


def _flaeche(element: dict, p: dict) -> float | None:
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p) - (4 - math.pi) * auswerten(r.get("radius", 0), p) ** 2
    if "kreis" in element:
        return math.pi * auswerten(element["kreis"]["durchmesser"], p) ** 2 / 4
    if "polygon" in element:
        return abs(_polygon_mit_radien(_punkte(element["polygon"]["punkte"], p), eckradien(element["polygon"], p)))
    if "langloch" in element:
        breite = auswerten(element["langloch"]["breite"], p)
        return auswerten(element["langloch"]["laenge"], p) * breite + math.pi * breite**2 / 4
    if "kontur" in element:
        return _kontur_flaeche(element["kontur"], p)
    return None


def _umriss(element: dict, p: dict) -> tuple[float, float, float, float] | None:
    """Achsparalleler Umriss (umin, vmin, umax, vmax) eines geschlossenen Skizzenelements, sonst None."""
    if "rechteck" in element or "kreis" in element or "langloch" in element:
        e = element.get("rechteck") or element.get("kreis") or element["langloch"]
        u, v = (auswerten(x, p) for x in e["mitte"])
        if "rechteck" in element:
            hu, hv = auswerten(e["breite"], p) / 2, auswerten(e["hoehe"], p) / 2
        elif "kreis" in element:
            hu = hv = auswerten(e["durchmesser"], p) / 2
        else:
            w, halb, r = math.radians(auswerten(e.get("winkel", 0), p)), auswerten(e["laenge"], p) / 2,                 auswerten(e["breite"], p) / 2
            hu, hv = halb * abs(math.cos(w)) + r, halb * abs(math.sin(w)) + r
        return u - hu, v - hv, u + hu, v + hv
    if "polygon" in element or "kontur" in element:
        pts = (_punkte(element["polygon"]["punkte"], p) if "polygon" in element
               else kontur_punkte(element["kontur"], p))
        return min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)
    return None


def _skizzen_flaeche(elemente: list, p: dict) -> float:
    """Fläche der geschlossenen Profile einer Skizze: ein Profil, dessen Umriss ganz in dem eines größeren liegt, ist
    ein Loch (z. B. Langlöcher in der Plattenskizze) und wird abgezogen; getrennte Profile werden addiert."""
    teile = [(e, _flaeche(e, p), _umriss(e, p)) for e in elemente]
    teile = [(e, a, u) for e, a, u in teile if a is not None]
    summe = 0.0
    for i, (_, a, u) in enumerate(teile):
        innen = u is not None and any(
            j != i and b > a and w is not None and w[0] <= u[0] and w[1] <= u[1] and u[2] <= w[2] and u[3] <= w[3]
            for j, (_, b, w) in enumerate(teile))
        summe += -a if innen else a
    return summe


def _hat_rundung(element: dict) -> bool:
    return ("radius" in element.get("rechteck", {}) or "radien" in element.get("polygon", {})
            or "langloch" in element or "kontur" in element)


def bohrspitze(d: float, winkel_grad: float = 118.0) -> float:
    """Volumen (mm³) der kegeligen Bohrspitze eines Bohrers mit Durchmesser d und Spitzenwinkel."""
    return math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(winkel_grad) / 2)


def normbohrung_volumen(art: str, masse: dict, tiefe: float | None, dicke: float | None = None,
                        spitze_grad: float = 118.0) -> float:
    """Volumen (mm³) einer Normbohrung aus der Maßtabelle (Spec 2c §3.3, Tiefenbezug laut S10 Frage 3).

    tiefe: Bohrungstiefe ab der Ansatzfläche (zylindrischer Teil, darunter die Bohrspitze) – blind.
    dicke: Materialdicke bei durchgehender Bohrung (tiefe None). Gewinde sind kosmetisch → Kernloch.
    """
    d = masse.get("kernloch") or masse.get("durchgang") or masse["durchmesser"]
    volumen = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        volumen += bohrspitze(d, spitze_grad)
    if art == "zylinderschraube":
        volumen += math.pi * (masse["senkung_d"] ** 2 - d**2) / 4 * masse["senkung_t"]
    elif art == "senkschraube":
        ds = masse["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(masse["senkwinkel"]) / 2)
        volumen += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return volumen


def _flaeche_schwerpunkt(element: dict, p: dict) -> tuple[float, tuple[float, float]]:
    """Fläche (mm²) und Schwerpunkt (u, v) eines geschlossenen Skizzenelements ohne Rundungen."""
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p), _punkte([r["mitte"]], p)[0]
    if "kreis" in element:
        k = element["kreis"]
        return math.pi * auswerten(k["durchmesser"], p) ** 2 / 4, _punkte([k["mitte"]], p)[0]
    pts = _punkte(element["polygon"]["punkte"], p)
    a2 = _polygon_flaeche(pts)
    kreuz = [(x1 * y2 - x2 * y1, x1 + x2, y1 + y2) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])]
    cx = sum(c * sx for c, sx, _ in kreuz) / (6 * a2)
    cy = sum(c * sy for c, _, sy in kreuz) / (6 * a2)
    return abs(a2), (cx, cy)


def _pappus(f: dict, p: dict) -> float | None:
    """Rotationsvolumen nach Pappus für genau ein Profil (Rechteck, Kreis oder Polygon); mehrere Profile → None
    (verschachtelte Profile zieht SolidWorks voneinander ab, das rechnet diese Formel nicht)."""
    elemente = f["skizze"]["elemente"]
    profile = [e for e in elemente if "mittellinie" not in e]
    if len(profile) != 1:
        return None
    linie = next(e["mittellinie"] for e in elemente if "mittellinie" in e)
    a, b = _punkte([linie["von"], linie["bis"]], p)
    d = (b[0] - a[0], b[1] - a[1])
    flaeche, (cx, cy) = _flaeche_schwerpunkt(profile[0], p)
    r = abs(d[0] * (cy - a[1]) - d[1] * (cx - a[0])) / math.hypot(*d)
    return flaeche * 2 * math.pi * r * auswerten(f.get("winkel", 360), p) / 360


_EBENEN_ACHSE = {"vorne": "z", "oben": "y", "rechts": "x"}


def _dicke(features: dict, flaeche, p: dict) -> float | None:
    """Materialdicke für einen Durchgang (durch_alles, durch): liegt die Skizze bzw. Fläche auf einer Fläche einer
    Extrusion mit fester Tiefe (blind, ohne Formschräge) quer zu deren Extrusionsrichtung – oder auf der Standardebene,
    auf der diese Extrusion beginnt –, ist deren Tiefe die Dicke (Annahme wie überall hier: der Durchgang geht nur durch
    dieses Feature). Sonst None."""
    if isinstance(flaeche, str) and flaeche in _EBENEN_ACHSE:   # Standardebene: die Platte, die auf ihr beginnt
        for x in features.values():
            if (x["typ"] == "extrusion" and x["skizze"]["ebene"] == flaeche and x["ende"]["typ"] == "blind"
                    and schraege(x) is None):
                return auswerten(x["ende"]["tiefe"], p)
        return None
    if not isinstance(flaeche, dict) or "feature" not in flaeche or "flaeche" not in flaeche:
        return None
    x = features.get(flaeche["feature"])
    if not x or x["typ"] != "extrusion" or x["ende"]["typ"] != "blind" or schraege(x) is not None:
        return None
    ebene = x["skizze"]["ebene"]
    if isinstance(ebene, str):
        achse = _EBENEN_ACHSE.get(ebene)
    elif isinstance(ebene, dict) and isinstance(ebene.get("flaeche"), str):
        achse = ebene["flaeche"][-1]
    else:
        return None
    if achse != str(flaeche["flaeche"])[-1]:
        return None
    return auswerten(x["ende"]["tiefe"], p)


def _ueberlappung(bisher: list, f: dict, tiefe: float, p: dict) -> float:
    """Gemeinsames Volumen von f mit früheren Features gleicher Art (beide Schnitt oder beide Aufsatz, blind, ohne
    Formschräge) auf derselben Skizzenebene und in derselben Richtung: liegt ein Profil ganz im anderen, überlappen sie
    auf der kleineren Tiefe (z. B. Freiraum Ø 23 hinter einer Senkung Ø 25,4 ab derselben Fläche). Wird abgezogen,
    damit der gemeinsame Teil nur einmal zählt (Messstand Umbau 4)."""
    schluessel = (f["typ"], repr(f["skizze"]["ebene"]), bool(f["ende"].get("umkehren")))
    profile = [(_flaeche(e, p), _umriss(e, p)) for e in f["skizze"]["elemente"]]
    summe = 0.0
    for alt_schluessel, alt_profile, alt_tiefe in bisher:
        if alt_schluessel != schluessel:
            continue
        for a, u in profile:
            for b, w in alt_profile:
                if None in (a, b, u, w):
                    continue
                innen = (w[0] <= u[0] and w[1] <= u[1] and u[2] <= w[2] and u[3] <= w[3]) or                         (u[0] <= w[0] and u[1] <= w[1] and w[2] <= u[2] and w[3] <= u[3])
                if innen:
                    summe += min(a, b) * min(tiefe, alt_tiefe)
    bisher.append((schluessel, profile, tiefe))
    return summe


def _bohrungs_ueberlappung(bohrungen: list, f: dict, d: float, tiefe: float | None, nach_id: dict, p: dict) -> float:
    """Gemeinsames Volumen der Bohrung bzw. Normbohrung f mit früheren Bohrungen in derselben Extrusion (Fläche ±a eines
    blinden Features mit bekannter Dicke) an denselben Positionen: koaxiale Zylinder, die sich entlang der Achse
    überschneiden (Senkung von oben, Gewinde durch von unten; Effilux AP 6.8). Gerechnet mit dem Kern-Ø (Senkungsring
    einer Normbohrung und Bohrspitze nicht); wird zurückaddiert, damit der gemeinsame Teil nur einmal zählt."""
    flaeche = f["flaeche"]
    if not isinstance(flaeche, dict) or "feature" not in flaeche or "flaeche" not in flaeche:
        return 0.0
    dicke = _dicke(nach_id, flaeche, p)
    if dicke is None:
        return 0.0
    t = dicke if tiefe is None else min(tiefe, dicke)
    seite = str(flaeche["flaeche"])
    von = 0.0 if seite.startswith("+") else dicke - t      # Abschnitt auf der Achse, gezählt ab der +-Fläche
    schluessel = (flaeche["feature"], seite[-1])
    positionen = _punkte(f["positionen"], p)
    summe = 0.0
    for alt_schluessel, alt_positionen, alt_d, alt_von, alt_bis in bohrungen:
        if alt_schluessel != schluessel:
            continue
        laenge = min(von + t, alt_bis) - max(von, alt_von)
        if laenge <= 0:
            continue
        gleich = sum(1 for u in positionen for w in alt_positionen if math.dist(u, w) < 1e-6)
        summe += gleich * math.pi * min(d, alt_d) ** 2 / 4 * laenge
    bohrungen.append((schluessel, positionen, d, von, von + t))
    return summe


def volumen_auto(spec: dict) -> tuple[float | None, str]:
    """Sollvolumen aus der Spezifikation, soweit analytisch möglich (Annahme: Schnitte liegen ganz im Material,
    Aufsätze überlappen nicht). Rückgabe (volumen, grund); volumen None = nicht berechenbar, grund sagt warum.
    Kennt Rundungen, Langloch, Kontur, Normbohrung mit Tiefe, Formschräge an einem Profil (swki.formschraege);
    Durchgänge (durch_alles, durch) nur auf der Fläche einer Extrusion mit fester Tiefe (`_dicke`);
    bis_flaeche/versatz_von_flaeche sind nicht berechenbar."""
    p = spec.get("parameter", {})
    beitrag: dict[str, float] = {}
    nach_id = {f["id"]: f for f in spec["features"]}
    bisher: list = []   # für _ueberlappung
    bohrungen: list = []   # für _bohrungs_ueberlappung
    for f in spec["features"]:
        typ = f["typ"]
        if typ in ("extrusion", "schnitt"):
            ende = f["ende"]
            tiefe = None
            if ende["typ"] == "durch_alles":
                tiefe = _dicke(nach_id, f["skizze"]["ebene"], p) if typ == "schnitt" else None
                if tiefe is None:
                    return None, f"{f['id']}: durch_alles"
                f = {**f, "ende": {**ende, "typ": "blind", "tiefe": tiefe}}   # Durchgang = blind über die Dicke
            if ende["typ"] in ("bis_flaeche", "versatz_von_flaeche"):
                return None, f"{f['id']}: ende {ende['typ']} (Tiefe hängt von der Geometrie ab)"
            if schraege(f) is not None:
                v, grund = volumen_feature(f, p)
                if v is None:
                    return None, grund
            else:
                t = tiefe or auswerten(ende["tiefe"], p)
                v = _skizzen_flaeche(f["skizze"]["elemente"], p) * t
                if ende["typ"] in ("blind", "durch_alles") and len(f["skizze"]["elemente"]) == 1:
                    v -= _ueberlappung(bisher, f, t, p)
            beitrag[f["id"]] = -v if typ == "schnitt" else v
        elif typ == "rotation":
            if any(_hat_rundung(e) for e in f["skizze"]["elemente"]):
                return None, f"{f['id']}: Rotation mit Rundungen (Eckradius, Langloch, Kontur) nicht analytisch"
            v = _pappus(f, p)
            if v is None:
                return None, f"{f['id']}: Rotation mit mehreren Profilen nicht analytisch"
            beitrag[f["id"]] = -v if f.get("schnitt") else v
        elif typ == "bohrung":
            t = _dicke(nach_id, f["flaeche"], p) if f.get("durch") else auswerten(f["tiefe"], p)
            if t is None:
                return None, f"{f['id']}: Bohrung durch"
            d = auswerten(f["durchmesser"], p)
            v = math.pi * d**2 / 4 * t
            if "senkung" in f:
                ds, ts = auswerten(f["senkung"]["durchmesser"], p), auswerten(f["senkung"]["tiefe"], p)
                v += math.pi * (ds**2 - d**2) / 4 * ts
            beitrag[f["id"]] = -v * len(f["positionen"]) + _bohrungs_ueberlappung(
                bohrungen, f, d, None if f.get("durch") else t, nach_id, p)
        elif typ == "normbohrung":
            dicke = _dicke(nach_id, f["flaeche"], p) if f.get("durch") else None
            if f.get("durch") and dicke is None:
                return None, f"{f['id']}: Normbohrung durch"
            masse = normmasse(f["art"], f["groesse"], norm_von(f))
            v = normbohrung_volumen(f["art"], masse, None if f.get("durch") else auswerten(f["tiefe"], p), dicke=dicke,
                                    spitze_grad=bohrspitze_grad())
            kern = masse.get("kernloch") or masse.get("durchgang") or masse["durchmesser"]
            beitrag[f["id"]] = -v * len(f["positionen"]) + _bohrungs_ueberlappung(
                bohrungen, f, kern, None if f.get("durch") else auswerten(f["tiefe"], p), nach_id, p)
        elif typ == "muster_linear":
            kopien = f["richtung1"]["anzahl"] * f.get("richtung2", {}).get("anzahl", 1) - 1
            beitrag[f["id"]] = kopien * sum(beitrag[q] for q in f["features"])
        elif typ == "muster_kreis":
            beitrag[f["id"]] = (f["anzahl"] - 1) * sum(beitrag[q] for q in f["features"])
        elif typ == "spiegeln":
            beitrag[f["id"]] = sum(beitrag[q] for q in f["features"])
        elif typ == "referenz":
            beitrag[f["id"]] = 0.0  # Bezugsgeometrie hat kein Volumen
        elif typ == "verzahnung":
            beitrag[f["id"]] = aus_feature(f, p).flaeche() * auswerten(f["breite"], p)
        else:
            return None, f"{f['id']}: {typ} nicht analytisch berechenbar"
    return sum(beitrag.values()), "analytisch"
