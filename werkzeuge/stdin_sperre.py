"""PreToolUse-Hook für Bash: lehnt Befehle ab, die auf stdin warten.

Im Bash-Tool bekommt ein Befehl kein Ende der Eingabe; Python-Skripte über stdin (`python -`, auch mit Heredoc oder
`||`-Rückfall), ein `python` ohne Skript und ein `cat` ohne Datei hängen bis zum 2-min-Zeitlimit (BTP D1/D2/D4, je
~2 min). Erlaubt bleiben `python <datei>`, `python -c …`, `python -m …` und `cat` mit Datei, Heredoc, `<` oder Pipe.

Eingabe: Hook-JSON auf stdin. Ausgabe: bei Ablehnung JSON mit permissionDecision "deny", sonst nichts (Exit 0).
Aufruf (`.claude/settings.json`): .venv/Scripts/python.exe -m werkzeuge.stdin_sperre
"""

import json
import re
import shlex
import sys

PYTHON = re.compile(r"^(python(3(\.\d+)?)?|py)(\.exe)?$", re.IGNORECASE)
FLAG_MIT_WERT = {"-X", "-W", "-Q"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
WEG = ("Längere Python-Schnipsel mit dem Write-Tool als Datei anlegen und `.venv\\Scripts\\python.exe <datei>` "
       "ausführen (kurze mit `python -c`); `cat` nur mit Datei, Heredoc oder Pipe.")


def _ohne_heredoc_inhalt(befehl: str) -> str:
    """Zeilen eines Heredoc-Inhalts entfernen (die Zeile mit `<<` bleibt), damit Text darin nicht als Befehl zählt."""
    zeilen, ende = [], None
    for zeile in befehl.split("\n"):
        if ende is not None:
            if zeile.strip() == ende:
                ende = None
            continue
        zeilen.append(zeile)
        treffer = [m for m in HEREDOC.finditer(zeile) if not zeile[max(0, m.start() - 1):m.start()] == "<"]
        if treffer:
            ende = treffer[-1].group(2)
    return "\n".join(zeilen)


def _abschnitte(befehl: str) -> list[tuple[str, bool]]:
    """Einfache Befehle (getrennt an ; && || | & und Zeilenende, nicht in Anführungszeichen) mit „liest aus Pipe“."""
    teile, aktuell, quote, gepiped = [], [], None, False
    i, n = 0, len(befehl)

    def abschliessen(naechster_gepiped: bool) -> None:
        nonlocal aktuell, gepiped
        teile.append(("".join(aktuell), gepiped))
        aktuell, gepiped = [], naechster_gepiped

    while i < n:
        c = befehl[i]
        if quote:
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < n:
                aktuell.append(c)
                i += 1
                c = befehl[i]
            aktuell.append(c)
        elif c in "'\"":
            quote = c
            aktuell.append(c)
        elif befehl.startswith(("&&", "||"), i):
            abschliessen(False)
            i += 1
        elif c == "|":
            abschliessen(True)
        elif c in ";\n":
            abschliessen(False)
        elif c == "&" and not (i and befehl[i - 1] in "<>") and not befehl.startswith(">", i + 1):
            abschliessen(False)
        else:
            aktuell.append(c)
        i += 1
    abschliessen(False)
    return [(t.strip(), p) for t, p in teile if t.strip()]


def _woerter(abschnitt: str) -> list[str]:
    text = abschnitt.replace("\\", "/")
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _name(wort: str) -> str:
    return wort.rsplit("/", 1)[-1]


def _python_grund(woerter: list[str], gepiped: bool, eingabe: bool) -> str | None:
    i = 1
    while i < len(woerter):
        w = woerter[i]
        if w == "-":
            return "`python -` liest das Skript von stdin"
        if w.startswith("<<"):
            return "Python-Skript über Heredoc"
        if re.match(r"^-[cm]", w):   # -c <code>, -m <modul> (auch -mpytest)
            return None
        if w in FLAG_MIT_WERT:
            i += 2
            continue
        if w.startswith("-"):
            i += 1
            continue
        if w.startswith(("<", ">")) or re.match(r"^\d*>", w):
            i += 2 if w in ("<", ">", ">>", "2>", "1>") else 1
            continue
        return None   # Skriptdatei
    if gepiped or eingabe:
        return "Python-Skript über stdin"
    return "`python` ohne Skript wartet auf Eingabe"


def _cat_grund(woerter: list[str], gepiped: bool) -> str | None:
    if gepiped:
        return None
    i = 1
    while i < len(woerter):
        w = woerter[i]
        if w.startswith("<"):
            return None
        if w in (">", ">>", "2>", "1>", "&>"):
            i += 2
            continue
        if re.match(r"^(\d|&)?>", w) or w.startswith("-") and w != "-":
            i += 1
            continue
        if w == "-":
            break
        return None   # Datei
    return "`cat` ohne Datei wartet auf Eingabe"


def grund(befehl: str) -> str | None:
    """Warum der Bash-Befehl auf stdin warten würde, sonst None."""
    for abschnitt, gepiped in _abschnitte(_ohne_heredoc_inhalt(befehl or "")):
        woerter = _woerter(abschnitt)
        while woerter and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", woerter[0]) or woerter[0] in ("(", "{", "exec")):
            woerter = woerter[1:]
        if not woerter:
            continue
        name = _name(woerter[0])
        eingabe = "<" in abschnitt
        if PYTHON.match(name):
            g = _python_grund(woerter, gepiped, eingabe)
        elif name == "cat":
            g = _cat_grund(woerter, gepiped)
        else:
            g = None
        if g:
            return g
    return None


def main() -> int:
    try:
        daten = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        befehl = daten.get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):
        return 0
    g = grund(befehl)
    if g:
        aus = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": f"Abgelehnt: {g} – hängt bis zum 2-min-Zeitlimit. {WEG}"}}
        sys.stdout.write(json.dumps(aus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
