"""Bewertung je Probe und Steuerung der Studie ohne Optuna (Spec C2 §3, §4) – reine Funktionen.

Ein Lauf ist das Ergebnis der Prüfaufgabe: {"ergebnis": "richtig" | …, "fehlerbild": str | None, "gueltig": bool}.
Ungültige Läufe (Energieprüfung) zählen in keiner Kennzahl außer `anteil_ungueltig`.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

RICHTIG = "richtig"
GRENZE_ANTEIL = 0.02          # Grenzanschlag: so nah (Anteil der Spanne) an einer Bereichsgrenze
_BEDINGUNG = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_:.]*)\s*(<=|>=)\s*(-?[0-9.]+(?:e-?[0-9]+)?)\s*$")


def gueltige(laeufe: list[dict]) -> list[dict]:
    return [r for r in laeufe if r.get("gueltig", True)]


def kennzahlen(je_szenario: dict[str, list[dict]]) -> dict:
    """Allgemeine Kennzahlen: anteil_richtig:<s>, gueltig:<s>, min_/mittel_anteil_richtig, anteil_ungueltig."""
    k, anteile, alle, ungueltig = {}, [], 0, 0
    for name, laeufe in je_szenario.items():
        ok = gueltige(laeufe)
        alle += len(laeufe)
        ungueltig += len(laeufe) - len(ok)
        a = sum(r["ergebnis"] == RICHTIG for r in ok) / len(ok) if ok else 0.0
        k[f"anteil_richtig:{name}"] = a
        k[f"gueltig:{name}"] = len(ok)
        anteile.append(a)
    k["min_anteil_richtig"] = min(anteile) if anteile else 0.0
    k["mittel_anteil_richtig"] = sum(anteile) / len(anteile) if anteile else 0.0
    k["anteil_ungueltig"] = ungueltig / alle if alle else 0.0
    return k


def zaehler(je_szenario: dict[str, list[dict]]) -> dict[str, tuple[int, int]]:
    """{Szenario: (richtig, gültig)}."""
    return {n: (sum(r["ergebnis"] == RICHTIG for r in gueltige(ls)), len(gueltige(ls))) for n, ls in je_szenario.items()}


def fehlerbilder(je_szenario: dict[str, list[dict]]) -> dict[str, float]:
    """Anteil je Fehlerbild an allen gültigen Läufen (ohne Fehlerbild: das Ergebnis), absteigend."""
    ok = [r for ls in je_szenario.values() for r in gueltige(ls)]
    c = Counter(r.get("fehlerbild") or r["ergebnis"] for r in ok if r["ergebnis"] != RICHTIG)
    return {k: v / len(ok) for k, v in c.most_common()} if ok else {}


def verletzung(ausdruck: str, k: dict) -> float:
    """Betrag, um den eine Nebenbedingung `name >= x` / `name <= x` verletzt ist (≤ 0: erfüllt, inf: Kennzahl fehlt)."""
    m = _BEDINGUNG.match(ausdruck)
    if m is None:
        raise ValueError(f"Nebenbedingung {ausdruck!r}: erwartet 'kennzahl >= zahl' oder 'kennzahl <= zahl'")
    name, op, grenze = m.group(1), m.group(2), float(m.group(3))
    if k.get(name) is None:
        return math.inf
    return grenze - k[name] if op == ">=" else k[name] - grenze


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    nenner = 1 + z * z / n
    mitte = (p + z * z / (2 * n)) / nenner
    breite = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
    return max(0.0, mitte - breite), min(1.0, mitte + breite)


def belastbar(stufe1: dict[str, tuple[int, int]], stufe2: dict[str, tuple[int, int]]) -> bool:
    """Prüfstufe 2 (§3.3): jeder Anteil der feineren Rechnung liegt im 95-%-Wilson-Bereich der Prüfstufe 1."""
    for name, (k2, n2) in stufe2.items():
        if name not in stufe1 or n2 == 0:
            continue
        lo, hi = wilson(*stufe1[name])
        if not lo - 1e-12 <= k2 / n2 <= hi + 1e-12:
            return False
    return True


@dataclass
class Fortschritt:
    """Bester Wert und Stillstand: `proben` Proben bzw. `minuten` ohne Verbesserung um mehr als `epsilon`. Zeiten in s."""
    maximieren: bool
    epsilon: float = 0.0
    proben: int | None = None
    minuten: float | None = None
    bester: tuple | None = None                    # (nr, wert)
    verlauf: list = field(default_factory=list)    # [(nr, wert, zeit)] je Verbesserung
    _ref: tuple = (0, 0.0)                         # (nr, zeit) der letzten Verbesserung bzw. des Phasenbeginns
    _letzte: int = 0

    def besser(self, a: float, b: float, eps: float = 0.0) -> bool:
        return a > b + eps if self.maximieren else a < b - eps

    def melde(self, nr: int, wert: float | None, zeit: float) -> bool:
        """True, wenn die Probe den Besten um mehr als epsilon verbessert."""
        self._letzte = nr
        if wert is None:
            return False
        if self.bester is None or self.besser(wert, self.bester[1], self.epsilon):
            self.bester = (nr, wert)
            self.verlauf.append((nr, wert, zeit))
            self._ref = (nr, zeit)
            return True
        if self.besser(wert, self.bester[1]):        # besser, aber unter epsilon: Bester ja, Fortschritt nein
            self.bester = (nr, wert)
        return False

    def stillstand(self, nr: int, zeit: float) -> bool:
        if self.proben is not None and nr - self._ref[0] >= self.proben:
            return True
        return self.minuten is not None and zeit - self._ref[1] >= 60 * self.minuten

    def neu_beginnen(self, zeit: float) -> None:
        """Neue Phase (Automatik): Zähler und Uhr von vorn, der Beste bleibt."""
        self._ref = (self._letzte, zeit)


def grenzanschlaege(werte: dict, bereich: dict, rahmen: dict, anteil: float = GRENZE_ANTEIL) -> list[dict]:
    """Stellschrauben, deren Wert (z. B. des Besten) an einer Bereichsgrenze liegt; erweiterbar, wenn der Rahmen dort
    weiter reicht."""
    out = []
    for name in sorted(werte):
        if name not in bereich:
            continue
        lo, hi = bereich[name]
        d = anteil * (hi - lo)
        for seite, grenze, r in (("unten", lo, rahmen[name][0]), ("oben", hi, rahmen[name][1])):
            if abs(werte[name] - grenze) <= d:
                out.append({"name": name, "seite": seite, "wert": werte[name], "bereich": [lo, hi],
                            "erweiterbar": (r < grenze - 1e-9) if seite == "unten" else (r > grenze + 1e-9)})
    return out


def erweitere(bereich: tuple, rahmen: tuple, seite: str) -> tuple:
    """Bereich an einer Seite um die halbe Spanne erweitern, nur innerhalb des Rahmens."""
    lo, hi = bereich
    d = (hi - lo) / 2
    return (max(rahmen[0], lo - d), hi) if seite == "unten" else (lo, min(rahmen[1], hi + d))
