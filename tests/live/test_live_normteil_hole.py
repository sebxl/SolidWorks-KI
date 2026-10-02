"""Live: swki normteil hole baut, prüft und legt ab; zweiter Abruf ist ein Cache-Treffer (Bibliothek in tmp_path)."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from swki.konfig import lade_rechner
from swki.normteile import befehle

pytestmark = pytest.mark.sw


@pytest.mark.parametrize(("norm", "groesse"), [("ISO 4762", "M8x30"), ("ISO 4032", "M8"), ("ISO 7089", "M8"),
                                               ("ISO 8734", "8x30")])
def test_hole_baut_und_trifft_den_cache(norm, groesse, tmp_path, monkeypatch):
    r = replace(lade_rechner(), normteilbibliothek=tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    erst = befehle.hole(norm, groesse)
    try:
        assert erst["gebaut"] is True and Path(erst["pfad"]).is_file()
        zweit = befehle.hole(norm, groesse)
        assert zweit["gebaut"] is False and zweit["pfad"] == erst["pfad"]
    finally:
        shutil.rmtree(erst["lauf"], ignore_errors=True)
