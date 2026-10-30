"""Score des Bewertungsbogens Tempo und Präzision (Spec 2026-10-23-bewertungsbogen-design §5): absolute Anker
0 / 7 / 10 je Gruppe, Sperren, Entscheidung je Umbau. Der alte Messstand-Score (score.py) bleibt für 09.10."""

from statistics import mean

from werkzeuge.messstand.score import fehlerzahl

GRUPPEN = {  # Gewicht, Anker 0, Anker 7, Anker 10
    "zeit_teile": (0.15, 300, 75, 40),
    "zeit_stehlager": (0.10, 700, 180, 100),
    "zeit_pruefstation": (0.25, 2400, 420, 240),
    "praezision_lauf": (0.20, 5, 1, 0),          # Fehlerpunkte im Durchgang
    "praezision_fallen": (0.20, 0, 5, 6),        # Treffer − Fehlalarme
    "aufwand": (0.05, 2.0, 0.6, 0.3),            # tokens_gewichtet / Durchgang 0
    "robustheit": (0.05, 16000, 8000, 5000),     # größte Speicherspitze MB + Hänger
}
TEILE = ("durchlicht", "kamera", "zentrieraufnahme")
AUFGABEN = (*TEILE, "stehlager", "pruefstation")
STRAFE_NICHT_FERTIG = 1.5    # × Durchgang-0-Zeit für Läufe ohne bestanden oder richtig
HAENGER_MB = 2000            # je Hänger oder ungeplantem Neustart
DECKEL_FALSCH = 4.0
SCHWELLE_BESSER = 0.3
PRAEZISION = ("praezision_lauf", "praezision_fallen")


def anker(x: float, null: float, ziel: float, ideal: float) -> float:
    """Stückweise linear durch (null, 0), (ziel, 7), (ideal, 10); außerhalb 0 bzw. 10. Richtung aus den Ankern."""
    if null < ideal:   # größer ist besser
        return anker(-x, -null, -ziel, -ideal)
    if x >= null:
        return 0.0
    if x >= ziel:
        return 7 * (null - x) / (null - ziel)
    if x >= ideal:
        return 7 + 3 * (ziel - x) / (ziel - ideal)
    return 10.0


def _ersetzte(laeufe: list[dict]) -> set[str]:
    return {k["wiederholung_von"] for k in laeufe if k.get("wiederholung_von")}


def _gueltig(laeufe: list[dict]) -> list[dict]:
    return [k for k in laeufe if not k.get("lecks")]


def _zaehlend(laeufe: list[dict]) -> dict[str, list[dict]]:
    """Je Aufgabe die Läufe, die für Zeit und Aufwand zählen (ersetzte Läufe nicht)."""
    weg = _ersetzte(laeufe)
    g: dict[str, list[dict]] = {}
    for k in _gueltig(laeufe):
        if k["lauf"] not in weg:
            g.setdefault(k["aufgabe"], []).append(k)
    return g


def fehlerpunkte(laeufe: list[dict]) -> int:
    """Summe über alle Läufe; ein ersetzter Lauf zählt nur, wenn die Wiederholung es verlangt (Durchgang 0)."""
    laeufe = _gueltig(laeufe)
    mitzaehlen = {k["wiederholung_von"] for k in laeufe if k.get("wiederholung_von") and k.get("original_fehler_zaehlen")}
    weg = _ersetzte(laeufe) - mitzaehlen
    return sum(fehlerzahl(k) for k in laeufe if k["lauf"] not in weg)


def _fertig(k: dict) -> bool:
    return bool(k.get("bestanden")) and bool(k.get("richtig"))


def bezug(d0: list[dict]) -> dict:
    """Durchgang-0-Werte je Aufgabe: Zeit (Strafbezug) und Tokens (Aufwand)."""
    return {"aufgaben": {a: {"zeit_s": mean(k["zeit_s"] for k in ks),
                             "tokens_gewichtet": mean(k["tokens"]["gewichtet"] for k in ks)}
                         for a, ks in _zaehlend(d0).items()}}


def _werte(laeufe: list[dict], fallen: dict, b: dict) -> tuple[dict[str, float], list[str]]:
    """Messgrößen je Gruppe (ungerundet) und die nicht richtigen Aufgaben eines Durchgangs."""
    g = _zaehlend(laeufe)
    fehlt = [a for a in AUFGABEN if a not in g]
    if fehlt:
        raise ValueError(f"Aufgaben ohne gültigen Lauf: {', '.join(fehlt)}")
    werte: dict[str, float] = {}
    for a, ks in g.items():
        ba = b["aufgaben"].get(a, {"zeit_s": 0.0})
        werte[f"zeit_{a}"] = mean(k["zeit_s"] if _fertig(k) else max(k["zeit_s"], STRAFE_NICHT_FERTIG * ba["zeit_s"])
                                  for k in ks)
    werte["zeit_teile"] = mean(werte[f"zeit_{a}"] for a in TEILE)
    werte["praezision_lauf"] = fehlerpunkte(laeufe)
    werte["praezision_fallen"] = fallen["treffer"] - fallen["fehlalarme"]
    werte["aufwand"] = mean(mean(k["tokens"]["gewichtet"] for k in ks) / b["aufgaben"][a]["tokens_gewichtet"]
                            for a, ks in g.items() if a in b["aufgaben"])
    alle = [k for ks in g.values() for k in ks]
    werte["robustheit"] = (max(k["speicher_spitze_mb"] for k in alle)
                           + HAENGER_MB * sum(k.get("haenger", 0) for k in _gueltig(laeufe)))
    return werte, sorted({k["aufgabe"] for k in alle if not k.get("richtig")})


def _score(werte: dict[str, float], falsch: list[str], stellen: int) -> dict:
    s = {gr: anker(werte[gr], *GRUPPEN[gr][1:]) for gr in GRUPPEN}
    gesamt = sum(GRUPPEN[gr][0] * s[gr] for gr in GRUPPEN)
    if falsch:
        gesamt = min(gesamt, DECKEL_FALSCH)
    return {"score": round(gesamt, stellen), "teilscores": {k: round(v, 2) for k, v in s.items()},
            "werte": {k: round(v, 1) for k, v in werte.items()}, "nicht_richtig": falsch}


def bewerte(laeufe: list[dict], fallen: dict, b: dict) -> dict:
    """Score eines Durchgangs: laeufe = kpi.json-Inhalte, fallen = {"treffer", "fehlalarme"}, b = bezug(Durchgang 0)."""
    werte, falsch = _werte(laeufe, fallen, b)
    return {**_score(werte, falsch, 1), "laeufe": sum(len(ks) for ks in _zaehlend(laeufe).values()),
            "ungueltig": [k["lauf"] for k in laeufe if k.get("lecks")], "fallen": fallen}


def mittel(durchgaenge: list[tuple[list[dict], dict]], b: dict) -> dict:
    """Score aus dem Mittel mehrerer Durchgänge (§5.1 ab Umbau 2): je Aufgabe Mittel der Zeiten (Teile aus den
    gemittelten Aufgabenzeiten), Fehlerpunkte, Fallen, Aufwand und Speicher je Durchgang gemittelt, dann die Anker.
    Score mit zwei Nachkommastellen; nicht richtig ist jede Aufgabe, die in einem Durchgang nicht richtig war."""
    je = [_werte(laeufe, fallen, b) for laeufe, fallen in durchgaenge]
    werte = {k: mean(w[k] for w, _ in je) for k in je[0][0] if k != "zeit_teile"}
    werte["zeit_teile"] = mean(werte[f"zeit_{a}"] for a in TEILE)
    falsch = sorted({a for _, f in je for a in f})
    return {**_score(werte, falsch, 2), "durchgaenge": len(durchgaenge)}


def besser(neu: dict, alt: dict, d0: dict) -> tuple[bool, str]:
    """Entscheidung je Umbau (§5.1): +0,3, Präzision nicht schlechter als der aktuelle Stand, Fallen nicht 1 unter
    Durchgang 0, keine zusätzliche nicht-richtige Aufgabe."""
    for gr in PRAEZISION:
        if neu["teilscores"][gr] < alt["teilscores"][gr]:
            return False, f"{gr} {neu['teilscores'][gr]} schlechter als {alt['teilscores'][gr]}"
    if neu["werte"]["praezision_fallen"] <= d0["werte"]["praezision_fallen"] - 1:
        return False, f"praezision_fallen {neu['werte']['praezision_fallen']} mindestens 1 unter Durchgang 0"
    if set(neu["nicht_richtig"]) - set(alt["nicht_richtig"]):
        return False, f"zusätzlich nicht richtig: {sorted(set(neu['nicht_richtig']) - set(alt['nicht_richtig']))}"
    if neu["score"] < alt["score"] + SCHWELLE_BESSER - 1e-9:
        return False, f"Score {neu['score']} < {alt['score']} + {SCHWELLE_BESSER}"
    return True, "besser"
