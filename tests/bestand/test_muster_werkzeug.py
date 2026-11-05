"""Muster je SolidWorks-Jahr (`werkzeuge.bestand_muster`): SolidWorks öffnet keine neueren Dateien und stuft ältere hoch, die Dateien im
Git gelten also nur für ihr Jahr."""

import copy
import json
from pathlib import Path

import pytest

from swki.konfig import PROJEKT, Rechner
from werkzeuge import bestand_muster as werkzeug
from werkzeuge.bestand_muster import (DATEIEN, HUB_DATEIEN, HUB_KOMPONENTEN, HUB_LAGE, HUB_STATUS, HUB_VERKNUEPFUNGEN, KONFIG_OHNE,
                                      SOLL_VOLUMEN_HUB, MusterFehlt, abweichungen, abweichungen_hub, hubeinheit_ordner, muster_ordner,
                                      uebernimm_hubeinheit, uebernimm_muster)

REFERENZ = PROJEKT / "tests" / "referenz" / "bestand"
JAHR_IM_GIT = json.loads((REFERENZ / "bestand.json").read_text(encoding="utf-8"))["sw_jahr"]


def rechner(tmp_path, jahr: int) -> Rechner:
    return Rechner(jahr, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path)


def gut() -> dict:
    return {"Standard": {"neuaufbau": True, "whats_wrong": 0, "volumen": 106239.38},
            "Variante B": {"neuaufbau": True, "whats_wrong": 0, "volumen": 106439.38},
            "oeffnen_baugruppe": {"fehler": 0, "warnungen": 0},
            "baugruppe": {"neuaufbau": True, "whats_wrong": 0, "komponenten": [("Lagerdeckel-1", "a"), ("gm42-10-1", "b")]}}


def test_jahr_der_dateien_im_git_nimmt_das_repo(tmp_path):
    assert muster_ordner(rechner(tmp_path, JAHR_IM_GIT)) == REFERENZ / "muster"


@pytest.mark.parametrize("jahr", [JAHR_IM_GIT - 1, JAHR_IM_GIT + 1])
def test_anderes_jahr_ohne_erzeugte_dateien_nennt_das_werkzeug(tmp_path, jahr):
    with pytest.raises(MusterFehlt, match="werkzeuge.bestand_muster"):
        muster_ordner(rechner(tmp_path, jahr))


def test_anderes_jahr_nimmt_die_erzeugten_dateien(tmp_path):
    jahr = JAHR_IM_GIT + 1
    ordner = tmp_path / "BESTAND-MUSTER" / str(jahr)
    ordner.mkdir(parents=True)
    for name in DATEIEN:
        (ordner / name).write_bytes(b"x")
    assert muster_ordner(rechner(tmp_path, jahr)) == ordner


def test_unvollstaendig_erzeugt_zaehlt_als_fehlend(tmp_path):
    jahr = JAHR_IM_GIT + 1
    ordner = tmp_path / "BESTAND-MUSTER" / str(jahr)
    ordner.mkdir(parents=True)
    (ordner / DATEIEN[0]).write_bytes(b"x")
    with pytest.raises(MusterFehlt, match=DATEIEN[1]):
        muster_ordner(rechner(tmp_path, jahr))


def test_ein_gutes_muster_hat_keine_abweichung():
    assert abweichungen(gut()) == []


@pytest.mark.parametrize("schluessel, wert, nennt", [
    ("Standard", {"neuaufbau": True, "whats_wrong": 0, "volumen": 106239.5}, "Standard"),
    ("Variante B", {"neuaufbau": False, "whats_wrong": 0, "volumen": 106439.38}, "Variante B"),
    ("Standard", {"neuaufbau": True, "whats_wrong": 1, "volumen": 106239.38}, "Standard"),
    ("oeffnen_baugruppe", {"fehler": 1, "warnungen": 0}, "Baugruppe"),
    ("baugruppe", {"neuaufbau": True, "whats_wrong": 0, "komponenten": [("Lagerdeckel-1", "a")]}, "Baugruppe"),
])
def test_abweichungen_werden_benannt(schluessel, wert, nennt):
    n = gut()
    n[schluessel] = wert
    assert any(nennt in a for a in abweichungen(n))


def test_fehlende_konfiguration_ist_eine_abweichung():
    """Eine Vorlage mit anderem Konfigurationsnamen ergäbe keine `Standard`; die Soll-Volumina prüfen dann nichts."""
    n = gut()
    del n["Standard"]
    assert any("Standard" in a for a in abweichungen(n))


# ---------------------------------------------------------------------------------------------------- Hubeinheit (Etappe 2)

def _lege_hubeinheit(ordner: Path) -> None:
    for rel in HUB_DATEIEN:
        (ordner / rel).parent.mkdir(parents=True, exist_ok=True)
        (ordner / rel).write_bytes(b"x")


def _git_ordner(tmp_path, monkeypatch, jahr: int) -> Path:
    """Ein Muster-Ordner wie im Repo: `bestand.json` nennt das Jahr, die Muster liegen in `muster/`."""
    muster = tmp_path / "git" / "muster"
    muster.mkdir(parents=True)
    (muster.parent / "bestand.json").write_text(json.dumps({"sw_jahr": jahr}), encoding="utf-8")
    monkeypatch.setattr(werkzeug, "MUSTER_GIT", muster)
    return muster


def test_hubeinheit_im_git_gilt_fuer_ihr_jahr(tmp_path, monkeypatch):
    muster = _git_ordner(tmp_path, monkeypatch, 2025)
    _lege_hubeinheit(muster / "baugruppe")
    assert hubeinheit_ordner(rechner(tmp_path, 2025)) == muster / "baugruppe"


def test_hubeinheit_ohne_git_kopie_liegt_im_arbeitsordner(tmp_path, monkeypatch):
    _git_ordner(tmp_path, monkeypatch, 2025)
    ordner = tmp_path / "BESTAND-MUSTER" / "2025" / "baugruppe"
    _lege_hubeinheit(ordner)
    assert hubeinheit_ordner(rechner(tmp_path, 2025)) == ordner


def test_hubeinheit_anderes_jahr_nimmt_nie_das_git(tmp_path, monkeypatch):
    muster = _git_ordner(tmp_path, monkeypatch, 2025)
    _lege_hubeinheit(muster / "baugruppe")
    ordner = tmp_path / "BESTAND-MUSTER" / "2026" / "baugruppe"
    _lege_hubeinheit(ordner)
    assert hubeinheit_ordner(rechner(tmp_path, 2026)) == ordner


def test_fehlende_hubeinheit_nennt_den_aufruf_und_die_datei(tmp_path, monkeypatch):
    _git_ordner(tmp_path, monkeypatch, 2025)
    ordner = tmp_path / "BESTAND-MUSTER" / "2025" / "baugruppe"
    _lege_hubeinheit(ordner)
    (ordner / "teile" / "Schlitten.SLDPRT").unlink()
    with pytest.raises(MusterFehlt, match=r"bestand_muster hubeinheit.*|teile/Schlitten.SLDPRT"):
        hubeinheit_ordner(rechner(tmp_path, 2025))


def test_muster_dateien_werden_kopiert_und_bleiben(tmp_path):
    """Die Unterbaugruppe ist vorhanden, nicht neu gebaut: Ein neues Muster hätte andere SHA-256 als `lagerdeckel_rev.yaml`."""
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    for name in DATEIEN:
        (quelle / name).write_bytes(name.encode())
    ziel = tmp_path / "bau"
    uebernimm_muster(quelle, ziel)
    assert {p.name: p.read_bytes() for p in ziel.iterdir()} == {name: name.encode() for name in DATEIEN}
    assert {p.name: p.read_bytes() for p in quelle.iterdir()} == {name: name.encode() for name in DATEIEN}


def test_ins_git_kopiert_alle_dateien_mit_struktur(tmp_path):
    quelle = tmp_path / "quelle"
    _lege_hubeinheit(quelle)
    ziel = tmp_path / "git"
    uebernimm_hubeinheit(quelle, ziel)
    assert sorted(p.relative_to(ziel).as_posix() for p in ziel.rglob("*") if p.is_file()) == sorted(HUB_DATEIEN)


def gute_hub() -> dict:
    t = {n: {"lage": list(xyz), "status": HUB_STATUS.get(n), "unterdrueckt": False} for n, xyz in HUB_LAGE.items()}
    t |= {n: {"lage": [0, 150, 0], "status": 3, "unterdrueckt": False} for n in HUB_KOMPONENTEN if n not in t}
    ohne = {n: {**e, "unterdrueckt": n.startswith("Muster-1")} for n, e in t.items()}
    mates = {n: {"fehler": 0} for n in HUB_VERKNUEPFUNGEN}
    return {"volumen": dict(SOLL_VOLUMEN_HUB), "oeffnen": {"fehler": 0, "warnungen": 0},
            "hub": {"wert": 0.0, "min": 0.0, "max": 25.0},
            "Standard": {"neuaufbau": True, "whats_wrong": 0, "komponenten": t, "verknuepfungen": mates},
            KONFIG_OHNE: {"neuaufbau": True, "whats_wrong": 0, "komponenten": ohne, "verknuepfungen": mates}}


def test_gute_hubeinheit_hat_keine_abweichung():
    assert abweichungen_hub(gute_hub()) == []


@pytest.mark.parametrize("aendern, nennt", [
    (lambda n: n["volumen"].update(Grundplatte=1.0), "Grundplatte"),
    (lambda n: n.update(oeffnen={"fehler": 4, "warnungen": 0}), "Öffnen"),
    (lambda n: n.pop(KONFIG_OHNE), KONFIG_OHNE),
    (lambda n: n["Standard"].update(neuaufbau=False), "Standard"),
    (lambda n: n["Standard"].update(whats_wrong=2), "Standard"),
    (lambda n: n["Standard"]["komponenten"].pop("Anschlag-2"), "Anschlag-2"),
    (lambda n: n["Standard"]["komponenten"].pop("Muster-1/gm42-10-1"), "gm42-10"),
    (lambda n: n["Standard"]["komponenten"]["Schlitten-1"].update(lage=[-70, 0, 30]), "Schlitten-1"),
    (lambda n: n["Standard"]["komponenten"]["Schlitten-1"].update(status=2), "Schlitten-1"),
    (lambda n: n["Standard"]["komponenten"]["Muster-1"].update(unterdrueckt=True), "Muster-1"),
    (lambda n: n[KONFIG_OHNE]["komponenten"]["Muster-1"].update(unterdrueckt=False), "Muster-1"),
    (lambda n: n[KONFIG_OHNE]["komponenten"]["Schlitten-1"].update(unterdrueckt=True), "Schlitten-1"),
    (lambda n: n["Standard"]["verknuepfungen"].pop("Hub"), "Hub"),
    (lambda n: n["Standard"].update(verknuepfungen={**n["Standard"]["verknuepfungen"], "Hub": {"fehler": 1}}), "Hub"),
    (lambda n: n.update(hub={"wert": 0.0, "min": 0.0, "max": 20.0}), "Hub"),
])
def test_abweichungen_der_hubeinheit_werden_benannt(aendern, nennt):
    n = copy.deepcopy(gute_hub())
    aendern(n)
    assert any(nennt in a for a in abweichungen_hub(n))


def test_kinder_der_unterbaugruppe_tragen_kein_lage_soll():
    """Wo der Motor in `Muster.SLDASM` sitzt, legt das Muster fest; nur das Kind selbst muss da sein."""
    assert all("/" not in n for n in HUB_LAGE) and "Muster-1/Lagerdeckel-1" in HUB_KOMPONENTEN
    n = gute_hub()
    n["Standard"]["komponenten"]["Muster-1/gm42-10-1"] = {"lage": [1, 2, 3], "status": 2, "unterdrueckt": False}
    assert abweichungen_hub(n) == []


def test_kinder_einer_unterdrueckten_unterbaugruppe_duerfen_fehlen():
    n = gute_hub()
    del n[KONFIG_OHNE]["komponenten"]["Muster-1/gm42-10-1"]
    del n[KONFIG_OHNE]["komponenten"]["Muster-1/Lagerdeckel-1"]
    assert abweichungen_hub(n) == []
