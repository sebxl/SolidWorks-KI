"""Fehler des Schnellbaus (Spec C1 §5); wie BauFehler mit Code, Feature und Spec-Pfad."""

from swki.cli import SwkiFehler

NICHT_UNTERSTUETZT = "SCHNELLBAU_NICHT_UNTERSTUETZT"
GEOMETRIE = "SCHNELLBAU_GEOMETRIE"
ANKER = "SCHNELLBAU_ANKER"


class SchnellbauFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, feature: str | None = None):
        super().__init__(meldung if feature is None else f"{feature}: {meldung}")
        self.code = code
        self.feature = feature
        self.daten = {"code": code, "feature": feature}
