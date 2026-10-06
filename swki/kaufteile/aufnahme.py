"""Aufnahme eines Kaufteils in SolidWorks (Spec 3c §5.1, §5.3, §6): untersuchen (Import und Diagnose, nichts wird
abgelegt) und baue_und_pruefe (Import, Einbaureferenzen, Prüfung, Speichern im Laufordner). Beide schließen ihr
Dokument immer; gespeichert wird nur im Arbeitsordner."""

import time
from pathlib import Path

from swki.compiler import sw
from swki.compiler.fehler import fehler_dict
from swki.kaufteile import sw_kaufteil
from swki.kaufteile.bewertung import bewerte_kaufteil
from swki.kaufteile.diagnose import uebersicht
from swki.kaufteile.katalog import bibliotheksschluessel
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.bilder import screenshots
from swki.speicher import Spitzenmessung
from swki.verbindung import verbinde


def _pid(app) -> int:
    return int(app.GetProcessID)


def untersuche(original: Path, ordner: Path) -> dict:
    """Diagnose einer STEP-Datei (Kopie im Quellordner): Kennzahlen, Flächenübersicht, Bilder, Zeit, Speicher."""
    r = lade_rechner()
    ordner.mkdir(parents=True, exist_ok=True)
    app = verbinde(r.sw_jahr)
    optionen = sw_kaufteil.optionen(app)
    with Spitzenmessung(_pid(app)) as speicher:
        beginn = time.perf_counter()
        model = sw_kaufteil.importiere(app, original)
        import_s = round(time.perf_counter() - beginn, 3)
        try:
            flaechen = sw_kaufteil.alle_flaechen(model)
            kennzahlen = sw_kaufteil.diagnose(model, flaechen)
            liste = uebersicht(sw_kaufteil.datensaetze(flaechen))
            bilder = screenshots(app, model, ordner / "bilder")
        finally:
            sw.schliesse(app, model)
    return {"datei": original.name, "dateigroesse_mb": round(original.stat().st_size / 2 ** 20, 3), "import_s": import_s,
            "dauer_s": round(time.perf_counter() - beginn, 3), "privat_mb": speicher.als_dict(),
            "optionen_vorher": optionen, **kennzahlen, **liste, "bilder": bilder}


def baue_und_pruefe(spec: dict, original: Path, ordner: Path, mit_bildern: bool = False) -> dict:
    """{"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler", "gewinde_modell", "kennzahlen"}. Ein Import- oder
    Einrichtungsfehler ergibt bestanden False mit fehler (nichts gemessen, nichts gespeichert)."""
    r, standard = lade_rechner(), lade_standard()
    tol = standard["toleranzen"]["anker_mm"]
    ordner.mkdir(parents=True, exist_ok=True)
    app = verbinde(r.sw_jahr)
    kennzahlen = {"optionen_vorher": sw_kaufteil.optionen(app)}
    with Spitzenmessung(_pid(app)) as speicher:
        beginn = time.perf_counter()
        try:
            model = sw_kaufteil.importiere(app, original)
        except Exception as e:
            return _abbruch(e)
        try:
            kennzahlen["import_s"] = round(time.perf_counter() - beginn, 3)
            try:
                flaechen, einbau, gewinde = sw_kaufteil.richte_ein(app, model, spec, tol)
            except Exception as e:  # z. B. MATERIAL_UNBEKANNT, Bezugsgeometrie nicht erzeugt
                return _abbruch(e)
            bericht = bewerte_kaufteil(spec, sw_kaufteil.messe(model, spec, flaechen, einbau, gewinde, tol))
            kennzahlen |= {"flaechen": len(flaechen), "interconnect": sw_kaufteil.interconnect_features(model)}
            bilder = {}
            if mit_bildern:
                sw_kaufteil.zeige_bezuege(model)
                bilder = screenshots(app, model, ordner / "bilder")
            teil = ordner / f"{bibliotheksschluessel(spec['hersteller'], spec['bestellnummer'])}.sldprt"
            sw.speichere(model, teil)
        finally:
            sw.schliesse(app, model)
    kennzahlen |= {"dauer_s": round(time.perf_counter() - beginn, 3), "privat_mb": speicher.als_dict()}
    modelle = {}
    for name, g in gewinde.items():
        if isinstance(g, dict) and g["ist"].get("modell"):
            modelle.setdefault(name.rsplit(".", 1)[0], g["ist"]["modell"])
    return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None, "gewinde_modell": modelle,
            "kennzahlen": kennzahlen}


def _abbruch(e: Exception) -> dict:
    f = fehler_dict(e)
    return {"bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": f, "gewinde_modell": {},
            "kennzahlen": {}, "maengel": [{"pruefung": "bau", "knoten": [], "beschreibung": f"{f['code']}: {f['meldung']}"}]}
