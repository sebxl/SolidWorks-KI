"""status.json und plateau.md je Ende einer Studie (Spec C2 §7): alles, was Claude für den nächsten Schritt braucht,
kompakt (plateau.md ≈ 1–2 k Tokens), ohne die Läufe selbst."""

import json
from collections import Counter
from pathlib import Path

import yaml

from swki.optimierung.auswertung import grenzanschlaege

NAECHSTER_SCHRITT = {
    "ZIEL": "Gewinner übernehmen: swki optimiere <spec> --uebernehmen (gibt im Raum frei), dann swki durchlauf <spec> "
            "--neustart, Prüfer, Bericht an den Nutzer.",
    "PLATEAU": "Eine Formvariante aus erlaubte_formaenderungen als Spec-Änderung (variante neu benennen) ODER bereich im "
               "rahmen ändern ODER abbrechen/annehmen; dann swki validieren und swki optimiere neu starten.",
    "BUDGET": "Budget erschöpft: Ergebnis annehmen (falls gut genug) oder Budget erhöhen und neu starten.",
    "FEHLER": "Fehler beheben (detail), dann neu starten; keine Bewertung während einer Studie ändern.",
}


def _kurz(x, n=4):
    return round(x, n) if isinstance(x, float) else x


def _features(pfad: Path) -> dict[str, dict]:
    if not pfad.is_file():
        return {}
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    return {f["id"]: f for f in spec.get("features", [])}


def formaenderungen(specs: Path, haupt: str) -> dict:
    """Features gegenüber der Freigabe-Kopie je Spec des Auftrags: {Datei: {hinzu, weg, geaendert}}."""
    spec = yaml.safe_load((specs / haupt).read_text(encoding="utf-8"))
    dateien = [haupt]
    if spec.get("art") == "baugruppe":
        dateien += sorted({k["quelle"]["teil"] for k in spec.get("komponenten", []) if "teil" in k.get("quelle", {})})
    out = {}
    for d in dateien:
        jetzt = _features(specs / d)
        frei = _features(specs / d.replace(".yaml", ".freigegeben.yaml"))
        if not frei:
            continue
        aenderung = {"hinzu": [i for i in jetzt if i not in frei], "weg": [i for i in frei if i not in jetzt],
                     "geaendert": [i for i in jetzt if i in frei and jetzt[i] != frei[i]]}
        if any(aenderung.values()):
            out[d] = {k: v for k, v in aenderung.items() if v}
    return out


def varianten(lauf: Path) -> list[dict]:
    """Bisherige Optimierungsläufe desselben Auftrags (Arbeitsordner) mit Variante, Grund und Bestem."""
    out = []
    for p in sorted(lauf.parent.glob("optimierung-*"), key=lambda x: int(x.name.split("-")[-1])
                    if x.name.split("-")[-1].isdigit() else 0):
        if p == lauf or not (p / "status.json").is_file():
            continue
        s = json.loads((p / "status.json").read_text(encoding="utf-8"))
        b = s.get("bester") or {}
        out.append({"lauf": p.name, "variante": s.get("variante"), "grund": s.get("grund"), "bester": b.get("wert"),
                    "werte": b.get("werte"), "formaenderungen": s.get("formaenderungen")})
    return out


def _wichtigkeit(r) -> dict:
    try:
        import optuna
        return {k: round(v, 3) for k, v in optuna.importance.get_param_importances(r.studie).items()}
    except Exception:  # zu wenige Proben oder nur eine Stellschraube mit festem Wert
        return {}


def status(r, grund: str, detail: str) -> dict:
    """Vollständiger Status (status.json) aus dem Zustand des Runners."""
    proben = r.proben
    simuliert = [p for p in proben if p.get("status") == "simuliert"]
    zeit = r.zeit()
    rang = r.rangfolge()
    bester = r.bester()

    def eintrag(p: dict) -> dict:
        e = {"nr": p["nr"], "wert": p["wert"], "werte": p["werte"], "laeufe": p.get("laeufe"),
             "fehlerbilder": dict(list(p.get("fehlerbilder", {}).items())[:4])}
        k = p.get("kennzahlen", {})
        e["anteile"] = {x.split(":", 1)[1]: v for x, v in k.items() if x.startswith("anteil_richtig:")}
        if p["nr"] in r.stufe2:
            s2 = r.stufe2[p["nr"]]
            e["stufe2"] = {"bestanden": s2.get("bestanden"), "wert": s2.get("wert"), "belastbar": s2.get("belastbar")}
        return e

    phase = r.phasen[-1] if r.phasen else {"bereich": {s.name: list(s.bereich) for s in r.a.stellschrauben}}
    anschlag = []
    if bester is not None:
        anschlag = grenzanschlaege(bester["werte"], {k: tuple(v) for k, v in phase["bereich"].items()}, r.rahmen)
    verworfen = Counter()
    for p in proben:
        if p.get("status") == "verworfen":
            s0 = p.get("stufe0", {})
            for k in s0.get("kollisionen", [])[:1]:
                verworfen[f"Kollision {k['a']}/{k['b']} ({k['stellung']})"] += 1
            for b in s0.get("befunde", [])[:1]:
                verworfen[f"Befund {b[:90]}"] += 1
            for b in s0.get("bauraum", [])[:1]:
                verworfen[f"Bauraum {b.split(':')[0]}"] += 1
        elif p.get("status") == "simuliert" and not p.get("zulaessig"):
            for k in p.get("neben", {}):
                verworfen[f"Nebenbedingung {k}"] += 1
    raum_frei = None
    try:
        from swki.optimierung.raum import pruefe_im_raum
        raum_frei = pruefe_im_raum(r.a.spec_pfad).get("im_raum", False)
    except Exception:
        raum_frei = False
    ablauf = {s.name for s in r.a.stellschrauben if s.ablauf}
    s_sim = [p["zeiten"].get("probe_s", 0) for p in simuliert]
    return {
        "grund": grund, "detail": detail, "spec": str(r.a.spec_pfad), "lauf": r.lauf.name, "lauf_ordner": str(r.lauf),
        "variante": r.a.block.get("variante"), "ziel": r.a.ziel, "raum_freigegeben": raum_frei,
        "proben": {"gesamt": len(proben), "simuliert": len(simuliert),
                   "verworfen": sum(p.get("status") == "verworfen" for p in proben),
                   "abgebrochen": sum(p.get("status") == "abgebrochen" for p in proben),
                   "laeufe": sum(p.get("laeufe", 0) for p in proben), "dauer_min": round(zeit / 60, 1),
                   "proben_je_stunde": round(len(proben) / zeit * 3600, 1) if zeit > 0 else None,
                   "simulierte_je_stunde": round(len(simuliert) / zeit * 3600, 1) if zeit > 0 else None,
                   "s_je_simulierte_probe": round(sum(s_sim) / len(s_sim), 1) if s_sim else None,
                   "kerne": r.kerne},
        "bester": None if bester is None else {**eintrag(bester), "kennzahlen": bester.get("kennzahlen"),
                                               "ablauf": {k: v for k, v in bester["werte"].items() if k in ablauf}},
        "top": [eintrag(p) for p in rang[:5]],
        "verlauf": [[nr, _kurz(w), round(t / 60, 1)] for nr, w, t in r.fortschritt.verlauf],
        "wichtigkeit": _wichtigkeit(r),
        "grenzanschlaege": anschlag,
        "phasen": [{k: v for k, v in ph.items() if k != "starts"} for ph in r.phasen],
        "stufe0_verworfen": dict(verworfen.most_common(6)),
        "kollisionen_ausgangsstand": r.pb.grund_meldung,
        "formaenderungen": formaenderungen(r.specs, r.a.spec_pfad.name),
        "erlaubte_formaenderungen": r.a.block.get("erlaubte_formaenderungen", []),
        "varianten": varianten(r.lauf),
        "rahmen": {k: list(v) for k, v in r.rahmen.items()},
        "bewertung": r.bewertung["sha256"][:16],
        "naechster_schritt": NAECHSTER_SCHRITT[grund],
    }


def _werte(w: dict) -> str:
    return ", ".join(f"{k} {v:g}" if isinstance(v, (int, float)) else f"{k} {v}" for k, v in w.items())


def plateau_md(s: dict) -> str:
    """Kurzfassung für Claude (≈ 1–2 k Tokens)."""
    p, z = s["proben"], s["ziel"]
    zeilen = [f"# {s['grund']} – {Path(s['spec']).name}, {s['lauf']}", "",
              f"**Grund:** {s['detail']}",
              f"**Ziel:** {z['kennzahl']} {'≥' if z['richtung'] == 'max' else '≤'} {z['zielwert']:g} · "
              f"Raum freigegeben: {'ja' if s['raum_freigegeben'] else 'NEIN'} · Variante: {s.get('variante') or '–'}",
              f"**Proben:** {p['gesamt']} ({p['simuliert']} simuliert, {p['verworfen']} Stufe 0 verworfen, "
              f"{p['abgebrochen']} abgebrochen), {p['laeufe']} Läufe in {p['dauer_min']} min · {p['proben_je_stunde']} "
              f"Proben/h ({p['simulierte_je_stunde']} simulierte/h), {p['kerne']} Kerne",
              "**Verlauf** (Probe: bester Wert @ min): " + " · ".join(f"{a}: {b} @ {c}" for a, b, c in s["verlauf"][-12:])]
    b = s.get("bester")
    if b:
        zeilen += ["", "## Bester", f"Probe {b['nr']}: **{b['wert']}** – {_werte(b['werte'])}"
                   + (f" · Prüfstufe 2: {'bestanden' if b['stufe2']['bestanden'] else 'NICHT bestanden'} "
                      f"({b['stufe2']['wert']}, belastbar: {b['stufe2']['belastbar']})" if b.get("stufe2") else ""),
                   "Anteile richtig: " + ", ".join(f"{k} {v:.3f}" for k, v in b.get("anteile", {}).items())]
        if b.get("fehlerbilder"):
            zeilen.append("Fehlerbilder (Anteil aller gültigen Läufe): "
                          + "; ".join(f"{k} {v:.1%}" for k, v in b["fehlerbilder"].items()))
    if s["top"]:
        namen = list(s["top"][0]["werte"])
        zeilen += ["", "## Top 5", "| Nr | Wert | " + " | ".join(namen) + " | Läufe | Stufe 2 | häufigstes Fehlerbild |",
                   "|" + "---|" * (len(namen) + 5)]
        for t in s["top"]:
            fb = next(iter(t["fehlerbilder"].items()), None)
            s2 = t.get("stufe2")
            stufe2 = "–" if not s2 else f"{'✔' if s2['bestanden'] else '✘'} {s2['wert']}"
            werte = " | ".join(f"{t['werte'][n]:g}" if n in t["werte"] else "" for n in namen)
            zeilen.append(f"| {t['nr']} | {t['wert']} | {werte} | {t['laeufe']} | {stufe2} | "
                          + (f"{fb[0]} {fb[1]:.1%}" if fb else "–") + " |")
    if s["wichtigkeit"]:
        zeilen += ["", "**Wichtigkeit (fANOVA):** " + ", ".join(f"{k} {v:.2f}" for k, v in s["wichtigkeit"].items())]
    if s["grenzanschlaege"]:
        zeilen.append("**Grenzanschläge des Besten:** " + "; ".join(
            f"{g['name']} {g['seite']} ({g['wert']:g}, bereich {g['bereich']}, "
            f"{'erweiterbar' if g['erweiterbar'] else 'am Rahmen ' + str(s['rahmen'][g['name']])})"
            for g in s["grenzanschlaege"]))
    zeilen.append("**Phasen (Automatik):** " + " → ".join(
        f"{ph['massnahme']} ab {ph['nr_ab']} [{ph['sampler']}]" + (f" ({ph['detail']})" if ph.get("detail") else "")
        for ph in s["phasen"]))
    if s["stufe0_verworfen"]:
        zeilen.append("**Verworfen:** " + "; ".join(f"{k} ×{v}" for k, v in s["stufe0_verworfen"].items()))
    if s["kollisionen_ausgangsstand"]:
        zeilen.append("**Im Ausgangsstand schon geschnitten (ausgenommen):** "
                      + ", ".join(f"{k['a']}/{k['b']} {k['mm3']:g} mm³" for k in s["kollisionen_ausgangsstand"][:6]))
    zeilen += ["", "## Form", "**Formänderungen gegenüber der Freigabe:** " + (
        "; ".join(f"{d}: " + ", ".join(f"{k} {v}" for k, v in a.items()) for d, a in s["formaenderungen"].items())
        or "keine")]
    zeilen.append("**Erlaubte Formänderungen:** " + ("; ".join(s["erlaubte_formaenderungen"]) or
                                                      "keine (Formänderung nur nach Rückfrage)"))
    if s["varianten"]:
        zeilen.append("**Bereits versucht:** " + "; ".join(
            f"{v['lauf']} „{v['variante'] or '–'}“ {v['grund']} {v['bester']}" for v in s["varianten"]))
    zeilen.append("**Rahmen:** " + ", ".join(f"{k} {v}" for k, v in s["rahmen"].items()))
    zeilen += ["", f"**Nächster Schritt:** {s['naechster_schritt']}", ""]
    return "\n".join(zeilen)


def schreibe(s: dict, lauf: Path) -> None:
    (lauf / "status.json").write_text(json.dumps(s, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (lauf / "plateau.md").write_text(plateau_md(s), encoding="utf-8")
