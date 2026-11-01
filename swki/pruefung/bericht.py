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


def _wert(wert) -> str:
    return f"{wert:g}" if isinstance(wert, (int, float)) and not isinstance(wert, bool) else str(wert)


def _quelle_text(q: dict) -> str:
    return " ".join(str(v) for v in q.values())


def _punkt_text(p: dict) -> str:
    """Was ein Punkt einer Änderungs-Spec tut, kurz (Spec Bestandsdateien §4.1)."""
    typ = p["typ"]
    if typ == "komponente_neu":
        text = f"neu: {_quelle_text(p['quelle'])}" if "quelle" in p else f"neu wie {p['wie']}"
    elif typ == "komponente_entfernen":
        text = " + ".join([p["komponente"], *p.get("verknuepfungen", [])])
    elif typ == "komponente_ersetzen":
        text = f"{p['komponente']} → {_quelle_text(p['quelle'])}"
    elif typ == "verknuepfung_neu":
        text = f"{p['art']} {p['a']['komponente']} – {p['b']['komponente']}"
    elif typ == "verknuepfung_wert":
        text = f"{p['verknuepfung']}{' (' + p['grenze'] + ')' if p.get('grenze') else ''}: {_wert(p['alt'])} → {_wert(p['neu'])}"
    elif typ == "verknuepfung_loeschen":
        text = p["verknuepfung"]
    elif typ == "mass":
        text = f"{p['mass']}: {_wert(p['alt'])} → {_wert(p['neu'])}"
    elif typ == "gleichung":
        text = f"{p.get('variable') or p['gleichung']}: {_wert(p['alt'])} → {_wert(p['neu'])}"
    elif typ == "loeschen":
        text = " + ".join([p["feature"], *p.get("kinder", [])])
    elif typ in ("unterdruecken", "aufheben"):
        text = p["feature"]
    elif typ == "feature":
        text = f"{p['name']} ({p['feature'].get('typ', '?')})" + (f" nach {p['nach']}" if p.get("nach") else "")
    elif typ == "material":
        text = _wert(p["neu"])
    elif typ == "eigenschaft":
        text = f"{p['name']} → {'gelöscht' if p['neu'] is None else _wert(p['neu'])}"
    else:  # skript
        text = f"{p['datei']} (Lücke: {p['luecke']})"
    return f"{p['was']}: {text}" if p.get("was") else text


def _ort(box: list[float]) -> str:
    return ", ".join(f"{achse} {box[i]:g}…{box[i + 3]:g}" for i, achse in enumerate("xyz"))


def _bereich_text(a: dict) -> str:
    """`bereich_offen`: Der Körper liegt vielleicht in diesem Bereich, nachgewiesen ist es nicht."""
    if a.get("bereich") is not None:
        return f"Bereich {a['bereich']}"
    return f"nicht sicher im Bereich {a['bereich_offen']}" if a.get("bereich_offen") is not None else "in keinem Bereich"


def _differenz_zeilen(differenzen: dict, pruefungen: list[dict], kennung: str = "bereich", vor: str = "") -> list[str]:
    """Je Konfiguration die Abweichungen einer Datei; `kennung`: ID ihrer `bereich`-Einträge, `vor`: was jede Zeile vorn nennt."""
    offen = {e["konfiguration"]: e.get("hinweis", "") for e in pruefungen if e["id"] == kennung and e["ok"] is None}
    zeilen = []
    for konfiguration, liste in differenzen.items():
        if konfiguration in offen:  # eine leere Liste aus gescheiterter Differenz ist kein Nachweis
            zeilen.append(f"- {vor}{konfiguration}: nicht nachgewiesen: {offen[konfiguration]}")
        elif not liste:
            zeilen.append(f"- {vor}{konfiguration}: keine Abweichung")
        zeilen += [f"- {vor}{konfiguration}: {a['art']} {a['volumen']:g} mm³ bei {_ort(a['box'])}, {_bereich_text(a)}"
                   for a in liste]
    return zeilen


def _folgen_text(p: dict) -> str:
    folgen = [*p.get("folgen", []), *([f"Lage: {', '.join(p['lage_folgen'])}"] if p.get("lage_folgen") else [])]
    return ", ".join(folgen) or "–"


def _paare(liste: list[dict], name: str) -> list[str]:
    return [f"- {name}: {' / '.join(k['paar'])}" + (f" ({k['volumen']:g} mm³)" if k.get("volumen") is not None else "")
            for k in liste]


def _kollisionen_abschnitt(pruefungen: list[dict]) -> list[str]:
    """Die Kollisionsliste (Spec Bestandsdateien §8.2): Nur neue sind Mängel, der Rest steht hier."""
    e = next((x for x in pruefungen if x["id"] == "kollision"), None)
    if e is None:
        return ["", "### Kollisionen", "", "- nicht geprüft"]
    zeilen = _paare(e.get("ist", []), "neu") + _paare(e.get("bekannt", []), "aus dem Bestand")
    zeilen += _paare(e.get("erlaubt", []), "erlaubt") + _paare(e.get("weggefallen", []), "weggefallen")
    return ["", "### Kollisionen", "", *(zeilen or ["- keine"])]


def _bewegungen_abschnitt(bewegungen: dict) -> list[str]:
    """Je Grenzverknüpfung die Fahrt des Laufs (Spec Bestandsdateien §8.4)."""
    zeilen = ["", "### Bewegungen", ""]
    if not bewegungen:
        return zeilen + ["- keine Grenzverknüpfung gefahren"]
    zeilen += ["| Grenze | Komponente | Bereich | gefahren | Stellungen | bewegt | Kollisionen | Hinweis |",
               "|---|---|---|---|---|---|---|---|"]
    for name, e in bewegungen.items():
        bereich = "–" if e.get("min") is None or e.get("max") is None else f"{e['min']:g} … {e['max']:g}"
        gefahren = {True: "ja", False: "nein"}.get(e.get("gefahren"), "nicht gelesen")
        zeilen.append(f"| {name} | {_zelle(e.get('komponente'))} | {bereich} | {gefahren} | {_zelle(e.get('stellungen'))} | "
                      f"{', '.join(e.get('bewegt') or []) or '–'} | {len(e.get('kollisionen') or [])} | "
                      f"{_zelle(e.get('hinweis'))} |")
    return zeilen


def _bestandsfehler_abschnitt(fehler: dict) -> list[str]:
    zeilen = [f"- {x}" for x in fehler.get("neuaufbau", [])]
    zeilen += [f"- {v['verknuepfung']} ({v['konfiguration']}): Code {v['code']}" for v in fehler.get("verknuepfungen", [])]
    zeilen += _paare(fehler.get("kollisionen", []), "Kollision")
    zeilen += [f"- {b['pruefung']}: {b['hinweis']}" for b in fehler.get("bewegungen", [])]
    return ["", "### Bestandsfehler (kein Mangel des Laufs)", "", *(zeilen or ["- keine"])]


def _baugruppe_abschnitt(letzter: dict) -> list[str]:
    """Was nur eine Baugruppe hat: Kollisionsliste, Bewegungen, Warnungen, Bestandsfehler, was die Prüfung nicht abdeckt."""
    zeilen = _kollisionen_abschnitt(letzter.get("pruefungen", [])) + _bewegungen_abschnitt(letzter.get("bewegungen") or {})
    warnungen = [f"- {w['code']}: {w['meldung']}" for w in letzter.get("warnungen", [])]
    zeilen += ["", "### Warnungen", "", *(warnungen or ["- keine"])] + _bestandsfehler_abschnitt(letzter.get("bestandsfehler") or {})
    offen = [f"- {h}" for h in letzter.get("nicht_abgedeckt", [])]
    return zeilen + ["", "### Nicht abgedeckt", "", *(offen or ["- nichts bekannt"])]


def _ausgabe_zeile(d: dict) -> str:
    if d.get("neu"):
        return f"- `{d['datei']}` (neu): neben die Hauptbaugruppe `{d['original']}`, Ausgabe `{d['ausgabe']}`"
    return f"- `{d['datei']}`: Original `{d['original']}`, Ausgabe `{d['ausgabe']}`"


def _aenderung_abschnitt(spec: dict, letzter: dict, ausgabe: dict | None, protokoll: dict | None) -> list[str]:
    """Abschnitt für `art: aenderung` (Spec Bestandsdateien §8, §9): Punkte mit Folgen, Differenzen, Ausgabeliste, Lizenz, bei
    einer Baugruppe je Datei und mit `_baugruppe_abschnitt`."""
    bestand = spec["bestand"]
    baugruppe = bestand["datei"].lower().endswith(".sldasm")
    zeilen = ["", "## Änderung am Bestand", "", f"Datei: `{bestand['datei']}` (Aufnahme {bestand['aufnahme']})", "",
              "### Punkte", "", "| Punkt | Typ | Änderung | Folgen |", "|---|---|---|---|"]
    zeilen += [f"| {p['id']} | {p['typ']} | {_punkt_text(p)}{' in ' + p['in_datei'] if p.get('in_datei') else ''} | "
               f"{_folgen_text(p)} |" for p in spec["punkte"]]
    zeilen += ["", "### Differenzen vorher/nachher (letzter Lauf)", ""]
    differenzen, pruefungen = letzter.get("differenzen"), letzter.get("pruefungen", [])
    if baugruppe and differenzen is not None:
        for rel, je in differenzen.items():
            zeilen += _differenz_zeilen(je, pruefungen, f"{rel}/bereich", f"{rel}, ")
        if not differenzen:
            zeilen.append("- kein Teil verglichen (keine Datei mit Punkten geändert)")
    else:
        if not differenzen:
            zeilen.append("- nicht geprüft")
        zeilen += _differenz_zeilen(differenzen or {}, pruefungen)
    if baugruppe:
        zeilen += _baugruppe_abschnitt(letzter)
    zeilen += ["", "### Ausgabe", ""]
    if ausgabe is None:
        zeilen.append("- Ausgabe erst nach bestandenem Lauf (geprüft und vom Prüfer abgenommen)")
    elif "fehler" in ausgabe:
        zeilen.append(f"- Ausgabeliste nicht ermittelt: {ausgabe['fehler']}")
    else:
        zeilen += [_ausgabe_zeile(d) for d in ausgabe["dateien"]]
        zeilen += [f"- unverändert, nicht ausgegeben: `{n}`" for n in ausgabe["unveraendert"]]
        zeilen += [f"- Warnung {w['code']}: {w['meldung']}" for w in ausgabe["warnungen"]]
        if not (ausgabe["dateien"] or ausgabe["unveraendert"]):
            zeilen.append("- keine Datei im Lauf")
        if h := ausgabe.get("herkunft"):
            zeilen.append(f"- Herkunft: Auftrag {h.get('auftrag')}, Lauf {h.get('lauf')} ({h.get('spec')}), dorthin schreibt swki "
                          "nichts")
    lizenz = (protokoll or {}).get("lizenz")
    if lizenz and isinstance(lizenz.get("sitzung"), dict):
        zeilen += ["", f"Lizenz beim Bau: Sitzung {lizenz['sitzung'].get('name')}, Datei {(lizenz.get('datei') or {}).get('name')}"]
    if not baugruppe:
        zeilen += ["", "Wirkung auf Baugruppen nicht geprüft (Etappe 1 prüft nur das Teil)."]
    return zeilen


def bericht_markdown(
    spec: dict, auftrag: str, laeufe: list[dict], empfehlung: tuple[str, str],
    letzter_bericht: dict | None, letztes_urteil: dict | None, letztes_protokoll: dict | None,
    compiler_aenderungen: list[str], ausgabe: dict | None = None,
) -> str:
    """`ausgabe`: nur für `art: aenderung`, das Ergebnis von `ausgabe_liste` (`None` solange kein Lauf bestanden ist, bei einem
    Fehler `{"fehler": Text}`)."""
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
    if spec.get("art") == "aenderung":
        zeilen += _aenderung_abschnitt(spec, letzter, ausgabe, letztes_protokoll)
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
                   "| Schraube bzw. Außengewinde | Teil | Bohrung | Einschraublänge (mm) | Gewindetiefe (mm) | Volumen ist / soll (mm³) |",
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
    if bewegungen and spec.get("art") != "aenderung" and bewegungen.get("laeufe"):  # eine Änderung trägt je Grenze einen Eintrag
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
    zeilen += [f"- vorher, {name}: `{pfad}`" for name, pfad in (letzter_bericht or {}).get("bilder_vorher", {}).items()]
    zeilen += [f"- {name}: `{pfad}`" for name, pfad in (letzter_bericht or {}).get("bilder_bewegung", {}).items()]
    zeilen += ["", "## Phasenzeiten (letzter Lauf)", "", "| Phase | s |", "|---|---|"]
    for phase, sekunden in (letztes_protokoll or {}).get("phasen", {}).items():
        zeilen.append(f"| {phase} | {sekunden} |")
    zeilen += ["", "## Compiler-Änderungen während des Auftrags", ""]
    zeilen += [f"- {c}" for c in compiler_aenderungen] or ["- keine"]
    return "\n".join(zeilen) + "\n"
