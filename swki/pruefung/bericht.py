"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""


def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)


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
            f"| {lauf['offen']} | {lauf['dauer_s']} |"
        )
    zeilen += ["", "## Offene Punkte (letzter Lauf)", ""]
    offene = []
    if letztes_protokoll and letztes_protokoll.get("fehler"):
        f = letztes_protokoll["fehler"]
        offene.append(f"Bau abgebrochen: {f.get('code')} – {f.get('meldung')}")
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']}" for m in (letzter_bericht or {}).get("maengel", [])]
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']} (Prüfer)" for m in (letztes_urteil or {}).get("maengel", [])]
    zeilen += [f"- {o}" for o in offene] or ["- keine"]
    zeilen += ["", "## Screenshots (letzter Lauf)", ""]
    bilder = (letzter_bericht or {}).get("bilder", {})
    zeilen += [f"- {name}: `{pfad}`" for name, pfad in bilder.items()] or ["- keine"]
    zeilen += ["", "## Phasenzeiten (letzter Lauf)", "", "| Phase | s |", "|---|---|"]
    for phase, sekunden in (letztes_protokoll or {}).get("phasen", {}).items():
        zeilen.append(f"| {phase} | {sekunden} |")
    zeilen += ["", "## Compiler-Änderungen während des Auftrags", ""]
    zeilen += [f"- {c}" for c in compiler_aenderungen] or ["- keine"]
    return "\n".join(zeilen) + "\n"
