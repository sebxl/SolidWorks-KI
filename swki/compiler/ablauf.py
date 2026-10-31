"""Bauablauf: Knoten in Reihenfolge abarbeiten, nach jedem prüfen, beim ersten Fehler anhalten."""

from collections.abc import Callable, Iterable

from swki.compiler.fehler import UNBEKANNTER_TYP, BauFehler
from swki.compiler.protokoll import Knoten, Protokoll


def durchlaufe(ctx, protokoll: Protokoll, eintraege: Iterable[dict], rufe: Callable[[Knoten, dict], None],
               nach_knoten: Callable) -> Exception | None:
    """Ruft `rufe(knoten, eintrag)` je Eintrag; liefert den ersten Fehler (oder None). Folgende Knoten werden übersprungen.
    Auch von swki.bestand.bau genutzt (Punkte statt Features)."""
    fehler = None
    for f in eintraege:
        if fehler is not None:
            protokoll.uebersprungen(f["id"], f["typ"])
            continue
        try:
            with protokoll.knoten_lauf(f["id"], f["typ"]) as knoten:
                ctx.knoten = f["id"]
                try:
                    rufe(knoten, f)
                    nach_knoten(ctx)
                finally:  # auch bei einem Fehler: die bis dahin gesetzten Maße helfen bei der Diagnose
                    knoten.masse = ctx.masse.pop(f["id"], None)
        except Exception as e:  # jeder Fehler (auch COM) beendet den Lauf und steht im Protokoll
            fehler = e
    return fehler


def baue_features(ctx, protokoll: Protokoll, handler: dict[str, Callable], nach_knoten: Callable) -> Exception | None:
    """Baut alle Features; liefert den ersten Fehler (oder None). Folgende Knoten werden übersprungen."""

    def rufe(knoten: Knoten, f: dict) -> None:
        funktion = handler.get(f["typ"])
        if funktion is None:
            raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für typ {f['typ']!r}", schritt="handler")
        ergebnis = funktion(ctx, f)
        ctx.ergebnisse[f["id"]] = ergebnis
        knoten.sw_name = ergebnis.sw_name
        knoten.punkte = [list(p) for p in ergebnis.punkte] or None

    return durchlaufe(ctx, protokoll, ctx.spec["features"], rufe, nach_knoten)
