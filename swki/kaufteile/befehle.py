"""Befehle "swki kaufteil untersuchen|muster|urteil|hole|liste" (Spec 3c §5). Validieren und Freigeben des Eintrags
laufen über die gemeinsamen Befehle (Weiche nach art in swki.spec.befehle)."""

import json
from datetime import date
from pathlib import Path

from swki.auftrag import laeufe, lauf_ordner
from swki.kaufteile import aufnahme, cache, katalog as kat, quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.fehler import KAUFTEIL_PRUEFUNG, KAUFTEIL_UNGEPRUEFT, KaufteilFehler
from swki.kaufteile.katalog import (bibliotheksschluessel, eintrag_pfad, eintraege, finde, geprueft, schluessel,
                                    urteil_pfad)
from swki.konfig import lade_rechner
from swki.pruefung.schleife import lies_urteil
from swki.spec.freigabe import FreigabeFehler, kopie_pfad, pruefe_freigabe, pruefsumme
from swki.spec.laden import SpecFehler, lade_yaml

AUFTRAG = "KAUFTEILE"


def _laufordner(r, bib_schluessel: str) -> tuple[Path, int]:
    """(Ordner, Nummer) des neuen Laufs <arbeitsordner>/KAUFTEILE/<schluessel>/lauf-<n> (bleibt zur Analyse stehen)."""
    auftrag = f"{AUFTRAG}/{bib_schluessel}"
    bisher = laeufe(r, auftrag)
    nummer = bisher[-1] + 1 if bisher else 1
    return lauf_ordner(r, auftrag, nummer), nummer


def _schreibe_json(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def geruest(hersteller: str, bestellnummer: str, original: dict, datenblatt: dict | None, diagnose: dict) -> dict:
    """Anfang eines Katalogeintrags aus der Diagnose; Claude ergänzt Benennung, Material, Belege, Einbau, Prüfwerte."""
    g = {"art": "kaufteil", "hersteller": hersteller, "bestellnummer": bestellnummer, "benennung": "",
         "original": {"datei": original["datei"], "sha256": original["sha256"],
                      "bezug": {"art": "nutzer", "datum": date.today().isoformat()}}}
    if datenblatt is not None:
        g["datenblatt"] = {"datei": datenblatt["datei"]}
    return g | {"koerper": diagnose["koerper"], "material": "", "einbau": {},
                "pruefung": {"volumen": {"soll": diagnose["volumen"], "toleranz_prozent": 0.01}}}


def untersuchen(step: Path, hersteller: str, bestellnummer: str, datenblatt: Path | None = None,
                neue_version: bool = False, katalog: Path | None = None) -> dict:
    """Original (und Datenblatt) in den Quellordner kopieren, importieren und diagnostizieren; schreibt nichts in den
    Katalog und nichts in den Cache (Spec 3c §5.1)."""
    quelle.pruefe_format(step)
    r = lade_rechner()
    pfad = eintrag_pfad(hersteller, bestellnummer, katalog)
    vorhanden = lade_yaml(pfad) if pfad.is_file() else None
    original = quelle.uebernimm(r, step, hersteller, bestellnummer, None if neue_version else vorhanden, neue_version)
    blatt = quelle.uebernimm_datenblatt(r, datenblatt, hersteller) if datenblatt is not None else None
    lauf, _ = _laufordner(r, bibliotheksschluessel(hersteller, bestellnummer))
    diagnose = aufnahme.untersuche(Path(original["pfad"]), lauf)
    _schreibe_json(lauf / "diagnose.json", diagnose)
    return {"schluessel": schluessel(hersteller, bestellnummer), "eintrag": str(pfad), "eintrag_vorhanden": vorhanden is not None,
            "original": original, "datenblatt": blatt, "lauf": str(lauf), "diagnose": diagnose,
            "geruest": geruest(hersteller, bestellnummer, original, blatt, diagnose)}


def _freigegeben(text: str, katalog: Path | None) -> tuple[Path, dict]:
    pfad = finde(text, katalog)
    spec = lade_eintrag(pfad)
    pruefe_freigabe(pfad, spec)
    return pfad, spec


def _baue(spec: dict, r, mit_bildern: bool) -> tuple[Path, dict]:
    original = quelle.original(r, spec)
    lauf, _ = _laufordner(r, bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"]))
    ergebnis = aufnahme.baue_und_pruefe(spec, original, lauf, mit_bildern)
    _schreibe_json(lauf / "pruefbericht.json", ergebnis)
    return lauf, ergebnis


def hole(text: str, katalog: Path | None = None) -> dict:
    """Kaufteil aus dem Cache oder neu aufnehmen, prüfen und ablegen (Spec 3c §5.3)."""
    pfad, spec = _freigegeben(text, katalog)
    if not geprueft(pfad, spec):  # vor dem Cache-Treffer (Spec 3c §5.3 Schritt 1): ohne Urteil nie ein Teil ausgeben
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"{text}: kein bestandenes Prüfer-Urteil zur aktuellen Freigabe – "
                                                  f"swki kaufteil muster \"{text}\", Prüfer-Agent, swki kaufteil urteil",
                             freigabe_pruefsumme=pruefsumme(spec))
    r = lade_rechner()
    ordner = cache.cacheordner(r)
    bib = bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"])
    summe = cache.cache_pruefsumme(spec)
    if cache.ist_aktuell(ordner, bib, summe):
        e = cache.lies(ordner, bib)
        return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pfad": str(cache.teil_pfad(ordner, bib)),
                "gebaut": False, "pruefsumme": summe, "gewinde_modell": e.get("gewinde_modell", {}),
                "pruefung": {"bestanden": True, "datum": e.get("datum")}}
    lauf, ergebnis = _baue(spec, r, mit_bildern=False)
    if ergebnis["fehler"] is not None:
        f = ergebnis["fehler"]
        raise KaufteilFehler(f["code"], f"{text}: {f['meldung']}", ordner=str(lauf))
    if not ergebnis["bestanden"]:
        raise KaufteilFehler(KAUFTEIL_PRUEFUNG, f"{text}: Prüfung nicht bestanden ({len(ergebnis['maengel'])} Mängel)",
                             maengel=ergebnis["maengel"], ordner=str(lauf))
    eintrag = {"schluessel": bib, "hersteller": spec["hersteller"], "bestellnummer": spec["bestellnummer"],
               "pruefsumme": summe, "bestanden": True, "pruefungen": [p["id"] for p in ergebnis["pruefungen"]],
               "gewinde_modell": ergebnis["gewinde_modell"], "kennzahlen": ergebnis["kennzahlen"],
               "datum": date.today().isoformat(), "sw_jahr": r.sw_jahr, "lauf": str(lauf)}
    ziel = cache.lege_ab(ordner, bib, Path(ergebnis["teil"]), eintrag)
    return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pfad": str(ziel), "gebaut": True,
            "pruefsumme": summe, "gewinde_modell": ergebnis["gewinde_modell"], "lauf": str(lauf),
            "pruefung": {"bestanden": True, "pruefungen": len(ergebnis["pruefungen"])}}


def muster(text: str, katalog: Path | None = None) -> dict:
    """Musterteil mit Bildern für den Prüfer-Agenten; braucht die Freigabe, kein Urteil, legt nichts im Cache ab."""
    pfad, spec = _freigegeben(text, katalog)
    r = lade_rechner()
    lauf, ergebnis = _baue(spec, r, mit_bildern=True)
    blatt = spec.get("datenblatt", {}).get("datei")
    return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "bestanden": ergebnis["bestanden"],
            "maengel": ergebnis["maengel"], "fehler": ergebnis["fehler"], "freigabe_pruefsumme": pruefsumme(spec),
            "eintrag": str(kopie_pfad(pfad)), "pruefbericht": str(lauf / "pruefbericht.json"), "bilder": ergebnis["bilder"],
            "datenblatt": str(quelle.quellordner(r, spec["hersteller"]) / blatt) if blatt else None}


def urteil(text: str, datei: Path, freigabe_summe: str, katalog: Path | None = None) -> dict:
    """Prüfer-Urteil (rohes JSON des Prüfer-Agenten) zur aktuellen Freigabe ablegen."""
    pfad, spec = _freigegeben(text, katalog)
    aktuell = pruefsumme(spec)
    if freigabe_summe != aktuell:
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"{text}: Eintrag seit dem Musterteil geändert – neu prüfen",
                             freigabe_pruefsumme=aktuell)
    u = lies_urteil(datei)
    if u is None:
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"Urteil {datei} fehlt")
    inhalt = {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "freigabe_pruefsumme": aktuell,
              "bestanden": u["bestanden"], "maengel": u["maengel"], "datum": date.today().isoformat()}
    _schreibe_json(urteil_pfad(pfad), inhalt)
    return {"datei": str(urteil_pfad(pfad)), **inhalt}


def liste(nur_veraltet: bool = False, katalog: Path | None = None) -> dict:
    r = lade_rechner()
    ordner = cache.cacheordner(r)
    teile = []
    for pfad in eintraege(katalog):
        try:
            spec = lade_eintrag(pfad)
        except SpecFehler as e:
            teile.append({"datei": str(pfad), "gueltig": False, "befunde": len(e.daten["befunde"])})
            continue
        try:
            pruefe_freigabe(pfad, spec)
            frei = True
        except FreigabeFehler:
            frei = False
        bib = bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"])
        im_cache = cache.lies(ordner, bib) is not None
        teile.append({"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "gueltig": True,
                      "freigegeben": frei, "geprueft": geprueft(pfad, spec),
                      "cache": cache.ist_aktuell(ordner, bib, cache.cache_pruefsumme(spec)) if im_cache else None})
    if nur_veraltet:
        teile = [t for t in teile if t.get("cache") is False]
    return {"katalog": str(kat.ORDNER if katalog is None else katalog), "cache": str(ordner), "teile": teile}


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("kaufteil", help="Kaufteile (STEP) untersuchen, prüfen, holen").add_subparsers(
        dest="unterbefehl", required=True)
    p = gruppe.add_parser("untersuchen", help="STEP in den Quellordner kopieren, importieren, Diagnose (schreibt nichts in den Katalog)")
    p.add_argument("step")
    p.add_argument("--hersteller", required=True)
    p.add_argument("--bestellnummer", required=True)
    p.add_argument("--datenblatt")
    p.add_argument("--neue-version", action="store_true", help="neue Herstellerversion neben dem alten Original ablegen")
    p.set_defaults(func=lambda a: untersuchen(Path(a.step), a.hersteller, a.bestellnummer,
                                              Path(a.datenblatt) if a.datenblatt else None, a.neue_version))
    p = gruppe.add_parser("muster", help="Musterteil mit Bildern für den Prüfer-Agenten (freigegebener Eintrag)")
    p.add_argument("schluessel")
    p.set_defaults(func=lambda a: muster(a.schluessel))
    p = gruppe.add_parser("urteil", help="Prüfer-Urteil zur aktuellen Freigabe ablegen")
    p.add_argument("schluessel")
    p.add_argument("datei")
    p.add_argument("--freigabe-pruefsumme", required=True)
    p.set_defaults(func=lambda a: urteil(a.schluessel, Path(a.datei), a.freigabe_pruefsumme))
    p = gruppe.add_parser("hole", help="Kaufteil aus dem Cache holen oder aufnehmen, prüfen und ablegen")
    p.add_argument("schluessel")
    p.set_defaults(func=lambda a: hole(a.schluessel))
    p = gruppe.add_parser("liste", help="Katalog und Cache anzeigen")
    p.add_argument("--veraltet", action="store_true")
    p.set_defaults(func=lambda a: liste(a.veraltet))
