"""Reine Hilfen für runde Konturen in Skizzen (Spec 2c §4): Eckradien, Konturpunkte, Bogenendpunkte. Längen in mm."""

from swki.spec.ausdruck import auswerten


def eckradien(polygon: dict, parameter: dict) -> list[float]:
    """Radius je Ecke eines Polygons: ein Wert für alle Ecken oder eine Liste je Ecke (0 = scharf); ohne radien 0."""
    roh = polygon.get("radien", 0)
    if isinstance(roh, list):
        return [auswerten(r, parameter) for r in roh]
    return [auswerten(roh, parameter)] * len(polygon["punkte"])


def kontur_punkte_roh(kontur: dict) -> list:
    """Eckpunkte wie in der Spezifikation: start, dann der Endpunkt jedes Segments (bei geschlossener Kontur = start)."""
    return [kontur["start"], *(s["linie"] if "linie" in s else s["bogen"] for s in kontur["segmente"])]


def kontur_punkte(kontur: dict, parameter: dict) -> list[tuple[float, float]]:
    return [(auswerten(u, parameter), auswerten(v, parameter)) for u, v in kontur_punkte_roh(kontur)]


def bogenende_koordinate(ende, mitte) -> int:
    """Welche Koordinate (0 = u, 1 = v) den Endpunkt eines Bogens festlegt, dessen Mittelpunkt und Anfang bestimmt sind:
    die mit dem kleineren Abstand zum Mittelpunkt – die andere folgt aus dem Radius (S10 Frage 5)."""
    return 0 if abs(ende[0] - mitte[0]) <= abs(ende[1] - mitte[1]) else 1
