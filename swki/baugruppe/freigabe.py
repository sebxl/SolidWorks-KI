"""Eine Freigabe für Baugruppe und Teil-Specs (Spec 3b §6). Jede Teil-Spec bekommt ihren Eintrag in freigabe.json und
ihre Freigabe-Kopie; die Baugruppe zusätzlich eine Prüfsumme über die Prüfsummen der Teile und der Katalogeinträge ihrer
Kaufteile (Spec 3c §8.3; die Einträge selbst gibt der Nutzer je Kaufteil frei)."""

from dataclasses import replace

import yaml

from swki.baugruppe.modell import Baugruppe, Quelle
from swki.spec.freigabe import FreigabeFehler, freigabe_eintrag, freigeben, kopie_pfad, pruefe_freigabe, pruefsumme


def kaufteil_summen(bg: Baugruppe) -> dict[str, str]:
    """"kaufteil:<Hersteller> <Bestellnummer>" → Freigabe-Prüfsumme des Katalogeintrags."""
    return {f"kaufteil:{q.kaufteil}": pruefsumme(q.eintrag) for q in bg.quellen.values() if q.art == "kaufteil"}


def teil_summen(bg: Baugruppe) -> dict[str, str]:
    return {datei: pruefsumme(spec) for datei, spec in bg.teile.items()} | kaufteil_summen(bg)


def freigeben_baugruppe(bg: Baugruppe, zeitpunkt: str | None = None) -> dict:
    teile = {datei: freigeben(bg.pfad.parent / datei, spec, zeitpunkt) for datei, spec in bg.teile.items()}
    zusatz = {"kaufteile": kaufteil_summen(bg)} if kaufteil_summen(bg) else None
    return {**freigeben(bg.pfad, bg.spec, zeitpunkt, teile=teil_summen(bg), zusatz=zusatz), "teile": teile}


def pruefe_freigabe_baugruppe(bg: Baugruppe) -> dict:
    """Erst jede Teil-Spec und jeden Kaufteil-Eintrag (die Meldung nennt das Teil), dann die Baugruppe; wirft
    FreigabeFehler."""
    for datei, spec in bg.teile.items():
        pruefe_freigabe(bg.pfad.parent / datei, spec)
    for q in {q.kaufteil: q for q in bg.quellen.values() if q.art == "kaufteil"}.values():
        pruefe_freigabe(q.eintrag_pfad, q.eintrag)
    frueher = (freigabe_eintrag(bg.pfad) or {}).get("kaufteile", {})
    for name, summe in kaufteil_summen(bg).items():
        if name in frueher and frueher[name] != summe:
            raise FreigabeFehler("FREIGABE_VERALTET", f"{name.removeprefix('kaufteil:')}: Katalogeintrag nach der "
                                                      f"Freigabe von {bg.pfad.name} geändert. Nutzer fragen und die "
                                                      "Baugruppe neu freigeben.")
    return pruefe_freigabe(bg.pfad, bg.spec, teile=teil_summen(bg))


def freigegebene_teile(bg: Baugruppe) -> dict[str, dict]:
    """Teil-Specs im Stand der Freigabe (Soll der Teilprüfungen)."""
    return {datei: yaml.safe_load(kopie_pfad(bg.pfad.parent / datei).read_text(encoding="utf-8")) for datei in bg.teile}


def freigegebene_quellen(bg: Baugruppe) -> dict[str, Quelle]:
    """Quellen mit den Teil-Specs im Stand der Freigabe. Soll der Stückliste: die Positionen der je_position-Features
    sind Bauweg der Teil-Spec (nicht in der Prüfsumme) und wären sonst nicht gegen die Freigabe geschützt."""
    soll = freigegebene_teile(bg)
    return {kid: replace(q, spec=soll[q.datei]) if q.art == "teil" else q for kid, q in bg.quellen.items()}
