"""Wiederverwenden unveränderter Eigenteile (BTP Umbau 3, Recherche O5): Schlüssel, Quellen, Sperren, Reihenfolge."""

import json
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import wiederverwendung as wv
from swki.konfig import PROJEKT, Rechner, lade_standard
from tests.baugruppe.beispiel import DECKEL, PLATTE, kopie

UMG = {"code": "c", "wissen": "w", "schema": "s", "standard": "st", "auftrag": "A", "sw": "2025/33.1.0",
       "vorlage": "v", "material": "m"}


def _key(spec, ordner=Path("."), umg=UMG, datei="platte.yaml"):
    return wv.schluessel(spec, datei, ordner, umg)


# --- Schlüssel ---------------------------------------------------------------------------------------------------

def test_gleiche_eingaben_gleicher_schluessel():
    assert _key(kopie(PLATTE)) == _key(kopie(PLATTE))


def test_parameter_aendert_den_schluessel():
    spec = kopie(PLATTE)
    spec["parameter"]["H"] = 21
    assert _key(spec) != _key(kopie(PLATTE))


@pytest.mark.parametrize("feld", ["code", "wissen", "schema", "standard", "auftrag", "sw", "vorlage"])
def test_jede_umgebungsgroesse_aendert_den_schluessel(feld):
    assert _key(kopie(PLATTE), umg={**UMG, feld: "anders"}) != _key(kopie(PLATTE))


def test_materialdatenbank_zaehlt_nur_mit_material():
    mit, ohne = kopie(PLATTE), kopie(PLATTE)
    del ohne["material"]
    anders = {**UMG, "material": "anders"}
    assert _key(mit, umg=anders) != _key(mit)
    assert _key(ohne, umg=anders) == _key(ohne)


def test_dateiname_der_teilspec_zaehlt():
    assert _key(kopie(PLATTE), datei="a.yaml") != _key(kopie(PLATTE), datei="b.yaml")


def test_skriptdatei_aendert_den_schluessel(tmp_path):
    spec = kopie(PLATTE)
    spec["features"].append({"id": "s1", "typ": "skript", "datei": "skripte/s1.py", "luecke": "x"})
    (tmp_path / "skripte").mkdir()
    skript = tmp_path / "skripte" / "s1.py"
    skript.write_text("def bauen(ctx):\n    return None\n", encoding="utf-8")
    vorher = _key(spec, tmp_path)
    skript.write_text("def bauen(ctx):\n    return 1\n", encoding="utf-8")
    assert _key(spec, tmp_path) != vorher


def test_code_huelle_enthaelt_handler_und_skizze_aber_nicht_die_befehlsschicht():
    namen = {p.relative_to(PROJEKT).as_posix() for p in wv.code_dateien()}
    assert {"swki/compiler/bauen.py", "swki/compiler/handler/extrusion.py", "swki/compiler/handler/normbohrung.py",
            "swki/compiler/skizze.py", "swki/compiler/sw.py", "swki/verzahnung.py"} <= namen
    assert not {"swki/baugruppe/bau.py", "swki/durchlauf.py", "swki/baugruppe/pruefen.py"} & namen


def test_standard_ohne_schalter_und_pruefgrenzen():
    standard = lade_standard()
    basis = wv.standard_pruefsumme(standard)
    assert wv.standard_pruefsumme({**standard, "wiederverwenden": not standard.get("wiederverwenden"),
                                   "speicher_grenze_mb": 1, "bewegung_schritte": 3}) == basis
    assert wv.standard_pruefsumme({**standard, "toleranzen": {**standard["toleranzen"], "anker_mm": 0.2}}) != basis
    assert wv.standard_pruefsumme({**standard, "neu": 1}) != basis  # unbekannte Schlüssel zählen (vorsichtig)


def test_umgebung_liest_revision_vorlage_und_materialdatenbanken(tmp_path):
    vorlage, db = tmp_path / "t.prtdot", tmp_path / "m.sldmat"
    vorlage.write_bytes(b"vorlage")
    db.write_bytes(b"db")

    class App:
        RevisionNumber = "33.1.0"
        GetMaterialDatabases = (str(db),)

    r = Rechner(2025, tmp_path, vorlage, None, None, tmp_path / "arbeit")
    u = wv.umgebung(App(), r, lade_standard(), "A")
    assert u["sw"] == "2025/33.1.0" and u["vorlage"] == sha256_datei(vorlage) and u["auftrag"] == "A"
    db.write_bytes(b"db2")
    assert wv.umgebung(App(), r, lade_standard(), "A")["material"] != u["material"]


# --- Quellen -----------------------------------------------------------------------------------------------------

@pytest.fixture
def auftrag(tmp_path):
    r = Rechner(2025, tmp_path, tmp_path / "t.prtdot", None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "A" / "bg.yaml"
    spec_pfad.parent.mkdir()
    spec_pfad.write_text("art: baugruppe\n", encoding="utf-8")
    return r, spec_pfad


def _lauf(r, spec_pfad, n, teile: dict, status="ok", inhalt=None, komponenten=None):
    """Lauf n mit Teilen {datei: (status, schluessel)}; Dateien im Lauf-Ordner mit eigenem Inhalt."""
    ordner = lauf_ordner(r, "A", n)
    ordner.mkdir(parents=True)
    dateien, sha, prot_teile = {}, {}, {}
    for datei, (st, key) in teile.items():
        pfad = ordner / f"A_{Path(datei).stem}.sldprt"
        pfad.write_bytes((inhalt or {}).get(datei, f"{datei}-{n}").encode())
        dateien[f"teil:{datei}"] = str(pfad)
        sha[pfad.name] = sha256_datei(pfad)
        prot_teile[datei] = {"status": st, "schluessel": key, "lauf": n, "knoten": [{"id": "f1", "punkte": None}]}
    komponenten = komponenten or [{"id": Path(d).stem, "sw_name": "x-1", "datei": Path(dateien[f"teil:{d}"]).name}
                                  for d in teile]
    protokoll = {"status": status, "lauf": n, "teile": prot_teile, "dateien": dateien, "sha256": sha,
                 "komponenten": komponenten}
    datei = lauf_datei(spec_pfad, n, "protokoll")
    datei.parent.mkdir(exist_ok=True)
    datei.write_text(json.dumps(protokoll), encoding="utf-8")
    return ordner


def _bericht(spec_pfad, n, teilpruefungen):
    lauf_datei(spec_pfad, n, "pruefbericht").write_text(json.dumps({"teilpruefungen": teilpruefungen}), encoding="utf-8")


def test_quelle_bei_gleichem_schluessel_und_unveraenderter_datei(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1"), "deckel.yaml": ("ok", "k2")})
    plan = wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1", "deckel.yaml": "k2-neu"})
    assert set(plan.quellen) == {"platte.yaml"}
    q = plan.quellen["platte.yaml"]
    assert q.lauf == 1 and q.pfad.name == "A_platte.sldprt" and q.protokoll["schluessel"] == "k1"


def test_neuester_passender_lauf_ist_die_quelle(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")})
    _lauf(r, spec_pfad, 2, {"platte.yaml": ("ok", "k1")})
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen["platte.yaml"].lauf == 2


def test_manuell_geaenderte_datei_ist_keine_quelle(auftrag):
    r, spec_pfad = auftrag
    ordner = _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")})
    (ordner / "A_platte.sldprt").write_bytes(b"von Hand geaendert")
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen == {}


def test_fehlende_datei_ist_keine_quelle(auftrag):
    r, spec_pfad = auftrag
    ordner = _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")})
    (ordner / "A_platte.sldprt").unlink()
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen == {}


def test_gescheitertes_teil_ist_keine_quelle_der_fehlgeschlagene_lauf_schon(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1"), "deckel.yaml": ("fehler", "k2")}, status="fehler")
    plan = wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1", "deckel.yaml": "k2"})
    assert set(plan.quellen) == {"platte.yaml"} and plan.gescheitert == {"deckel.yaml"}


def test_alte_protokolle_ohne_schluessel_sind_keine_quelle(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", None)})
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen == {}


def test_teilmangel_im_pruefbericht_sperrt_schluessel_und_datei(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")}, inhalt={"platte.yaml": "gleich"})
    _lauf(r, spec_pfad, 2, {"platte.yaml": ("ok", "k1")}, inhalt={"platte.yaml": "gleich"})
    _bericht(spec_pfad, 1, {"platte": {"bestanden": False, "maengel": 1}})
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen == {}


def test_bestandene_teilpruefung_sperrt_nichts(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")})
    _bericht(spec_pfad, 1, {"platte": {"bestanden": True, "maengel": 0}})
    assert set(wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen) == {"platte.yaml"}


def test_pruefer_mangel_am_teil_sperrt_dessen_datei(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1"), "deckel.yaml": ("ok", "k2")})
    lauf_datei(spec_pfad, 1, "pruefer").write_text(json.dumps(
        {"bestanden": False, "maengel": [{"knoten": ["deckel/f2"], "beschreibung": "x"}]}), encoding="utf-8")
    assert set(wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1", "deckel.yaml": "k2"}).quellen) == {"platte.yaml"}


def test_instanz_im_komponentennamen_wird_auf_die_komponente_zurueckgefuehrt(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"platte.yaml": ("ok", "k1")},
          komponenten=[{"id": "halter.1", "sw_name": "x-1", "datei": "A_platte.sldprt"}])
    _bericht(spec_pfad, 1, {"halter": {"bestanden": False, "maengel": 2}})
    assert wv.plane(r, "A", spec_pfad, {"platte.yaml": "k1"}).quellen == {}


def test_reihenfolge_gescheiterte_zuerst_dann_ohne_quelle_dann_wiederverwendbare(auftrag):
    r, spec_pfad = auftrag
    _lauf(r, spec_pfad, 1, {"a.yaml": ("ok", "ka"), "b.yaml": ("ok", "kb"), "c.yaml": ("fehler", "kc")},
          status="fehler")
    plan = wv.plane(r, "A", spec_pfad, {"a.yaml": "ka", "b.yaml": "kb-neu", "c.yaml": "kc", "d.yaml": "kd"})
    teile = ["a.yaml", "b.yaml", "c.yaml", "d.yaml"]
    assert plan.zu_bauen(teile, wiederverwenden=True) == ["c.yaml", "b.yaml", "d.yaml"]
    assert plan.zu_bauen(teile, wiederverwenden=False) == ["c.yaml", "b.yaml", "d.yaml", "a.yaml"]


def test_ohne_laeufe_kein_plan(auftrag):
    r, spec_pfad = auftrag
    plan = wv.plane(r, "A", spec_pfad, {"a.yaml": "ka"})
    assert plan.quellen == {} and plan.zu_bauen(["a.yaml"], True) == ["a.yaml"]
