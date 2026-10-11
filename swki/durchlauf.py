"""swki durchlauf <spec>: validieren → (freigeben) → bauen → prüfen → status in einem Aufruf, mit kompakter Ausgabe.

Spart dem Agenten Runden und Kontext (Messstand Umbau 1). `--freigeben` nur, wenn der Nutzer die Anforderungen
ausdrücklich freigegeben hat (CLAUDE.md); ohne die Option braucht der Durchlauf eine gültige Freigabe.
Bei einem Fehler endet der Durchlauf im betreffenden Schritt und nennt ihn (`schritt`)."""

from argparse import Namespace
from pathlib import Path

from swki.cli import SwkiFehler, ganzzahl_ab


def _kurz_pruefung(bericht: dict) -> dict:
    fehlgeschlagen = [{k: v for k, v in p.items() if k != "ok"}
                      for p in bericht.get("pruefungen", []) if p.get("ok") is False]
    ungeprueft = [p["id"] for p in bericht.get("pruefungen", []) if p.get("ok") is None]
    erg = {"bestanden": bericht.get("bestanden"), "maengel": bericht.get("maengel", []),
           "fehlgeschlagen": fehlgeschlagen, "ohne_urteil": ungeprueft,
           "geprueft": len(bericht.get("pruefungen", [])), "baum": bericht.get("baum"),
           "bilder": sorted(set(str(Path(b).parent) for b in (bericht.get("bilder") or {}).values()))}
    if bericht.get("merkmale_text") and not bericht["merkmale_text"].startswith("("):
        erg["merkmale"] = bericht["merkmale_text"].splitlines()
    elif bericht.get("steckbrief_text"):
        erg["steckbrief"] = bericht["steckbrief_text"].splitlines()
    return erg


def pruefer_auftrag(spec_pfad: Path, lauf: int, bericht: dict) -> str:
    """Fertiger Prompt für den Prüfer-Agenten (nur erlaubte Eingaben: Eingabe, Freigabe-Kopien, Prüfbericht,
    Merkmalsbericht, Steckbrief, Bilder – keine Protokolle, keine Skripte). Screenshots nur, wenn der Abgleich der STEP
    nicht alle Features abbildet (sonst prüft der Prüfer nur Text)."""
    from swki.auftrag import lauf_datei
    from swki.pruefung.vorpruefung import ersetzt_bildpruefung

    ordner = spec_pfad.parent
    kopien = ", ".join(str(p) for p in sorted(ordner.glob("*.freigegeben.yaml")))
    bilder = sorted({str(Path(b).parent) for b in (bericht.get("bilder") or {}).values()})
    laufordner = Path(bericht["datei"]).parent if bericht.get("datei") else None
    merkmale = laufordner / "merkmale.txt" if laufordner and (laufordner / "merkmale.txt").exists() else None
    steck = laufordner / "steckbrief.txt" if laufordner and (laufordner / "steckbrief.txt").exists() else None
    teile = [f"Prüfe Lauf {lauf} von {spec_pfad.name}.", f"Eingabe des Nutzers: {ordner / 'eingabe'} (und aufgabe.md, falls vorhanden).",
             f"Freigegebene Spezifikation(en): {kopien}.", f"Prüfbericht: {lauf_datei(spec_pfad, lauf, 'pruefbericht')}."]
    if merkmale:
        teile.append(f"Merkmalsbericht aus der STEP: {merkmale} (Lage, Seite, Maße jedes Merkmals).")
    elif steck:
        teile.append(f"Geometrie-Steckbrief: {steck} (Lage und Vorzeichen zuerst daran prüfen).")
    if bilder and not ersetzt_bildpruefung(bericht):
        teile.append(f"Screenshots: {', '.join(bilder)}.")
    teile.append("Antworte nur mit dem JSON-Urteil.")
    return " ".join(teile)


def durchlauf(spec_pfad: Path, freigeben: bool = False, maximal: int | None = None) -> dict:
    from swki.compiler.bauen import BauAbbruch, _bauen
    from swki.pruefung.befehle import pruefen, status
    from swki.spec.befehle import _freigeben, _validieren

    spec_pfad = spec_pfad.resolve()
    erg: dict = {"spec": spec_pfad.name}
    try:
        v = _validieren(Namespace(spec=str(spec_pfad)))
    except SwkiFehler as e:
        return {**erg, "schritt": "validieren", "fehler": str(e), **getattr(e, "daten", {})}
    erg["hinweise"] = v.get("hinweise", [])
    if "auto" in v:
        erg["auto"] = v["auto"]
    pruefwerte = [h for h in erg["hinweise"] if h.get("art") == "pruefwert"]
    if freigeben and pruefwerte:   # nach der Freigabe kostet ein falscher Prüfwert eine neue Freigabe
        return {**erg, "schritt": "validieren", "pruefwerte": pruefwerte,
                "fehler": "Prüfwert weicht von der Rechnung aus den Features ab – Spec korrigieren (oder bewusst "
                          "abweichend: swki freigeben, dann swki durchlauf ohne --freigeben)"}
    if freigeben and (offen := _vorpruefung_offen(spec_pfad)):
        return {**erg, "schritt": "vorpruefung", "maengel": offen,
                "fehler": "Die Vorprüfung dieses Spec-Texts hat Mängel – Spec korrigieren, Vorprüfung wiederholen"}
    if freigeben:
        try:
            f = _freigeben(Namespace(spec=str(spec_pfad)))
        except SwkiFehler as e:
            return {**erg, "schritt": "freigeben", "fehler": str(e), **getattr(e, "daten", {})}
        erg["freigegeben"] = f.get("kopie", True)
    try:
        b = _bauen(Namespace(spec=str(spec_pfad), lauf=None, verwerfen=False, uebernommen=False))
    except BauAbbruch as e:
        d = e.daten
        return {**erg, "schritt": "bauen", "lauf": d.get("lauf"), "fehler": d.get("fehler"),
                "knoten": [k for k in d.get("knoten", []) if k.get("status") != "ok"]}
    except SwkiFehler as e:
        return {**erg, "schritt": "bauen", "fehler": str(e), **getattr(e, "daten", {})}
    erg |= {"lauf": b["lauf"], "bau_s": b.get("dauer_s")}
    try:
        p = pruefen(spec_pfad, b["lauf"])
    except SwkiFehler as e:
        return {**erg, "schritt": "pruefen", "fehler": str(e), **getattr(e, "daten", {})}
    erg["pruefung"] = _kurz_pruefung(p)
    st = status(spec_pfad, maximal)
    erg |= {"schritt": "fertig", "empfehlung": st["empfehlung"], "empfehlung_text": st["text"]}
    if st["empfehlung"] == "bestanden":
        erg["naechstes"] = f"bestanden (Vorprüfung + Code-Prüfung): swki bericht {spec_pfad.name}"
    elif p.get("bestanden"):
        erg["pruefer_auftrag"] = pruefer_auftrag(spec_pfad, b["lauf"], p)
        erg["naechstes"] = _naechstes_pruefer(spec_pfad, p)
    else:
        erg["naechstes"] = "nachbessern (Bauweg) und erneut swki durchlauf"
    return erg


def _vorpruefung_offen(spec_pfad: Path) -> list | None:
    from swki.pruefung.vorpruefung import offene_maengel

    return offene_maengel(spec_pfad)


def _naechstes_pruefer(spec_pfad: Path, bericht: dict) -> str:
    """Was nach einem bestandenen Code-Prüfbericht noch fehlt."""
    from swki.pruefung.vorpruefung import ersetzt_bildpruefung, lies

    if ersetzt_bildpruefung(bericht) and lies(spec_pfad) is None:
        return ("Urteil der Vorprüfung ablegen (swki urteil --vorpruefung) – es ersetzt den Prüfer nach dem Bau; "
                "ohne Vorprüfung: Prüfer-Agent mit pruefer_auftrag starten")
    return "Prüfer-Agent mit pruefer_auftrag starten, Urteil mit swki urteil ablegen"


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("durchlauf", help="validieren, (freigeben), bauen, prüfen, status in einem Aufruf")
    p.add_argument("spec")
    p.add_argument("--freigeben", action="store_true",
                   help="vorher freigeben – nur nach ausdrücklichem OK des Nutzers zu den Anforderungen")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: durchlauf(Path(a.spec), a.freigeben, a.max))
