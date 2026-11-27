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


def _regel(**ueber) -> Regel:
    werte = dict(id="Z-T-1", pruefung="toleranzen", text="t", quelle="Nutzer 16.11.2026, Design §2", beleg="B",
                 art="hart", herkunft="norm")
    return Regel(**{**werte, **ueber})


def test_regeln_vollstaendig():
    regeln = lade_regeln()
    ids = [r.id for r in regeln]
    assert len(ids) == len(set(ids))
    assert set(PFLICHT_IDS) <= set(ids)
    for p in PRUEFUNGEN:
        assert any(r.pruefung == p for r in regeln), p
    for r in regeln:
        assert isinstance(r, Regel)
        assert r.quelle.strip() and r.text.strip(), r.id
    assert regel(regeln, "Z-LES-1").art == "hinweis"


def test_ausgelieferte_regeln_erfuellen_invariante():
    for r in lade_regeln():
        assert r.art != "hart" or r.beleg in ("A", "B") or r.herkunft == "projekt", r.id
        if r.herkunft == "projekt":
            assert "Nutzer" in r.quelle or "Design" in r.quelle, r.id
        assert "Hausregel" not in r.quelle, r.id


def test_regel_unbekannt():
    with pytest.raises(KeyError, match="Z-XX-9"):
        regel(lade_regeln(), "Z-XX-9")


@pytest.mark.parametrize("feld,wert", [
    ("pruefung", "unbekannt"), ("beleg", "D"), ("art", "weich"), ("herkunft", "hausregel"),
])
def test_ungueltiger_wert(feld, wert):
    with pytest.raises(ValueError, match="Z-T-1"):
        _regel(**{feld: wert})


def test_invariante_hart_ohne_beleg():
    with pytest.raises(ValueError, match="Z-T-1"):
        _regel(beleg="C", herkunft="norm", art="hart")
    _regel(beleg="C", herkunft="projekt", art="hart")
    _regel(beleg="C", herkunft="norm", art="hinweis")


def test_projektregel_braucht_nutzer_oder_design():
    with pytest.raises(ValueError, match="Z-T-1"):
        _regel(herkunft="projekt", quelle="Hausregel swki")


def test_leere_datei(tmp_path):
    p = tmp_path / "leer.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="leer"):
        lade_regeln(p)
