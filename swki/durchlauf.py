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
    if bericht.get("steckbrief_text"):
        erg["steckbrief"] = bericht["steckbrief_text"].splitlines()
    return erg


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
    erg |= {"schritt": "fertig", "empfehlung": st["empfehlung"], "empfehlung_text": st["text"],
            "naechstes": "Prüfer-Agent starten (Eingabe, freigegebene Spec, Prüfbericht, Bilder)"
            if p.get("bestanden") else "nachbessern (Bauweg) und erneut swki durchlauf"}
    return erg


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("durchlauf", help="validieren, (freigeben), bauen, prüfen, status in einem Aufruf")
    p.add_argument("spec")
    p.add_argument("--freigeben", action="store_true",
                   help="vorher freigeben – nur nach ausdrücklichem OK des Nutzers zu den Anforderungen")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: durchlauf(Path(a.spec), a.freigeben, a.max))
