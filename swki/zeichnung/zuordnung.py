"""Zuordnung Maß → Ansicht (Z1.3 Stufe 2; Design §6.1, Nutzer 17.11.2026: meist 3–4 Ansichten, keine überladen).

Jedes Maß kommt in genau eine Ansicht, in der es darstellbar ist (Kandidaten). Maße mit wenig Kandidaten zuerst, dann
in die Ansicht mit den wenigsten Maßen, bei Gleichstand nach Vorrang (Hauptansicht zuerst). Keine Ansicht über der
Obergrenze; was nicht passt, verlangt eine weitere Ansicht und steht in `meldungen` (nie still weglassen).
"""

from dataclasses import dataclass, field

MAX_VORGABE = 12  # Design §6.1, selbst entschieden


@dataclass
class Zuordnung:
    je_ansicht: dict[str, list[str]]
    ohne_ansicht: list[str] = field(default_factory=list)
    weitere_ansicht: bool = False
    meldungen: list[str] = field(default_factory=list)


def max_je_ansicht(standard: dict) -> int:
    return int((standard.get("zeichnung") or {}).get("max_masse_je_ansicht", MAX_VORGABE))


def ordne_zu(kandidaten: dict[str, list[str]], ansichten: list[str], max_je_ansicht: int) -> Zuordnung:
    z = Zuordnung({r: [] for r in ansichten})
    rang = {r: i for i, r in enumerate(ansichten)}
    for mass in sorted(kandidaten, key=lambda m: (len(kandidaten[m]), m)):
        moeglich = [r for r in kandidaten[mass] if r in z.je_ansicht]
        if not moeglich:
            z.ohne_ansicht.append(mass)
            z.weitere_ansicht = True
            z.meldungen.append(f"MASS_OHNE_ANSICHT: {mass} ist in keiner Ansicht darstellbar")
            continue
        frei = [r for r in moeglich if len(z.je_ansicht[r]) < max_je_ansicht]
        if not frei:
            z.weitere_ansicht = True
            z.meldungen.append(f"ANSICHT_VOLL: {mass} passt nicht mehr in {', '.join(moeglich)} "
                               f"(Obergrenze {max_je_ansicht} Maße je Ansicht)")
            continue
        ziel = min(frei, key=lambda r: (len(z.je_ansicht[r]), rang[r]))
        z.je_ansicht[ziel].append(mass)
    return z
