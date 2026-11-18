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
