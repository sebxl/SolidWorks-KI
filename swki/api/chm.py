"""Entpackt die lokale SolidWorks-API-Hilfe (CHM) und liest die HTML-Seiten."""

import re
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

CHM_DATEIEN = ["sldworksapi.chm", "swconst.chm", "sldworksapiprogguide.chm", "toolboxapi.chm"]
_TITEL_RE = re.compile(
    r"^(?P<member>[\w]+)\s+(?P<art>Method|Property|Event|Enumeration|Interface)(?:\s+\((?P<iface>\w+)\))?"
)
_SEIT_RE = re.compile(r"SOLIDWORKS\s+(\d{4})", re.IGNORECASE)


@dataclass
class Seite:
    datei: str
    titel: str
    interface: str | None
    member: str | None
    art: str | None
    seit: int | None
    text: str


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titel, self.teile, self._in_titel, self._ueberspringen = "", [], False, 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_titel = True
        elif tag in ("script", "style"):
            self._ueberspringen += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_titel = False
        elif tag in ("script", "style") and self._ueberspringen:
            self._ueberspringen -= 1

    def handle_data(self, data):
        if self._in_titel:
            self.titel += data
        elif not self._ueberspringen and data.strip():
            self.teile.append(data.strip())


def _dekodiere(roh: bytes) -> str:
    try:
        return roh.decode("utf-8")
    except UnicodeDecodeError:
        return roh.decode("cp1252", errors="replace")


def lese_seite(pfad: Path) -> Seite:
    p = _Text()
    p.feed(_dekodiere(pfad.read_bytes()))
    titel = " ".join(p.titel.split())
    text = " ".join(p.teile)
    m = _TITEL_RE.match(titel)
    seit = None
    pos = text.find("Availability")
    if pos >= 0 and (s := _SEIT_RE.search(text, pos, pos + 300)):
        seit = int(s.group(1))
    return Seite(
        datei=str(pfad),
        titel=titel,
        interface=m.group("iface") if m else None,
        member=m.group("member") if m else None,
        art=m.group("art") if m else None,
        seit=seit,
        text=text,
    )


def lese_ordner(ordner: Path) -> list[Seite]:
    return [lese_seite(p) for p in sorted(ordner.rglob("*")) if p.suffix.lower() in (".htm", ".html")]


def entpacke(chm: Path, ziel: Path, neu: bool = False) -> Path:
    if ziel.exists() and any(ziel.rglob("*.htm*")) and not neu:
        return ziel
    ziel.mkdir(parents=True, exist_ok=True)
    subprocess.run(["hh.exe", "-decompile", str(ziel), str(chm)], check=False, timeout=900)
    if not any(ziel.rglob("*.htm*")):
        raise RuntimeError(f"Entpacken fehlgeschlagen: {chm}")
    return ziel
