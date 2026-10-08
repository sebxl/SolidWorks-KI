"""Score eines Durchgangs gegen die Baseline (Spec Messstand §4). Anker: Baseline = 2, Ziel = 7, Ideal = 10."""

from statistics import mean

GRUPPEN = {  # Gewicht, Ziel-Verhältnis (7), Ideal-Verhältnis (10)
    "zeit": (0.50, 0.25, 0.125),
    "aufwand": (0.20, 0.50, 0.25),
    "fehler": (0.20, 0.50, 0.0),
    "speicher": (0.10, 0.70, 0.50),
}
STRAFE_NICHT_FERTIG = 1.5   # Zeitfaktor für Läufe ohne bestanden oder ohne richtig
STRAFE_NEUSTART = 0.25      # Speicher-Verhältnis je SolidWorks-Neustart oder Hänger
DECKEL_FALSCH = 4.0         # höchster Gesamtscore, wenn eine Aufgabe nicht richtig ist
SCHWELLE_BESSER = 1.0


def teilscore(r: float, ziel: float, ideal: float) -> float:
    """r = 1 → 2, r = ziel → 7, r = ideal → 10 (linear dazwischen); r ≥ 2 → 0."""
    if r >= 2:
        return 0.0
    if r >= 1:
        return 2.0 * (2 - r)
    if r >= ziel:
        return 2 + 5 * (1 - r) / (1 - ziel)
    if r >= ideal:
        return 7 + 3 * (ziel - r) / (ziel - ideal) if ziel > ideal else 7.0
    return 10.0


def fehlerzahl(k: dict) -> int:
    return k["bauabbrueche"] + k["pruefmaengel"] + k["pruefer_maengel"] + max(0, k["freigaben"] - 1)


def _fertig(k: dict) -> bool:
    return bool(k.get("bestanden")) and bool(k.get("richtig"))


def _je_aufgabe(laeufe: list[dict]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = {}
    for k in laeufe:
        if not k.get("lecks"):
            g.setdefault(k["aufgabe"], []).append(k)
    return g


def bezug(baseline: list[dict]) -> dict:
    """Baseline-Mittelwerte je Aufgabe (Zeit, Aufrufe, Tokens, Speicher) und Fehler-Summe."""
    g = _je_aufgabe(baseline)
    return {
        "aufgaben": {a: {"zeit_s": mean(k["zeit_s"] for k in ks),
                         "tool_aufrufe": mean(k["tool_aufrufe"] for k in ks),
                         "tokens_gewichtet": mean(k["tokens"]["gewichtet"] for k in ks),
                         "speicher_spitze_mb": mean(k["speicher_spitze_mb"] for k in ks)}
                     for a, ks in g.items()},
        "fehler_summe": sum(fehlerzahl(k) for ks in g.values() for k in ks),
        "laeufe": sum(len(ks) for ks in g.values()),
    }


def bewerte(laeufe: list[dict], b: dict) -> dict:
    """Score eines Durchgangs (laeufe: kpi.json-Inhalte) gegen den Bezug b."""
    g = _je_aufgabe(laeufe)
    r_zeit, r_aufwand, r_speicher = [], [], []
    for a, ks in g.items():
        ba = b["aufgaben"].get(a)
        if not ba:
            continue
        for k in ks:
            zeit = k["zeit_s"] if _fertig(k) else max(k["zeit_s"], STRAFE_NICHT_FERTIG * ba["zeit_s"])
            r_zeit.append(zeit / ba["zeit_s"])
            r_aufwand.append(0.5 * k["tool_aufrufe"] / ba["tool_aufrufe"]
                             + 0.5 * k["tokens"]["gewichtet"] / ba["tokens_gewichtet"])
            r_speicher.append(k["speicher_spitze_mb"] / ba["speicher_spitze_mb"]
                              + STRAFE_NEUSTART * (k.get("sw_neustarts", 0) + k.get("haenger", 0)))
    n = sum(len(ks) for ks in g.values())
    fehler = sum(fehlerzahl(k) for ks in g.values() for k in ks)
    # Fehler je Lauf, damit unterschiedliche Laufzahlen vergleichbar bleiben
    if b["fehler_summe"]:
        r_fehler = (fehler / n) / (b["fehler_summe"] / b["laeufe"])
        s_fehler = teilscore(r_fehler, *GRUPPEN["fehler"][1:])
    else:
        r_fehler, s_fehler = (0.0, 7.0) if fehler == 0 else (2.0, 0.0)
    r = {"zeit": mean(r_zeit), "aufwand": mean(r_aufwand), "fehler": r_fehler, "speicher": mean(r_speicher)}
    s = {gr: teilscore(r[gr], *GRUPPEN[gr][1:]) for gr in GRUPPEN}
    s["fehler"] = s_fehler
    gesamt = sum(GRUPPEN[gr][0] * s[gr] for gr in GRUPPEN)
    falsch = sorted({k["aufgabe"] for ks in g.values() for k in ks if not k.get("richtig")})
    if falsch:
        gesamt = min(gesamt, DECKEL_FALSCH)
    return {"score": round(gesamt, 1), "teilscores": {k: round(v, 2) for k, v in s.items()},
            "verhaeltnisse": {k: round(v, 3) for k, v in r.items()}, "nicht_richtig": falsch,
            "laeufe": n, "ungueltig": [k["lauf"] for k in laeufe if k.get("lecks")]}


def deutlich_besser(neu: dict, alt: dict) -> tuple[bool, str]:
    if neu["score"] < alt["score"] + SCHWELLE_BESSER:
        return False, f"Score {neu['score']} < {alt['score']} + {SCHWELLE_BESSER}"
    for gr, v in neu["teilscores"].items():
        if v < alt["teilscores"][gr] - 1.0:
            return False, f"Teilscore {gr} {v} mehr als 1,0 unter {alt['teilscores'][gr]}"
    if set(neu["nicht_richtig"]) - set(alt["nicht_richtig"]):
        return False, f"zusätzlich nicht richtig: {sorted(set(neu['nicht_richtig']) - set(alt['nicht_richtig']))}"
    return True, "deutlich besser"
