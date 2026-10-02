"""swki bauen: freigegebene Spezifikation in einem frischen Lauf bauen, speichern und protokollieren."""

import time
from pathlib import Path

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
from swki.spec.laden import lade_spec
from swki.verbindung import verbinde


class BauAbbruch(SwkiFehler):
    def __init__(self, ergebnis: dict):
        f = ergebnis["fehler"]
        super().__init__(f"Bau abgebrochen: {f['code']} – {f['meldung']}")
        self.daten = ergebnis


def _vorbereiten(app, model, spec: dict, auftrag: str) -> None:
    globale_variablen(model, spec.get("parameter", {}))
    if "material" in spec:
        setze_material(app, model, spec["material"])
    setze_eigenschaften(model, eigenschaften_fuer(spec, auftrag))


def bauen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    name = dateiname(spec, auftrag, standard)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    beginn = time.perf_counter()
    fehler = None

    app = verbinde(r.sw_jahr)
    with protokoll.phase("vorbereiten"):
        model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"])
        try:
            with protokoll.phase("vorbereiten"):
                _vorbereiten(app, model, spec, auftrag)
        except Exception as e:
            fehler = e
        if fehler is None:
            with protokoll.phase("bauen"):
                fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        with protokoll.phase("speichern"):
            dateien = {"teil": ordner / f"{name}.sldprt", "step": ordner / f"{name}.step"}
            try:
                for pfad in dateien.values():
                    sw.speichere(model, pfad)
                protokoll.dateien = {art: str(pfad) for art, pfad in dateien.items()}
            except Exception as e:
                fehler = fehler or e
    finally:
        sw.schliesse(app, model)  # Titel wird hier neu gelesen (nach SaveAs geändert)

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
    return bauen(Path(args.spec), args.lauf)


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("bauen", help="freigegebene Spezifikation in SolidWorks bauen (neuer Lauf)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Laufnummer ≥ 1 (Vorgabe: nächste freie)")
    p.set_defaults(func=_bauen)
