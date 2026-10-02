"""Bau und Selbstprüfung eines Normteils in SolidWorks (Spec 3a §6): neues Teil, Werkstoff und Eigenschaften, Features,
Messung und Bewertung im selben Dokument, Speichern im Arbeitsordner."""

import time
from pathlib import Path

from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.bauen import vorbereiten
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.bewertung import bewerte
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import messe
from swki.verbindung import verbinde

AUFTRAG = "NORMTEILE"


def baue_und_pruefe(spec: dict, ordner: Path, mit_bildern: bool = False) -> dict:
    """{"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler"}; ordner liegt im Arbeitsordner. Bei
    Bauabbruch: bestanden False, fehler gesetzt, nichts gemessen und nichts gespeichert."""
    r, standard = lade_rechner(), lade_standard()
    ordner.mkdir(parents=True, exist_ok=True)
    protokoll = Protokoll(AUFTRAG, f"{spec['name']}.yaml", 0, r.sw_jahr)
    beginn = time.perf_counter()
    app = verbinde(r.sw_jahr)
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, ordner / f"{spec['name']}.yaml", standard["toleranzen"]["anker_mm"])
        try:
            vorbereiten(app, model, spec, AUFTRAG)
            fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        except Exception as e:  # z. B. MATERIAL_UNBEKANNT beim Vorbereiten
            fehler = e
        protokoll.status = "fehler" if fehler else "ok"
        protokoll.fehler = fehler_dict(fehler) if fehler else None
        protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
        protokoll.schreibe(ordner / "protokoll.json")
        if fehler is not None:
            return {"bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": fehler_dict(fehler),
                    "maengel": [{"pruefung": "bau", "knoten": [], "beschreibung": str(fehler)}]}
        bericht = bewerte(spec, messe(ctx), standard)
        bilder = screenshots(app, model, ordner / "bilder") if mit_bildern else {}
        teil = ordner / f"{spec['name']}.sldprt"
        sw.speichere(model, teil)
        return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None}
    finally:
        sw.schliesse(app, model)
