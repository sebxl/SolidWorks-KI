"""Änderungserkennung (Spec 3b §8): manuelle Änderungen an gebauten Dateien erkennen, bevor ein neuer Lauf sie still
verliert.

swki bauen schreibt den SHA-256 jeder gespeicherten Datei ins Protokoll (Feld sha256). Vor dem nächsten Bau vergleicht
pruefe_unveraendert den höchsten durchgebauten Lauf (Protokollstatus ok) damit. Läufe ohne Prüfsummen (vor Stufe 3b) und
ganz entfernte Lauf-Ordner gelten als unverändert. swki aenderungen liest die Parameter geänderter Dateien aus (mit
SolidWorks, nur lesend) und vergleicht sie mit der freigegebenen Spezifikation."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_nummern_dateien, lauf_ordner
from swki.cli import SwkiFehler, ganzzahl_ab
from swki.compiler import sw
from swki.konfig import Rechner, lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.spec.ausdruck import auswerten
from swki.spec.freigabe import freigabe_pfad, freigegebene_spec
from swki.spec.laden import art_der_datei
from swki.verbindung import verbinde

MANUELL_GEAENDERT = "MANUELL_GEAENDERT"
# Eigener Code (nicht MANUELL_GEAENDERT): MANUELL_GEAENDERT löst die Rückfrage übernehmen/verwerfen aus, diese
# Meldung hat eine andere Abhilfe (Spezifikation übernehmen und neu freigeben).
UEBERNAHME_OHNE_NEUE_FREIGABE = "UEBERNAHME_OHNE_NEUE_FREIGABE"
_TOL = 1e-6
_SW_DATEIEN = (".sldprt", ".sldasm")


class AenderungFehler(SwkiFehler):
    def __init__(self, meldung: str, code: str = MANUELL_GEAENDERT, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}


def sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pruefsummen(ordner: Path, dateien) -> dict[str, str]:
    """{Pfad relativ zum Lauf-Ordner: SHA-256} der vorhandenen Dateien."""
    return {Path(d).relative_to(ordner).as_posix(): sha256_datei(Path(d)) for d in dateien if Path(d).is_file()}


def letzter_gebauter_lauf(spec_pfad: Path) -> tuple[int, dict] | None:
    """(Nummer, Protokoll) des höchsten Laufs mit Status ok, wenn er Prüfsummen hat; sonst None."""
    for n in sorted(lauf_nummern_dateien(spec_pfad), reverse=True):
        try:
            protokoll = json.loads(lauf_datei(spec_pfad, n, "protokoll").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(protokoll, dict) and protokoll.get("status") == "ok":
            return (n, protokoll) if protokoll.get("sha256") else None
    return None


def abweichungen(ordner: Path, soll: dict[str, str]) -> dict[str, list[str]]:
    geaendert, fehlend = [], []
    for name, summe in sorted(soll.items()):
        pfad = ordner / name
        if not pfad.is_file():
            fehlend.append(name)
        elif sha256_datei(pfad) != summe:
            geaendert.append(name)
    return {"geaendert": geaendert, "fehlend": fehlend}


def befund(r: Rechner, auftrag: str, spec_pfad: Path) -> dict | None:
    letzter = letzter_gebauter_lauf(spec_pfad)
    if letzter is None:
        return None
    n, protokoll = letzter
    ordner = lauf_ordner(r, auftrag, n)
    if not ordner.is_dir():
        return None  # Lauf-Ordner aufgeräumt: es gibt nichts, was verloren gehen könnte
    a = abweichungen(ordner, protokoll["sha256"])
    return {"lauf": n, **a} if a["geaendert"] or a["fehlend"] else None


def _lauf_zeitpunkt(spec_pfad: Path, n: int) -> datetime:
    """Beginn von Lauf n laut Protokoll (Feld gestartet); fehlt es, die Änderungszeit der Protokolldatei (sie wird am
    Ende des Laufs geschrieben, ist also nie früher als der Beginn)."""
    datei = lauf_datei(spec_pfad, n, "protokoll")
    try:
        return datetime.fromisoformat(json.loads(datei.read_text(encoding="utf-8"))["gestartet"])
    except (OSError, ValueError, KeyError, TypeError):
        return datetime.fromtimestamp(datei.stat().st_mtime)


def _freigabe_zeitpunkt(spec_pfad: Path) -> datetime | None:
    try:
        eintrag = json.loads(freigabe_pfad(spec_pfad).read_text(encoding="utf-8"))[spec_pfad.name]
        return datetime.fromisoformat(eintrag["freigegeben"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def pruefe_unveraendert(r: Rechner, auftrag: str, spec_pfad: Path, verwerfen: bool = False,
                        uebernommen: bool = False) -> dict | None:
    """Wirft AenderungFehler, wenn Dateien des letzten durchgebauten Laufs geändert wurden oder fehlen.

    verwerfen (ausdrückliche Anweisung des Nutzers) gibt den Befund nur zurück (fürs Protokoll). uebernommen gilt
    nur, wenn die aktuelle Freigabe NACH Beginn dieses Laufs erteilt wurde (die Änderung also in die Spezifikation
    übernommen und neu freigegeben ist); sonst UEBERNAHME_OHNE_NEUE_FREIGABE. Ohne Abweichung sind beide wirkungslos."""
    if verwerfen and uebernommen:
        raise SwkiFehler("--verwerfen und --uebernommen schließen sich aus: entweder die manuelle Änderung wird "
                         "verworfen oder in die Spezifikation übernommen")
    b = befund(r, auftrag, spec_pfad)
    if b is None or verwerfen:
        return b
    genannt = ", ".join(b["geaendert"] + b["fehlend"])
    if uebernommen:
        freigabe, lauf = _freigabe_zeitpunkt(spec_pfad), _lauf_zeitpunkt(spec_pfad, b["lauf"])
        if freigabe is not None and freigabe > lauf:
            return b
        raise AenderungFehler(
            f"Freigabe ist nicht neuer als Lauf {b['lauf']} (geändert: {genannt}) – erst die Änderung in die "
            "Spezifikation übernehmen, validieren, vom Nutzer bestätigen lassen und per swki freigeben neu freigeben, "
            "dann swki bauen --uebernommen", code=UEBERNAHME_OHNE_NEUE_FREIGABE, **b)
    raise AenderungFehler(
        f"Lauf {b['lauf']} wurde nach dem Bau verändert ({genannt}). "
        "swki aenderungen zeigt die Parameter; Nutzer fragen: übernehmen (Spezifikation ändern, validieren, neu "
        "freigeben, swki bauen --uebernommen) oder verwerfen (swki bauen --verwerfen)", **b)


def vermerke_befund(protokoll, b: dict | None, verwerfen: bool) -> None:
    """Hält den übergangenen Befund im Bauprotokoll fest: verworfen (--verwerfen) oder uebernommen (--uebernommen)."""
    protokoll.verworfen = b if verwerfen else None
    protokoll.uebernommen = None if verwerfen else b


def parameter_differenz(soll: dict, ist: dict) -> list[dict]:
    """Parameter, die fehlen, neu sind oder sich um mehr als 1e-6 unterscheiden (alphabetisch)."""
    differenz = []
    for name in sorted(set(soll) | set(ist)):
        s, i = soll.get(name), ist.get(name)
        if s is None or i is None or abs(float(s) - float(i)) > _TOL:
            differenz.append({"name": name, "soll": s, "ist": i})
    return differenz


def lies_globale_variablen(model) -> dict[str, float]:
    """Globale Variablen (Name → Wert in mm bzw. Grad; IEquationMgr.Value wie in Spike S9a Baustein 5)."""
    gleichungen = model.GetEquationMgr
    werte = {}
    for i in range(gleichungen.GetCount):
        if gleichungen.GlobalVariable(i):
            werte[gleichungen.Equation(i).split('"')[1]] = float(gleichungen.Value(i))
    return werte


def soll_verknuepfungswerte(spec: dict, quellen: dict, parameter: dict | None = None) -> dict[str, float]:
    """Abstands- und Winkelwerte der aufgelösten Verknüpfungen (mm bzw. Grad) nach Verknüpfungs-ID; die Ausdrücke
    werden mit parameter ausgewertet (Vorgabe: die Parameter von spec)."""
    from swki.baugruppe.aufloesen import verknuepfungen  # spät importiert (Kreisimport)

    p = spec.get("parameter", {}) if parameter is None else parameter
    return {v.id: auswerten(v.wert, p) for v in verknuepfungen(spec, quellen) if v.wert is not None}


def soll_parameter(spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, dict]:
    """Dateiname im Lauf → Parameter der freigegebenen Spezifikation (Teil bzw. Baugruppe und ihre Teile)."""
    soll = freigegebene_spec(spec_pfad)
    ergebnis = {}
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.freigabe import freigegebene_teile  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.laden import lade_baugruppe
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        # Verknüpfungen sind Bauweg (aktuelle Spec), ihre Ausdrücke gelten aber mit den freigegebenen Parametern (Spec §8)
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldasm"] = {
            **soll.get("parameter", {}),
            **{f"verknuepfung:{n}": w
               for n, w in soll_verknuepfungswerte(bg.spec, bg.quellen, soll.get("parameter", {})).items()}}
        for datei, teil in freigegebene_teile(bg).items():
            ergebnis[dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard)] = teil.get("parameter", {})
    else:
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldprt"] = soll.get("parameter", {})
    return ergebnis


def aenderungen(spec_pfad: Path, lauf: int | None = None) -> dict:
    """Geänderte Dateien eines Laufs mit Parameterdifferenz zur Freigabe; öffnet SolidWorks nur bei geänderten
    .sldprt/.sldasm und speichert nie."""
    spec_pfad = spec_pfad.resolve()
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        letzter = letzter_gebauter_lauf(spec_pfad)
        if letzter is None:
            return {"spec": spec_pfad.name, "lauf": None, "geaendert": [], "fehlend": [],
                    "text": "kein durchgebauter Lauf mit Prüfsummen"}
        lauf, protokoll = letzter
    else:
        protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    ordner = lauf_ordner(r, auftrag, lauf)
    a = abweichungen(ordner, protokoll.get("sha256", {}))
    soll = soll_parameter(spec_pfad, auftrag, standard)
    ergebnis = []
    sw_dateien = [n for n in a["geaendert"] if n.lower().endswith(_SW_DATEIEN)]
    if sw_dateien:
        app = verbinde(r.sw_jahr)
        for name in sw_dateien:
            model = oeffne(app, ordner / name)
            try:
                ist = lies_globale_variablen(model)
                if name.lower().endswith(".sldasm"):
                    from swki.baugruppe import sw_baugruppe  # spät importiert (Kreisimport)

                    ist |= {f"verknuepfung:{n}": w for n, w in sw_baugruppe.verknuepfungswerte(model).items()}
            finally:
                sw.schliesse(app, model)  # schließt ohne zu speichern (S9b)
            if name not in soll:
                ergebnis.append({"datei": name, "parameter": [], "hinweis": "keine Spezifikation zu dieser Datei (Normteil-Kopie)"})
                continue
            differenz = parameter_differenz(soll[name], ist)
            eintrag = {"datei": name, "parameter": differenz}
            if not differenz:
                eintrag["hinweis"] = "Datei geändert, Parameter gleich – den Nutzer fragen, was geändert wurde"
            ergebnis.append(eintrag)
    ergebnis += [{"datei": n, "parameter": [], "hinweis": "Datei geändert (nicht ausgelesen)"}
                 for n in a["geaendert"] if n not in sw_dateien]
    return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": ergebnis, "fehlend": a["fehlend"]}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("aenderungen", help="manuelle Änderungen am letzten Lauf auslesen (nur lesend)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter durchgebauter Lauf")
    p.set_defaults(func=lambda a: aenderungen(Path(a.spec), a.lauf))
