"""Probe-Aufnahme eines noch nicht freigegebenen Kaufteil-Eintrags (vor `swki freigeben`): baut und prüft wie
`swki kaufteil muster`, legt aber nur im Arbeitsordner ab (`<arbeitsordner>/KAUFTEILE/vorpruefung/<eintrag>/`), nie in
der kaufteilbibliothek. Findet Fehler in Kennmaßen und Einbaureferenzen, bevor der Nutzer freigibt (AP 6.8, UEBERGABE §9).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.kaufteil_vorpruefung <swki/wissen/kaufteile/…/<nr>.yaml> [--bilder]
"""

import argparse
import json
import sys
from pathlib import Path

from swki.kaufteile import aufnahme
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.quelle import quellordner
from swki.konfig import lade_rechner


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("eintrag", type=Path)
    a.add_argument("--bilder", action="store_true", help="Screenshots mit erzeugen")
    args = a.parse_args()
    spec = lade_eintrag(args.eintrag)
    r = lade_rechner()
    original = quellordner(r, spec["hersteller"]) / spec["original"]["datei"]
    ordner = r.arbeitsordner / "KAUFTEILE" / "vorpruefung" / args.eintrag.stem
    erg = aufnahme.baue_und_pruefe(spec, original, ordner, mit_bildern=args.bilder)
    (ordner / "ergebnis.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("bestanden", erg.get("bestanden"), "fehler", erg.get("fehler"))
    for m in erg.get("maengel", []):
        print("MANGEL", json.dumps(m, ensure_ascii=False, default=str)[:400])
    for p in erg.get("pruefungen", []):
        print("P", json.dumps(p, ensure_ascii=False, default=str)[:300])
    print("gewinde_modell", erg.get("gewinde_modell"), "privat", erg.get("kennzahlen", {}).get("privat_mb"))
    print("Ergebnis:", ordner / "ergebnis.json")
    return 0 if erg.get("bestanden") else 1


if __name__ == "__main__":
    sys.exit(main())
