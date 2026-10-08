from pathlib import Path

import pytest

from swki.konfig import KonfigFehler, Rechner
from swki.rechner import behalte_handeintraege, erkenne, sw_jahre


class FakeRegistry:
    def __init__(self, schluessel: dict[str, list[str]], werte: dict[str, dict[str, str]]):
        self.schluessel = schluessel
        self.werte = {k.lower(): {n.lower(): v for n, v in w.items()} for k, w in werte.items()}

    def unterschluessel(self, pfad):
        return self.schluessel.get(pfad, [])

    def wert(self, pfad, name):
        return self.werte.get(pfad.lower(), {}).get(name.lower())


def _reg(tmp_path, teil="", baugruppe=""):
    vorlagen = tmp_path / "templates"
    vorlagen.mkdir()
    (vorlagen / "Teil.prtdot").write_text("x")
    (vorlagen / "Baugruppe.asmdot").write_text("x")
    return FakeRegistry(
        {r"HKLM\SOFTWARE\SolidWorks": ["AddIns", "SOLIDWORKS 2025", "SOLIDWORKS 2026", "Licenses"]},
        {
            r"HKLM\SOFTWARE\SolidWorks\SOLIDWORKS 2025\Setup": {"SolidWorks Folder": "C:\\SW25\\"},
            r"HKLM\SOFTWARE\SolidWorks\SOLIDWORKS 2026\Setup": {"SolidWorks Folder": "C:\\SW26\\"},
            r"HKCU\Software\SolidWorks\SOLIDWORKS 2025\Document Templates": {
                "Default Part template": teil, "Default Assembly Template": baugruppe,
            },
            r"HKCU\Software\SolidWorks\SOLIDWORKS 2025\ExtReferences": {
                "Document Template Folders": str(vorlagen),
                "Material Database Folders": r"C:\Mat\Eigene;C:\Mat\Zweite",
            },
        },
    ), vorlagen


def test_sw_jahre(tmp_path):
    reg, _ = _reg(tmp_path)
    assert sw_jahre(reg) == [2025, 2026]


def test_erkenne_jahr_und_vorlagen(tmp_path, swki_home):
    reg, vorlagen = _reg(tmp_path, teil=str(tmp_path / "templates" / "Teil.prtdot"))
    r = erkenne(reg, jahr=2025)
    assert r.sw_jahr == 2025
    assert str(r.installationsordner) == r"C:\SW25"
    assert r.vorlage_teil == vorlagen / "Teil.prtdot"
    assert r.vorlage_baugruppe == vorlagen / "Baugruppe.asmdot"   # Rückfall: Suche im Vorlagenordner
    assert str(r.materialdatenbank) == r"C:\Mat\Eigene"
    assert r.arbeitsordner == swki_home / "arbeit"
    assert r.normteilbibliothek == r.arbeitsordner.parent / "normteile" == swki_home / "normteile"
    assert r.kaufteilbibliothek == swki_home / "kaufteile"


def test_ohne_jahr_neuestes(tmp_path, swki_home):
    reg, _ = _reg(tmp_path)
    reg.werte[r"hkcu\software\solidworks\solidworks 2026\extreferences"] = {
        "document template folders": str(tmp_path / "templates")
    }
    assert erkenne(reg).sw_jahr == 2026


def test_unbekanntes_jahr(tmp_path):
    reg, _ = _reg(tmp_path)
    with pytest.raises(KonfigFehler, match="2019"):
        erkenne(reg, jahr=2019)


def test_kein_solidworks():
    with pytest.raises(KonfigFehler, match="Kein SOLIDWORKS"):
        erkenne(FakeRegistry({}, {}))


def _rechner(jahr, **mehr):
    return Rechner(sw_jahr=jahr, installationsordner=Path(f"C:/SW{jahr}"), vorlage_teil=Path("t.prtdot"),
                   vorlage_baugruppe=None, materialdatenbank=None, arbeitsordner=Path("arbeit"), **mehr)


def test_init_neu_behaelt_handeintraege():
    # "rechner init --neu" erkennt nur die Registry-Werte; blender und dateien pflegt man von Hand.
    alt = _rechner(2025, blender=Path("C:/Blender/blender.exe"), dateien={"szene": Path("C:/x/szene.blend")})
    neu = behalte_handeintraege(_rechner(2026), alt)
    assert neu.sw_jahr == 2026
    assert neu.blender == Path("C:/Blender/blender.exe")
    assert neu.dateien == {"szene": Path("C:/x/szene.blend")}


def test_init_neu_ohne_alte_datei():
    assert behalte_handeintraege(_rechner(2026), None) == _rechner(2026)
