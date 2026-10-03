import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import bau
from swki.compiler.anker import AnkerFehler
from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, fehler_dict
from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.freigabe import freigeben_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.cli import SwkiFehler, main
from swki.compiler.bauen import BauAbbruch
from swki.compiler.protokoll import Protokoll
from swki.konfig import Rechner, lade_standard
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


def test_uebernommen_nach_neuer_freigabe_vermerkt_das_protokoll(umgebung, monkeypatch):
    r, pfad, aufrufe = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad), zeitpunkt="2026-10-03T09:00:00")
    ordner = lauf_ordner(r, "A", 1)
    ordner.mkdir(parents=True)
    (ordner / "A_Probe.sldasm").write_bytes(b"gebaut")
    from swki.aenderungen import pruefsummen

    protokoll = lauf_datei(pfad, 1, "protokoll")
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    protokoll.write_text(json.dumps({"status": "ok", "gestartet": "2026-10-03T10:00:00",
                                     "sha256": pruefsummen(ordner, [ordner / "A_Probe.sldasm"])}), encoding="utf-8")
    (ordner / "A_Probe.sldasm").write_bytes(b"von Hand geaendert")
    with pytest.raises(SwkiFehler) as e:                       # Freigabe (09:00) ist älter als der Lauf (10:00)
        bau.bauen(pfad, uebernommen=True)
    assert e.value.daten["code"] == "UEBERNAHME_OHNE_NEUE_FREIGABE" and aufrufe["verbinde"] == 0
    freigeben_baugruppe(lade_baugruppe(pfad), zeitpunkt="2026-10-03T12:00:00")
    vermerkt = []
    echt = bau.vermerke_befund
    monkeypatch.setattr(bau, "vermerke_befund", lambda p, b, v: (vermerkt.append((b, v)), echt(p, b, v)))
    with pytest.raises(_KeinSolidWorks):
        bau.bauen(pfad, uebernommen=True)
    assert vermerkt[0][0]["geaendert"] == ["A_Probe.sldasm"] and vermerkt[0][1] is False


def test_weiche_in_swki_bauen(capsys, umgebung, monkeypatch):
    _, pfad, _ = umgebung
    monkeypatch.setattr(bau, "bauen", lambda p, lauf, verwerfen, uebernommen: {
        "art": "baugruppe", "lauf": lauf, "verwerfen": verwerfen, "uebernommen": uebernommen})
    assert main(["bauen", str(pfad), "--lauf", "3", "--verwerfen"]) == 0
    assert json.loads(capsys.readouterr().out) == {"art": "baugruppe", "lauf": 3, "verwerfen": True, "uebernommen": False}
    assert main(["bauen", str(pfad), "--uebernommen"]) == 0
    assert json.loads(capsys.readouterr().out)["uebernommen"] is True


def _baulauf(pfad, tmp_path):
    bg = lade_baugruppe(pfad)
    standard = lade_standard()
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


def _kontexte(b, bg):
    for q in bg.quellen.values():
        b.kontexte[q.schluessel_dokument] = SimpleNamespace(model=SimpleNamespace(GetPathName="C:/x/Q.SLDPRT"))


def test_referenzfehler_nennt_komponente_und_verknuepfung(umgebung, tmp_path, monkeypatch):
    _, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    _kontexte(b, bg)

    def loese(ctx, seite):
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "Feature 'f2' fehlt im Teil")

    monkeypatch.setattr(bau, "loese_im_teil", loese)
    fehler = bau._verknuepfe(b, verknuepfungen(bg.spec, bg.quellen))
    d = fehler_dict(fehler)
    assert d["code"] == REFERENZ_NICHT_GEFUNDEN and d["schritt"] == "referenz"
    assert "deckel" in d["meldung"] and "v1" in d["meldung"] and "Feature 'f2' fehlt im Teil" in d["meldung"]
    assert b.protokoll.knoten[0].id == "v1" and b.protokoll.knoten[0].fehler == d
    assert {k.status for k in b.protokoll.knoten[1:]} == {"uebersprungen"}


def test_verknuepfungsfehler_aus_der_auswahl_nennt_knoten_id(umgebung, tmp_path, monkeypatch):
    _, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    monkeypatch.setattr(bau, "_entitaet", lambda b_, seite: object())

    def verknuepfe(*args, **kwargs):
        raise bau.BauFehler("VERKNUEPFUNG_FEHLER", "Auswahl für die Verknüpfung fehlgeschlagen", schritt="auswahl")

    monkeypatch.setattr(bau.sw_baugruppe, "verknuepfe", verknuepfe)
    d = fehler_dict(bau._verknuepfe(b, verknuepfungen(bg.spec, bg.quellen)))
    assert d["code"] == "VERKNUEPFUNG_FEHLER" and d["schritt"] == "auswahl"
    assert d["meldung"].startswith("Verknüpfung v1 (deckungsgleich)") and "Auswahl" in d["meldung"]


def test_unerwartete_ausnahme_beim_einfuegen_ist_komponente_fehler(umgebung, tmp_path, monkeypatch):
    _, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    _kontexte(b, bg)
    monkeypatch.setattr(bau.sw, "teilebox_mm", lambda model: [0] * 6)

    def fuege_ein(app, asm, p, box):
        raise RuntimeError("COM kaputt")

    monkeypatch.setattr(bau.sw_baugruppe, "fuege_ein", fuege_ein)
    d = fehler_dict(bau._fuege_ein(b, instanzen(bg.spec, bg.quellen)))
    assert d["code"] == "KOMPONENTE_FEHLER" and d["schritt"] == "einfuegen"
    assert "platte" in d["meldung"] and "A_Platte.sldprt" in d["meldung"] and "COM kaputt" in d["meldung"]
    assert b.protokoll.knoten[0].fehler == d


def _bauen_mit_attrappen(umgebung, monkeypatch, verknuepf_fehler=None):
    r, pfad, _ = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad))
    dok = [SimpleNamespace(name="teil1"), SimpleNamespace(name="teil2")]
    geschlossen = []

    def schliesse(app, model):
        geschlossen.append(model)
        if len(geschlossen) == 1:
            raise RuntimeError("Titel nicht lesbar")

    def teile(b, r_):
        b.offen.extend(dok)

    monkeypatch.setattr(bau, "verbinde", lambda jahr: object())
    monkeypatch.setattr(bau, "_baue_teile", teile)
    monkeypatch.setattr(bau, "_hole_normteile", lambda b, r_, tol: None)
    monkeypatch.setattr(bau, "_fuege_ein", lambda b, alle: None)
    monkeypatch.setattr(bau, "_verknuepfe", lambda b, alle: verknuepf_fehler)
    monkeypatch.setattr(bau.sw_baugruppe, "neue_baugruppe", lambda app, vorlage: SimpleNamespace(name="asm"))
    monkeypatch.setattr(bau, "globale_variablen", lambda *a: None)
    monkeypatch.setattr(bau, "setze_eigenschaften", lambda *a: None)
    monkeypatch.setattr(bau.sw, "speichere", lambda model, ziel: None)
    monkeypatch.setattr(bau.sw, "schliesse", schliesse)
    return r, pfad, dok, geschlossen


def test_schliessfehler_haelt_die_uebrigen_nicht_auf(umgebung, monkeypatch):
    r, pfad, dok, geschlossen = _bauen_mit_attrappen(umgebung, monkeypatch)
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(pfad)
    assert [g.name for g in geschlossen] == ["asm", "teil2", "teil1"]  # Baugruppe zuerst, Teile rückwärts
    assert e.value.daten["fehler"]["code"] == "SCHLIESSEN_FEHLER" and "Titel nicht lesbar" in e.value.daten["fehler"]["meldung"]
    assert (lauf_ordner(r, "A", 1) / "protokoll.json").is_file() and lauf_datei(pfad, 1, "protokoll").is_file()


def test_schliessfehler_verdeckt_den_urspruenglichen_fehler_nicht(umgebung, monkeypatch):
    original = bau.BauFehler("VERKNUEPFUNG_FEHLER", "v1: kaputt", schritt="verknuepfung")
    r, pfad, dok, geschlossen = _bauen_mit_attrappen(umgebung, monkeypatch, original)
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(pfad)
    assert len(geschlossen) == 3
    assert e.value.daten["fehler"] == {"code": "VERKNUEPFUNG_FEHLER", "schritt": "verknuepfung", "meldung": "v1: kaputt"}
    protokoll = json.loads(lauf_datei(pfad, 1, "protokoll").read_text(encoding="utf-8"))
    assert protokoll["status"] == "fehler" and protokoll["fehler"]["code"] == "VERKNUEPFUNG_FEHLER"


def test_abbruch_vor_dem_einfuegen_vermerkt_komponenten_als_uebersprungen(umgebung, monkeypatch):
    _, pfad, _ = umgebung
    bg = lade_baugruppe(pfad)
    freigeben_baugruppe(bg)
    monkeypatch.setattr(bau, "verbinde", lambda jahr: object())
    monkeypatch.setattr(bau, "_baue_teile",
                        lambda b, r_: bau.BauFehler("TEIL_BAU", "platte/f2: kaputt", schritt="teil"))
    monkeypatch.setattr(bau.sw, "schliesse", lambda app, model: None)
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(pfad)
    knoten = e.value.daten["knoten"]
    assert [k["id"] for k in knoten[:5]] == ["platte", "deckel", "schraube.1", "schraube.2", "stift"]
    assert {k["status"] for k in knoten} == {"uebersprungen"}
    assert len(knoten) == 5 + len(verknuepfungen(bg.spec, bg.quellen))


def test_fixierte_komponente_wird_zuerst_eingefuegt_und_fixiert(tmp_path, monkeypatch):
    from tests.baugruppe.beispiel import BAUGRUPPE, kopie

    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][1:] + spec["komponenten"][:1]  # fixierte Platte zuletzt in der Spec
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    b, bg = _baulauf(pfad, tmp_path)
    _kontexte(b, bg)
    for q in bg.quellen.values():
        b.dateien[f"teil:{q.datei}" if q.art == "teil" else f"normteil:{q.schluessel}"] = tmp_path / "x.sldprt"
    zaehler, fixiert = iter(range(1, 100)), []
    monkeypatch.setattr(bau.sw, "teilebox_mm", lambda model: [0] * 6)
    monkeypatch.setattr(bau.sw_baugruppe, "fuege_ein", lambda app, asm, p, box: SimpleNamespace(Name2=f"K-{next(zaehler)}"))
    monkeypatch.setattr(bau.sw_baugruppe, "fixiere", lambda asm, komp: fixiert.append(komp.Name2))
    assert bau._fuege_ein(b, instanzen(bg.spec, bg.quellen)) is None
    assert b.protokoll.komponenten[0]["id"] == "platte" and fixiert == ["K-1"]


def test_normteile_werden_kopiert_und_die_bibliothek_bleibt_unveraendert(umgebung, tmp_path, monkeypatch):
    r, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    bibliothek = tmp_path / "bibliothek"
    bibliothek.mkdir()
    pfade = {}
    for q in bg.quellen.values():
        if q.art == "normteil":
            pfade[(q.norm, q.hole_groesse)] = bibliothek / f"{q.schluessel}.sldprt"
            pfade[(q.norm, q.hole_groesse)].write_bytes(q.schluessel.encode())
    vorher = {p.name: p.read_bytes() for p in bibliothek.iterdir()}
    monkeypatch.setattr(bau.normteil_befehle, "hole",
                        lambda norm, groesse, variante: {"pfad": str(pfade[(norm, groesse)]), "gebaut": False})
    monkeypatch.setattr(bau, "bibliotheksordner", lambda r_: bibliothek)
    monkeypatch.setattr(bau, "lies_eintrag", lambda ordner, schluessel: {"pruefsumme": "abc"})
    monkeypatch.setattr(bau, "oeffne", lambda app, p: SimpleNamespace(pfad=Path(p)))
    monkeypatch.setattr(bau, "kontext_aus_datei", lambda app, model, spec, p, tol, prot: SimpleNamespace(model=model))
    assert bau._hole_normteile(b, r, 0.01) is None
    assert {p.name: p.read_bytes() for p in bibliothek.iterdir()} == vorher  # nichts in die Bibliothek geschrieben
    assert {p.name for p in b.ordner.iterdir()} == set(vorher)               # Kopien im Lauf-Ordner
    assert all(m.pfad.parent == b.ordner for m in b.offen)                  # geöffnet werden nur die Kopien
