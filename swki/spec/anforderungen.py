"""Anforderungen an Features nach Wirkung (Zeichnungsableitung, Design 2026-11-16 §4.2).

Features sind Bauweg: beim Nachbessern werden sie umbenannt, zusammengefasst oder zwischen `positionen` und Muster
gewechselt. Die Prüfsumme nimmt deshalb nicht die Feature-IDs, sondern eine sortierte Liste von Tupeln
[Feature-Art, Nenngröße, {Anforderungsfelder}, Anzahl] auf (Mehrfachmenge: Anzahl = Instanzen über Positionen, Muster
und Spiegelungen, damit Zusammenfassen und Mustern sie nicht ändern). Die Lage im Teil prüft erst swki pruefen am Modell.
"""

import json

from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.funktionen import ANFORDERUNG_FELDER, aufloesen
from swki.spec.instanzen import anzahl_instanzen
from swki.spec.normen import groesse_text


def _hat_anforderung(f: dict) -> bool:
    return any(feld in f for feld in ANFORDERUNG_FELDER)


def _nenngroesse(f: dict, parameter: dict):
    if f.get("typ") == "normbohrung":
        return f"{f['art']} {groesse_text(f['groesse'])}"
    if f.get("typ") == "bohrung" and "durchmesser" in f:
        try:
            return round(auswerten(f["durchmesser"], parameter), 6)
        except (AusdruckFehler, ValueError, TypeError):  # auch maskierte Stellschrauben (swki.optimierung.raum)
            return f["durchmesser"]
    return None


def anforderungs_tupel(spec: dict) -> list[list]:
    """[[typ_gruppe, nenngroesse, {feld: wert}, anzahl], …] sortiert; gleiche Tupel zusammengezählt (Instanzen);
    typ_gruppe "bohrung" für bohrung und normbohrung, sonst der Feature-Typ."""
    parameter = spec.get("parameter", {})
    tupel: dict[str, list] = {}
    for f in spec.get("features", []):
        if not _hat_anforderung(f):
            continue
        gruppe = "bohrung" if f.get("typ") in ("bohrung", "normbohrung") else f.get("typ")
        kern = [gruppe, _nenngroesse(f, parameter), {feld: f[feld] for feld in ANFORDERUNG_FELDER if feld in f}]
        schluessel = json.dumps(kern, sort_keys=True, ensure_ascii=False)
        tupel.setdefault(schluessel, [*kern, 0])[3] += anzahl_instanzen(spec, f["id"])
    return [tupel[k] for k in sorted(tupel)]


def aufgeloeste_anforderungen(spec: dict) -> list[dict]:
    """Geltende Werte je Feature mit Anforderung (Tabellenstand zum Zeitpunkt des Aufrufs), für freigabe.json."""
    return [{"feature": f["id"], **aufloesen(f)} for f in spec.get("features", []) if _hat_anforderung(f)]
