"""Regelkatalog der Zeichnungsprüfung (Design §8.1)."""

import pytest

from swki.zeichnung.regeln import Regel, lade_regeln, regel

PRUEFUNGEN = (
    "vollstaendig", "ueberbestimmt", "toleranzen", "sammelangaben", "schriftfeld", "ansichten", "lesbarkeit",
    "gewinde", "drehteil",
)
PFLICHT_IDS = (
    "Z-VOLL-1", "Z-VOLL-2", "Z-UEB-1", "Z-TOL-1", "Z-TOL-2", "Z-TOL-3", "Z-TOL-4", "Z-TOL-5", "Z-TOL-6",
    "Z-SAM-1", "Z-SAM-2", "Z-SAM-3", "Z-SAM-4", "Z-SAM-5", "Z-SAM-6", "Z-SAM-7", "Z-SCH-1", "Z-SCH-2", "Z-SCH-3",
    "Z-ANS-1", "Z-ANS-2", "Z-ANS-3", "Z-LES-1", "Z-GEW-1", "Z-DRE-1",
)


def test_regeln_vollstaendig():
    regeln = lade_regeln()
    ids = [r.id for r in regeln]
    assert len(ids) == len(set(ids))
    assert set(PFLICHT_IDS) <= set(ids)
    assert {r.pruefung for r in regeln} >= set(PRUEFUNGEN)
    for p in PRUEFUNGEN:
        assert any(r.pruefung == p for r in regeln), p
    for r in regeln:
        assert isinstance(r, Regel)
        assert r.pruefung in PRUEFUNGEN, r.id
        assert r.quelle.strip() and r.text.strip(), r.id
        assert r.art in ("hart", "hinweis"), r.id
        assert r.beleg in ("A", "B", "C"), r.id
    assert regel(regeln, "Z-LES-1").art == "hinweis"


def test_regel_unbekannt():
    with pytest.raises(KeyError, match="Z-XX-9"):
        regel(lade_regeln(), "Z-XX-9")
