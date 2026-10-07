"""Regressions-Suite: Referenzteile freigeben, bauen, prüfen – müssen bestehen (SolidWorks muss laufen).

Die Aufträge werden in ein temporäres Verzeichnis kopiert, damit Freigaben und Protokolle nicht im Repo landen.
"""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.kaufteile import quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.katalog import finde
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent
KAUFTEILE = {"motorhalter": ["Nanotec GPLE60-2S-32"]}  # Referenz → Kaufteile, deren Original im Quellordner liegen muss


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def bereite_vor(ordner: str) -> None:
    """Vorbereitung ohne SolidWorks: Referenzen mit Kaufteilen brauchen das Original des Herstellers im Quellordner der
    Kaufteil-Bibliothek – es liegt nicht im Git (Nutzerentscheidung 2026-10-06). Fehlt es, scheitert der Test hier mit
    KAUFTEIL_QUELLE_FEHLT samt Download-URL aus dem Eintrag; weicht es ab, mit KAUFTEIL_QUELLE_ABWEICHEND."""
    for schluessel in KAUFTEILE.get(ordner, []):
        quelle.original(lade_rechner(), lade_eintrag(finde(schluessel)))


@pytest.mark.parametrize(("ordner", "spec"), [
    ("buchse", "buchse.yaml"),
    ("formplatte", "formplatte_ds.yaml"),
    ("auswerferhalteplatte", "auswerferhalteplatte.yaml"),
    ("stehlager", "stehlager.yaml"),
    ("schlitten", "linearschlitten.yaml"),
    ("zahnstangentrieb", "zahnstange.yaml"),
    ("zahnstangentrieb", "ritzelwelle.yaml"),
    ("zahnstangentrieb", "antriebswelle.yaml"),
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
    ("motorhalter", "motorhalter.yaml"),
    ("zentrieraufnahme", "zentrieraufnahme.yaml"),
])
def test_referenz_besteht(capsys, tmp_path, ordner, spec):
    auftrag = tmp_path / f"REF-{ordner}"
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    bereite_vor(ordner)
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
        assert bericht["bestanden"] is True
        assert all(Path(p).stat().st_size > 0 for p in bericht["bilder"].values())
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / f"REF-{ordner}", ignore_errors=True)
