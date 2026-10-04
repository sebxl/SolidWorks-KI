"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""


def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)


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
    bewegungen = letzter.get("bewegungen")
    if bewegungen:
        zeilen += ["", "## Bewegungen (letzter Lauf)", "",
                   "| Bewegung | Lauf | Stellungen | bewegt | Kollisionen | Grenze oben / unten | Dauer (s) |",
                   "|---|---|---|---|---|---|---|"]
        for lauf in bewegungen["laeufe"]:
            gegen = ", ".join(f"{n} auf {s}" for n, s in lauf["gegen"].items()) or "Grundstellung"
            grenze = " / ".join(_grenze_text(lauf["grenze"].get(s)) for s in ("oben", "unten"))
            zeilen.append(f"| {lauf['bewegung']} | {gegen} | {lauf['stellungen']} | {', '.join(lauf['bewegt']) or '–'} | "
                          f"{lauf['kollisionen']} | {grenze} | {lauf['dauer_s']} |")
        if bewegungen.get("paare"):
            zeilen += ["", "Paarläufe für: " + "; ".join(" × ".join(p["bewegungen"]) for p in bewegungen["paare"])]
    zeilen += ["", "## Screenshots (letzter Lauf)", ""]
    bilder = (letzter_bericht or {}).get("bilder", {})
    zeilen += [f"- {name}: `{pfad}`" for name, pfad in bilder.items()] or ["- keine"]
    zeilen += ["", "## Phasenzeiten (letzter Lauf)", "", "| Phase | s |", "|---|---|"]
    for phase, sekunden in (letztes_protokoll or {}).get("phasen", {}).items():
        zeilen.append(f"| {phase} | {sekunden} |")
    zeilen += ["", "## Compiler-Änderungen während des Auftrags", ""]
    zeilen += [f"- {c}" for c in compiler_aenderungen] or ["- keine"]
    return "\n".join(zeilen) + "\n"
