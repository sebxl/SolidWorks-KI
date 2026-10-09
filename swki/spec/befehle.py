"""Befehle "swki validieren <spec>" und "swki freigeben <spec>"."""

from pathlib import Path

from swki.spec.freigabe import FreigabeFehler, freigeben, kopie_pfad, pruefsumme
from swki.spec.hinweise import hinweise
from swki.spec.laden import art_der_datei, lade_spec


def _validieren(args) -> dict:
    pfad = Path(args.spec)
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.befehle import validieren  # spät importiert: swki.baugruppe nutzt swki.spec

        return validieren(pfad)
    if art_der_datei(pfad) == "kaufteil":
        from swki.kaufteile.eintrag import validieren as validieren_kaufteil  # spät importiert (Kreisimport)

        return validieren_kaufteil(pfad)
    spec = lade_spec(pfad)
    erg = {
        "gueltig": True,
        "spec": str(pfad),
        "name": spec["name"],
        "features": len(spec["features"]),
        "pruefsumme": pruefsumme(spec),
        "hinweise": hinweise(spec),
    }
    if auto := auto_werte(spec):
        erg["auto"] = auto
    return erg


def auto_werte(spec: dict) -> dict:
    """Die Sollwerte, die `auto` aus den Features rechnet – zum Abgleich mit der Zeichnung vor der Freigabe."""
    from swki.pruefung.geometrie import volumen_auto  # spät importiert (Kreisimport)
    from swki.pruefung.huellquader import huellquader_auto

    pr, erg = spec.get("pruefung", {}), {}
    if pr.get("huellquader") == "auto":
        erg["huellquader"] = huellquader_auto(spec)[0]
    if pr.get("volumen", {}).get("soll") == "auto":
        v, grund = volumen_auto(spec)
        erg["volumen"] = round(v, 3) if v is not None else f"nicht berechenbar ({grund})"
    return erg


_KOPIE_ENDUNG = ".freigegeben.yaml"


def _freigeben(args) -> dict:
    pfad = Path(args.spec)
    if pfad.name.endswith(_KOPIE_ENDUNG):
        original = pfad.name.removesuffix(_KOPIE_ENDUNG) + ".yaml"
        raise FreigabeFehler("FREIGABE_KOPIE", f"{pfad.name} ist die Freigabe-Kopie; freigegeben wird die "
                                               f"Spezifikation selbst ({original})")
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.befehle import freigeben as freigeben_baugruppe  # spät importiert (Kreisimport)

        return freigeben_baugruppe(pfad)
    if art_der_datei(pfad) == "kaufteil":
        from swki.kaufteile.eintrag import freigeben as freigeben_kaufteil  # spät importiert (Kreisimport)

        return freigeben_kaufteil(pfad)
    spec = lade_spec(pfad)
    return {"spec": str(pfad), "kopie": str(kopie_pfad(pfad)), **freigeben(pfad, spec)}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("validieren", help="Schema und Plausibilität prüfen (ohne SolidWorks)")
    p.add_argument("spec")
    p.set_defaults(func=_validieren)
    p = subparsers.add_parser("freigeben", help="Anforderungen freigeben (schreibt freigabe.json)")
    p.add_argument("spec")
    p.set_defaults(func=_freigeben)
