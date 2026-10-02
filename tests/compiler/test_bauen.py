"""swki bauen ohne SolidWorks: Laufnummer und Sperre belegter Läufe (verbinde wird nie erreicht bzw. abgefangen)."""

from pathlib import Path

import pytest

from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import SwkiFehler
from swki.compiler import bauen as bauen_modul
from swki.konfig import Rechner


class _KeinSolidWorks(Exception):
    pass


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "auftraege" / "A" / "platte.yaml"
    spec_pfad.parent.mkdir(parents=True)
    spec_pfad.write_text("name: platte\n", encoding="utf-8")
    aufrufe = {"verbinde": 0, "protokoll_lauf": None}

    def verbinde(jahr):
        aufrufe["verbinde"] += 1
        raise _KeinSolidWorks

    def protokoll(auftrag, spec_name, lauf, sw_jahr):
        aufrufe["protokoll_lauf"] = lauf
        return object()

    monkeypatch.setattr(bauen_modul, "lade_spec", lambda pfad: {"name": "platte"})
    monkeypatch.setattr(bauen_modul, "pruefe_freigabe", lambda pfad, spec: None)
    monkeypatch.setattr(bauen_modul, "lade_rechner", lambda: r)
    monkeypatch.setattr(bauen_modul, "lade_standard", lambda: {"namensschema": {"datei": "{auftrag}_{name}"}})
    monkeypatch.setattr(bauen_modul, "verbinde", verbinde)
    monkeypatch.setattr(bauen_modul, "Protokoll", protokoll)
    return r, spec_pfad, aufrufe


def test_belegter_lauf_wird_vor_solidworks_verweigert(umgebung):
    r, spec_pfad, aufrufe = umgebung
    lauf_ordner(r, "A", 2).mkdir(parents=True)
    with pytest.raises(SwkiFehler, match="Lauf 2 von A existiert schon"):
        bauen_modul.bauen(spec_pfad, lauf=2)
    assert aufrufe["verbinde"] == 0


def test_lauf_mit_nur_pruefdatei_ist_belegt(umgebung):
    r, spec_pfad, aufrufe = umgebung
    datei = lauf_datei(spec_pfad, 1, "pruefbericht")
    datei.parent.mkdir(parents=True)
    datei.write_text("{}", encoding="utf-8")
    with pytest.raises(SwkiFehler, match="Lauf 1 von A existiert schon"):
        bauen_modul.bauen(spec_pfad, lauf=1)
    assert aufrufe["verbinde"] == 0


def test_automatische_laufnummer_ueberspringt_alte_pruefdateien(umgebung):
    """Arbeitsordner aufgeräumt, aber Prüfdateien von Lauf 1 liegen noch im Auftragsordner: es wird Lauf 2 gebaut."""
    r, spec_pfad, aufrufe = umgebung
    for art in ("protokoll", "pruefbericht", "pruefer"):
        datei = lauf_datei(spec_pfad, 1, art)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text("{}", encoding="utf-8")
    with pytest.raises(_KeinSolidWorks):
        bauen_modul.bauen(spec_pfad)
    assert aufrufe["protokoll_lauf"] == 2
