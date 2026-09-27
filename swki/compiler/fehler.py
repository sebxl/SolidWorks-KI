"""Fehler beim Bauen. Jeder Fehler trägt einen Code, der ins Protokoll geht."""

from swki.cli import SwkiFehler

REFERENZ_NICHT_GEFUNDEN = "REFERENZ_NICHT_GEFUNDEN"
REFERENZ_MEHRDEUTIG = "REFERENZ_MEHRDEUTIG"
FEATURE_NICHT_ERZEUGT = "FEATURE_NICHT_ERZEUGT"
REBUILD_FEHLER = "REBUILD_FEHLER"
SKIZZE_NICHT_BESTIMMT = "SKIZZE_NICHT_BESTIMMT"
SKRIPT_FEHLER = "SKRIPT_FEHLER"
UNBEKANNTER_TYP = "UNBEKANNTER_TYP"
SPEICHERN_FEHLGESCHLAGEN = "SPEICHERN_FEHLGESCHLAGEN"
GLEICHUNG_FEHLER = "GLEICHUNG_FEHLER"
SKIZZE_UNGUELTIG = "SKIZZE_UNGUELTIG"
MATERIAL_UNBEKANNT = "MATERIAL_UNBEKANNT"


class BauFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, schritt: str | None = None):
        super().__init__(meldung)
        self.code = code
        self.schritt = schritt
        self.daten = {"code": code, "schritt": schritt}

    def als_dict(self) -> dict:
        return {"code": self.code, "schritt": self.schritt, "meldung": str(self)}


def fehler_dict(e: BaseException) -> dict:
    """Fehler als {"code", "schritt", "meldung"} für Protokolle; fremde Ausnahmen mit ihrem Typnamen als Code."""
    if isinstance(e, BauFehler):
        return e.als_dict()
    return {"code": type(e).__name__, "schritt": None, "meldung": str(e)}
