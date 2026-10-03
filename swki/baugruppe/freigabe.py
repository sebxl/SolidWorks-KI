"""Eine Freigabe für Baugruppe und Teil-Specs (Spec 3b §6). Jede Teil-Spec bekommt ihren Eintrag in freigabe.json und
ihre Freigabe-Kopie; die Baugruppe zusätzlich eine Prüfsumme über die Prüfsummen der Teile."""

import yaml

from swki.baugruppe.modell import Baugruppe
from swki.spec.freigabe import freigeben, kopie_pfad, pruefe_freigabe, pruefsumme


def teil_summen(bg: Baugruppe) -> dict[str, str]:
    return {datei: pruefsumme(spec) for datei, spec in bg.teile.items()}


def freigeben_baugruppe(bg: Baugruppe, zeitpunkt: str | None = None) -> dict:
    teile = {datei: freigeben(bg.pfad.parent / datei, spec, zeitpunkt) for datei, spec in bg.teile.items()}
    return {**freigeben(bg.pfad, bg.spec, zeitpunkt, teile=teil_summen(bg)), "teile": teile}


def pruefe_freigabe_baugruppe(bg: Baugruppe) -> dict:
    """Erst jede Teil-Spec (die Meldung nennt das Teil), dann die Baugruppe; wirft FreigabeFehler."""
    for datei, spec in bg.teile.items():
        pruefe_freigabe(bg.pfad.parent / datei, spec)
    return pruefe_freigabe(bg.pfad, bg.spec, teile=teil_summen(bg))


def freigegebene_teile(bg: Baugruppe) -> dict[str, dict]:
    """Teil-Specs im Stand der Freigabe (Soll der Teilprüfungen)."""
    return {datei: yaml.safe_load(kopie_pfad(bg.pfad.parent / datei).read_text(encoding="utf-8")) for datei in bg.teile}
