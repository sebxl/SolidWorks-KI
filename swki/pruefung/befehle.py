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
        messwerte = messe(ctx, soll)
        bilder = screenshots(app, model, ordner / "bilder")
        geometrie = steckbrief_fuer(app, model, ordner)
    finally:
        sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil),
        **bewerte(spec, messwerte, standard, soll), "baum": baum_kennzahl(spec, protokoll), "bilder": bilder,
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
    text = bericht_markdown(
        spec, auftrag_name(spec_pfad), alle, (stand["empfehlung"], stand["text"]),
        _lies(lauf_datei(spec_pfad, letzter, "pruefbericht")) if letzter else None,
        _lies(lauf_datei(spec_pfad, letzter, "pruefer")) if letzter else None,
        protokoll,
        _compiler_aenderungen(erstes["gestartet"]) if erstes else [],
    )
    ziel = spec_pfad.parent / "bericht.md"
    ziel.write_text(text, encoding="utf-8")
    return {"bericht": str(ziel), "status": stand["empfehlung"]}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("pruefen", help="gespeicherten Lauf messen, bewerten, Screenshots (pruefbericht.json)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter Lauf")
    p.set_defaults(func=lambda a: pruefen(Path(a.spec), a.lauf))
    p = subparsers.add_parser("status", help="Stand der Nachbesserungsschleife und Empfehlung")
    p.add_argument("spec")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: status(Path(a.spec), a.max))
    p = subparsers.add_parser("bericht", help="bericht.md des Auftrags schreiben")
    p.add_argument("spec")
    p.set_defaults(func=lambda a: bericht(Path(a.spec)))
