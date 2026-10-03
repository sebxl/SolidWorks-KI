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
    spec = lade_spec(pfad)
    return {
        "gueltig": True,
        "spec": str(pfad),
        "name": spec["name"],
        "features": len(spec["features"]),
        "pruefsumme": pruefsumme(spec),
        "hinweise": hinweise(spec),
    }


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
    spec = lade_spec(pfad)
    return {"spec": str(pfad), "kopie": str(kopie_pfad(pfad)), **freigeben(pfad, spec)}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("validieren", help="Schema und Plausibilität prüfen (ohne SolidWorks)")
    p.add_argument("spec")
    p.set_defaults(func=_validieren)
    p = subparsers.add_parser("freigeben", help="Anforderungen freigeben (schreibt freigabe.json)")
    p.add_argument("spec")
    p.set_defaults(func=_freigeben)
