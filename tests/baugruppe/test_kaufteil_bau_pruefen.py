import math
from pathlib import Path
from types import SimpleNamespace

from swki.baugruppe import bau
from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.geometrie import ueberlappung_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import gewindebohrungen_kaufteil
from swki.compiler.protokoll import Protokoll
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import lade_standard
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.geometrie import Messgeometrie
from tests.baugruppe.beispiel_kaufteil import L, katalog, kopie, schreibe

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}, "namensschema": {"datei": "{auftrag}_{name}"}}
Y = (0.0, 1.0, 0.0)
KERN = {"modell": "kernloch", "durchmesser": 4.2}
NENN = {"modell": "nenn", "durchmesser": 5.0}


def _ins_gewinde(spec: dict) -> dict:
    spec["komponenten"][2] = {"id": "schraube", "quelle": {"normteil": "ISO 4762 M5x12"},
                              "je_position": {"komponente": "motor", "gewinde": "flansch"}}
    spec["verknuepfungen"][3]["b"] = {"komponente": "halter", "feature": "f1", "flaeche": "-y"}
    spec["verknuepfungen"][4]["b"] = {"komponente": "motor", "gewinde": "flansch", "instanz": "je", "achse": True}
    return spec


def _baulauf(pfad, tmp_path):
    bg = lade_baugruppe(pfad)
    return bau.Baulauf(app=None, bg=bg, auftrag="A", ordner=tmp_path / "lauf", standard=lade_standard(),
                       protokoll=Protokoll("A", pfad.name, 1, 2025)), bg


def test_kaufteile_werden_kopiert(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    b, bg = _baulauf(schreibe(tmp_path / "A"), tmp_path)
    cache = tmp_path / "cache" / "SWKI-MUSTER_GM42-10.sldprt"
    cache.parent.mkdir()
    cache.write_bytes(b"kaufteil")
    aufrufe = []

    def hole(text):
        aufrufe.append(text)
        return {"pfad": str(cache), "gebaut": False, "pruefsumme": "abc", "gewinde_modell": {"flansch": KERN}}

    monkeypatch.setattr(bau.kaufteil_befehle, "hole", hole)
    monkeypatch.setattr(bau, "oeffne", lambda app, p: SimpleNamespace(pfad=Path(p)))
    monkeypatch.setattr(bau, "kontext_aus_datei", lambda app, model, spec, p, tol, prot: SimpleNamespace(model=model, spec=spec))
    assert bau._hole_kaufteile(b, 0.1) is None
    kopie_datei = b.ordner / "SWKI-MUSTER_GM42-10.sldprt"
    assert aufrufe == ["SWKI-MUSTER GM42-10"] and kopie_datei.read_bytes() == b"kaufteil" and cache.read_bytes() == b"kaufteil"
    assert b.dateien == {"kaufteil:SWKI-MUSTER_GM42-10": kopie_datei} and b.offen[0].pfad == kopie_datei
    assert b.protokoll.kaufteile["SWKI-MUSTER_GM42-10"] == {
        "kaufteil": "SWKI-MUSTER GM42-10", "cache": str(cache), "gebaut": False, "pruefsumme": "abc",
        "gewinde_modell": {"flansch": KERN}, "masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
    assert b.kontexte["SWKI-MUSTER_GM42-10"].spec["gewinde"]["flansch"]["groesse"] == "M5"


def test_kaufteilfehler_beim_holen(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    b, _ = _baulauf(schreibe(tmp_path / "A"), tmp_path)

    def hole(text):
        raise KaufteilFehler("KAUFTEIL_QUELLE_FEHLT", "Original fehlt")

    monkeypatch.setattr(bau.kaufteil_befehle, "hole", hole)
    fehler = bau._hole_kaufteile(b, 0.1)
    assert fehler.code == "KAUFTEIL_QUELLE_FEHLT" and str(fehler) == "motor: Original fehlt"


def test_gewindebohrungen_des_kaufteils(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    liste = gewindebohrungen_kaufteil(bg.quellen["motor"].spec)
    assert [(b["feature"], b["instanz"]) for b in liste] == [("flansch", i) for i in range(1, 5)]
    assert liste[1]["punkt"] == (-L, 0, L)


def _messwerte(bg, laenge_im_gewinde: float, volumen: float, modell: dict | str | None = KERN) -> BaugruppenMesswerte:
    """Schraube.1 sitzt mit der Kopfauflage 12 − laenge vor dem Eintritt (Flansch y = 0, Normale −y) der Position 1."""
    vs = verknuepfungen(bg.spec, bg.quellen)
    ids = [i.id for i in instanzen(bg.spec, bg.quellen)]
    return BaugruppenMesswerte(
        rebuild_fehler=[], verknuepfungen={v.id: 0 for v in vs},
        komponenten={i: {"status": 3, "fixiert": i == "halter"} for i in ids},
        stueckliste=stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD),
        interferenzen=[{"paar": ["motor", "schraube.1"], "volumen": volumen}], box=[0, 0, 0, 1, 1, 1], masse_kg=1.0,
        eigenschaften={"Benennung": "Motorprobe"},
        schrauben={"schraube.1": Messgeometrie("ebene", (L, -(12 - laenge_im_gewinde), L), Y)},
        gewindebohrungen=[{"teil": "motor", "feature": "flansch", "instanz": 1,
                           "eintritt": Messgeometrie("punkt", (L, 0.0, L))}],
        teilberichte={"halter.yaml": {"bestanden": True, "pruefungen": [], "maengel": []}},
        gewinde_modelle={"SWKI-MUSTER_GM42-10": {"flansch": modell}} if modell else {})


def _gewinde(bg, m) -> dict:
    bericht = bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))
    return next(e for e in bericht["pruefungen"] if e["id"] == "gewinde:schraube.1")


def test_gewindepaarung_im_kaufteil(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    soll = ueberlappung_soll(5, 0.8, 4.2, 7.4)
    ok = _gewinde(bg, _messwerte(bg, 7.4, soll))
    assert ok["ok"] is True and ok["soll"] == round(soll, 3) and ok["gewindetiefe"] == 8 and ok["tiefe"] == 10
    zu_lang = _gewinde(bg, _messwerte(bg, 9.0, ueberlappung_soll(5, 0.8, 4.2, 9.0)))
    assert zu_lang["ok"] is False and "Einschraublänge 9.00 mm größer als Gewindetiefe 8" in zu_lang["hinweis"]
    nenn = _gewinde(bg, _messwerte(bg, 7.4, 0.0, NENN))
    assert nenn["ok"] is True and nenn["soll"] == 0.0
    assert _gewinde(bg, _messwerte(bg, 7.4, 3.0, NENN))["ok"] is False
    unbekannt = _gewinde(bg, _messwerte(bg, 7.4, soll, None))
    assert unbekannt["ok"] is None and "Gewindemodell" in unbekannt["hinweis"]


def test_gewindepaarung_mit_gemessenem_kernloch(tmp_path, monkeypatch):
    """Spec 3c §6.4 (Nutzerentscheidung 2026-10-06): Ring Nenn-Ø/gemessener Ø – D1 4,134 statt Tabellen-Kernloch 4,2."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    d1 = {"modell": "kernloch", "durchmesser": 4.134}
    soll = ueberlappung_soll(5, 0.8, 4.134, 7.4)
    ok = _gewinde(bg, _messwerte(bg, 7.4, soll, d1))
    assert ok["ok"] is True and ok["soll"] == round(soll, 3) == 42.305
    assert _gewinde(bg, _messwerte(bg, 7.4, soll + 1.1 * _RING_P, d1))["ok"] is False
    alt = _gewinde(bg, _messwerte(bg, 7.4, soll, "kernloch"))  # alte Form (nur Text) gilt als unbekannt
    assert alt["ok"] is None and "Gewindemodell" in alt["hinweis"]


def test_gewindepaarung_nenn_mit_untergrenze(tmp_path, monkeypatch):
    """Modell nenn (Soll 0): Rechenrauschen bis TOL_GEWINDE_MIN_MM3 (0,01 mm³) ist kein Mangel, mehr schon."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    assert _gewinde(bg, _messwerte(bg, 7.4, 0.004, NENN))["ok"] is True
    assert _gewinde(bg, _messwerte(bg, 7.4, 0.02, NENN))["ok"] is False


def test_bericht_nennt_kaufteile():
    pruefbericht = {"maengel": [], "kaufteile": {"SWKI-MUSTER_GM42-10": {
        "kaufteil": "SWKI-MUSTER GM42-10", "gebaut": True, "pruefsumme": "abc", "masse": "1.2 kg (Datenblatt)",
        "kennmasse": "nicht belegt", "gewinde_modell": {"flansch": {"modell": "kernloch", "durchmesser": 4.134}}}}}
    text = bericht_markdown({"name": "Motorprobe"}, "A", [], ("WEITER", "x"), pruefbericht, None, None, [])
    assert "| SWKI-MUSTER GM42-10 | ja | abc | 1.2 kg (Datenblatt) | nicht belegt | flansch: kernloch Ø 4.134 |" in text


_RING_P = math.pi / 4 * (5 ** 2 - 4.134 ** 2) * 0.8  # Gewindering M5 / D1 4,134 über eine Steigung


def test_kaufteil_gewinde_band_eine_steigung(tmp_path, monkeypatch):
    """AP 6.8 (Sebastian 10.10.2026, Frage 5 A): Herstellergeometrie (Senkung am Eintritt, Auslauf) – im Kaufteil-Gewinde
    gilt ein Band von ± einer Steigung Gewindering statt 1 %."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    d1 = {"modell": "kernloch", "durchmesser": 4.134}
    soll = ueberlappung_soll(5, 0.8, 4.134, 7.4)
    assert _gewinde(bg, _messwerte(bg, 7.4, soll - 0.9 * _RING_P, d1))["ok"] is True   # Senkung 90° am Eintritt
    assert _gewinde(bg, _messwerte(bg, 7.4, soll + 0.9 * _RING_P, d1))["ok"] is True
    assert _gewinde(bg, _messwerte(bg, 7.4, soll - 1.1 * _RING_P, d1))["ok"] is False
    assert _gewinde(bg, _messwerte(bg, 7.4, soll + 1.1 * _RING_P, d1))["ok"] is False


def test_koaxiales_gewinde_nicht_erreicht(tmp_path, monkeypatch):
    """AP 6.8: vorderes und hinteres Deckelgewinde des ADNM liegen auf einer Achse – das nicht erreichte hintere zählt
    nicht (vorher eine zweite Prüfung mit Soll 0 und dem Volumen des vorderen)."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    d1 = {"modell": "kernloch", "durchmesser": 4.134}
    soll = ueberlappung_soll(5, 0.8, 4.134, 7.4)
    m = _messwerte(bg, 7.4, soll, d1)
    m.gewindebohrungen.append({"teil": "motor", "feature": "flansch", "instanz": 2,
                               "eintritt": Messgeometrie("punkt", (L, 150.0, L))})
    bericht = bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))
    gewinde = [e for e in bericht["pruefungen"] if e["id"] == "gewinde:schraube.1"]
    assert len(gewinde) == 1 and gewinde[0]["ok"] is True
    assert next(e for e in bericht["pruefungen"] if e["id"] == "kollision")["ok"] is True
