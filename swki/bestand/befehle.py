"""Befehle "swki bestand aufnehmen|zeige|abgleich|ausgabe" (Spec Bestandsdateien §5, §8, §9). Das Original wird nur gelesen; in
SolidWorks geöffnet wird nur die schreibgeschützte Bestandskopie, nur lesend, und nie gespeichert. Die Rohdaten stehen in
`bestand.json`, ausgegeben wird eine Zusammenfassung, mit der sich „das 40er Maß an der Bohrung“ zuordnen lässt. Baugruppen
laufen über `swki.bestand.aufnahme_baugruppe`, der Abgleich gegen den Spec-Stand über `swki.bestand.abgleich_lauf`."""

import re
from pathlib import Path

from swki.bestand import ausgabe
from swki.bestand.ablage import (AUFNAHME_DATEI, aufnahmen, bestand_ordner, ist_baugruppe, kopiere_original, lade_aufnahme,
                                 pruefe_format, schreibe_aufnahme, sha_original, verwirf_aufnahme)
from swki.bestand.fehler import BESTAND_REFERENZ, BESTAND_REFERENZ_EXTERN, BESTAND_UNBEKANNT, BestandFehler
from swki.bestand.pfade import oeffne_in
from swki.bestand.spec import einheit_text
from swki.bestand.sw_bestand import (externe_referenzen, lies_bestand, pruefe_version, zeige_feature, zeige_komponente,
                                     zeige_mass)
from swki.cli import ganzzahl_ab
from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

VOLL_BESTIMMT = 3  # swConstrainedStatus_e.swFullyConstrained


def _extern(pfad: Path, referenzen: list[str]) -> BestandFehler:
    return BestandFehler(BESTAND_REFERENZ_EXTERN, f"{pfad.name} hängt von anderen Dateien ab – Teile mit externen Referenzen "
                                                  "nimmt diese Etappe nicht auf", referenzen=referenzen)


def _kurzwert(werte: dict):
    """Ein Wert, wenn alle lesbaren Konfigurationen übereinstimmen, sonst die Werte je Konfiguration."""
    lesbar = {k: v for k, v in werte.items() if v is not None}
    return next(iter(lesbar.values()), None) if len(set(lesbar.values())) <= 1 else lesbar


def _kurzfeature(f: dict) -> dict:
    aus = [k for k, u in f["unterdrueckt"].items() if u]
    return {"name": f["name"], "typ": f["typ"], **({"unterdrueckt": aus} if aus else {})}


def zusammenfassung(auftrag: str, nummer: int, a: dict, ordner: Path, neu: bool) -> dict:
    """Kompakte Ausgabe: Zähler, Maße (Name, Wert, Zustand), Features, Konfigurationen; Rohdaten in `bestand.json`."""
    offen = {n.rsplit("/", 1)[-1]: s for n, s in a["skizzen"].items() if s != VOLL_BESTIMMT}
    return {"auftrag": auftrag, "aufnahme": nummer, "neu": neu, "datei": a["datei"]["name"], "sha256": a["datei"]["sha256"],
            "version_aelter": a["datei"]["version_aelter"], "konfigurationen": a["konfigurationen"], "aktiv": a["aktiv"],
            "tabelle": a["tabelle"], "einheitensystem": einheit_text(a["einheitensystem"]),
            "zaehler": {"konfigurationen": len(a["konfigurationen"]), "features": len(a["features"]), "masse": len(a["masse"]),
                        "gleichungen": len(a["gleichungen"]), "variablen": len(a["variablen"]),
                        "neuaufbau": len(a["neuaufbau"])},
            "variablen": a["variablen"], "skizzen_offen": offen, "neuaufbau": a["neuaufbau"],
            "masse": [{"name": m["name"], "wert": _kurzwert(m["werte"]), "zustand": m["zustand"]} for m in a["masse"]],
            "features": [_kurzfeature(f) for f in a["features"]],
            "bestand_json": str(ordner / AUFNAHME_DATEI), "bilder": str(ordner / "bilder")}


def _lies_kopie(app, kopie: Path, ordner: Path) -> dict:
    """Lesen geht ohne Fenster (S18b: 1,4 statt 5,3 s, +0 statt +2,3 GB), nur die Bilder brauchen eins; deshalb zweimal
    öffnen."""
    model = oeffne(app, kopie, sichtbar=False, nur_lesen=True)
    try:
        gelesen = lies_bestand(app, model)
    finally:
        sw.schliesse(app, model)
    if gelesen["externe_referenzen"]:
        raise _extern(kopie, gelesen["externe_referenzen"])
    model = oeffne(app, kopie, nur_lesen=True)
    try:
        screenshots(app, model, ordner / "bilder")
    finally:
        sw.schliesse(app, model)
    return gelesen


def aufnehmen(original: Path, auftrag: str, ohne_bewegung: bool = False) -> dict:
    """Spec §5.1/5.2. Prüfungen ohne Öffnen vor der Kopie, damit eine abgelehnte Datei keine Aufnahme hinterlässt; zeigt sich die
    Referenz erst im offenen Dokument, wird der Ordner wieder entfernt. Ob zu lesen ist, entscheidet das fehlende `bestand.json`, nicht
    `neu`: Scheiterte das Lesen, liegt die Kopie schon da und das Lesen lässt sich nachholen. Eine Baugruppe geht über
    `swki.bestand.aufnahme_baugruppe` (§8.1), `ohne_bewegung` gilt nur dort."""
    pruefe_format(original)
    if ist_baugruppe(original):
        from swki.bestand import aufnahme_baugruppe  # spät importiert: nutzt `zusammenfassung` aus diesem Modul

        return aufnahme_baugruppe.aufnehmen(original, auftrag, ohne_bewegung)
    sha_original(original)  # BESTAND_NICHT_LESBAR, bevor SolidWorks gefragt wird
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    pfad = original.absolute()
    versionen, aelter = pruefe_version(app, pfad)
    if referenzen := externe_referenzen(app, pfad):
        raise _extern(pfad, referenzen)
    kopie = kopiere_original(r, auftrag, pfad)
    nummer = kopie["nummer"]
    ordner = bestand_ordner(r, auftrag, nummer)
    if (ordner / AUFNAHME_DATEI).is_file():
        return zusammenfassung(auftrag, nummer, lade_aufnahme(r, auftrag, nummer), ordner, neu=False)
    try:
        gelesen = _lies_kopie(app, kopie["pfad"], ordner)
    except BestandFehler as e:
        if e.daten["code"] == BESTAND_REFERENZ_EXTERN:  # abgelehnt, auch wenn die Kopie aus einem abgebrochenen Versuch stammt
            verwirf_aufnahme(ordner)
        raise
    daten = {**gelesen, "sw_jahr": r.sw_jahr,
             "datei": {"name": kopie["pfad"].name, "original": str(pfad), "sha256": kopie["sha256"], "versionen": versionen,
                       "version_aelter": aelter}}
    schreibe_aufnahme(r, auftrag, nummer, daten)
    return zusammenfassung(auftrag, nummer, daten, ordner, neu=True)


def sichtbar_in(aufnahme: dict, feature: str) -> str:
    """Konfiguration für ein Bild: die aktive, außer das Feature ist dort unterdrückt (das Bild zeigte sonst nichts)."""
    f = next((f for f in aufnahme["features"] if f["name"] == feature), None)
    if f is None or not f["unterdrueckt"].get(aufnahme["aktiv"]):
        return aufnahme["aktiv"]
    return next((k for k in aufnahme["konfigurationen"] if not f["unterdrueckt"].get(k)), aufnahme["aktiv"])


def _dateiname(name: str) -> str:
    """Windows verbietet die Sonderzeichen, SaveAs3 zusätzlich `@` (swFileNameContainsAtSign), das in jedem Maßnamen steht."""
    return re.sub(r'[\\/:*?"<>|@\s]+', "_", name)


def komponente_sichtbar_in(aufnahme: dict, name: str) -> str:
    """Konfiguration für ein Bild der Komponente: die aktive, außer sie ist dort unterdrückt."""
    weg = aufnahme["komponenten"][name]["unterdrueckt"]
    if not weg.get(aufnahme["aktiv"]):
        return aufnahme["aktiv"]
    return next((k for k in aufnahme["konfigurationen"] if not weg.get(k)), aufnahme["aktiv"])


def _zeige_komponente(r, auftrag: str, nummer: int, a: dict, name: str) -> dict:
    """§5.3 für eine Komponente einer Baugruppen-Aufnahme: geöffnet über den Pfadschutz, die Kopie bleibt nur lesend."""
    if a.get("art") != "baugruppe" or name not in a["komponenten"]:
        raise BestandFehler(BESTAND_REFERENZ, f"Komponente {name!r} gibt es in der Aufnahme nicht", komponente=name)
    konfiguration = komponente_sichtbar_in(a, name)
    ordner = bestand_ordner(r, auftrag, nummer)
    ziel = ordner / "bilder" / f"zeige_{_dateiname(name)}.png"
    app = verbinde(r.sw_jahr)
    asm = oeffne_in(app, ordner / a["datei"]["name"], ordner, sichtbar=True, nur_lesen=True)
    try:
        if konfiguration != a["aktiv"]:
            asm.ShowConfiguration2(konfiguration)
        zeige_komponente(app, asm, name, ziel)
    finally:
        sw.schliesse(app, asm)
    return {"auftrag": auftrag, "aufnahme": nummer, "konfiguration": konfiguration, "bild": str(ziel)}


def zeige(auftrag: str, mass: str | None, feature: str | None, komponente: str | None = None) -> dict:
    """Spec §5.3: Bild der jüngsten Bestandskopie mit hervorgehobenem Maß, Feature oder (Baugruppe) Komponente; genau eines
    davon."""
    if sum(x is not None for x in (mass, feature, komponente)) != 1:
        raise BestandFehler(BESTAND_REFERENZ, "Genau eines von --mass, --feature und --komponente nennen")
    r = lade_rechner()
    nummern = aufnahmen(r, auftrag)
    if not nummern:
        raise BestandFehler(BESTAND_UNBEKANNT, f"Keine Aufnahme im Auftrag {auftrag} – zuerst swki bestand aufnehmen",
                            auftrag=auftrag)
    nummer = nummern[-1]
    a = lade_aufnahme(r, auftrag, nummer)
    if komponente is not None:
        return _zeige_komponente(r, auftrag, nummer, a, komponente)
    if mass is not None:
        eintrag = next((m for m in a["masse"] if m["name"] == mass), None)
        if eintrag is None:
            raise BestandFehler(BESTAND_REFERENZ, f"Maß {mass!r} gibt es in der Aufnahme nicht", mass=mass)
        konfiguration = sichtbar_in(a, eintrag["feature"])
    else:
        if not any(f["name"] == feature for f in a["features"]):
            raise BestandFehler(BESTAND_REFERENZ, f"Feature {feature!r} gibt es in der Aufnahme nicht", feature=feature)
        konfiguration = sichtbar_in(a, feature)
    ordner = bestand_ordner(r, auftrag, nummer)
    ziel = ordner / "bilder" / f"zeige_{_dateiname(mass or feature)}.png"
    app = verbinde(r.sw_jahr)
    pfad = ordner / a["datei"]["name"]
    if ist_baugruppe(pfad):
        model = oeffne_in(app, pfad, ordner, sichtbar=True, nur_lesen=True)
    else:
        model = oeffne(app, pfad, nur_lesen=True)
    try:
        if konfiguration != a["aktiv"]:
            model.ShowConfiguration2(konfiguration)
        if mass is not None:
            zeige_mass(app, model, eintrag, ziel)
        else:
            zeige_feature(app, model, feature, ziel)
    finally:
        sw.schliesse(app, model)
    return {"auftrag": auftrag, "aufnahme": nummer, "konfiguration": konfiguration, "bild": str(ziel)}


def _abgleich(a) -> dict:
    from swki.bestand import abgleich_lauf  # spät importiert: zieht Compiler und Differenz nach

    return abgleich_lauf.abgleich(a.auftrag, Path(a.spec), aufnahme=a.aufnahme, lagen_pfad=Path(a.lagen) if a.lagen else None,
                                  referenz=a.referenzbau)


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("bestand", help="Fremde Teile und Baugruppen aufnehmen und ansehen").add_subparsers(
        dest="unterbefehl", required=True)
    p = gruppe.add_parser("aufnehmen", help="Original kopieren und die Kopie lesend aufnehmen (bestand.json, Bilder)")
    p.add_argument("pfad")
    p.add_argument("--auftrag", required=True)
    p.add_argument("--ohne-bewegung", action="store_true",
                   help="Baugruppe: Grenzen nicht fahren, swki pruefen meldet bewegung:* dann als nicht nachgewiesen")
    p.set_defaults(func=lambda a: aufnehmen(Path(a.pfad), a.auftrag, a.ohne_bewegung))
    p = gruppe.add_parser("zeige", help="Bild der Bestandskopie mit hervorgehobenem Maß, Feature oder Komponente")
    p.add_argument("auftrag")
    was = p.add_mutually_exclusive_group(required=True)
    was.add_argument("--mass")
    was.add_argument("--feature")
    was.add_argument("--komponente")
    p.set_defaults(func=lambda a: zeige(a.auftrag, a.mass, a.feature, a.komponente))
    p = gruppe.add_parser("abgleich",
                          help="Aufnahme gegen den Spec-Stand: Was wurde von Hand geändert? Öffnet nichts im Lauf-Ordner")
    p.add_argument("auftrag")
    p.add_argument("--spec", required=True, help="die eigene Spec, aus der die Datei gebaut ist")
    p.add_argument("--aufnahme", type=ganzzahl_ab(1, "--aufnahme"), help="Vorgabe: die jüngste")
    p.add_argument("--lagen", help="JSON mit Soll-Lagen (name, transform), Vorgabe: Prüfbericht des Laufs")
    p.add_argument("--referenzbau", action="store_true",
                   help="geänderte Eigenteile nach <auftrag>/referenz-<n>/ bauen und vergleichen (braucht SolidWorks)")
    p.set_defaults(func=_abgleich)
    p = gruppe.add_parser("ausgabe", help="geänderte Dateien eines bestandenen Laufs nach <auftrag>/ausgabe/ kopieren "
                                          "(der Nutzer kopiert selbst zurück)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter Lauf")
    p.set_defaults(func=lambda a: ausgabe.ausgabe(Path(a.spec), a.lauf))
