"""Bauablauf: Features in Reihenfolge bauen, nach jedem Knoten prüfen, beim ersten Fehler anhalten."""

from collections.abc import Callable

from swki.compiler.fehler import UNBEKANNTER_TYP, BauFehler
from swki.compiler.protokoll import Protokoll


def baue_features(ctx, protokoll: Protokoll, handler: dict[str, Callable], nach_knoten: Callable) -> Exception | None:
    """Baut alle Features; liefert den ersten Fehler (oder None). Folgende Knoten werden übersprungen."""
    fehler = None
    for f in ctx.spec["features"]:
        if fehler is not None:
            protokoll.uebersprungen(f["id"], f["typ"])
            continue
        try:
            with protokoll.knoten_lauf(f["id"], f["typ"]) as knoten:
                funktion = handler.get(f["typ"])
                if funktion is None:
                    raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für typ {f['typ']!r}", schritt="handler")
                ergebnis = funktion(ctx, f)
                ctx.ergebnisse[f["id"]] = ergebnis
                knoten.sw_name = ergebnis.sw_name
                knoten.punkte = [list(p) for p in ergebnis.punkte] or None
                nach_knoten(ctx)
        except Exception as e:  # jeder Fehler (auch COM) beendet den Lauf und steht im Protokoll
            fehler = e
    return fehler
