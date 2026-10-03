"""swki bauen: freigegebene Spezifikation in einem frischen Lauf bauen, speichern und protokollieren."""

import time
from pathlib import Path

from swki.aenderungen import pruefe_unveraendert, pruefsummen
from swki.auftrag import auftrag_name, dateiname, lauf_belegt, lauf_datei, lauf_ordner, naechster_lauf
from swki.cli import SwkiFehler, ganzzahl_ab
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import eigenschaften_fuer, globale_variablen, setze_eigenschaften, setze_material
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner, lade_standard
from swki.spec.freigabe import pruefe_freigabe
from swki.spec.laden import art_der_datei, lade_spec
from swki.verbindung import verbinde


class BauAbbruch(SwkiFehler):
    def __init__(self, ergebnis: dict):
        f = ergebnis["fehler"]
        super().__init__(f"Bau abgebrochen: {f['code']} – {f['meldung']}")
        self.daten = ergebnis


def vorbereiten(app, model, spec: dict, auftrag: str) -> None:
    """Parameter als Gleichungen, Werkstoff und Eigenschaften setzen (auch von swki.normteile.bau genutzt)."""
    globale_variablen(model, spec.get("parameter", {}))
    if "material" in spec:
        setze_material(app, model, spec["material"])
    setze_eigenschaften(model, eigenschaften_fuer(spec, auftrag))


def baue_teil_dokument(app, r, standard: dict, spec: dict, spec_pfad: Path, auftrag: str, protokoll: Protokoll):
    """Neues Teil aus der Vorlage, Parameter/Werkstoff/Eigenschaften, Features (auch von swki.baugruppe.bau genutzt).
    Liefert (model, ctx, fehler); das Dokument bleibt offen – der Aufrufer speichert und schließt es."""
    with protokoll.phase("vorbereiten"):
        model = sw.neues_teil(app, r.vorlage_teil)
    ctx = Kontext(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"])
    fehler = None
    try:
        with protokoll.phase("vorbereiten"):
            vorbereiten(app, model, spec, auftrag)
    except Exception as e:  # z. B. MATERIAL_UNBEKANNT
        fehler = e
    if fehler is None:
        with protokoll.phase("bauen"):
            fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    return model, ctx, fehler


def bauen(spec_pfad: Path, lauf: int | None = None, verwerfen: bool = False) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    verworfen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    name = dateiname(spec, auftrag, standard)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    beginn = time.perf_counter()

    app = verbinde(r.sw_jahr)
    protokoll.verworfen = verworfen
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, spec_pfad, auftrag, protokoll)
    dateien = {"teil": ordner / f"{name}.sldprt", "step": ordner / f"{name}.step"}
    try:
        with protokoll.phase("speichern"):
            try:
                for pfad in dateien.values():
                    sw.speichere(model, pfad)
                protokoll.dateien = {art: str(pfad) for art, pfad in dateien.items()}
            except Exception as e:
                fehler = fehler or e
    finally:
        sw.schliesse(app, model)  # Titel wird hier neu gelesen (nach SaveAs geändert)
    protokoll.sha256 = pruefsummen(ordner, dateien.values())

    protokoll.status = "fehler" if fehler else "ok"
    protokoll.fehler = fehler_dict(fehler) if fehler else None
    protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
    protokoll.schreibe(ordner / "protokoll.json")
    protokoll.schreibe(lauf_datei(spec_pfad, lauf, "protokoll"))
    ergebnis = {
        "status": protokoll.status,
        "auftrag": auftrag,
        "lauf": lauf,
        "ordner": str(ordner),
        "dateien": protokoll.dateien,
        "knoten": [{"id": k.id, "status": k.status, "sw_name": k.sw_name} for k in protokoll.knoten],
        "fehler": protokoll.fehler,
        "dauer_s": protokoll.dauer_s,
    }
    if fehler:
        raise BauAbbruch(ergebnis)
    return ergebnis


def _bauen(args) -> dict:
    pfad = Path(args.spec)
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.bau import bauen as baugruppe_bauen  # spät importiert (Kreisimport); Modul aus Task 8

        return baugruppe_bauen(pfad, args.lauf, args.verwerfen)
    return bauen(pfad, args.lauf, args.verwerfen)


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("bauen", help="freigegebene Spezifikation in SolidWorks bauen (neuer Lauf)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Laufnummer ≥ 1 (Vorgabe: nächste freie)")
    p.add_argument("--verwerfen", action="store_true",
                   help="manuelle Änderungen am letzten Lauf ausdrücklich verwerfen (nur auf Anweisung des Nutzers)")
    p.set_defaults(func=_bauen)
