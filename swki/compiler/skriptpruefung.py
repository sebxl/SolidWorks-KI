"""Statische Prüfung von Notausgang-Skripten (typ: skript) vor dem Laden.

Ein Skript darf nur `math` importieren, muss `def bauen(ctx)` definieren und darf weder
gefährliche Builtins noch Dunder-Attribute noch Speicher-/Schließ-/Makro-Aufrufe der
SolidWorks-API verwenden. Speichern und Schließen übernimmt ausschließlich der Compiler.
"""

import ast

ERLAUBTE_IMPORTE = {"math"}
VERBOTENE_NAMEN = {
    "exec", "eval", "compile", "open", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "exit", "quit",
}
VERBOTENE_ATTRIBUTE = {
    "SaveAs", "SaveAs2", "SaveAs3", "Save", "Save2", "Save3", "SaveBMP",
    "CloseDoc", "CloseAllDocuments", "QuitDoc", "ExitApp",
    "OpenDoc", "OpenDoc6", "OpenDoc7", "LoadFile4",
    "RunMacro", "RunMacro2", "RunCommand",
    "DeleteFile", "SetUserPreferenceToggle", "SetUserPreferenceIntegerValue",
    "SetUserPreferenceDoubleValue", "SetUserPreferenceStringValue",
}
VERBOTENE_PRAEFIXE = {
    "save", "close", "quit", "exit", "activatedoc", "opendoc", "loadfile",
    "runmacro", "runcommand", "setuserpreference", "deletefile",
}


def _befund(knoten, meldung: str) -> dict:
    return {"zeile": getattr(knoten, "lineno", 0), "meldung": meldung}


def pruefe_skript(quelltext: str) -> list[dict]:
    """Liefert Befunde [{"zeile", "meldung"}]; leere Liste = Skript zulässig."""
    try:
        baum = ast.parse(quelltext)
    except SyntaxError as e:
        return [{"zeile": e.lineno or 0, "meldung": f"Syntaxfehler: {e.msg}"}]
    befunde = []
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for alias in k.names:
                if alias.name.split(".")[0] not in ERLAUBTE_IMPORTE:
                    befunde.append(_befund(k, f"Import {alias.name!r} nicht erlaubt (erlaubt: math)"))
        elif isinstance(k, ast.ImportFrom):
            if (k.module or "").split(".")[0] not in ERLAUBTE_IMPORTE:
                befunde.append(_befund(k, f"Import aus {k.module!r} nicht erlaubt (erlaubt: math)"))
        elif isinstance(k, ast.Name) and k.id in VERBOTENE_NAMEN:
            befunde.append(_befund(k, f"{k.id!r} ist nicht erlaubt"))
        elif isinstance(k, ast.Name) and k.id.startswith("__"):
            befunde.append(_befund(k, f"Dunder-Name {k.id!r} ist nicht erlaubt"))
        elif isinstance(k, ast.Attribute):
            if k.attr.startswith("__"):
                befunde.append(_befund(k, f"Dunder-Attribut {k.attr!r} ist nicht erlaubt"))
            elif k.attr in VERBOTENE_ATTRIBUTE or k.attr.lower().startswith(tuple(VERBOTENE_PRAEFIXE)):
                befunde.append(_befund(k, f"API-Aufruf {k.attr!r} ist im Skript nicht erlaubt"))
    bauen = [
        k for k in baum.body
        if isinstance(k, ast.FunctionDef) and k.name == "bauen" and len(k.args.args) == 1
    ]
    if not bauen:
        befunde.append({"zeile": 0, "meldung": "Funktion 'def bauen(ctx)' fehlt"})
    return sorted(befunde, key=lambda b: b["zeile"])
