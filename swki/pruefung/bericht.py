"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""

from swki.pruefung.bewertung import beschreibung

_ERGEBNIS = {True: "bestanden", False: "Mangel", None: "nicht geprüft"}


def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)


def _gewindemodelle(werte: dict | None) -> str:
    """„flansch: kernloch Ø 4.134“ je Gruppe (Spec 3c §4.3); ohne Gewindegruppen „–“."""
    teile = [f"{g}: {m['modell']} Ø {m['durchmesser']:g}" if isinstance(m, dict) and m.get("durchmesser") is not None
             else f"{g}: unbekannt" for g, m in sorted((werte or {}).items())]
    return ", ".join(teile) or "–"


def _grenze_text(wert) -> str:
    return {True: "geht durch", False: "wirkt", None: "–"}[wert]


def bericht_markdown(
    spec: dict, auftrag: str, laeufe: list[dict], empfehlung: tuple[str, str],
    letzter_bericht: dict | None, letztes_urteil: dict | None, letztes_protokoll: dict | None,
    compiler_aenderungen: list[str],
) -> str:
    code, text = empfehlung
    status = "bestanden" if code == "bestanden" else f"offen ({code})"
    zeilen = [
        f"# Bericht {spec['name']} (Auftrag {auftrag})",
        "",
        f"**Status:** {status} – {text}",
        "",
        "## Läufe",
        "",
        "| Lauf | Bau | Code-Mängel | Prüfer | Offen | Dauer (s) |",
        "|---|---|---|---|---|---|",
    ]
    for lauf in laeufe:
        zeilen.append(
            f"| {lauf['lauf']} | {lauf['bau']} | {_zelle(lauf['code_maengel'])} | {lauf['pruefer']} "
            f"| {_zelle(lauf['offen'])} | {lauf['dauer_s']} |"
        )
    zeilen += ["", "## Offene Punkte (letzter Lauf)", ""]
    offene = []
    if letztes_protokoll and letztes_protokoll.get("fehler"):
        f = letztes_protokoll["fehler"]
        offene.append(f"Bau abgebrochen: {f.get('code')} – {f.get('meldung')}")
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']}" for m in (letzter_bericht or {}).get("maengel", [])]
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']} (Prüfer)" for m in (letztes_urteil or {}).get("maengel", [])]
    zeilen += [f"- {o}" for o in offene] or ["- keine"]
    baum = (letzter_bericht or {}).get("baum")
    if baum:
        zeilen += ["", "## Feature-Baum (letzter Lauf)", "", f"- Knoten der Spezifikation: {baum['knoten']}",
                   f"- erzeugte Features (ohne Skizzen, Ebenen, Achsen): {baum['features']}"]
    letzter = letzter_bericht or {}
    if letzter.get("stueckliste"):
        zeilen += ["", "## Stückliste (letzter Lauf)", "", "| Datei | Anzahl |", "|---|---|"]
        zeilen += [f"| {n} | {c} |" for n, c in sorted(letzter["stueckliste"].items())]
    if letzter.get("normteile"):
        zeilen += ["", "## Normteile", "", "| Schlüssel | neu gebaut | Bibliotheksprüfsumme |", "|---|---|---|"]
        zeilen += [f"| {s} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} |"
                   for s, e in sorted(letzter["normteile"].items())]
    if letzter.get("kaufteile"):
        zeilen += ["", "## Kaufteile", "",
                   "| Kaufteil | neu aufgenommen | Cache-Prüfsumme | Masse | Kennmaße | Gewindemodell (Ø mm) |",
                   "|---|---|---|---|---|---|"]
        zeilen += [f"| {e.get('kaufteil', s)} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} | "
                   f"{_zelle(e.get('masse'))} | {_zelle(e.get('kennmasse'))} | {_gewindemodelle(e.get('gewinde_modell'))} |"
                   for s, e in sorted(letzter["kaufteile"].items())]
    if letzter.get("gewindepaarungen"):
        zeilen += ["", "## Gewindepaarungen", "",
                   "| Schraube | Teil | Bohrung | Einschraublänge (mm) | Gewindetiefe (mm) | Volumen ist / soll (mm³) |",
                   "|---|---|---|---|---|---|"]
        zeilen += [f"| {g['schraube']} | {g['teil']} | {g['bohrung']} | {g['einschraublaenge']} | "
                   f"{_zelle(g.get('gewindetiefe'))} | {g['volumen']} / {_zelle(g.get('soll'))} |"
                   for g in letzter["gewindepaarungen"]]
    if letzter.get("teilpruefungen"):
        zeilen += ["", "## Teilprüfungen (letzter Lauf)", "", "| Komponente | bestanden | Mängel |", "|---|---|---|"]
        zeilen += [f"| {k} | {'ja' if t['bestanden'] else 'nein'} | {t['maengel']} |"
                   for k, t in sorted(letzter["teilpruefungen"].items())]
    if letzter.get("kopplungen"):
        zeilen += ["", "## Kopplungen (letzter Lauf)", "",
                   "| Kopplung | Typ | a → b | Übersetzung soll | gelesen | Achsabstand ist / soll (mm) | Überdeckung (mm) |",
                   "|---|---|---|---|---|---|---|"]
        for k in letzter["kopplungen"]:
            g = k["gelesen"]
            gelesen = (f"{g['zaehler']:g}:{g['nenner']:g}" if "zaehler" in g else f"Ø {g['durchmesser']:g}"
                       ) if isinstance(g, dict) else _zelle(g)
            zeilen.append(f"| {k['kopplung']} | {k['typ']} | {k['a']} → {k['b']} | {k['soll']} | {gelesen} | "
                          f"{k['achsabstand']:g} / {k['achsabstand_soll']:g} | {k['ueberdeckung']:g} |")
    bewegungen = letzter.get("bewegungen")
    if bewegungen and bewegungen.get("laeufe"):
        zeilen += ["", "## Bewegungen (letzter Lauf)", "",
                   "| Bewegung | Grenze | Bereich | Lauf | Stellungen | bewegt | Kollisionen | Grenze oben / unten | "
                   "Dauer (s) |",
                   "|---|---|---|---|---|---|---|---|---|"]
        for lauf in bewegungen["laeufe"]:
            gegen = ", ".join(f"{n} auf {s}" for n, s in lauf["gegen"].items()) or "Grundstellung"
            grenze = " / ".join(_grenze_text(lauf["grenze"].get(s)) for s in ("oben", "unten"))
            bereich = " … ".join(f"{w:g}" for w in lauf["bereich"]) if lauf.get("bereich") else "–"
            zeilen.append(f"| {lauf['bewegung']} | {lauf.get('grenz_id', '–')} | {bereich} | {gegen} | {lauf['stellungen']} | "
                          f"{', '.join(lauf['bewegt']) or '–'} | {lauf['kollisionen']} | {grenze} | {lauf['dauer_s']} |")
        if bewegungen.get("paare"):
            zeilen += ["", "Paarläufe für: " + "; ".join(" × ".join(p["bewegungen"]) for p in bewegungen["paare"])]
        wege = [e for e in letzter.get("pruefungen", []) if e["id"].startswith(("endlage:", "sollweg:"))]
        if wege:
            zeilen += ["", "## Endlagen und Sollweg (letzter Lauf)", "", "| Prüfung | Ergebnis | Befund |", "|---|---|---|"]
            zeilen += [f"| {e['id']} | {_ERGEBNIS[e['ok']]} | {'–' if e['ok'] else beschreibung(e)} |" for e in wege]
    zeilen += ["", "## Screenshots (letzter Lauf)", ""]
    bilder = (letzter_bericht or {}).get("bilder", {})
    zeilen += [f"- {name}: `{pfad}`" for name, pfad in bilder.items()] or ["- keine"]
    zeilen += ["", "## Phasenzeiten (letzter Lauf)", "", "| Phase | s |", "|---|---|"]
    for phase, sekunden in (letztes_protokoll or {}).get("phasen", {}).items():
        zeilen.append(f"| {phase} | {sekunden} |")
    zeilen += ["", "## Compiler-Änderungen während des Auftrags", ""]
    zeilen += [f"- {c}" for c in compiler_aenderungen] or ["- keine"]
    return "\n".join(zeilen) + "\n"
