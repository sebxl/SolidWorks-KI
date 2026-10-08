"""Auswertung der Agenten-Transkripte (JSONL von Claude Code): Zeit, Zeitanteile je Werkzeug, Tool-Aufrufe, Tokens,
Freigaben und Leck-Prüfung. Der Konstruktions-Agent ist der Wurzelagent; seine Subagenten (Prüfer) zählen bei Aufrufen
und Tokens mit, ihre Zeit steckt in der Dauer des Agent-Aufrufs."""

import json
import re
from datetime import datetime
from pathlib import Path

_SWKI = re.compile(r"-m\s+swki\s+(\w+)")
_EIGENE = {"bauen", "pruefen", "validieren", "freigeben"}
_RANG = ["bauen", "pruefen", "freigeben", "validieren"]   # verkettete Befehle zählen zur teuersten Kategorie

# Gewichte für tokens_gewichtet (relativ zum Eingabepreis)
GEWICHTE = {"input_tokens": 1.0, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1,
            "output_tokens": 5.0}


def lade(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in Path(pfad).read_text(encoding="utf-8").splitlines() if z.strip()]


def _zeit(e: dict) -> float | None:
    ts = e.get("timestamp")
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else None


def _bloecke(e: dict) -> list[dict]:
    inhalt = (e.get("message") or {}).get("content")
    return inhalt if isinstance(inhalt, list) else []


def kategorie(name: str, eingabe: dict) -> str:
    """Zeitkategorie eines Tool-Aufrufs."""
    if name in ("Bash", "PowerShell"):
        befehl = str(eingabe.get("command", ""))
        befehle = _SWKI.findall(befehl)
        for k in _RANG:
            if k in befehle:
                return k
        if befehle:
            return "swki_sonst"
        return "werkzeuge" if "-m werkzeuge" in befehl else "shell"
    if name in ("Agent", "Task"):
        return "pruefer" if eingabe.get("subagent_type") == "pruefer" else "subagent"
    if name in ("Read", "Grep", "Glob"):
        return "lesen"
    if name in ("Write", "Edit", "NotebookEdit"):
        return "schreiben"
    if name == "Skill":
        return "skill"
    return "sonst"


def _vereinigung(intervalle: list[tuple[float, float]]) -> float:
    summe, ende = 0.0, None
    for a, b in sorted(intervalle):
        if ende is None or a > ende:
            summe += b - a
            ende = b
        elif b > ende:
            summe += b - ende
            ende = b
    return summe


def aufrufe(eintraege: list[dict]) -> list[dict]:
    """Tool-Aufrufe eines Transkripts mit Start, Ende, Fehlerflag und Ergebnistext (gekürzt)."""
    offen: dict[str, dict] = {}
    liste = []
    for e in eintraege:
        t = _zeit(e)
        for b in _bloecke(e):
            if b.get("type") == "tool_use" and b.get("id") not in offen:
                a = {"id": b["id"], "name": b.get("name", ""), "eingabe": b.get("input") or {}, "start": t,
                     "ende": None, "fehler": False, "ergebnis": ""}
                offen[b["id"]] = a
                liste.append(a)
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in offen:
                a = offen[b["tool_use_id"]]
                a["ende"] = t
                a["fehler"] = bool(b.get("is_error"))
                inhalt = b.get("content")
                if isinstance(inhalt, list):
                    inhalt = " ".join(str(x.get("text", "")) for x in inhalt if isinstance(x, dict))
                a["ergebnis"] = str(inhalt or "")[:4000]
    return liste


def tokens(eintraege: list[dict]) -> dict:
    """Summe der usage je Nachricht (Einträge derselben Nachricht wiederholen die usage, die letzte zählt)."""
    je_nachricht: dict[str, dict] = {}
    for e in eintraege:
        m = e.get("message") or {}
        if e.get("type") == "assistant" and m.get("usage") and m.get("id"):
            je_nachricht[m["id"]] = m["usage"]
    summe = {k: 0 for k in GEWICHTE}
    for u in je_nachricht.values():
        for k in GEWICHTE:
            summe[k] += int(u.get(k) or 0)
    summe["gewichtet"] = round(sum(summe[k] * g for k, g in GEWICHTE.items()))
    summe["nachrichten"] = len(je_nachricht)
    return summe


def _freigabe_ok(a: dict) -> bool:
    """swki meldet Fehler mit Exit ≠ 0 (Tool-Fehler) bzw. "fehler" im JSON."""
    return not a["fehler"] and not re.search(r'"fehler":\s*[{"]', a["ergebnis"]) and "Exit code" not in a["ergebnis"]


def _normiere(s: str) -> str:
    return s.replace("\\\\", "/").replace("\\", "/").lower()


def lecks(alle: dict[str, list[dict]], verboten: list[str]) -> list[str]:
    """Verbotene Pfade in den Eingaben der Tool-Aufrufe (Read/Grep/Glob/Bash …) aller Transkripte."""
    muster = [_normiere(v) for v in verboten]
    treffer = []
    for agent, eintraege in alle.items():
        for a in aufrufe(eintraege):
            text = _normiere(json.dumps(a["eingabe"], ensure_ascii=False))
            for v in muster:
                if v in text:
                    treffer.append(f"{agent}: {a['name']} → {v}")
    return treffer


def auswerten(wurzel: list[dict], unter: dict[str, list[dict]] | None = None,
              verboten: list[str] | None = None) -> dict:
    """KPI aus dem Transkript des Konstruktions-Agenten (wurzel) und seiner Subagenten (unter: id → Einträge)."""
    unter = unter or {}
    zeiten = [t for t in map(_zeit, wurzel) if t is not None]
    zeit_s = (max(zeiten) - min(zeiten)) if zeiten else 0.0
    eigene = aufrufe(wurzel)
    anteile: dict[str, float] = {}
    intervalle = []
    for a in eigene:
        if a["start"] is None or a["ende"] is None:
            continue
        k = kategorie(a["name"], a["eingabe"])
        anteile[k] = anteile.get(k, 0.0) + (a["ende"] - a["start"])
        intervalle.append((a["start"], a["ende"]))
    anteile = {k: round(v, 1) for k, v in sorted(anteile.items(), key=lambda kv: -kv[1])}
    anteile["modell"] = round(max(0.0, zeit_s - _vereinigung(intervalle)), 1)

    alle = {"wurzel": wurzel, **unter}
    je_werkzeug: dict[str, int] = {}
    tok = {k: 0 for k in [*GEWICHTE, "gewichtet", "nachrichten"]}
    for eintraege in alle.values():
        for a in aufrufe(eintraege):
            je_werkzeug[a["name"]] = je_werkzeug.get(a["name"], 0) + 1
        for k, v in tokens(eintraege).items():
            tok[k] += v
    swki: dict[str, int] = {}
    freigaben = 0
    for a in eigene:
        if a["name"] not in ("Bash", "PowerShell"):
            continue
        befehle = _SWKI.findall(str(a["eingabe"].get("command", "")))
        for b in befehle:
            k = b if b in _EIGENE else "swki_sonst"
            swki[k] = swki.get(k, 0) + 1
        if "freigeben" in befehle and _freigabe_ok(a):
            freigaben += befehle.count("freigeben")
    return {
        "zeit_s": round(zeit_s, 1),
        "zeit_anteile_s": anteile,
        "tool_aufrufe": sum(je_werkzeug.values()),
        "tool_aufrufe_je_werkzeug": dict(sorted(je_werkzeug.items(), key=lambda kv: -kv[1])),
        "swki_aufrufe": swki,
        "subagenten": len(unter),
        "tokens": tok,
        "freigaben": freigaben,
        "lecks": lecks(alle, verboten or []),
    }


def subagenten(ordner: Path, wurzel_id: str) -> dict[str, Path]:
    """Alle Transkripte unterhalb des Agenten wurzel_id (rekursiv über parentAgentId in *.meta.json)."""
    eltern: dict[str, str] = {}
    for meta in Path(ordner).glob("agent-*.meta.json"):
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("parentAgentId"):
            eltern[meta.name[len("agent-"):-len(".meta.json")]] = d["parentAgentId"]
    gefunden: dict[str, Path] = {}
    neu = [wurzel_id]
    while neu:
        vater = neu.pop()
        for kind, v in eltern.items():
            if v == vater and kind not in gefunden:
                gefunden[kind] = Path(ordner) / f"agent-{kind}.jsonl"
                neu.append(kind)
    return gefunden


def finde_transkript(agent_id: str, projekte: Path | None = None) -> Path:
    """Pfad von agent-<id>.jsonl unter ~/.claude/projects (neueste Fundstelle)."""
    projekte = projekte or Path.home() / ".claude" / "projects"
    treffer = sorted(projekte.glob(f"*/*/subagents/agent-{agent_id}.jsonl"), key=lambda p: p.stat().st_mtime)
    if not treffer:
        raise FileNotFoundError(f"Transkript agent-{agent_id}.jsonl nicht gefunden unter {projekte}")
    return treffer[-1]
