"""Listet alle Tool-Namen von solidworks-mcp (Mock-Modus, ohne SolidWorks).

Aufruf:
  & "$env:USERPROFILE\\.swki\\SolidworksMCP-python\\.venv\\Scripts\\python.exe" setup\\mcp_tools_auflisten.py
Schreibt config/mcp-tools-alle.json.
"""

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJEKT = Path(__file__).resolve().parent.parent
MCP_DIR = Path(os.environ["USERPROFILE"]) / ".swki" / "SolidworksMCP-python"


async def liste() -> list[str]:
    params = StdioServerParameters(
        command=str(MCP_DIR / ".venv" / "Scripts" / "python.exe"),
        args=[str(MCP_DIR / "src" / "utils" / "start_local_server_claude.py")],  # ohne --real = Mock
        env={**os.environ, "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "GH_TOKEN": ""},
    )
    async with stdio_client(params) as (lesen, schreiben):
        async with ClientSession(lesen, schreiben) as sitzung:
            await sitzung.initialize()
            antwort = await sitzung.list_tools()
            return sorted(t.name for t in antwort.tools)


if __name__ == "__main__":
    namen = asyncio.run(liste())
    ziel = PROJEKT / "config" / "mcp-tools-alle.json"
    ziel.write_text(json.dumps(namen, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"anzahl": len(namen), "datei": str(ziel)}))
