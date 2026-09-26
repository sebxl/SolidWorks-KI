"""SQLite-Index für die SolidWorks-API (Member, Enums, Hilfeseiten) mit FTS5-Volltextsuche."""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from swki.api.chm import Seite
from swki.api.typbib import EnumWert, Member

_SCHEMA = """
CREATE TABLE member(interface TEXT, name TEXT, art TEXT, parameter TEXT, seit INTEGER, text TEXT,
                    PRIMARY KEY (interface, name, art));
CREATE TABLE enum(enum TEXT, name TEXT, wert INTEGER, PRIMARY KEY (enum, name));
CREATE VIRTUAL TABLE suchindex USING fts5(schluessel, titel, text);
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
"""


@contextmanager
def _verbinde(db: Path):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()


def baue(db: Path, members: list[Member], enums: list[EnumWert], seiten: list[Seite], jahr: int) -> dict:
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    zu_seite = {(s.interface, s.member): s for s in seiten if s.interface and s.member}
    with _verbinde(db) as con:
        con.executescript(_SCHEMA)
        for m in members:
            s = zu_seite.get((m.interface, m.name))
            params = json.dumps([p.__dict__ for p in m.parameter], ensure_ascii=False)
            con.execute(
                "INSERT OR REPLACE INTO member VALUES (?,?,?,?,?,?)",
                (m.interface, m.name, m.art, params, s.seit if s else None, s.text if s else ""),
            )
        con.executemany("INSERT OR REPLACE INTO enum VALUES (?,?,?)", [(e.enum, e.name, e.wert) for e in enums])
        for s in seiten:
            schluessel = f"{s.interface}.{s.member}" if s.interface and s.member else (s.member or s.datei)
            con.execute("INSERT INTO suchindex VALUES (?,?,?)", (schluessel, s.titel, s.text))
        con.executemany(
            "INSERT INTO meta VALUES (?,?)", [("jahr", str(jahr)), ("erstellt", date.today().isoformat())]
        )
    return {"member": len(members), "enums": len(enums), "seiten": len(seiten)}


def methode(db: Path, qualifiziert: str) -> list[dict]:
    interface, _, name = qualifiziert.partition(".")
    with _verbinde(db) as con:
        zeilen = con.execute(
            "SELECT * FROM member WHERE interface=? AND name=? ORDER BY art", (interface, name)
        ).fetchall()
    ergebnis = []
    for z in zeilen:
        params = json.loads(z["parameter"])
        ergebnis.append({
            "interface": z["interface"], "name": z["name"], "art": z["art"], "parameter": params,
            "anzahl_parameter": len(params), "seit": z["seit"], "text": (z["text"] or "")[:4000],
        })
    return ergebnis


def enum(db: Path, name: str) -> list[dict]:
    with _verbinde(db) as con:
        zeilen = con.execute("SELECT name, wert FROM enum WHERE enum=? ORDER BY wert, name", (name,)).fetchall()
    return [{"name": z["name"], "wert": z["wert"]} for z in zeilen]


def _fts(anfrage: str, verbinder: str) -> str:
    woerter = re.findall(r"\w+", anfrage)
    return f" {verbinder} ".join(f'"{w}"' for w in woerter)


def suche(db: Path, anfrage: str, limit: int = 10) -> list[dict]:
    with _verbinde(db) as con:
        for verbinder in ("AND", "OR"):
            ausdruck = _fts(anfrage, verbinder)
            if not ausdruck:
                return []
            zeilen = con.execute(
                "SELECT schluessel, titel, snippet(suchindex, 2, '[', ']', ' … ', 20) AS auszug "
                "FROM suchindex WHERE suchindex MATCH ? ORDER BY bm25(suchindex) LIMIT ?",
                (ausdruck, limit),
            ).fetchall()
            if zeilen:
                return [dict(z) for z in zeilen]
    return []


def seit_je_member(db: Path) -> dict[str, int]:
    with _verbinde(db) as con:
        zeilen = con.execute(
            "SELECT name, MIN(seit) AS seit FROM member WHERE seit IS NOT NULL GROUP BY name"
        ).fetchall()
    return {z["name"]: z["seit"] for z in zeilen}


def meta(db: Path) -> dict:
    with _verbinde(db) as con:
        return {z["k"]: z["v"] for z in con.execute("SELECT k, v FROM meta")}
