"""Erzeugt permissions.deny für alle nicht-lesenden Tools von solidworks-mcp.

Aufruf: .venv\\Scripts\\python.exe setup\\mcp_sperren.py
Liest config/mcp-tools-alle.json und config/mcp-lesetools.txt, schreibt .claude/settings.json.
"""

import json
from pathlib import Path

PRAEFIX = "mcp__solidworks-mcp__"
PFLICHT_GESPERRT = {
    "execute_macro", "batch_execute_macros", "pack_and_go_assembly",
    "batch_file_operations", "execute_workflow", "batch_process_files",
}
PROJEKT = Path(__file__).resolve().parent.parent


def sperrliste(alle: list[str], erlaubt: list[str]) -> list[str]:
    unbekannt = sorted(set(erlaubt) - set(alle))
    if unbekannt:
        raise ValueError(f"Unbekannte Tools in mcp-lesetools.txt: {unbekannt}")
    verboten = sorted(set(erlaubt) & PFLICHT_GESPERRT)
    if verboten:
        raise ValueError(f"Diese Tools müssen gesperrt bleiben: {verboten}")
    return sorted(PRAEFIX + t for t in alle if t not in set(erlaubt))


def aktualisiere_settings(settings: dict, deny: list[str]) -> dict:
    perms = settings.setdefault("permissions", {})
    fremd = [r for r in perms.get("deny", []) if not r.startswith(PRAEFIX)]
    perms["deny"] = fremd + deny
    return settings


def main() -> None:
    alle = json.loads((PROJEKT / "config" / "mcp-tools-alle.json").read_text(encoding="utf-8"))
    erlaubt = [
        z.strip() for z in (PROJEKT / "config" / "mcp-lesetools.txt").read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.startswith("#")
    ]
    pfad = PROJEKT / ".claude" / "settings.json"
    settings = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
    deny = sperrliste(alle, erlaubt)
    pfad.parent.mkdir(exist_ok=True)
    pfad.write_text(json.dumps(aktualisiere_settings(settings, deny), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"erlaubt": len(erlaubt), "gesperrt": len(deny)}))


if __name__ == "__main__":
    main()
