import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "mcp_sperren", Path(__file__).resolve().parent.parent / "setup" / "mcp_sperren.py"
)
mcp_sperren = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_sperren)


def test_sperrliste_alles_ausser_erlaubt():
    alle = ["list_features", "get_mass_properties", "create_extrusion", "execute_macro"]
    deny = mcp_sperren.sperrliste(alle, ["list_features", "get_mass_properties"])
    assert deny == ["mcp__solidworks-mcp__create_extrusion", "mcp__solidworks-mcp__execute_macro"]


def test_unbekanntes_erlaubtes_tool():
    with pytest.raises(ValueError, match="gibtsnicht"):
        mcp_sperren.sperrliste(["a"], ["gibtsnicht"])


def test_pflichtsperre_nicht_erlaubbar():
    with pytest.raises(ValueError, match="execute_macro"):
        mcp_sperren.sperrliste(["execute_macro"], ["execute_macro"])


def test_settings_behaelt_fremde_regeln():
    settings = {"permissions": {"deny": ["Bash(rm:*)", "mcp__solidworks-mcp__alt"], "ask": ["Bash(git push:*)"]}}
    neu = mcp_sperren.aktualisiere_settings(settings, ["mcp__solidworks-mcp__x"])
    assert neu["permissions"]["deny"] == ["Bash(rm:*)", "mcp__solidworks-mcp__x"]
    assert neu["permissions"]["ask"] == ["Bash(git push:*)"]


def test_settings_deny_stimmt_mit_sperrliste_ueberein():
    """Driftprüfung: die mcp__solidworks-mcp__*-Einträge in .claude/settings.json permissions.deny
    sind genau sperrliste(config/mcp-tools-alle.json, erlaubt aus config/mcp-lesetools.txt)."""
    projekt = Path(__file__).resolve().parent.parent
    alle = json.loads((projekt / "config" / "mcp-tools-alle.json").read_text(encoding="utf-8"))
    erlaubt = mcp_sperren.lies_lesetools(projekt / "config" / "mcp-lesetools.txt")
    erwartet = mcp_sperren.sperrliste(alle, erlaubt)
    settings = json.loads((projekt / ".claude" / "settings.json").read_text(encoding="utf-8"))
    tatsaechlich = sorted(r for r in settings["permissions"]["deny"] if r.startswith(mcp_sperren.PRAEFIX))
    assert tatsaechlich == erwartet
