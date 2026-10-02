"""Normteil-Anfrage: Norm, Größe, Länge und Variante auflösen und gegen die Normtabelle prüfen (Spec 3a §7, §8)."""

import re
from dataclasses import dataclass
from pathlib import Path

from swki.normteile.fehler import (
    NORMLAENGE_UNGUELTIG, NORMTEIL_GESPERRT, NORMTEIL_UNBEKANNT, NORMVARIANTE_UNBEKANNT, NormteilFehler,
)
from swki.normteile.tabelle import ORDNER, lade_normtabelle, norm_datei

_GROESSE = re.compile(r"^(M?\d+(?:\.\d+)?)(?:[xX×](\d+(?:\.\d+)?))?$")


@dataclass(frozen=True)
class Anfrage:
    norm: str              # wie in der Tabelle, z. B. "ISO 4762"
    groesse: str           # Tabellenschlüssel, z. B. "M8" oder "8"
    laenge: float | None   # mm; None bei Teilen ohne Länge
    variante: str

    @property
    def bezeichnung(self) -> str:
        """Größe wie in der Normbezeichnung: "M8 x 30", "M8", "8 x 30"."""
        return self.groesse if self.laenge is None else f"{self.groesse} x {self.laenge:g}"

    @property
    def schluessel(self) -> str:
        """Dateiname in der Bibliothek und Name der Spezifikation, z. B. "ISO4762_M8x30_8_8"."""
        groesse = self.groesse if self.laenge is None else f"{self.groesse}x{self.laenge:g}"
        return re.sub(r"[^A-Za-z0-9-]+", "_", f"{norm_datei(self.norm).upper()}_{groesse}_{self.variante}")


def naechste_laengen(laengen: list, laenge: float) -> dict:
    darunter = [x for x in laengen if x < laenge]
    darueber = [x for x in laengen if x > laenge]
    return {"darunter": max(darunter) if darunter else None, "darueber": min(darueber) if darueber else None}


def loese_auf(norm: str, groesse: str, variante: str | None = None, ordner: Path = ORDNER) -> tuple[dict, Anfrage]:
    """(Normtabelle, Anfrage) z. B. für ("ISO 4762", "M8x30", "10.9"); wirft NormteilFehler mit Code (Spec 3a §8)."""
    t = lade_normtabelle(norm, ordner)
    treffer = _GROESSE.match(re.sub(r"\s+", "", str(groesse)).replace(",", "."))
    if not treffer or treffer.group(1) not in t["groessen"]:
        raise NormteilFehler(NORMTEIL_UNBEKANNT,
                             f"{t['norm']}: Größe {groesse!r} unbekannt; vorhanden: {', '.join(t['groessen'])}",
                             vorhanden=list(t["groessen"]))
    g = treffer.group(1)
    zeile = t["groessen"][g]
    laenge = float(treffer.group(2)) if treffer.group(2) else None
    if t["laenge"]:
        if laenge is None:
            raise NormteilFehler(NORMLAENGE_UNGUELTIG, f"{t['norm']} {g}: Länge fehlt (z. B. {g}x{zeile['laengen'][0]:g})",
                                 laengen=zeile["laengen"])
        if laenge not in zeile["laengen"]:
            naechste = naechste_laengen(zeile["laengen"], laenge)
            raise NormteilFehler(NORMLAENGE_UNGUELTIG,
                                 f"{t['norm']} {g}: Länge {laenge:g} ist keine Normlänge (nächste: "
                                 f"{naechste['darunter']} / {naechste['darueber']})",
                                 naechste=naechste, laengen=zeile["laengen"])
    elif laenge is not None:
        raise NormteilFehler(NORMLAENGE_UNGUELTIG, f"{t['norm']} hat keine Länge (Größe {g})")
    variante = t["vorgabe_variante"] if variante is None else str(variante)
    if variante not in t["varianten"]:
        raise NormteilFehler(NORMVARIANTE_UNBEKANNT,
                             f"{t['norm']}: Variante {variante!r} unbekannt; vorhanden: {', '.join(t['varianten'])}",
                             vorhanden=list(t["varianten"]))
    if zeile["status"] != "abgeglichen":
        raise NormteilFehler(NORMTEIL_GESPERRT, f"{t['norm']} {g} ist gesperrt: {zeile.get('grund')}",
                             grund=zeile.get("grund"))
    return t, Anfrage(t["norm"], g, laenge, variante)
