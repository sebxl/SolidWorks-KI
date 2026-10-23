"""Bewertungsbogen: Vorlage der Prüfstation, Ausgangslauf, Fallen – ohne SolidWorks."""

import json
from pathlib import Path

import pytest

from werkzeuge.messstand import fallen, protokolle, transkript, umgebung


def _schreibe(p: Path, text: str = "x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_vorlage_kopiert_nur_bauweg_und_eingabe(tmp_path):
    q = tmp_path / "AP68"
    for rel in ["pruefstation.yaml", "pruefstation.freigegeben.yaml", "freigabe.json", "eingabe/hersteller/a.png",
                "skripte/f1.py", "protokolle/x.lauf-1.protokoll.json", "layout/l.blend", "simulation/s.blend",
                "UEBERGABE.md", "bericht.md", "layout.v1.yaml", "umgebung/u.yaml", "skizzen_v5/s.svg"]:
        _schreibe(q / rel)
    ziel = umgebung.vorlage_kopieren(q, tmp_path / "vorlage")
    da = sorted(str(p.relative_to(ziel)).replace("\\", "/") for p in ziel.rglob("*") if p.is_file())
    assert da == ["eingabe/hersteller/a.png", "freigabe.json", "pruefstation.freigegeben.yaml", "pruefstation.yaml",
                  "skripte/f1.py"]


def test_auftrag_aus_vorlage(tmp_path, monkeypatch):
    vorlage = tmp_path / "vorlage"
    _schreibe(vorlage / "pruefstation.yaml")
    _schreibe(vorlage / "eingabe" / "a.png")
    a = umgebung.Aufgabe("pruefstation", _schreibe(tmp_path / "def" / "aufgabe.md", "Ändere …").parent, "baugruppe",
                         "baugruppe", [], {}, [], [], vorlage=str(vorlage), spec="pruefstation.yaml", ausgangslauf=True)
    wt = tmp_path / "wt"
    auftrag = umgebung.auftrag_anlegen(wt, "d0-pruefstation-1", a)
    assert (auftrag / "pruefstation.yaml").exists() and (auftrag / "eingabe" / "a.png").exists()
    assert (auftrag / "aufgabe.md").read_text(encoding="utf-8") == "Ändere …"


def test_aufgabe_mit_vorlage_aus_yaml(tmp_path, monkeypatch):
    d = tmp_path / "pruefstation"
    _schreibe(d / "aufgabe.md")
    _schreibe(d / "aufgabe.yaml", "id: pruefstation\nart: baugruppe\nskill: baugruppe\n"
                                  "vorlage: '{arbeitsordner}/MESSSTAND/vorlagen/pruefstation'\nspec: pruefstation.yaml\n"
                                  "ausgangslauf: true\nreferenz: {spec_ordner: '{arbeitsordner}/MESSSTAND/vorlagen/"
                                  "pruefstation-referenz', spec: pruefstation.yaml}\n")
    monkeypatch.setattr(umgebung, "AUFGABEN", tmp_path)
    a = umgebung.aufgaben()["pruefstation"]
    assert a.ausgangslauf and a.spec == "pruefstation.yaml"
    assert a.vorlage_pfad(Path("C:/arbeit")) == Path("C:/arbeit/MESSSTAND/vorlagen/pruefstation")


def test_quellrepo_ist_hauptcheckout():
    # aus einem Worktree heraus zeigt QUELLREPO auf den Hauptcheckout (dort liegen auftraege/ und Herstellerdateien)
    assert (umgebung.QUELLREPO / ".git").is_dir()


def test_protokolle_erst_nach_dem_ausgangslauf(tmp_path):
    pk = tmp_path / "protokolle"
    _schreibe(pk / "p.lauf-1.protokoll.json", json.dumps({"status": "fehler"}))
    _schreibe(pk / "p.lauf-2.protokoll.json", json.dumps({"status": "ok", "phasen": {"teile": 200.0}}))
    _schreibe(pk / "p.lauf-2.pruefer.json", json.dumps({"bestanden": True}))
    _schreibe(pk / "p.lauf-3.protokoll.json", json.dumps({"status": "ok", "phasen": {"teile": 20.0, "verknuepfen": 5.0}}))
    _schreibe(pk / "p.lauf-3.pruefbericht.json", json.dumps({"pruefungen": [{"ok": False}]}))
    _schreibe(pk / "p.lauf-3.pruefer.json", json.dumps({"bestanden": True}))
    alle = protokolle.auswerten(tmp_path)
    assert alle["laeufe"] == 3 and alle["bauabbrueche"] == 1
    ab = protokolle.auswerten(tmp_path, ab_lauf=3)
    assert ab["laeufe"] == 1 and ab["bauabbrueche"] == 0 and ab["pruefmaengel"] == 1
    assert ab["letzter_lauf"] == 3 and ab["phasen_s"] == {"teile": 20.0, "verknuepfen": 5.0}


def test_neustart_eigene_kategorie():
    assert transkript.kategorie("Bash", {"command": "x -m werkzeuge.sw_neustart"}) == "neustart"
    assert transkript.kategorie("Bash", {"command": "x -m werkzeuge.inspiziere a"}) == "werkzeuge"


# --- Fallen ---------------------------------------------------------------------------------------------------------

def _falle(tmp_path, fid="F1", art="falle", knoten=("stecker",), stichworte=("gespiegelt",)):
    d = tmp_path / "fallen" / fid
    _schreibe(d / "falle.yaml", json.dumps({"id": fid, "art": art, "spec": "durchlicht.yaml",
                                            "erwartet": {"knoten": list(knoten), "stichworte": list(stichworte)}}))
    _schreibe(d / "spec" / "durchlicht.yaml")
    return d


def test_fallen_laden(tmp_path, monkeypatch):
    _falle(tmp_path)
    _falle(tmp_path, "R1", art="richtig", knoten=(), stichworte=())
    monkeypatch.setattr(fallen, "FALLEN", tmp_path / "fallen")
    f = fallen.fallen()
    assert sorted(f) == ["F1", "R1"] and f["R1"].art == "richtig"


@pytest.mark.parametrize("urteil, treffer", [
    ({"bestanden": False, "maengel": [{"knoten": ["stecker"], "beschreibung": "liegt falsch"}]}, "treffer"),
    ({"bestanden": False, "maengel": [{"knoten": ["koerper"], "beschreibung": "Stecker GESPIEGELT in X"}]}, "treffer"),
    ({"bestanden": False, "maengel": [{"knoten": ["koerper"], "beschreibung": "Fase fehlt"}]}, "unklar"),
    ({"bestanden": True, "maengel": []}, "verfehlt"),
])
def test_urteil_einordnen(tmp_path, monkeypatch, urteil, treffer):
    monkeypatch.setattr(fallen, "FALLEN", tmp_path / "fallen")
    _falle(tmp_path)
    assert fallen.einordnen(fallen.fallen()["F1"], urteil) == treffer


def test_richtig_einordnen(tmp_path, monkeypatch):
    monkeypatch.setattr(fallen, "FALLEN", tmp_path / "fallen")
    _falle(tmp_path, "R1", art="richtig", knoten=(), stichworte=())
    f = fallen.fallen()["R1"]
    assert fallen.einordnen(f, {"bestanden": True, "maengel": []}) == "ok"
    assert fallen.einordnen(f, {"bestanden": False, "maengel": [{"knoten": ["x"]}]}) == "fehlalarm"


def test_auswerten_mehrheit_und_entscheid(tmp_path, monkeypatch):
    monkeypatch.setattr(fallen, "FALLEN", tmp_path / "fallen")
    _falle(tmp_path, "F1")
    _falle(tmp_path, "F2")
    _falle(tmp_path, "R1", art="richtig", knoten=(), stichworte=())
    ordner = tmp_path / "durchgang-0" / "fallen"
    t = {"bestanden": False, "maengel": [{"knoten": ["stecker"]}]}
    u = {"bestanden": False, "maengel": [{"knoten": ["fase"]}]}
    ok = {"bestanden": True, "maengel": []}
    for fid, urteile in {"F1": [t, t, ok], "F2": [t, u, ok], "R1": [ok, u, u]}.items():
        for k, d in enumerate(urteile, 1):
            _schreibe(ordner / f"urteil-{fid}-{k}.json", json.dumps(d))
    erg = fallen.auswerten(ordner)
    assert erg["treffer"] == 1 and erg["fehlalarme"] == 1
    assert erg["je_falle"]["F2"]["unklar"] == ["F2-2"]
    _schreibe(ordner / "entscheid.json", json.dumps({"F2-2": "treffer"}))
    assert fallen.auswerten(ordner)["treffer"] == 2


def test_falle_aus_basis_mit_ersetzung(tmp_path, monkeypatch):
    basis = tmp_path / "vorlage"
    _schreibe(basis / "durchlicht.yaml", "parameter:\n  SX: 50         # Stecker\n")
    _schreibe(basis / "kamera.yaml", "k")
    monkeypatch.setattr(fallen, "FALLEN", tmp_path / "fallen")
    monkeypatch.setattr(fallen, "AUFGABEN", tmp_path / "aufgaben")
    _schreibe(tmp_path / "aufgaben" / "durchlicht" / "aufgabe.md", "Ersatzkörper Durchlicht")
    d = tmp_path / "fallen" / "F1"
    _schreibe(d / "falle.yaml", json.dumps({
        "id": "F1", "art": "falle", "spec": "durchlicht.yaml", "basis": "{arbeitsordner}/vorlage",
        "dateien": ["durchlicht.yaml"], "aufgabe": "durchlicht",
        "ersetzen": [{"datei": "durchlicht.yaml", "alt": "SX: 50 ", "neu": "SX: 25 "}],
        "erwartet": {"knoten": ["stecker"]}}))
    f = fallen.fallen()["F1"]
    a = fallen.auftrag_anlegen(f, tmp_path / "auftraege", arbeitsordner=tmp_path)
    assert "SX: 25 " in (a / "durchlicht.yaml").read_text(encoding="utf-8")
    assert not (a / "kamera.yaml").exists()
    assert (a / "aufgabe.md").read_text(encoding="utf-8") == "Ersatzkörper Durchlicht"
    f.ersetzen[0]["alt"] = "SX: 99"
    with pytest.raises(ValueError, match="0-mal"):
        fallen.auftrag_anlegen(f, tmp_path / "auftraege", arbeitsordner=tmp_path)


def test_pruefauftrag_enthaelt_pruefer_anweisung_und_lauf(tmp_path):
    text = fallen.pruefauftrag("---\nname: pruefer\ntools: Read, Glob\n---\nDu prüfst unabhängig.", "Prüfe Lauf 1 von a.yaml.")
    assert "Du prüfst unabhängig." in text and "Prüfe Lauf 1 von a.yaml." in text and "name: pruefer" not in text
