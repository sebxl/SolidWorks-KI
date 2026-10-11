"""Befehle "swki pruefen", "swki status" und "swki bericht"."""

import json
import subprocess
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.cli import SwkiFehler, ganzzahl_ab
from swki.compiler import sw
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.bewertung import baum_kennzahl, bewerte
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import kontext_aus_datei, messe, oeffne
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe
from swki.spec.freigabe import freigegebene_spec, pruefe_freigabe
from swki.spec.laden import art_der_datei, lade_spec
from swki.verbindung import verbinde


class LaufFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def pruefe_lauf_gebaut(protokoll: dict, lauf: int) -> None:
    """Ein abgebrochener Bau hinterlässt ein halbes Teil: nicht messen, sondern Bauweg nachbessern (Regel „kein
    Fortschritt“, Option A – der Lauf zählt nur als verbrauchter Lauf)."""
    if protokoll.get("status") != "ok":
        f = protokoll.get("fehler") or {}
        raise LaufFehler(
            "LAUF_ABGEBROCHEN",
            f"Lauf {lauf} ist beim Bau abgebrochen ({f.get('code')}: {f.get('meldung')}) – nicht prüfen, "
            "Bauweg nachbessern und neu bauen",
        )


def lade_spec_beliebig(spec_pfad: Path) -> dict:
    """Geprüfte Spezifikation eines Teils oder einer Baugruppe (für status und bericht)."""
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.laden import lade_baugruppe  # spät importiert (Kreisimport)

        return lade_baugruppe(spec_pfad).spec
    return lade_spec(spec_pfad)


def schreibe_pruefbericht(spec_pfad: Path, lauf: int, ordner: Path, bericht: dict) -> None:
    """Prüfbericht in den Lauf-Ordner und nach protokolle/. Ein Prüfer-Urteil gehört zum vorherigen Bericht dieses Laufs
    und wird verworfen; sonst könnte status ein veraltetes "bestanden" melden."""
    pruefer_datei = lauf_datei(spec_pfad, lauf, "pruefer")
    if pruefer_datei.exists():
        pruefer_datei.unlink()
        bericht["pruefer_urteil_verworfen"] = True
    text = json.dumps(bericht, indent=2, ensure_ascii=False, default=str) + "\n"
    (ordner / "pruefbericht.json").write_text(text, encoding="utf-8")
    ziel = lauf_datei(spec_pfad, lauf, "pruefbericht")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")


def steckbrief_fuer(app, model, ordner: Path) -> dict:
    """Geometrie-Steckbrief aus einer STL des geöffneten Modells (numpy/trimesh, Messstand Umbau 1): Lage der Zylinder,
    Hüllquader, Schwerpunkt als Text – damit Agent und Prüfer Seiten- und Spiegelfehler an Zahlen prüfen. Ein Fehler
    hier bricht die Prüfung nicht ab."""
    try:
        from swki.pruefung.steckbrief import als_text, steckbrief
        from swki.pruefung.stl import exportiere_stl

        sb = steckbrief(exportiere_stl(app, model, ordner / "geometrie.stl"))
        text = als_text(sb)
        (ordner / "steckbrief.txt").write_text(text + "\n", encoding="utf-8")
        return {"steckbrief": sb, "steckbrief_text": text}
    except Exception as e:  # Steckbrief ist Zusatz, keine Prüfung
        return {"steckbrief_text": f"(Steckbrief nicht erzeugt: {type(e).__name__}: {e})"}


def merkmale_fuer(protokoll: dict, ordner: Path, soll: dict) -> dict:
    """Merkmalsbericht aus der STEP, die swki bauen je Lauf speichert, und Abgleich mit der freigegebenen Spec
    (Prüfung `merkmale`). Schreibt merkmale.txt und merkmale.json in den Laufordner. Ein Lesefehler bricht die Prüfung
    nicht ab (Eintrag ok None, dann bleibt der Prüfer mit Bildern nötig)."""
    from swki.pruefung.abgleich import abgleich
    from swki.pruefung.bewertung import eintrag
    from swki.pruefung.merkmale import als_text, merkmale_aus_datei

    step = (protokoll.get("dateien") or {}).get("step")
    if not step or not Path(step).is_file():
        return {"eintrag": eintrag("merkmale", None, hinweis="STEP des Laufs fehlt", knoten=[])}
    try:
        m = merkmale_aus_datei(Path(step))
        text = als_text(m)
        (ordner / "merkmale.txt").write_text(text + "\n", encoding="utf-8")
        (ordner / "merkmale.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"merkmale_text": text, "eintrag": abgleich(soll, m)}
    except Exception as e:  # Zusatzprüfung: ohne sie prüft der Prüfer wie bisher mit Bildern
        grund = f"{type(e).__name__}: {e}"
        return {"merkmale_text": f"(Merkmalsbericht nicht erzeugt: {grund})",
                "eintrag": eintrag("merkmale", None, hinweis=f"STEP nicht lesbar ({grund})", knoten=[])}


def mit_merkmalen(bewertung: dict, merkmal: dict) -> dict:
    """Prüfung `merkmale` in die Bewertung aufnehmen (Mangel, wenn ok False)."""
    from swki.pruefung.bewertung import beschreibung

    e = merkmal["eintrag"]
    bewertung["pruefungen"].append(e)
    if e["ok"] is False:
        bewertung["maengel"].append({"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": beschreibung(e)})
        bewertung["bestanden"] = False
    if "merkmale_text" in merkmal:
        bewertung["merkmale_text"] = merkmal["merkmale_text"]
    return bewertung


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.pruefen import pruefen as baugruppe_pruefen  # spät importiert (Kreisimport)

        return baugruppe_pruefen(spec_pfad, lauf)
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    ordner = lauf_ordner(r, auftrag, lauf)
    teil = ordner / f"{dateiname(spec, auftrag, standard)}.sldprt"
    if not teil.exists():
        raise SwkiFehler(f"{teil} fehlt (Lauf {lauf} ohne gespeichertes Teil)")
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    pruefe_lauf_gebaut(protokoll, lauf)
    app = verbinde(r.sw_jahr)
    soll = freigegebene_spec(spec_pfad)
    model = oeffne(app, teil)
    try:
        ctx = kontext_aus_datei(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"], protokoll)
        with sw.schnell(app, model):   # Messen ohne Bildschirmarbeit (Messstand Umbau 5); Screenshots danach normal
            messwerte = messe(ctx, soll)
        bilder = screenshots(app, model, ordner / "bilder")
        geometrie = steckbrief_fuer(app, model, ordner)
    finally:
        sw.schliesse(app, model)
    bewertung = mit_merkmalen(bewerte(spec, messwerte, standard, soll), merkmale_fuer(protokoll, ordner, soll))
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil),
        **bewertung, "baum": baum_kennzahl(spec, protokoll), "bilder": bilder,
        **geometrie,
    }
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht


def status(spec_pfad: Path, anweisung: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec_beliebig(spec_pfad)
    alle = lies_laeufe(spec_pfad)
    maximal = max_laeufe(spec, lade_standard(), anweisung)
    code, text = empfehlung(alle, maximal)
    return {"spec": spec_pfad.name, "laeufe": alle, "max_laeufe": maximal, "empfehlung": code, "text": text}


def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def _compiler_aenderungen(seit: str) -> list[str]:
    """Commits an Compiler und Schema seit dem ersten Lauf; ohne git eine Hinweiszeile statt eines Abbruchs."""
    try:
        ergebnis = subprocess.run(
            ["git", "log", f"--since={seit}", "--format=%h %s", "--", "swki/compiler", "schema"],
            cwd=PROJEKT, capture_output=True, text=True, encoding="utf-8",
        )
    except OSError as e:
        return [f"(git nicht ausführbar: {e})"]
    if ergebnis.returncode != 0:
        return [f"(git log fehlgeschlagen: {ergebnis.stderr.strip() or ergebnis.returncode})"]
    return [z for z in ergebnis.stdout.splitlines() if z.strip()]


def bericht(spec_pfad: Path) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec_beliebig(spec_pfad)
    stand = status(spec_pfad)
    alle = stand["laeufe"]
    letzter = alle[-1]["lauf"] if alle else None
    protokoll = _lies(lauf_datei(spec_pfad, letzter, "protokoll")) if letzter else None
    erstes = _lies(lauf_datei(spec_pfad, alle[0]["lauf"], "protokoll")) if alle else None
    pruefbericht = _lies(lauf_datei(spec_pfad, letzter, "pruefbericht")) if letzter else None
    urteil = _lies(lauf_datei(spec_pfad, letzter, "pruefer")) if letzter else None
    if urteil is None and letzter:
        from swki.pruefung.vorpruefung import urteil_fuer_lauf

        urteil = urteil_fuer_lauf(spec_pfad, pruefbericht)
    text = bericht_markdown(
        spec, auftrag_name(spec_pfad), alle, (stand["empfehlung"], stand["text"]),
        pruefbericht,
        urteil,
        protokoll,
        _compiler_aenderungen(erstes["gestartet"]) if erstes else [],
    )
    ziel = spec_pfad.parent / "bericht.md"
    ziel.write_text(text, encoding="utf-8")
    return {"bericht": str(ziel), "status": stand["empfehlung"]}


def _urteil_lesen(text: str, quelle: str) -> dict:
    from swki.pruefung.schleife import _urteil_fehler, pruefe_urteil

    roh = text.strip()
    if roh.startswith("```"):   # Code-Fences des Agenten weglassen, Inhalt unverändert
        roh = roh.strip("`").removeprefix("json").strip()
    try:
        u = json.loads(roh)
    except json.JSONDecodeError as e:
        raise _urteil_fehler(Path(quelle), f"Prüfer-Urteil nicht lesbar ({e.msg}, Zeile {e.lineno})") from e
    pruefe_urteil(u, Path(quelle))
    return u


def urteil(spec_pfad: Path, text: str, lauf: int | None = None, vorpruefung: bool = False,
           anweisung: int | None = None) -> dict:
    """Prüfer-Urteil ablegen (Lauf-Urteil oder Vorprüfung), dann status und bei „bestanden“ bericht – ein Aufruf statt
    Heredoc + status + bericht."""
    from swki.pruefung import vorpruefung as vp

    spec_pfad = spec_pfad.resolve()
    if vorpruefung:
        u = _urteil_lesen(text, vp.vorpruefung_pfad(spec_pfad).name)
        erg = {"abgelegt": str(vp.lege_ab(spec_pfad, u)), "bestanden": u["bestanden"]}
    else:
        if lauf is None:
            bisher = lies_laeufe(spec_pfad)
            if not bisher:
                raise SwkiFehler(f"{spec_pfad.name} hat noch keinen Lauf – Vorprüfung mit --vorpruefung ablegen")
            lauf = bisher[-1]["lauf"]
        ziel = lauf_datei(spec_pfad, lauf, "pruefer")
        u = _urteil_lesen(text, ziel.name)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(u, ensure_ascii=False) + "\n", encoding="utf-8")
        erg = {"abgelegt": str(ziel), "bestanden": u["bestanden"]}
    if lies_laeufe(spec_pfad):
        stand = status(spec_pfad, anweisung)
        erg |= {"empfehlung": stand["empfehlung"], "empfehlung_text": stand["text"]}
        if stand["empfehlung"] == "bestanden":
            erg["bericht"] = bericht(spec_pfad)["bericht"]
    return erg


def _urteil_befehl(a) -> dict:
    import sys

    text = a.json if a.json is not None else sys.stdin.read()
    return urteil(Path(a.spec), text, a.lauf, a.vorpruefung, a.max)


def merkmale_befehl(step: Path) -> dict:
    """Merkmalsbericht einer beliebigen STEP (zum Nachsehen, z. B. an alten Läufen) – nur lesen."""
    from swki.pruefung.merkmale import als_text, merkmale_aus_datei

    m = merkmale_aus_datei(step)
    return {"datei": str(step), "text": als_text(m).splitlines(), "merkmale": m}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("pruefen", help="gespeicherten Lauf messen, bewerten, Screenshots (pruefbericht.json)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter Lauf")
    p.set_defaults(func=lambda a: pruefen(Path(a.spec), a.lauf))
    p = subparsers.add_parser("status", help="Stand der Nachbesserungsschleife und Empfehlung")
    p.add_argument("spec")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: status(Path(a.spec), a.max))
    p = subparsers.add_parser("urteil", help="Prüfer-Urteil ablegen (JSON über --json oder stdin), dann status und "
                                             "bei bestanden bericht")
    p.add_argument("spec")
    p.add_argument("--json", help="Urteil als JSON-Text (sonst von stdin)")
    p.add_argument("--vorpruefung", action="store_true", help="Urteil der Vorprüfung (vor dem Bau)")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter Lauf")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=_urteil_befehl)
    p = subparsers.add_parser("merkmale", help="Merkmalsbericht einer STEP-Datei (Bohrungen, Zapfen, Ebenen …)")
    p.add_argument("step")
    p.set_defaults(func=lambda a: merkmale_befehl(Path(a.step)))
    p = subparsers.add_parser("bericht", help="bericht.md des Auftrags schreiben")
    p.add_argument("spec")
    p.set_defaults(func=lambda a: bericht(Path(a.spec)))
