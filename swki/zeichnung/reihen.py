"""Reihenanlage linearer Maße (Z1.3 Stufe 2, Nachtrag; Nutzer 18.11.2026: Maße übereinander, Maßzahlen von Linien
gekreuzt). SolidWorks' `AlignDimensions` legte verschachtelte Spannen auf eine Maßlinie; Nachschieben einzelner Zahlen
verschob die Konflikte nur (Live-Diagnose 18.11.). Deshalb deterministisch je Ansichtsseite:

- Seite bleibt, wie SolidWorks sie gewählt hat (unter, über, links, rechts der Ansicht).
- Kurze Spannen innen, lange außen (DIN 406-11 / ISO 129-1: kleinere Maße innen, damit sich Maß- und Hilfslinien
  nicht kreuzen); Spannen, die sich samt Zahl überlappen, nie in einer Reihe.
- Erste Reihe `ERSTE_MM` vor dem Ansichtsumriss, dann je `ABSTAND_MM` (Umriss von SolidWorks schon ~6 mm um das Teil).
- Zahl mittig zwischen den Hilfslinien, wenn sie samt Pfeilen hineinpasst, sonst außen daneben (von der Ansichtsmitte
  weg zuerst).

Alle Werte in Blatt-mm. Ergebnis je Maß: (Lage der Zahlmitte entlang der Maßlinie, Lage der Maßlinie quer dazu).
"""

import math
from dataclasses import dataclass

ERSTE_MM = 5.0
ABSTAND_MM = 8.0
LUECKE_MM = 2.0     # Mindestabstand zweier Belegungen in einer Reihe
PFEILE_MM = 6.0     # Platz für beide Pfeile, wenn die Zahl zwischen den Hilfslinien steht
AUSSEN_MM = 1.5     # Abstand der außen stehenden Zahl zur Hilfslinie
NAH_SCHRITTE = 5    # außen stehende Zahl in der Ansichtsbreite höchstens 4 × 1,5 = 6 mm weiter weg als nötig


@dataclass(frozen=True)
class LinMass:
    schluessel: object
    richtung: str        # h: misst entlang x, Maßlinie waagrecht | v: misst entlang y, Maßlinie senkrecht
    von: float           # Spanne entlang der Messrichtung (Hilfslinien)
    bis: float
    lage: float          # heutige Lage der Maßlinie quer zur Messrichtung (bestimmt die Seite)
    text: float          # Länge der Zahl entlang der Maßlinie


def seite(m: LinMass, umriss) -> str:
    x0, y0, x1, y1 = umriss
    lo, hi = (y0, y1) if m.richtung == "h" else (x0, x1)
    if m.lage <= lo:
        return "-"
    if m.lage >= hi:
        return "+"
    return "-" if m.lage - lo <= hi - m.lage else "+"


def _textlagen(m: LinMass, mitte_ansicht: float, lo_ansicht: float, hi_ansicht: float) -> list[float]:
    """Mögliche Zahlmitten: mittig, wenn die Zahl samt Pfeilen zwischen die Hilfslinien passt; sonst außen daneben,
    zuerst innerhalb der Ansichtsbreite (Live 18.11.: außen links stand die Zahl in der Ecke der senkrechten Maße), dann
    von der Ansichtsmitte weg; je Seite auch weiter außen, um Hilfslinien äußerer Reihen auszuweichen."""
    von, bis = min(m.von, m.bis), max(m.von, m.bis)
    if bis - von >= m.text + PFEILE_MM:
        mitte = (von + bis) / 2
        frei = (bis - von - m.text - PFEILE_MM) / 2
        return [mitte] + [mitte + s * d for d in (1.0 * i for i in range(1, 11)) if d <= frei for s in (1, -1)]
    seiten = [(1, bis + AUSSEN_MM + m.text / 2), (-1, von - AUSSEN_MM - m.text / 2)]
    if (von + bis) / 2 < mitte_ansicht:
        seiten.reverse()
    aus = [t + s * d for d in (1.5 * i for i in range(15)) for s, t in seiten]
    drin = [t for t in aus[:2 * NAH_SCHRITTE] if _drin(m, t, lo_ansicht, hi_ansicht)]
    return drin + [t for t in aus if t not in drin]


def _belegung(m: LinMass, t: float) -> tuple[float, float]:
    von, bis = min(m.von, m.bis), max(m.von, m.bis)
    return min(von, t - m.text / 2) - LUECKE_MM / 2, max(bis, t + m.text / 2) + LUECKE_MM / 2


def _frei(intervall, belegt) -> bool:
    lo, hi = intervall
    return all(hi <= a or b <= lo for a, b in belegt)


def _drin(m: LinMass, t: float, lo_ansicht: float, hi_ansicht: float) -> bool:
    return lo_ansicht <= t - m.text / 2 and t + m.text / 2 <= hi_ansicht


def _anlage(ordnung: list[LinMass], lagen: dict, drin: dict, mindest: dict):
    """Ein Durchlauf für eine Ansichtsseite. Liefert Reihe und Zahlmitte je Maß und das erste Maß, dessen Zahl in
    seiner Reihe keinen guten Platz fand (Liste der klemmenden Maße)."""
    reihe, erste, belegt = {}, {}, []
    for m in ordnung:  # 1. Reihe: kurz innen, Spanne samt Zahl nie überlappend
        k = mindest.get(m.schluessel, 0)
        while m.schluessel not in reihe:
            while k >= len(belegt):
                belegt.append([])
            for t in lagen[m.schluessel]:
                if _frei(_belegung(m, t), belegt[k]):
                    belegt[k].append(_belegung(m, t))
                    reihe[m.schluessel], erste[m.schluessel] = k, t
                    break
            k += 1
    wahl, klemmt = {}, []
    for m in ordnung:  # 2. Zahl: keine Hilfslinie eines Maßes weiter außen darf sie kreuzen; in der Ansichtsbreite
        k = reihe[m.schluessel]
        linien = [x for n in ordnung if reihe[n.schluessel] > k for x in (n.von, n.bis)]
        nachbarn = [_belegung(n, wahl.get(n.schluessel, erste[n.schluessel])) for n in ordnung
                    if n is not m and reihe[n.schluessel] == k]

        def sauber(t):
            lo, hi = t - m.text / 2 - 0.5, t + m.text / 2 + 0.5
            return not any(lo < x < hi for x in linien) and _frei(_belegung(m, t), nachbarn)

        gut = [t for t in lagen[m.schluessel] if not drin[m.schluessel] or t in drin[m.schluessel]]
        t = next((t for t in gut if sauber(t)), None)
        if t is None:  # klemmt: zuletzt jede saubere Lage, auch außerhalb der Ansichtsbreite
            klemmt.append(m)
            t = next((t for t in lagen[m.schluessel] if sauber(t)), erste[m.schluessel])
        wahl[m.schluessel] = t
    return reihe, wahl, klemmt


def reihen(masse: list[LinMass], umriss: tuple[float, float, float, float],
           vorlauf: dict[tuple[str, str], float] | None = None) -> dict[object, tuple[float, float]]:
    """Je Ansichtsseite: Reihen anlegen (`_anlage`); klemmt eine Zahl (Live 18.11.: „20,00“ passte nicht zwischen die
    Hilfslinien der 30 und 40), versuchsweise ihr Maß eine Reihe nach außen rücken – dort kreuzen jene Hilfslinien sie
    nicht mehr. Behalten nur, wenn danach weniger Zahlen klemmen (sonst kaskadieren kurze Maße nach außen).
    `vorlauf`: je (Richtung, Seite) zusätzlicher Abstand der ersten Reihe vom Umriss in mm – für Beschriftungen, die
    SolidWorks dort setzt (Live 18.11.: „SCHNITT A-A“ unter dem Schnitt, Kennbuchstabe über der Stirnansicht)."""
    vorlauf = vorlauf or {}
    x0, y0, x1, y1 = umriss
    aus: dict[object, tuple[float, float]] = {}
    gruppen: dict[tuple[str, str], list[LinMass]] = {}
    for m in masse:
        gruppen.setdefault((m.richtung, seite(m, umriss)), []).append(m)
    for (richtung, s), gruppe in gruppen.items():
        kante = (y0 if s == "-" else y1) if richtung == "h" else (x0 if s == "-" else x1)
        kante += (-1 if s == "-" else 1) * vorlauf.get((richtung, s), 0.0)
        lo_a, hi_a = (x0, x1) if richtung == "h" else (y0, y1)
        vorzeichen = -1 if s == "-" else 1
        ordnung = sorted(gruppe, key=lambda m: (abs(m.bis - m.von), min(m.von, m.bis), str(m.schluessel)))
        lagen = {m.schluessel: _textlagen(m, (lo_a + hi_a) / 2, lo_a, hi_a) for m in ordnung}
        drin = {m.schluessel: {t for t in lagen[m.schluessel][:2 * NAH_SCHRITTE] if _drin(m, t, lo_a, hi_a)}
                for m in ordnung}
        mindest: dict[object, int] = {}
        reihe, wahl, klemmt = _anlage(ordnung, lagen, drin, mindest)
        besser = True
        while klemmt and besser:  # Ausrücken nur behalten, wenn danach weniger Zahlen klemmen
            besser = False
            for m, schritt in ((m, s) for m in klemmt for s in range(1, len(ordnung) + 1)):
                versuch = {**mindest, m.schluessel: reihe[m.schluessel] + schritt}
                r2, w2, k2 = _anlage(ordnung, lagen, drin, versuch)
                if len(k2) < len(klemmt):
                    mindest, reihe, wahl, klemmt, besser = versuch, r2, w2, k2, True
                    break
        for m in ordnung:
            aus[m.schluessel] = (wahl[m.schluessel], kante + vorzeichen * (ERSTE_MM + reihe[m.schluessel] * ABSTAND_MM))
    return aus


def radius_zahl(mitte: tuple[float, float], anfang: tuple[float, float], ende: tuple[float, float],
                abstand: float) -> tuple[float, float] | None:
    """Lage der Zahl eines Radiusmaßes (Nutzer 18.11.2026: Pfeil zeigte auf das Mittelpunktkreuz): außen auf der
    Winkelhalbierenden des Bogens (Bögen unter 180°, z. B. Verrundungen), `abstand` hinter dem Bogen. So läuft die
    Maßlinie von der Zahl zum Bogen, der Pfeil endet am Bogen. Vollkreis oder entarteter Bogen: None."""
    mx, my = (anfang[0] + ende[0]) / 2 - mitte[0], (anfang[1] + ende[1]) / 2 - mitte[1]
    laenge = (mx ** 2 + my ** 2) ** 0.5
    r = ((anfang[0] - mitte[0]) ** 2 + (anfang[1] - mitte[1]) ** 2) ** 0.5
    sehne = ((ende[0] - anfang[0]) ** 2 + (ende[1] - anfang[1]) ** 2) ** 0.5
    if laenge < 1e-6 or r < 1e-6 or sehne < 1e-6:
        return None
    return mitte[0] + mx / laenge * (r + abstand), mitte[1] + my / laenge * (r + abstand)


def radius_zahl_frei(mitte: tuple[float, float], anfang: tuple[float, float], ende: tuple[float, float],
                     abstand: float, hindernisse: list[tuple[tuple[float, float], tuple[float, float]]],
                     laenge: float, breite: float = 4.0) -> tuple[float, float] | None:
    """Wie `radius_zahl`, aber Kanten ausweichen (Live 18.11.: „R4,00“ lag auf der Kabelnut): Strahlen vom Mittelpunkt
    durch Punkte des Bogens (Mitte zuerst, dann nach außen) und wachsende Abstände; die Zahl steht entlang des Strahls
    (Länge `laenge`, Breite `breite` quer). Unter den Lagen, deren Zahl keine Strecke aus `hindernisse` kreuzt, die mit
    den wenigsten Kreuzungen der Hinweislinie, dann die nächste; sonst die Grundlage."""
    grund = radius_zahl(mitte, anfang, ende, abstand)
    if grund is None or not hindernisse:
        return grund
    r = math.dist(anfang, mitte)
    w0 = math.atan2(anfang[1] - mitte[1], anfang[0] - mitte[0])
    w1 = math.atan2(ende[1] - mitte[1], ende[0] - mitte[0])
    spanne = (w1 - w0 + math.pi) % (2 * math.pi) - math.pi  # kürzerer Bogen (Verrundungen < 180°)
    beste = None
    for i, zusatz in enumerate((0.0, 4.0, 8.0, 12.0, 18.0, 25.0)):
        for j, anteil in enumerate((0.5, 0.3, 0.7, 0.15, 0.85)):
            w = w0 + anteil * spanne
            d = (math.cos(w), math.sin(w))
            c = r + abstand + zusatz
            lage = (mitte[0] + d[0] * c, mitte[1] + d[1] * c)
            o = (lage[0] - d[0] * laenge / 2, lage[1] - d[1] * laenge / 2)

            def lokal(p, o=o, d=d):
                px, py = p[0] - o[0], p[1] - o[1]
                return (px * d[0] + py * d[1], -px * d[1] + py * d[0])

            if any(_kreuzt(lokal(a), lokal(b), (0.0, -breite / 2, laenge, breite / 2)) for a, b in hindernisse):
                continue
            # Hinweislinie vom Bogen bis zur Zahl: je weniger Kanten sie kreuzt, desto besser (Live 18.11.: quer über die Nut)
            bogenpunkt = (mitte[0] + d[0] * r, mitte[1] + d[1] * r)
            wert = (sum(_schnitt(bogenpunkt, o, a, b) for a, b in hindernisse), i, j)
            if beste is None or wert < beste[0]:
                beste = (wert, lage)
    return beste[1] if beste else grund


def _schnitt(p, q, a, b) -> bool:
    """Schneiden sich die Strecken p–q und a–b (echt, nicht nur berührend)?"""
    def kreuz(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])

    d1, d2, d3, d4 = kreuz(a, b, p), kreuz(a, b, q), kreuz(p, q, a), kreuz(p, q, b)
    return d1 * d2 < 0 and d3 * d4 < 0


def _kreuzt(a, b, r) -> bool:
    """Strecke a–b gegen Rechteck r = (x0, y0, x1, y1) (Liang-Barsky)."""
    x0, y0, x1, y1 = r
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True
