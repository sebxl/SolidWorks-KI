"""Live: swki kaufteil hole am freigegebenen und geprüften Eintrag Nanotec GPLE60-2S-32 (Spec 3c §5.3) mit eigenem
Cache; der zweite Aufruf ist ein Cache-Treffer. Das Original ist eine Herstellerdatei und liegt nur im Quellordner der
Kaufteil-Bibliothek dieses Rechners (nicht im Git); fehlt es, scheitert der Test mit KAUFTEIL_QUELLE_FEHLT und der
Download-URL aus dem Eintrag (wie die Regression, Nutzerentscheidung 2026-10-06)."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from swki.kaufteile import befehle, quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.katalog import finde
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
SCHLUESSEL = "Nanotec GPLE60-2S-32"
D1_M5 = 4.134  # Kerndurchmesser D1 nach ISO 724, so modelliert Nanotec die Flanschgewinde (Diagnose lauf-1)


def test_hole_baut_und_trifft_den_cache(tmp_path, monkeypatch):
    echt = lade_rechner()
    eintrag = lade_eintrag(finde(SCHLUESSEL))
    original = quelle.original(echt, eintrag)  # KAUFTEIL_QUELLE_FEHLT mit URL, wenn die Herstellerdatei fehlt
    r = replace(echt, kaufteilbibliothek=tmp_path / "kauf")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    quelle.uebernimm(r, original, "Nanotec", "GPLE60-2S-32", eintrag)
    erst = befehle.hole(SCHLUESSEL)
    modell = erst["gewinde_modell"]["flansch"]
    assert erst["gebaut"] is True and modell["modell"] == "kernloch" and abs(modell["durchmesser"] - D1_M5) <= 0.0005
    cache_eintrag = json.loads(Path(erst["pfad"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert cache_eintrag["bestanden"] is True and cache_eintrag["kennzahlen"]["interconnect"] == []
    assert cache_eintrag["gewinde_modell"] == erst["gewinde_modell"]
    zweit = befehle.hole(SCHLUESSEL)
    assert zweit["gebaut"] is False and zweit["pfad"] == erst["pfad"] and zweit["gewinde_modell"] == erst["gewinde_modell"]
