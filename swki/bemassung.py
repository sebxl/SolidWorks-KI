"""Bemaßungsbezug (Spec 2026-10-23): Bezüge lesen, Paare für `mitte`, Maßplan ohne Überbestimmung, Kennkoordinate eines
Rechtecks. Reine Rechnung ohne SolidWorks; Längen in mm. Achsen: 0 = u, 1 = v.

Der Skizzierer legt je Skizze `Kennpunkt`e an, ruft `massplan` und setzt jeden `Auftrag` als SolidWorks-Beziehung oder -Maß.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Callable

URSPRUNG = "ursprung"
MITTE = "mitte"
_NULL_MM = 1e-6  # Lage, unterhalb der eine Rechteckseite oder -mitte als auf 0 liegend gilt


def _alle_ursprung() -> dict[int, str | dict]:
    return {0: URSPRUNG, 1: URSPRUNG}


@dataclass
class Kennpunkt:
    """Punkt einer Skizze, dessen Lage bemaßt wird (Mittelpunkt, Position, Rechteckmitte oder -seite)."""
    uv: tuple[float, float]
    achsen: tuple[int, ...] = (0, 1)
    bezug: dict[int, str | dict] = field(default_factory=_alle_ursprung)
    pfad: str = ""
    roh: tuple = (None, None)
    gruppe: str = ""  # Art und Größe des Elements; Paare nur innerhalb gleicher Gruppe


@dataclass
class Auftrag:
    """Eine Beziehung oder ein Maß für die Skizze.

    art: ursprung (Maß zum Ursprung, wert), ausrichtung (Koordinate 0), deckung (Punkt im Ursprung, beide Achsen),
    symmetrie (punkt, partner, Mittellinie entlang der anderen Achse), paarabstand (punkt, partner, wert = Abstand),
    bezug (Rand/Fläche, wert = Abstand, bezug = Spec-Wert)."""
    art: str
    punkt: int
    achse: int
    partner: int | None = None
    bezug: str | dict | None = None
    wert: float | None = None


def bezug_von(obj: dict) -> dict[int, str | dict]:
    """Bezug je Achse aus dem `bezug` eines Spec-Knotens; fehlende Achse = "ursprung". Werte unverändert."""
    angabe = obj.get("bezug") or {}
    return {0: angabe.get("u", URSPRUNG), 1: angabe.get("v", URSPRUNG)}


def ebene_ist_flaeche(ebene) -> bool:
    """Liegt eine Skizze auf einer Fläche (Flächenanker `{feature, flaeche}` oder `{nahe}`), nicht auf einer Standard- oder
    Versatzebene? Nur dort gibt es eine Skizzenfläche mit Randkanten für `-rand`/`+rand` und `{flaeche}`."""
    return isinstance(ebene, dict) and ("nahe" in ebene or "flaeche" in ebene)


def paare_mitte(punkte: list[Kennpunkt], achse: int, tol: float) -> list[tuple[int, int]]:
    """Index-Paare (i < j) mit `mitte` auf `achse`, gleicher Gruppe, auf `achse` entgegengesetzt gleich und ≠ 0, auf der
    anderen Achse gleich. Nur Kennpunkte mit beiden Achsen: die Symmetrie legt den Partner ganz fest."""
    andere = 1 - achse
    paare = []
    for i, p in enumerate(punkte):
        if p.bezug.get(achse) != MITTE or abs(p.uv[achse]) <= tol or p.achsen != (0, 1):
            continue
        for j in range(i + 1, len(punkte)):
            q = punkte[j]
            if (q.bezug.get(achse) == MITTE and q.gruppe == p.gruppe and q.achsen == (0, 1)
                    and abs(p.uv[achse] + q.uv[achse]) <= tol and abs(p.uv[andere] - q.uv[andere]) <= tol):
                paare.append((i, j))
    return paare


def _komponenten(anzahl: int, kanten: list[tuple[int, int, int]]) -> list[list[int]]:
    """Zusammenhangskomponenten der Punkte über die Paar-Kanten; je Komponente aufsteigend nach Index."""
    gruppe = list(range(anzahl))

    def wurzel(i: int) -> int:
        while gruppe[i] != i:
            gruppe[i] = gruppe[gruppe[i]]
            i = gruppe[i]
        return i

    for i, j, _ in kanten:
        gruppe[max(wurzel(i), wurzel(j))] = min(wurzel(i), wurzel(j))
    komponenten: dict[int, list[int]] = {}
    for i in range(anzahl):
        komponenten.setdefault(wurzel(i), []).append(i)
    return sorted(komponenten.values())


def _ist_rand_oder_flaeche(bezug) -> bool:
    return isinstance(bezug, dict) or bezug in ("-rand", "+rand")


def massplan(punkte: list[Kennpunkt], bezugslage: Callable[[int, int], float], tol: float) -> list[Auftrag]:
    """Aufträge für alle Punkte einer Skizze, ohne Überbestimmung (Spec §5.2).

    Eine Symmetrie legt den Partner vollständig fest, das Abstandsmaß ersetzt die Lage des festlegenden Punkts. Je
    Komponente gleichzeitig verbundener Paare trägt nur die Wurzel (kleinster Index) Lage- und Abstandsmaße.
    `bezugslage(punkt, achse)` liefert für Rand-/Flächenbezüge die Koordinate des Bezugs auf der Achse."""
    kanten = [(i, j, a) for a in (0, 1) for (i, j) in paare_mitte(punkte, a, tol)]
    benachbart: dict[int, list[tuple[int, int, int]]] = {i: [] for i in range(len(punkte))}
    for i, j, a in kanten:
        benachbart[i].append((i, j, a))
        benachbart[j].append((i, j, a))

    auftraege: list[Auftrag] = []
    wurzeln: list[int] = []
    baumkanten: list[tuple[int, int, int]] = []  # (eltern, kind, achse)
    for komponente in _komponenten(len(punkte), kanten):
        w = komponente[0]
        wurzeln.append(w)
        besucht = {w}
        schlange = deque([w])
        while schlange:
            n = schlange.popleft()
            for i, j, a in benachbart[n]:
                kind = j if i == n else i
                if kind in besucht:
                    continue
                besucht.add(kind)
                schlange.append(kind)
                baumkanten.append((n, kind, a))
                auftraege.append(Auftrag("symmetrie", n, a, partner=kind))

    for w in wurzeln:
        p = punkte[w]
        eigene = []
        for a in p.achsen:
            u = p.uv[a]
            kind = next((k for eltern, k, ba in baumkanten if eltern == w and ba == a), None)
            if kind is not None:
                eigene.append(Auftrag("paarabstand", w, a, partner=kind, wert=abs(u - punkte[kind].uv[a])))
            elif _ist_rand_oder_flaeche(p.bezug.get(a)):
                eigene.append(Auftrag("bezug", w, a, bezug=p.bezug[a], wert=abs(u - bezugslage(w, a))))
            elif abs(u) <= tol:
                eigene.append(Auftrag("ausrichtung", w, a))
            else:
                eigene.append(Auftrag("ursprung", w, a, wert=abs(u)))
        # beide Achsen auf 0 ohne Paar und Rand/Fläche: ein Deckungsmaß statt zweier Ausrichtungen
        if len(eigene) == 2 and all(o.art == "ausrichtung" for o in eigene):
            eigene = [Auftrag("deckung", w, 0)]
        auftraege.extend(eigene)
    return auftraege


def rechteck_kennkoordinate(mitte: float, groesse: float, bezug: str | dict, bezugslage: float | None) -> float:
    """Koordinate (Mitte oder Seite) des bemaßten Kennpunkts eines Rechtecks auf einer Achse (Spec §3).

    `mitte`: die Mitte. `ursprung`: die Mitte, wenn sie auf 0 liegt, sonst die dem Ursprung nächste Seite. `-rand`/`+rand`:
    die Seite in −/+ Richtung. `{flaeche: …}`: die dem Bezug (`bezugslage`) zugewandte, also nähere Seite."""
    minus, plus = mitte - groesse / 2, mitte + groesse / 2
    if bezug == MITTE:
        return mitte
    if bezug == URSPRUNG:
        if abs(mitte) <= _NULL_MM:
            return mitte
        return min((minus, plus), key=abs)
    if bezug == "-rand":
        return minus
    if bezug == "+rand":
        return plus
    if isinstance(bezug, dict):
        if bezugslage is None:
            raise ValueError("Flächenbezug braucht die Lage des Bezugs")
        return min((minus, plus), key=lambda s: abs(s - bezugslage))
    raise ValueError(f"unbekannter Bezug: {bezug!r}")
