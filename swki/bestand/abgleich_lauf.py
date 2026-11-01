"""`swki bestand abgleich` (Spec Bestandsdateien §8.5, §8.6): Was wurde an einer selbst gebauten Datei von Hand geändert? Soll
sind Protokoll und Freigabe der alten Spec, Ist ist die Aufnahme, also öffnet der Abgleich nichts im Lauf-Ordner und braucht
kein SolidWorks. Die Logik steht in `swki.bestand.abgleich`, hier werden nur die Stände zusammengetragen.

`--referenzbau` schließt die Lücke des Vergleichs (gleicher Name, gleiche Maße, aber anders): Es baut die Eigenteile mit
geänderter SHA-256 aus der freigegebenen Teil-Spec nach `<auftrag>/referenz-<n>/` und vergleicht sie exakt mit der
Bestandskopie. Das ist eine Messlatte, kein Nachbau: Der Ordner fließt in keinen Lauf und keine Ausgabe ein, die Referenz heißt
`referenz_<name>`, weil SolidWorks keine zwei gleichnamigen Dokumente öffnet (S18d)."""

import json
import re
from dataclasses import asdict
from pathlib import Path, PureWindowsPath

from swki.aenderungen import baum_gegen_soll, letzter_gebauter_lauf, soll_lagen, soll_teile, soll_verknuepfungen_lauf, teil_specs
from swki.auftrag import auftrag_name, lauf_datei
from swki.bestand.abgleich import abgleich_baugruppe, abgleich_dateien
from swki.bestand.ablage import ENDUNG, ENDUNGEN, aufnahmen, bestand_ordner, lade_aufnahme, lade_datei_aufnahme, lade_herkunft
from swki.bestand.differenz import DifferenzFehler, koerper_differenz
from swki.bestand.fehler import BESTAND_NICHT_LESBAR, BESTAND_REFERENZ, BESTAND_UNBEKANNT, BestandFehler
from swki.bestand.pfade import oeffne_in
from swki.bestand.scheiben import datei_schluessel
from swki.bestand.spec import ist_baugruppen_aufnahme
from swki.bestand.sw_bestand import lies_bestand
from swki.bestand.vergleich import vergleiche
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import fehler_dict
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.spec.laden import art_der_datei
from swki.verbindung import verbinde

_REFERENZ = re.compile(r"^referenz-(\d+)$")


def _name(rel: str) -> str:
    return PureWindowsPath(rel).name


def _lauf_zur_aufnahme(r, auftrag: str, nummer: int, spec_pfad: Path) -> tuple[int, dict]:
    """Der Lauf, gegen den verglichen wird, und sein Protokoll aus dem Auftragsordner der Spec, nichts aus dem Lauf-Ordner: der
    aus `herkunft.json`, wenn sie diese Spec nennt, sonst der letzte durchgebaute."""
    herkunft = lade_herkunft(r, auftrag, nummer)
    if herkunft is not None and herkunft.get("spec") == spec_pfad.name:
        datei = lauf_datei(spec_pfad, int(herkunft["lauf"]), "protokoll")
        if datei.is_file():
            return int(herkunft["lauf"]), json.loads(datei.read_text(encoding="utf-8"))
    letzter = letzter_gebauter_lauf(spec_pfad)
    if letzter is None:
        raise BestandFehler(BESTAND_UNBEKANNT,
                            f"Zu {spec_pfad.name} gibt es keinen durchgebauten Lauf mit Prüfsummen: nichts zu vergleichen",
                            spec=str(spec_pfad))
    return letzter


def _lies_lagen(pfad: Path) -> dict | list:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"--lagen {pfad} lässt sich nicht lesen ({e})", pfad=str(pfad)) from e


def _rel_aufnahme(a: dict, datei: str) -> str | None:
    """Der Pfad in der Aufnahme zu einem Dateinamen aus `_vergleiche_dateien`, die Hauptdatei eingeschlossen."""
    return next(rel for rel in _dateien_ist(a) if _name(rel).casefold() == _name(datei).casefold())


def _aufnahme_der_datei(r, auftrag: str, nummer: int, a: dict, rel: str) -> dict:
    return a if datei_schluessel(rel) == datei_schluessel(a["datei"]["name"]) else lade_datei_aufnahme(r, auftrag, nummer, rel)


def _dateien_ist(a: dict) -> dict[str, str]:
    """rel → SHA-256 aller Dateien der Aufnahme. Die Namen im Protokoll liegen flach, die der Aufnahme in ihrer Struktur."""
    return {a["datei"]["name"]: a["datei"]["sha256"], **{rel: d["sha256"] for rel, d in (a.get("dateien") or {}).items()}}


def _vergleiche_dateien(protokoll: dict, a: dict) -> dict:
    """Protokoll gegen Aufnahme, nach Dateinamen (Eindeutig: Gleiche Namen lehnt die Aufnahme ab). Nur SolidWorks-Dateien, eine
    STEP-Ausgabe des Laufs gehört nicht zur Bestandsaufnahme."""
    soll = {_name(n): s for n, s in (protokoll.get("sha256") or {}).items() if n.lower().endswith(ENDUNGEN)}
    ist = {_name(rel): s for rel, s in _dateien_ist(a).items()}
    return abgleich_dateien(soll, ist)


def _referenz_ordner(r, auftrag: str) -> Path:
    wurzel = r.arbeitsordner / auftrag
    ordner = wurzel.iterdir() if wurzel.is_dir() else ()
    belegt = [int(m.group(1)) for p in ordner if p.is_dir() and (m := _REFERENZ.match(p.name))]
    return wurzel / f"referenz-{max(belegt, default=0) + 1}"


def _differenzen(app, kopie: Path, wurzel: Path, model, konfigurationen: list[str]) -> dict[str, list | str]:
    """Bestandskopie gegen die Referenz je gemeinsamer Konfiguration; scheitert eine, steht der Grund da. Die Kopie geht nur
    lesend auf."""
    vorher = oeffne_in(app, kopie, wurzel, sichtbar=False, nur_lesen=True)
    try:
        aus: dict[str, list | str] = {}
        for k in konfigurationen:
            try:
                aus[k] = [asdict(x) for x in koerper_differenz(app, vorher, model, k)]
            except DifferenzFehler as e:
                aus[k] = str(e)
        return aus
    finally:
        sw.schliesse(app, vorher)


def _referenz_teil(app, r, standard: dict, rel: str, spec_teil: dict, spec_pfad: Path, auftrag: str, nummer: int, vorher: dict,
                   ordner: Path) -> dict:
    """Ein Teil aus der freigegebenen Spec bauen, unter `ordner` speichern und mit der Bestandskopie vergleichen. Das Dokument
    geht immer zu, auch nach einem Fehler; ein Baufehler ist ein Befund. Gebaut wird im Auftrag der Spec, nicht in dem der
    Aufnahme, sonst wiche die Eigenschaft `Auftrag` immer ab."""
    eigener = auftrag_name(spec_pfad)
    protokoll = Protokoll(eigener, spec_pfad.name, 0, r.sw_jahr)
    model, _, fehler = baue_teil_dokument(app, r, standard, spec_teil, spec_pfad, eigener, protokoll)
    try:
        if fehler is not None:
            return {"datei": rel, "fehler": fehler_dict(fehler)}
        ziel = ordner / f"referenz_{_name(rel)}"
        sw.speichere(model, ziel)
        nachher = lies_bestand(app, model)
        konfigurationen = [k for k in vorher["konfigurationen"] if k in nachher["konfigurationen"]]
        wurzel = bestand_ordner(r, auftrag, nummer)
        differenzen = _differenzen(app, wurzel / rel, wurzel, model, konfigurationen) if konfigurationen else {}
    finally:
        sw.schliesse(app, model)
    pruefungen = vergleiche({"punkte": []}, {**vorher, "datei": {**vorher["datei"], "ordner": str((wurzel / rel).parent)}},
                            {**nachher, "datei": {"name": ziel.name, "ordner": str(ordner)}}, {})
    je_id = {e["id"]: e for e in pruefungen}
    hinweis = {} if konfigurationen else {"hinweis": "Bestandskopie und Referenz haben keine gemeinsame Konfiguration ("
                                                     f"{', '.join(vorher['konfigurationen'])} gegen "
                                                     f"{', '.join(nachher['konfigurationen'])}): Körper nicht verglichen"}
    return {"datei": str(ziel), "features": je_id["baum"], "masse": je_id["masse"], "differenzen": differenzen,
            "pruefungen": pruefungen, **hinweis}


def referenzbau(r, standard: dict, auftrag: str, nummer: int, a: dict, geaendert: list[str], specs: dict) -> dict:
    """Nur Eigenteile mit geänderter SHA-256; Normteile, Kaufteile und Baugruppen haben keine Teil-Spec und stehen in
    `nicht_gebaut`. `specs`: Dateiname im Lauf → (freigegebene Teil-Spec, ihr Pfad). Ohne etwas zu bauen wird kein SolidWorks
    gefragt."""
    ordner = _referenz_ordner(r, auftrag)
    teile, nicht_gebaut, offen = {}, [], []
    for datei in geaendert:
        rel = _rel_aufnahme(a, datei)
        quelle = next((q for n, q in specs.items() if datei_schluessel(n) == datei_schluessel(_name(rel))), None)
        if quelle is None:
            nicht_gebaut.append({"datei": rel,
                                 "grund": "keine Teil-Spec im Lauf (Normteil, Kaufteil, Baugruppe oder neue Datei)"})
        else:
            offen.append((rel, quelle))
    if offen:
        app = verbinde(r.sw_jahr)
        for rel, (spec_teil, spec_pfad) in offen:
            teile[rel] = _referenz_teil(app, r, standard, rel, spec_teil, spec_pfad, auftrag, nummer,
                                        _aufnahme_der_datei(r, auftrag, nummer, a, rel), ordner)
    return {"ordner": str(ordner), "teile": teile, "nicht_gebaut": nicht_gebaut}


def abgleich(auftrag: str, spec_pfad: Path, aufnahme: int | None = None, lagen_pfad: Path | None = None,
             referenz: bool = False) -> dict:
    """§8.6: Aufnahme `aufnahme` (Vorgabe: die jüngste) des Auftrags gegen den Spec-Stand. `dateien` per SHA-256, `teile` je
    geänderter Datei (`abgleich_teil`), `baugruppe` (`abgleich_baugruppe`, Soll-Lagen aus `--lagen` oder dem Prüfbericht des
    Laufs, sonst steht die Lage in `luecken`). Mit `referenz` zusätzlich `referenzbau`, das allein braucht SolidWorks und öffnet
    nie den Lauf-Ordner."""
    spec_pfad = spec_pfad.resolve()
    art = art_der_datei(spec_pfad)
    if art == "aenderung":
        raise BestandFehler(BESTAND_REFERENZ,
                            f"{spec_pfad.name} ist eine Änderungs-Spec: Der Abgleich braucht die Spec der Datei",
                            spec=str(spec_pfad))
    r, standard = lade_rechner(), lade_standard()
    nummern = aufnahmen(r, auftrag)
    if not nummern:
        raise BestandFehler(BESTAND_UNBEKANNT, f"Keine Aufnahme im Auftrag {auftrag} – zuerst swki bestand aufnehmen",
                            auftrag=auftrag)
    nummer = nummern[-1] if aufnahme is None else aufnahme
    a = lade_aufnahme(r, auftrag, nummer)
    lauf, protokoll = _lauf_zur_aufnahme(r, auftrag, nummer, spec_pfad)
    dateien = _vergleiche_dateien(protokoll, a)
    soll_t = soll_teile(protokoll, spec_pfad, auftrag_name(spec_pfad), standard) if dateien["geaendert"] else {}
    teile = {}
    for datei in dateien["geaendert"]:
        if datei.lower().endswith(ENDUNG):
            rel = _rel_aufnahme(a, datei)
            teile[rel] = baum_gegen_soll(_name(datei), soll_t, _aufnahme_der_datei(r, auftrag, nummer, a, rel), None,
                                         auftrag_name(spec_pfad))
    baugruppe = None
    if ist_baugruppen_aufnahme(a) and art == "baugruppe":
        lagen = _lies_lagen(lagen_pfad) if lagen_pfad is not None else soll_lagen(spec_pfad, lauf)
        baugruppe = abgleich_baugruppe(protokoll, soll_verknuepfungen_lauf(spec_pfad, protokoll), a, lagen)
    aus = {"auftrag": auftrag, "aufnahme": nummer, "spec": spec_pfad.name, "lauf": lauf, "dateien": dateien, "teile": teile,
           "baugruppe": baugruppe}
    if referenz:
        specs = teil_specs(protokoll, spec_pfad, auftrag_name(spec_pfad), standard) if dateien["geaendert"] else {}
        aus["referenzbau"] = referenzbau(r, standard, auftrag, nummer, a, dateien["geaendert"], specs)
    return aus
