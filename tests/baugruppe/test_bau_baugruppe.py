import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import bau
from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.freigabe import freigeben_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.cli import SwkiFehler, main
from swki.compiler.protokoll import Protokoll
from swki.konfig import Rechner
from tests.baugruppe.beispiel import schreibe


class _KeinSolidWorks(Exception):
    pass


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), Path("C:/b.asmdot"), None, tmp_path / "arbeit")
    pfad = schreibe(tmp_path / "A")
    aufrufe = {"verbinde": 0}

    def verbinde(jahr):
        aufrufe["verbinde"] += 1
        raise _KeinSolidWorks

    monkeypatch.setattr(bau, "lade_rechner", lambda: r)
    monkeypatch.setattr(bau, "verbinde", verbinde)
    return r, pfad, aufrufe


def test_ohne_freigabe(umgebung):
    _, pfad, aufrufe = umgebung
    with pytest.raises(SwkiFehler) as e:
        bau.bauen(pfad)
    assert e.value.daten["code"] == "FREIGABE_FEHLT" and aufrufe["verbinde"] == 0


def test_ohne_baugruppenvorlage(umgebung, monkeypatch):
    r, pfad, aufrufe = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad))
    monkeypatch.setattr(bau, "lade_rechner", lambda: replace(r, vorlage_baugruppe=None))
    with pytest.raises(SwkiFehler, match="vorlage_baugruppe"):
        bau.bauen(pfad)
    assert aufrufe["verbinde"] == 0


def test_manuelle_aenderung_vor_solidworks(umgebung):
    r, pfad, aufrufe = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad))
    ordner = lauf_ordner(r, "A", 1)
    ordner.mkdir(parents=True)
    (ordner / "A_Probe.sldasm").write_bytes(b"gebaut")
    from swki.aenderungen import pruefsummen

    protokoll = lauf_datei(pfad, 1, "protokoll")
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    protokoll.write_text(json.dumps({"status": "ok", "sha256": pruefsummen(ordner, [ordner / "A_Probe.sldasm"])}),
                         encoding="utf-8")
    (ordner / "A_Probe.sldasm").write_bytes(b"geaendert")
    with pytest.raises(SwkiFehler) as e:
        bau.bauen(pfad)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and aufrufe["verbinde"] == 0
    with pytest.raises(_KeinSolidWorks):
        bau.bauen(pfad, verwerfen=True)


def test_weiche_in_swki_bauen(capsys, umgebung, monkeypatch):
    _, pfad, _ = umgebung
    monkeypatch.setattr(bau, "bauen", lambda p, lauf, verwerfen: {"art": "baugruppe", "lauf": lauf, "verwerfen": verwerfen})
    assert main(["bauen", str(pfad), "--lauf", "3", "--verwerfen"]) == 0
    assert json.loads(capsys.readouterr().out) == {"art": "baugruppe", "lauf": 3, "verwerfen": True}


def _baulauf(pfad, tmp_path):
    bg = lade_baugruppe(pfad)
    standard = {"toleranzen": {"anker_mm": 0.01}}
    return bau.Baulauf(app=None, bg=bg, auftrag="A", ordner=tmp_path / "lauf", standard=standard,
                       protokoll=Protokoll("A", pfad.name, 1, 2025)), bg


def test_gesetzt_wird_ueber_alle_verknuepfungen_durchgereicht(umgebung, tmp_path, monkeypatch):
    _, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    alle = verknuepfungen(bg.spec, bg.quellen)
    erhalten = []

    def verknuepfe(asm, v, a, b_, parameter, gesetzt=None):
        erhalten.append(gesetzt)
        return SimpleNamespace(Name=v.id)

    monkeypatch.setattr(bau, "_entitaet", lambda b_, seite: object())
    monkeypatch.setattr(bau.sw_baugruppe, "verknuepfe", verknuepfe)
    assert bau._verknuepfe(b, alle) is None
    assert len(erhalten) == len(alle) > 1
    assert all(g is b.gesetzt for g in erhalten)


def test_komponenten_datei_ist_die_von_swki_gespeicherte(umgebung, tmp_path, monkeypatch):
    _, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    b.ordner.mkdir()
    for datei, name in (("platte.yaml", "A_Platte.sldprt"), ("deckel.yaml", "A_Deckel.sldprt")):
        b.dateien[f"teil:{datei}"] = b.ordner / name
    for q in bg.quellen.values():
        if q.art == "normteil":
            b.dateien[f"normteil:{q.schluessel}"] = b.ordner / f"{q.schluessel}.sldprt"
    for q in bg.quellen.values():  # GetPathName liefert bei SolidWorks eine andere Schreibweise (Spike S12)
        b.kontexte[q.schluessel_dokument] = SimpleNamespace(model=SimpleNamespace(GetPathName="C:/x/Q.SLDPRT"))
    zaehler = iter(range(1, 100))
    monkeypatch.setattr(bau.sw, "teilebox_mm", lambda model: [0] * 6)
    monkeypatch.setattr(bau.sw_baugruppe, "fuege_ein",
                        lambda app, asm, p, box: SimpleNamespace(Name2=f"K-{next(zaehler)}"))
    monkeypatch.setattr(bau.sw_baugruppe, "fixiere", lambda asm, komp: None)
    assert bau._fuege_ein(b, instanzen(bg.spec, bg.quellen)) is None
    datei = {k["id"]: k["datei"] for k in b.protokoll.komponenten}
    assert datei["platte"] == "A_Platte.sldprt" and datei["deckel"] == "A_Deckel.sldprt"
    assert datei["schraube.1"] == datei["schraube.2"] == "ISO4762_M8x16_8_8.sldprt"
    assert datei["stift"] == "ISO8734_8x16_St.sldprt" and set(b.komponenten) == set(datei)
