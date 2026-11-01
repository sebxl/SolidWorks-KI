import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from swki.bestand import ablage, fehler
from swki.bestand.ablage import (aufnahmen, aufnahmen_aus_lauf, bestand_ordner, herkunft_von, kopiere_baugruppe,
                                 kopiere_original, lade_datei_aufnahme, lade_dateien, lauf_kopie_alle, ordne_referenzen,
                                 pruefe_auftrag_frei, schreibe_datei_aufnahme, schreibe_herkunft, sperrdateien,
                                 verwirf_aufnahme)
from swki.bestand.fehler import (BESTAND_ANDERE_DATEI, BESTAND_AUFTRAG_BELEGT, BESTAND_NICHT_LESBAR, BESTAND_REFERENZ_EXTERN,
                                 BESTAND_REFERENZ_FEHLT, BESTAND_UNBEKANNT, BestandFehler)
from swki.konfig import Rechner


@pytest.fixture
def r(tmp_path):
    return Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")


def _datei(ordner: Path, name: str, inhalt: bytes) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / name
    pfad.write_bytes(inhalt)
    return pfad


def _sha(inhalt: bytes) -> str:
    return hashlib.sha256(inhalt).hexdigest()


def _kunde(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    """Haupt mit einem Teil daneben und einem im Unterordner."""
    ordner = tmp_path / "kunde"
    haupt = _datei(ordner, "Haupt.SLDASM", b"haupt")
    quellen = {"A.SLDPRT": _datei(ordner, "A.SLDPRT", b"a"), "teile/B.SLDPRT": _datei(ordner / "teile", "B.SLDPRT", b"b")}
    return haupt, quellen


def test_fehlercodes():
    for name in ("BESTAND_PFAD_FREMD", "BESTAND_AUFTRAG_BELEGT", "BESTAND_REFERENZ_FEHLT", "BESTAND_OFFEN",
                 "VERKNUEPFUNGEN_FEHLEN", "NAME_BELEGT"):
        assert getattr(fehler, name) == name


# --- ordne_referenzen ---------------------------------------------------------------------------------------------

def test_datei_neben_der_baugruppe_hat_vorrang(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    daneben = _datei(tmp_path / "kunde", "A.SLDPRT", b"neu")
    woanders = _datei(tmp_path / "alt", "A.SLDPRT", b"alt")
    assert ordne_referenzen(haupt, [str(woanders)]) == {"A.SLDPRT": daneben}


def test_unterordner_behalten_struktur(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    teil = _datei(tmp_path / "kunde" / "teile", "A.SLDPRT", b"a")
    assert ordne_referenzen(haupt, [str(teil)]) == {"teile/A.SLDPRT": teil}


def test_fremder_ordner_liegt_flach(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    norm = _datei(tmp_path / "norm", "S.sldprt", b"s")
    assert ordne_referenzen(haupt, [str(norm)]) == {"S.sldprt": norm}


def test_gleiche_namen_aus_zwei_ordnern(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    eins = _datei(tmp_path / "x", "S.sldprt", b"1")
    zwei = _datei(tmp_path / "y", "s.SLDPRT", b"2")
    with pytest.raises(BestandFehler) as e:
        ordne_referenzen(haupt, [str(eins), str(zwei)])
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN
    nennt = json.dumps(e.value.daten["gleiche_namen"])
    assert str(eins).replace("\\", "\\\\") in nennt and str(zwei).replace("\\", "\\\\") in nennt


def test_exakt_gleicher_name_aus_zwei_ordnern(tmp_path):
    """Gleiches `rel`, andere Quelle: die zweite darf die erste nicht still überschreiben."""
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    eins = _datei(tmp_path / "x", "S.sldprt", b"1")
    zwei = _datei(tmp_path / "y", "S.sldprt", b"2")
    with pytest.raises(BestandFehler) as e:
        ordne_referenzen(haupt, [str(eins), str(zwei)])
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN
    assert sorted(e.value.daten["gleiche_namen"]["s.sldprt"]) == sorted([str(eins), str(zwei)])


def test_gleiche_namen_im_unterordner_und_flach(tmp_path):
    """SolidWorks öffnet keine zwei gleichnamigen Dokumente: auch teile/A und ein fremdes A kollidieren."""
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    eins = _datei(tmp_path / "kunde" / "teile", "A.SLDPRT", b"1")
    zwei = _datei(tmp_path / "fremd", "A.SLDPRT", b"2")
    with pytest.raises(BestandFehler) as e:
        ordne_referenzen(haupt, [str(eins), str(zwei)])
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN


def test_dieselbe_datei_zweimal_ist_kein_konflikt(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    norm = _datei(tmp_path / "norm", "S.sldprt", b"s")
    assert ordne_referenzen(haupt, [str(norm), str(norm)]) == {"S.sldprt": norm}


def test_fehlende_referenz(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    da = _datei(tmp_path / "kunde", "A.SLDPRT", b"a")
    weg1, weg2 = tmp_path / "gone" / "X.SLDPRT", tmp_path / "gone" / "Y.SLDPRT"
    with pytest.raises(BestandFehler) as e:
        ordne_referenzen(haupt, [str(weg1), str(da), str(weg2)])
    assert e.value.daten["code"] == BESTAND_REFERENZ_FEHLT
    assert sorted(e.value.daten["fehlen"]) == sorted([str(weg1), str(weg2)])


def test_virtuelles_teil_fehlt_nicht(tmp_path):
    """Review Focus 1: Eine virtuelle Komponente liegt in der Baugruppe und unter einem Temp-Pfad."""
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    da = _datei(tmp_path / "kunde", "A.SLDPRT", b"a")
    virtuell = str(tmp_path / "temp" / "Teil1^Haupt.sldprt")
    assert ordne_referenzen(haupt, [virtuell, str(da)]) == {"A.SLDPRT": da}


def test_die_hauptbaugruppe_selbst_ist_keine_referenz(tmp_path):
    haupt = _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")
    assert ordne_referenzen(haupt, [str(haupt)]) == {}


# --- sperrdateien / kopiere_baugruppe -------------------------------------------------------------------------------

def test_sperrdatei_wird_gemeldet_nicht_kopiert(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    _datei(haupt.parent, "~$A.SLDPRT", b"sperre")
    assert sperrdateien(quellen) == ["A.SLDPRT"]
    k = kopiere_baugruppe(r, "a1", haupt, quellen)
    gefunden = [p.name for p in bestand_ordner(r, "a1", k["nummer"]).rglob("*") if p.is_file()]
    assert not [n for n in gefunden if n.startswith("~$")]
    assert sperrdateien({"B": quellen["teile/B.SLDPRT"]}) == []


def test_kopie_ist_schreibgeschuetzt_mit_struktur_und_dateien_json(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    k = kopiere_baugruppe(r, "a1", haupt, quellen)
    ordner = bestand_ordner(r, "a1", 1)
    assert k["nummer"] == 1 and k["neu"] and k["pfad"] == ordner / "Haupt.SLDASM" and k["sha256"] == _sha(b"haupt")
    assert set(k["dateien"]) >= {"A.SLDPRT", "teile/B.SLDPRT"}
    assert k["dateien"]["teile/B.SLDPRT"]["original"] == str(quellen["teile/B.SLDPRT"])
    assert k["dateien"]["teile/B.SLDPRT"]["sha256"] == _sha(b"b")
    for rel in ("Haupt.SLDASM", "A.SLDPRT", "teile/B.SLDPRT"):
        assert (ordner / rel).is_file() and not os.access(ordner / rel, os.W_OK)
    assert (ordner / "teile" / "B.SLDPRT").read_bytes() == b"b"
    assert lade_dateien(r, "a1", 1) == k["dateien"]


def test_gleiche_shas_keine_neue_aufnahme(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    erste = kopiere_baugruppe(r, "a1", haupt, quellen)
    zweite = kopiere_baugruppe(r, "a1", haupt, quellen)
    assert zweite["nummer"] == 1 and not zweite["neu"] and zweite["pfad"] == erste["pfad"]
    assert zweite["dateien"] == erste["dateien"] and aufnahmen(r, "a1") == [1]


def test_eine_geaenderte_datei_neue_aufnahme(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    kopiere_baugruppe(r, "a1", haupt, quellen)
    quellen["teile/B.SLDPRT"].write_bytes(b"b2")
    k = kopiere_baugruppe(r, "a1", haupt, quellen)
    assert k["nummer"] == 2 and k["neu"] and aufnahmen(r, "a1") == [1, 2]
    assert (bestand_ordner(r, "a1", 1) / "teile" / "B.SLDPRT").read_bytes() == b"b"
    assert (bestand_ordner(r, "a1", 2) / "teile" / "B.SLDPRT").read_bytes() == b"b2"


def test_zusaetzliche_datei_ist_neue_aufnahme(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    kopiere_baugruppe(r, "a1", haupt, quellen)
    quellen["C.SLDPRT"] = _datei(haupt.parent, "C.SLDPRT", b"c")
    assert kopiere_baugruppe(r, "a1", haupt, quellen)["nummer"] == 2


def test_andere_hauptdatei_im_auftrag_wird_abgelehnt(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    kopiere_baugruppe(r, "a1", haupt, quellen)
    anders = _datei(tmp_path / "kunde", "Andere.SLDASM", b"x")
    with pytest.raises(BestandFehler) as e:
        kopiere_baugruppe(r, "a1", anders, {})
    assert e.value.daten["code"] == BESTAND_ANDERE_DATEI and aufnahmen(r, "a1") == [1]
    with pytest.raises(BestandFehler) as e:   # und ein Teil statt der Baugruppe
        kopiere_original(r, "a1", _datei(tmp_path / "kunde", "Teil.SLDPRT", b"t"))
    assert e.value.daten["code"] == BESTAND_ANDERE_DATEI


def test_original_und_lauf_bleiben_unberuehrt(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    alle = [haupt, *quellen.values()]
    vorher = {p: (p.read_bytes(), p.stat().st_mtime_ns, os.access(p, os.W_OK)) for p in alle}
    liste = sorted(p.relative_to(haupt.parent).as_posix() for p in haupt.parent.rglob("*"))
    kopiere_baugruppe(r, "a1", haupt, quellen)
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns, os.access(p, os.W_OK)) for p in alle} == vorher
    assert sorted(p.relative_to(haupt.parent).as_posix() for p in haupt.parent.rglob("*")) == liste


def test_kopie_weicht_vom_original_ab_laesst_nichts_liegen(r, tmp_path, monkeypatch):
    haupt, quellen = _kunde(tmp_path)
    echt = ablage.shutil.copy2

    def kopiere(quelle, ziel):
        echt(quelle, ziel)
        if Path(quelle).name == "B.SLDPRT":
            os.chmod(ziel, stat.S_IWRITE)
            Path(ziel).write_bytes(b"halb")
            os.chmod(ziel, stat.S_IREAD)

    monkeypatch.setattr(ablage.shutil, "copy2", kopiere)
    with pytest.raises(BestandFehler) as e:
        kopiere_baugruppe(r, "a1", haupt, quellen)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and aufnahmen(r, "a1") == []
    assert not bestand_ordner(r, "a1", 1).exists()


def test_quelle_fehlt_beim_kopieren(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    quellen["Weg.SLDPRT"] = tmp_path / "kunde" / "Weg.SLDPRT"
    with pytest.raises(BestandFehler) as e:
        kopiere_baugruppe(r, "a1", haupt, quellen)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and aufnahmen(r, "a1") == []


def test_verwirf_entfernt_alle_schreibgeschuetzten(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    kopiere_baugruppe(r, "a1", haupt, quellen)
    ordner = bestand_ordner(r, "a1", 1)
    verwirf_aufnahme(ordner)
    assert not ordner.exists() and aufnahmen(r, "a1") == []


def test_etappe1_aufnahme_bleibt_gueltig(r, tmp_path):
    """Ohne dateien.json ist die Kopie die einzige .sldprt, wie bisher."""
    k = kopiere_original(r, "a1", _datei(tmp_path, "Deckel.SLDPRT", b"abc"))
    assert ablage._kopie_in(bestand_ordner(r, "a1", 1)) == k["pfad"]
    with pytest.raises(BestandFehler) as e:
        lade_dateien(r, "a1", 1)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_kopie_in_findet_die_baugruppe_nicht_ein_teil_daneben(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    k = kopiere_baugruppe(r, "a1", haupt, quellen)
    assert ablage._kopie_in(bestand_ordner(r, "a1", 1)) == k["pfad"]


# --- lauf_kopie_alle ------------------------------------------------------------------------------------------------

def test_lauf_kopie_alle_ist_beschreibbar_mit_struktur(r, tmp_path):
    haupt, quellen = _kunde(tmp_path)
    k = kopiere_baugruppe(r, "a1", haupt, quellen)
    lauf = r.arbeitsordner / "a1" / "lauf-1"
    ziel = lauf_kopie_alle(bestand_ordner(r, "a1", 1), lade_dateien(r, "a1", 1), lauf)
    assert ziel == lauf / "Haupt.SLDASM"
    for rel, inhalt in (("Haupt.SLDASM", b"haupt"), ("A.SLDPRT", b"a"), ("teile/B.SLDPRT", b"b")):
        assert (lauf / rel).read_bytes() == inhalt and os.access(lauf / rel, os.W_OK)
        assert not os.access(bestand_ordner(r, "a1", 1) / rel, os.W_OK)   # die Bestandskopie bleibt geschützt
    (lauf / "teile" / "B.SLDPRT").write_bytes(b"geaendert")
    assert (bestand_ordner(r, "a1", 1) / "teile" / "B.SLDPRT").read_bytes() == b"b"
    assert k["pfad"].read_bytes() == b"haupt"


# --- Herkunft -------------------------------------------------------------------------------------------------------

def _lauf(r, auftrag="a1", n=2, spec="a1.yaml") -> Path:
    lauf = r.arbeitsordner / auftrag / f"lauf-{n}"
    lauf.mkdir(parents=True)
    (lauf / "protokoll.json").write_text(json.dumps({"auftrag": auftrag, "lauf": n, "spec": spec, "status": "ok"}),
                                         encoding="utf-8")
    return lauf


def test_herkunft_aus_lauf_ordner(r, tmp_path):
    lauf = _lauf(r)
    original = _datei(lauf, "Haupt.SLDASM", b"h")
    assert herkunft_von(r, original) == {"auftrag": "a1", "lauf": 2, "spec": "a1.yaml"}
    tief = _datei(lauf / "teile", "A.SLDPRT", b"a")
    assert herkunft_von(r, tief) == {"auftrag": "a1", "lauf": 2, "spec": "a1.yaml"}


def test_herkunft_fehlt_ausserhalb(r, tmp_path):
    assert herkunft_von(r, _datei(tmp_path / "kunde", "Haupt.SLDASM", b"h")) is None
    ohne_protokoll = r.arbeitsordner / "a1" / "lauf-3"
    assert herkunft_von(r, _datei(ohne_protokoll, "Haupt.SLDASM", b"h")) is None
    assert herkunft_von(r, _datei(r.arbeitsordner / "a1" / "bestand-1", "Haupt.SLDASM", b"h")) is None


def test_herkunft_lesen_veraendert_den_lauf_nicht(r):
    lauf = _lauf(r)
    original = _datei(lauf, "Haupt.SLDASM", b"h")
    vorher = sorted((p.name, p.stat().st_mtime_ns) for p in lauf.rglob("*"))
    herkunft_von(r, original)
    assert sorted((p.name, p.stat().st_mtime_ns) for p in lauf.rglob("*")) == vorher


def test_auftrag_mit_spec_laeufen_ist_belegt(r):
    with pytest.raises(BestandFehler) as e:
        pruefe_auftrag_frei(r, "a1", [1, 2])
    assert e.value.daten["code"] == BESTAND_AUFTRAG_BELEGT and e.value.daten["laeufe"] == [1, 2]
    assert pruefe_auftrag_frei(r, "a1", []) is None


def test_aufnahmen_aus_lauf_findet_und_liest_nichts_im_lauf(r, tmp_path):
    lauf = _lauf(r, "a1", 2)
    original = _datei(lauf, "Haupt.SLDASM", b"h")
    vorher = sorted((p.name, p.stat().st_mtime_ns) for p in lauf.rglob("*"))
    herkunft = herkunft_von(r, original)
    pfad = schreibe_herkunft(r, "neu1", 1, herkunft)
    assert pfad == bestand_ordner(r, "neu1", 1) / "herkunft.json"
    schreibe_herkunft(r, "neu2", 3, {**herkunft, "lauf": 5})               # andere Herkunft
    schreibe_herkunft(r, "neu3", 1, {"auftrag": "a2", "lauf": 2, "spec": "a2.yaml"})   # anderer Auftrag, gleiche Laufnummer
    (bestand_ordner(r, "kaputt", 1)).mkdir(parents=True)
    (bestand_ordner(r, "kaputt", 1) / "herkunft.json").write_text("{", encoding="utf-8")
    treffer = aufnahmen_aus_lauf(r, lauf)
    assert [(t["auftrag"], t["nummer"]) for t in treffer] == [("neu1", 1)]
    assert treffer[0]["herkunft"] == herkunft
    assert sorted((p.name, p.stat().st_mtime_ns) for p in lauf.rglob("*")) == vorher
    assert aufnahmen_aus_lauf(r, r.arbeitsordner / "a1" / "lauf-9") == []


# --- Rohdaten je Datei ----------------------------------------------------------------------------------------------

def test_datei_aufnahme_schreiben_und_laden(r):
    daten = {"version": 1, "datei": {"name": "teile/Größe.SLDPRT"}}
    pfad = schreibe_datei_aufnahme(r, "a1", 1, "teile/Größe.SLDPRT", daten)
    assert pfad == bestand_ordner(r, "a1", 1) / "aufnahme" / "teile" / "Größe.SLDPRT.json"
    assert lade_datei_aufnahme(r, "a1", 1, "teile/Größe.SLDPRT") == daten
    assert "Größe" in pfad.read_text(encoding="utf-8")


def test_datei_aufnahme_unbekannt_und_pfad_ausserhalb(r):
    with pytest.raises(BestandFehler) as e:
        lade_datei_aufnahme(r, "a1", 1, "A.SLDPRT")
    assert e.value.daten["code"] == BESTAND_UNBEKANNT
    for rel in ("../bestand.json", "/x.SLDPRT", "C:/x.SLDPRT"):
        with pytest.raises(BestandFehler):
            schreibe_datei_aufnahme(r, "a1", 1, rel, {})
