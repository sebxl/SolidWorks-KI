"""Fehlercodes der Kaufteile (Spec 3c §10)."""

from swki.cli import SwkiFehler

KAUFTEIL_FORMAT = "KAUFTEIL_FORMAT"
KAUFTEIL_UNBEKANNT = "KAUFTEIL_UNBEKANNT"
KAUFTEIL_QUELLE_FEHLT = "KAUFTEIL_QUELLE_FEHLT"
KAUFTEIL_QUELLE_ABWEICHEND = "KAUFTEIL_QUELLE_ABWEICHEND"
KAUFTEIL_IMPORT = "KAUFTEIL_IMPORT"
KAUFTEIL_UNGEPRUEFT = "KAUFTEIL_UNGEPRUEFT"
KAUFTEIL_PRUEFUNG = "KAUFTEIL_PRUEFUNG"


class KaufteilFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}
