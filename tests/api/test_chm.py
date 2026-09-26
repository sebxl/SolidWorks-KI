import subprocess
from pathlib import Path

import swki.api.chm as chm_modul
from swki.api.chm import entpacke, lese_ordner, lese_seite

SEITE = """<html><head><title>BeispielMethode Method (IBeispielManager)</title>
<script>var x = 1;</script></head><body>
<h1>BeispielMethode Method (IBeispielManager)</h1>
<p>Erzeugt ein Beispiel-Feature.</p>
<h4>Availability</h4><p>SOLIDWORKS 2014 FCS, Revision Number 22.0</p>
</body></html>"""

ENUM = """<html><head><title>swBeispiel_e Enumeration</title></head><body>
<p>Werte für Beispiele.</p></body></html>"""


def test_methode(tmp_path):
    p = tmp_path / "a.htm"
    p.write_text(SEITE, encoding="utf-8")
    s = lese_seite(p)
    assert (s.member, s.art, s.interface, s.seit) == ("BeispielMethode", "Method", "IBeispielManager", 2014)
    assert "Erzeugt ein Beispiel-Feature." in s.text
    assert "var x" not in s.text


def test_enum_ohne_interface(tmp_path):
    p = tmp_path / "e.html"
    p.write_text(ENUM, encoding="utf-8")
    s = lese_seite(p)
    assert (s.member, s.art, s.interface, s.seit) == ("swBeispiel_e", "Enumeration", None, None)


def test_cp1252(tmp_path):
    p = tmp_path / "c.htm"
    p.write_bytes(SEITE.replace("Erzeugt", "Größe").encode("cp1252"))
    assert "Größe" in lese_seite(p).text


def test_utf8_bom(tmp_path):
    p = tmp_path / "d.htm"
    p.write_bytes(SEITE.encode("utf-8-sig"))
    s = lese_seite(p)
    assert s.titel == "BeispielMethode Method (IBeispielManager)"
    assert not s.text.startswith("﻿")
    assert "﻿" not in s.text


def test_ordner_rekursiv(tmp_path):
    (tmp_path / "unter").mkdir()
    (tmp_path / "unter" / "a.htm").write_text(SEITE, encoding="utf-8")
    (tmp_path / "b.html").write_text(ENUM, encoding="utf-8")
    (tmp_path / "bild.gif").write_bytes(b"GIF")
    assert len(lese_ordner(tmp_path)) == 2


def test_entpacke_ruft_hh_ohne_leerzeichenpfade_auf(tmp_path, monkeypatch):
    quelle = tmp_path / "eingabe.chm"
    quelle.write_bytes(b"tut-nichts-zur-sache")
    ziel = tmp_path / "ziel mit leerzeichen"

    aufrufe = []

    def fake_run(args, cwd=None, check=False, timeout=None):
        aufrufe.append((args, cwd))
        (Path(cwd) / "seite.htm").write_text("<html><head><title>x</title></head></html>", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(chm_modul.subprocess, "run", fake_run)

    ergebnis = entpacke(quelle, ziel)

    assert ergebnis == ziel
    assert len(aufrufe) == 1
    args, cwd = aufrufe[0]
    assert args == ["hh.exe", "-decompile", ".", "quelle.chm"]
    assert cwd == ziel
    assert not (ziel / "quelle.chm").exists()
