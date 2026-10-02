"""Befehle "swki normteil hole|tabellen-pruefen|liste|muster|urteil" (Spec 3a §6, §7)."""

import json
from datetime import date
from pathlib import Path

import yaml

from swki.auftrag import laeufe, lauf_ordner
from swki.konfig import lade_rechner
from swki.normteile import bau
from swki.normteile.bibliothek import bibliotheksordner, eintraege, ist_aktuell, lege_ab, lies_eintrag, teil_pfad
from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, teil_pruefsumme, vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NORMTABELLE_UNGUELTIG, NORMTEIL_PRUEFUNG, NORMVORLAGE_UNGEPRUEFT, NormteilFehler
from swki.normteile.schluessel import Anfrage, loese_auf
from swki.normteile.tabelle import ORDNER, lade_normtabelle, norm_datei, normen, pruefe_tabelle, tabellen_befunde
from swki.pruefung.schleife import lies_urteil


def urteil_pfad(t: dict, wissen: Path = ORDNER) -> Path:
    return wissen / "vorlagen" / f"{norm_datei(t['norm'])}.pruefer.json"


def vorlage_geprueft(t: dict, text: str, wissen: Path = ORDNER) -> bool:
    """Bestandenes Prüfer-Urteil zur aktuellen Vorlage (Prüfsumme) vorhanden?"""
    pfad = urteil_pfad(t, wissen)
    if not pfad.is_file():
        return False
    u = json.loads(pfad.read_text(encoding="utf-8"))
    return u.get("vorlage_pruefsumme") == vorlage_pruefsumme(text) and u.get("bestanden") is True


def _laufordner(r, schluessel: str) -> tuple[Path, int]:
    """(Ordner, Nummer) des neuen Laufs <arbeitsordner>/NORMTEILE/<schluessel>/lauf-<n> (bleibt zur Analyse stehen)."""
    auftrag = f"{bau.AUFTRAG}/{schluessel}"
    bisher = laeufe(r, auftrag)
    nummer = bisher[-1] + 1 if bisher else 1
    return lauf_ordner(r, auftrag, nummer), nummer


def _baue(t: dict, a: Anfrage, text: str, r, wissen: Path, mit_bildern: bool = False) -> tuple[Path, dict]:
    spec = erzeuge_spec(t, a, text)
    if befunde := spec_befunde(spec, wissen):
        raise NormteilFehler(NORMTEIL_PRUEFUNG, f"{a.schluessel}: erzeugte Spezifikation ungültig", befunde=befunde)
    lauf, nummer = _laufordner(r, a.schluessel)
    lauf.mkdir(parents=True, exist_ok=True)
    (lauf / "spec.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    ergebnis = bau.baue_und_pruefe(spec, lauf, mit_bildern, nummer)
    text_bericht = json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str) + "\n"
    (lauf / "pruefbericht.json").write_text(text_bericht, encoding="utf-8")
    return lauf, ergebnis


def hole(norm: str, groesse: str, variante: str | None = None, wissen: Path = ORDNER) -> dict:
    # Erst die Tabelle prüfen: loese_auf greift auf Pflichtschlüssel zu, die bei einer kaputten Tabelle fehlen können.
    pruefe_tabelle(lade_normtabelle(norm, wissen), wissen)
    t, a = loese_auf(norm, groesse, variante, wissen)
    text = vorlage_text(t, wissen)
    summe = teil_pruefsumme(t, a, text)
    r = lade_rechner()
    bib = bibliotheksordner(r)
    if ist_aktuell(bib, a.schluessel, summe):
        eintrag = lies_eintrag(bib, a.schluessel)
        return {"schluessel": a.schluessel, "pfad": str(teil_pfad(bib, a.schluessel)), "gebaut": False,
                "pruefung": {"bestanden": True, "datum": eintrag.get("datum")}}
    if not vorlage_geprueft(t, text, wissen):
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT,
                             f"{t['norm']}: kein bestandenes Prüfer-Urteil zur aktuellen Vorlage – swki normteil muster "
                             f"\"{t['norm']}\", Prüfer-Agent, swki normteil urteil",
                             norm=t["norm"], vorlage_pruefsumme=vorlage_pruefsumme(text))
    lauf, ergebnis = _baue(t, a, text, r, wissen)
    if not ergebnis["bestanden"]:
        raise NormteilFehler(NORMTEIL_PRUEFUNG,
                             f"{a.schluessel}: Selbstprüfung nicht bestanden ({len(ergebnis['maengel'])} Mängel)",
                             maengel=ergebnis["maengel"], ordner=str(lauf))
    eintrag = {"schluessel": a.schluessel, "norm": t["norm"], "groesse": a.groesse, "laenge": a.laenge,
               "variante": a.variante, "pruefsumme": summe, "bestanden": True,
               "pruefungen": [p["id"] for p in ergebnis["pruefungen"]], "datum": date.today().isoformat(),
               "sw_jahr": r.sw_jahr, "lauf": str(lauf)}
    pfad = lege_ab(bib, a.schluessel, Path(ergebnis["teil"]), eintrag)
    return {"schluessel": a.schluessel, "pfad": str(pfad), "gebaut": True, "lauf": str(lauf),
            "pruefung": {"bestanden": True, "pruefungen": len(ergebnis["pruefungen"])}}


def _zusammenfassung(t: dict, befunde: list[dict]) -> dict:
    """Befunde, Anzahl der Größen und gesperrte Größen; liest nur, was auch bei einer kaputten Tabelle sicher da ist."""
    groessen = t["groessen"] if isinstance(t.get("groessen"), dict) else {}
    return {"befunde": befunde, "groessen": len(groessen),
            "gesperrt": [g for g, z in groessen.items() if isinstance(z, dict) and z.get("status") == "gesperrt"]}


def tabellen_pruefen(norm: str | None = None, wissen: Path = ORDNER) -> dict:
    """Tabellenbefunde und – wenn die Tabelle stimmt – Befunde jeder erzeugten Spezifikation (alle Größen und Längen)."""
    ergebnis = {}
    for name in [norm_datei(norm)] if norm else normen(wissen):
        t = lade_normtabelle(name, wissen)
        befunde = tabellen_befunde(t, wissen)
        if not befunde:  # nur eine gültige Tabelle hat alle Schlüssel, die erzeuge_spec liest
            text = vorlage_text(t, wissen)
            for g, z in t["groessen"].items():
                for laenge in z.get("laengen") or [None]:
                    a = Anfrage(t["norm"], g, None if laenge is None else float(laenge), t["vorgabe_variante"])
                    befunde += [{**b, "pfad": f"{a.schluessel}: {b['pfad']}"}
                                for b in spec_befunde(erzeuge_spec(t, a, text), wissen)]
        ergebnis[t.get("norm", name)] = _zusammenfassung(t, befunde)
    if any(e["befunde"] for e in ergebnis.values()):
        raise NormteilFehler(NORMTABELLE_UNGUELTIG, "Normtabellen mit Befunden", normen=ergebnis)
    return {"gueltig": True, "normen": ergebnis}


def liste(nur_veraltet: bool = False, wissen: Path = ORDNER) -> dict:
    bib = bibliotheksordner(lade_rechner())
    teile = []
    for e in eintraege(bib):
        try:
            t = lade_normtabelle(e["norm"], wissen)
            a = Anfrage(t["norm"], e["groesse"], e["laenge"], e["variante"])
            aktuell = ist_aktuell(bib, e["schluessel"], teil_pruefsumme(t, a, vorlage_text(t, wissen)))
        except (NormteilFehler, KeyError):
            aktuell = False  # Norm, Größe oder Variante gibt es nicht mehr
        teile.append({"schluessel": e["schluessel"], "aktuell": aktuell, "datum": e.get("datum")})
    if nur_veraltet:
        teile = [x for x in teile if not x["aktuell"]]
    return {"ordner": str(bib), "teile": teile}


def muster(norm: str, wissen: Path = ORDNER) -> dict:
    """Musterteil (kleinste Größe, kürzeste Länge, Vorgabevariante) mit Screenshots für den Prüfer-Agenten; wird nicht
    abgelegt und braucht kein Urteil. Der Status der Größe zählt hier nicht – geprüft wird die Vorlage."""
    t = lade_normtabelle(norm, wissen)
    pruefe_tabelle(t, wissen)
    g, zeile = next(iter(t["groessen"].items()))
    a = Anfrage(t["norm"], g, float(zeile["laengen"][0]) if t["laenge"] else None, t["vorgabe_variante"])
    text = vorlage_text(t, wissen)
    lauf, ergebnis = _baue(t, a, text, lade_rechner(), wissen, mit_bildern=True)
    return {"norm": t["norm"], "schluessel": a.schluessel, "bestanden": ergebnis["bestanden"],
            "maengel": ergebnis["maengel"], "vorlage_pruefsumme": vorlage_pruefsumme(text),
            "spec": str(lauf / "spec.yaml"), "pruefbericht": str(lauf / "pruefbericht.json"),
            "bilder": ergebnis["bilder"], "tabelle": str(wissen / f"{norm_datei(t['norm'])}.yaml"),
            "vorlage": str(wissen / t["vorlage"])}


def urteil(norm: str, datei: Path, vorlage_summe: str, wissen: Path = ORDNER) -> dict:
    """Prüfer-Urteil (rohes JSON des Prüfer-Agenten) zur aktuellen Vorlage ablegen."""
    t = lade_normtabelle(norm, wissen)
    aktuell = vorlage_pruefsumme(vorlage_text(t, wissen))
    if vorlage_summe != aktuell:
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT, f"{t['norm']}: Vorlage seit dem Musterteil geändert – neu prüfen",
                             vorlage_pruefsumme=aktuell)
    u = lies_urteil(datei)
    if u is None:
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT, f"Urteil {datei} fehlt")
    inhalt = {"norm": t["norm"], "vorlage_pruefsumme": aktuell, "bestanden": u["bestanden"], "maengel": u["maengel"],
              "datum": date.today().isoformat()}
    ziel = urteil_pfad(t, wissen)
    ziel.write_text(json.dumps(inhalt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"datei": str(ziel), **inhalt}


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("normteil", help="Normteile abrufen, bauen und prüfen").add_subparsers(
        dest="unterbefehl", required=True)
    p = gruppe.add_parser("hole", help="Normteil aus der Bibliothek holen oder bauen, prüfen und ablegen")
    p.add_argument("norm")
    p.add_argument("groesse")
    p.add_argument("--variante")
    p.set_defaults(func=lambda a: hole(a.norm, a.groesse, a.variante))
    p = gruppe.add_parser("tabellen-pruefen", help="Normtabellen und erzeugte Spezifikationen prüfen (ohne SolidWorks)")
    p.add_argument("norm", nargs="?")
    p.set_defaults(func=lambda a: tabellen_pruefen(a.norm))
    p = gruppe.add_parser("liste", help="Bibliothek anzeigen")
    p.add_argument("--veraltet", action="store_true")
    p.set_defaults(func=lambda a: liste(a.veraltet))
    p = gruppe.add_parser("muster", help="Musterteil mit Screenshots für den Prüfer-Agenten bauen")
    p.add_argument("norm")
    p.set_defaults(func=lambda a: muster(a.norm))
    p = gruppe.add_parser("urteil", help="Prüfer-Urteil zur aktuellen Vorlage ablegen")
    p.add_argument("norm")
    p.add_argument("datei")
    p.add_argument("--vorlage-pruefsumme", required=True)
    p.set_defaults(func=lambda a: urteil(a.norm, Path(a.datei), a.vorlage_pruefsumme))
