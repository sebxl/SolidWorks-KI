"""werkzeuge.stdin_sperre: PreToolUse-Hook gegen Bash-Befehle, die auf stdin warten (BTP: ~2 min je Hänger)."""

import json
import subprocess
import sys

import pytest

from werkzeuge.stdin_sperre import grund


@pytest.mark.parametrize("befehl", [
    "cd x && .venv/Scripts/python.exe - <<'EOF'\nprint(1)\nEOF",
    "cd x && ../../.venv/Scripts/python.exe - <<'EOF' 2>&1 || true\nEOF\necho skip",   # d4-pruefstation-1
    "python - <<'EOF'\na\nEOF\n|| python - <<'EOF'\nb\nEOF",                          # d2-pruefstation-1
    ".venv\\Scripts\\python.exe -",
    "python3 -I - < skript.py",
    "echo 'print(1)' | python -",
    "python <<EOF\nprint(1)\nEOF",
    "python",
    "python -u",
    "x=1 python",
    "python - 2>/dev/null; cat > /dev/null; sed -i s/a/b/ f",                         # d1-stehlager-1
    "cat",
    "cat > ausgabe.txt",
    "cat >/dev/null",
])
def test_wartet_auf_stdin(befehl):
    assert grund(befehl)


@pytest.mark.parametrize("befehl", [
    ".venv/Scripts/python.exe -m swki validieren a.yaml",
    ".venv\\Scripts\\python.exe C:\\tmp\\skript.py",
    "python -c \"import sys; print(sys.argv)\" -",
    "python -X utf8 skript.py",
    "python -m pytest -q -x",
    "cat datei.txt",
    "cat a b | grep x",
    "cat > datei.txt <<'EOF'\npython -\ncat\nEOF",
    "cat <<'EOF' | head\nx\nEOF",
    "cat < eingabe.txt",
    "echo x | cat",
    "git log --oneline -3",
    "grep -rn 'python -' docs",
    "echo \"python - <<EOF\"",
    "ls 2>&1 && echo ok &",
    "",
])
def test_harmlos(befehl):
    assert grund(befehl) is None


def _hook(befehl: str, tool: str = "Bash") -> subprocess.CompletedProcess:
    eingabe = json.dumps({"tool_name": tool, "tool_input": {"command": befehl}})
    return subprocess.run([sys.executable, "-m", "werkzeuge.stdin_sperre"], input=eingabe.encode("utf-8"),
                          capture_output=True, timeout=30)


def test_hook_lehnt_ab_mit_weg():
    lauf = _hook("python - <<'EOF'\nprint('ä')\nEOF")
    assert lauf.returncode == 0
    aus = json.loads(lauf.stdout)["hookSpecificOutput"]
    assert aus["hookEventName"] == "PreToolUse" and aus["permissionDecision"] == "deny"
    assert "Write-Tool" in aus["permissionDecisionReason"]


def test_hook_laesst_durch():
    lauf = _hook(".venv/Scripts/python.exe -m swki status a.yaml")
    assert lauf.returncode == 0 and lauf.stdout.strip() == b""


def test_hook_unlesbare_eingabe_laesst_durch():
    lauf = subprocess.run([sys.executable, "-m", "werkzeuge.stdin_sperre"], input=b"kein json",
                          capture_output=True, timeout=30)
    assert lauf.returncode == 0 and lauf.stdout.strip() == b""
