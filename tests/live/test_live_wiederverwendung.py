"""Live: unveränderte Eigenteile wiederverwenden (BTP Umbau 3, Recherche O5) an den Referenz-Baugruppen.

Je Referenz: Durchlauf 1 baut alle Eigenteile, Durchlauf 2 übernimmt alle und der Prüfbericht ist Wert für Wert gleich;
eine von Hand geänderte Datei löst weiter MANUELL_GEAENDERT aus (mit --verwerfen kommt das Teil aus dem unveränderten
Lauf davor); nach einer Parameteränderung wird genau dieses Teil neu gebaut. Jeder Durchlauf mit --neustart (frisches
SolidWorks vor Bauen und Prüfen). Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.live_frisch
tests\\live\\test_live_wiederverwendung.py --zeit 1200"""

import copy
import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import main
from swki.durchlauf import durchlauf
from swki.konfig import lade_rechner
from tests.referenz.test_referenzen import REFERENZEN, bereite_vor

pytestmark = pytest.mark.sw


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _vergleichbar(bericht: dict, lauf: int):
    """Prüfbericht ohne Laufnummer, Pfade und Bilder; Listen aus Texten sortiert (Reihenfolge von `bewegt` variiert),
    Zahlen auf 1e-9 gerundet."""
    def norm(x):
        if isinstance(x, dict):
            return {k: norm(v) for k, v in x.items() if k not in ("lauf", "datei", "bilder", "bild")}
        if isinstance(x, list):
            return sorted(x) if x and all(isinstance(e, str) for e in x) else [norm(e) for e in x]
        if isinstance(x, str):
            return x.replace(f"lauf-{lauf}", "lauf-N")
        if isinstance(x, float):
            return round(x, 9)
        return x
    return norm(copy.deepcopy(bericht))


@pytest.mark.parametrize(("ordner", "spec", "teil", "parameter", "wert"), [
    ("stehlager", "stehlager.yaml", "grundplatte.yaml", "L", 210),
    ("schlitten", "linearschlitten.yaml", "hebel.yaml", "L", 62),
    ("zahnstangentrieb", "zahnstangentrieb.yaml", "grundplatte.yaml", "L", 310),
    ("motorhalter", "motorhalter.yaml", "grundplatte.yaml", "L", 170),
])
def test_zweiter_bau_uebernimmt_alle_eigenteile(capsys, tmp_path, ordner, spec, teil, parameter, wert):
    auftrag = tmp_path / f"REF-WV-{ordner}"
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    bereite_vor(ordner)
    bg = yaml.safe_load(spec_pfad.read_text(encoding="utf-8"))
    teile = sorted({k["quelle"]["teil"] for k in bg["komponenten"] if "teil" in k["quelle"]})
    r = lade_rechner()
    try:
        e1 = durchlauf(spec_pfad, freigeben=True, neustart=True)
        assert e1["schritt"] == "fertig" and e1["pruefung"]["bestanden"], e1
        assert sorted(e1["teile_gebaut"]) == teile and e1["teile_wiederverwendet"] == 0

        e2 = durchlauf(spec_pfad, neustart=True)
        assert e2["schritt"] == "fertig" and e2["pruefung"]["bestanden"], e2
        assert e2["teile_gebaut"] == [] and e2["teile_wiederverwendet"] == len(teile)
        b1, b2 = (json.loads(lauf_datei(spec_pfad, e["lauf"], "pruefbericht").read_text(encoding="utf-8"))
                  for e in (e1, e2))
        assert _vergleichbar(b1, e1["lauf"]) == _vergleichbar(b2, e2["lauf"])

        # Von Hand geänderte Datei: MANUELL_GEAENDERT wie bisher; --verwerfen holt das Teil aus Lauf 1
        protokoll = json.loads(lauf_datei(spec_pfad, e2["lauf"], "protokoll").read_text(encoding="utf-8"))
        datei = lauf_ordner(r, auftrag.name, e2["lauf"]) / Path(protokoll["dateien"][f"teil:{teil}"]).name
        datei.write_bytes(datei.read_bytes() + b"von Hand")
        code, out = _lauf(capsys, "bauen", str(spec_pfad))
        assert code != 0 and out["code"] == "MANUELL_GEAENDERT", out
        code, b3 = _lauf(capsys, "bauen", str(spec_pfad), "--verwerfen")
        assert code == 0 and b3["teile_gebaut"] == [], b3
        p3 = json.loads(lauf_datei(spec_pfad, b3["lauf"], "protokoll").read_text(encoding="utf-8"))
        assert p3["teile"][teil]["wiederverwendet"]["lauf"] == e1["lauf"]

        # Parameter geändert → genau dieses Teil neu (zuerst gebaut)
        teil_pfad = auftrag / teil
        t = yaml.safe_load(teil_pfad.read_text(encoding="utf-8"))
        t["parameter"][parameter] = wert
        teil_pfad.write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False), encoding="utf-8")
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, b4 = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, b4
        assert b4["teile_gebaut"] == [teil] and sorted(b4["teile_wiederverwendet"]) == [x for x in teile if x != teil]
    finally:
        shutil.rmtree(r.arbeitsordner / auftrag.name, ignore_errors=True)
