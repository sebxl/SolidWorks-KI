"""Hinweise zu einer gültigen Spezifikation, die nicht verhindern, dass sie gebaut wird.

Feste Zahlen in maßtragenden Feldern der Features deckt die Freigabe-Prüfsumme nicht ab (sie gehören zum Bauweg).
Anforderungsmaße sollen deshalb als Parameter geführt werden ("=Name"); validieren meldet die übrigen.
"""

MASS_FELDER = frozenset({
    "tiefe", "durchmesser", "radius", "abstand", "winkel", "breite", "hoehe", "mitte", "punkte", "positionen", "von", "bis",
})
_ANKER = frozenset({"nahe", "kanten", "flaeche"})  # Anker wählen Geometrie aus, sie sind keine Maße


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"pfad", "meldung"}] (0 = Lage auf Achse/Ebene)."""
    hinweise = []

    def gehe(wert, pfad: str, mass: bool) -> None:
        if isinstance(wert, dict):
            for k, v in wert.items():
                if k not in _ANKER:
                    gehe(v, f"{pfad}.{k}", mass or k in MASS_FELDER)
        elif isinstance(wert, list):
            for i, v in enumerate(wert):
                gehe(v, f"{pfad}[{i}]", mass)
        elif mass and isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0:
            hinweise.append({
                "pfad": pfad,
                "meldung": f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab",
            })

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False)
    return hinweise
