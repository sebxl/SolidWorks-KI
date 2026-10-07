import json

import pytest
import yaml

from swki.cli import main
from swki.kaufteile import katalog
from swki.kaufteile.eintrag import eintrag_befunde, hinweise_eintrag, lade_eintrag
from swki.kaufteile.fehler import KaufteilFehler
from swki.spec.freigabe import FreigabeFehler, pruefe_freigabe, pruefsumme
from swki.spec.laden import SpecFehler
from tests.kaufteile.beispiel import EINTRAG, kopie, schreibe


def _meldungen(spec, pfad=None) -> list[str]:
    return [f"{b['pfad']}: {b['meldung']}" for b in eintrag_befunde(spec, pfad)]


def test_namen_im_katalog():
    assert katalog.ordnername("SWKI Muster/AG") == "swki-muster-ag"
    assert katalog.dateiname("GM42-10/A") == "gm42-10_a"
    assert katalog.bibliotheksschluessel("SWKI-MUSTER", "GM42 10.1") == "SWKI-MUSTER_GM42_10_1"
    assert katalog.teile_schluessel(" SWKI-MUSTER  GM42 10 ") == ("SWKI-MUSTER", "GM42 10")


def test_finde_und_unbekannt(tmp_path):
    pfad = schreibe(tmp_path)
    assert pfad == tmp_path / "swki-muster" / "gm42-10.yaml"
    assert katalog.finde("SWKI-MUSTER GM42-10", tmp_path) == pfad
    assert katalog.vorhandene(tmp_path) == ["SWKI-MUSTER GM42-10"]
    with pytest.raises(KaufteilFehler) as e:
        katalog.finde("SWKI-MUSTER GM42-20", tmp_path)
    assert e.value.daten["code"] == "KAUFTEIL_UNBEKANNT" and e.value.daten["vorhanden"] == ["SWKI-MUSTER GM42-10"]
    with pytest.raises(KaufteilFehler):
        katalog.finde("swki-muster gm42-10", tmp_path)  # Schreibweise des Eintrags zählt


def test_gueltiger_eintrag(tmp_path):
    pfad = schreibe(tmp_path)
    assert lade_eintrag(pfad) == EINTRAG
    assert hinweise_eintrag(EINTRAG) == []


def test_lage_im_katalog(tmp_path):
    spec = kopie()
    pfad = schreibe(tmp_path, spec)
    falsch = pfad.with_name("anders.yaml")
    pfad.rename(falsch)
    assert _meldungen(spec, falsch) == ["(Datei): Eintrag gehört nach swki-muster/gm42-10.yaml (Hersteller und Bestellnummer)"]


def test_datum_muss_text_sein():
    spec = kopie()
    spec["original"]["bezug"]["datum"] = yaml.safe_load("d: 2026-10-07")["d"]
    [meldung] = _meldungen(spec)
    assert meldung.startswith("original.bezug.datum")


@pytest.mark.parametrize("stelle", ["original", "datenblatt", "beleg"])
def test_url_braucht_schema(stelle):
    """Ohne http(s):// wäre die Domain leer und die Belegregel (≥ 2 Domains) umgehbar."""
    spec = kopie()
    if stelle == "original":
        spec["original"]["bezug"] = {"art": "url", "url": "haendler.de/x", "datum": "2026-10-07"}
    elif stelle == "datenblatt":
        spec["datenblatt"] = {"datei": "datenblatt.md", "url": "www.hersteller.de/d.pdf"}
    else:
        spec["belege"]["d1"] = {"art": "hersteller", "url": "hersteller.de/d.pdf", "abgerufen": "2026-10-07"}
    meldungen = _meldungen(spec)
    assert meldungen and any("url" in m for m in meldungen), meldungen
    assert not _meldungen(kopie())


def test_einbau_bezuege():
    spec = kopie()
    spec["einbau"]["EINBAU_ACHSE"]["zylinder"]["senkrecht_zu"] = "EINBAU_ACHSE"
    spec["einbau"]["EINBAU_DREHLAGE"]["ebene_durch_achse"]["achse"] = "EINBAU_FLANSCH"
    spec["einbau"]["EINBAU_FLANSCH"]["ebene"]["normale"] = [0, 0, 0]
    assert _meldungen(spec) == [
        "einbau.EINBAU_ACHSE.zylinder.senkrecht_zu: 'EINBAU_ACHSE' ist keine ebene-Referenz dieses Eintrags",
        "einbau.EINBAU_FLANSCH.ebene.normale: Normale darf nicht der Nullvektor sein",
        "einbau.EINBAU_DREHLAGE.ebene_durch_achse.achse: 'EINBAU_FLANSCH' ist keine zylinder-Referenz dieses Eintrags",
    ]


def test_gewinde_befunde():
    spec = kopie()
    g = spec["gewinde"]["flansch"]
    g["groesse"], g["gewindetiefe"] = "M7", 12
    g["positionen"].append(list(g["positionen"][0]))
    assert _meldungen(spec) == [
        "gewinde.flansch.groesse: Gewinde M7 nicht in swki/wissen/bohrungsnormen.yaml",
        "gewinde.flansch.gewindetiefe: gewindetiefe darf nicht größer als tiefe sein",
        "gewinde.flansch.positionen[4]: Position 5 ist doppelt",
    ]


def test_messpunkte_und_namen():
    spec = kopie()
    pr = spec["pruefung"]
    pr["durchmesser_pruefen"][0]["referenz"] = "EINBAU_FLANSCH"
    pr["masse_pruefen"][0]["von"] = {"referenz": "EINBAU_FEHLT"}
    pr["masse_pruefen"][1]["zu"] = {"gewinde": "flansch", "instanz": 5}
    pr["durchmesser_pruefen"][1]["was"] = "Wellen-Ø"
    assert _meldungen(spec) == [
        "pruefung.durchmesser_pruefen[0].referenz: 'EINBAU_FLANSCH' ist keine zylinder-Referenz dieses Eintrags",
        "pruefung.masse_pruefen[0].von.referenz: Einbaureferenz 'EINBAU_FEHLT' fehlt unter einbau",
        "pruefung.masse_pruefen[1].zu.instanz: flansch hat nur 4 Positionen",
        "pruefung.durchmesser_pruefen[1].was: was 'Wellen-Ø' ist doppelt",
    ]


@pytest.mark.parametrize(("belege", "befund"), [
    ({"h1": {"art": "hersteller", "url": "https://hersteller.de/gm42", "abgerufen": "2026-10-07"}}, None),
    ({"h1": {"art": "nutzer", "hinweis": "im Chat"}}, None),
    ({"h1": {"art": "haendler", "url": "https://shop-a.de/x", "abgerufen": "2026-10-07"}}, "BELEG_UNZUREICHEND"),
    ({"h1": {"art": "haendler", "url": "https://www.shop-a.de/x", "abgerufen": "2026-10-07"},
      "h2": {"art": "haendler", "url": "https://shop-a.de/y", "abgerufen": "2026-10-07"}}, "BELEG_UNZUREICHEND"),
    ({"h1": {"art": "haendler", "url": "https://shop-a.de/x", "abgerufen": "2026-10-07"},
      "h2": {"art": "haendler", "url": "https://shop-b.com/y", "abgerufen": "2026-10-07"}}, None),
])
def test_belegregel(belege, befund):
    spec = kopie()
    spec["belege"] = belege
    spec["masse"]["beleg"] = list(belege)
    meldungen = [m for m in _meldungen(spec) if m.startswith("masse.")]
    if befund is None:
        assert meldungen == []
    else:
        [m] = meldungen
        assert befund in m


def test_beleg_fehlt_unter_belege():
    spec = kopie()
    spec["pruefung"]["huellquader"]["beleg"] = ["x9"]
    assert _meldungen(spec) == ["pruefung.huellquader.beleg: Beleg x9 fehlt unter belege"]


@pytest.mark.parametrize(("feld", "text", "genormt"), [
    ("benennung", "Zylinderschraube DIN 912 M5", True),
    ("bestellnummer", "ISO4762-M5x12", True),
    ("benennung", "Scheibe DIN 125-1 A", True),
    ("benennung", "Zylinderschraube DIN 912-12", True),
    ("benennung", "Schraube DIN912-10", True),
    ("bestellnummer", "ISO 4762-10", True),
    ("benennung", "Scheibe ISO 7089-8", True),
    ("benennung", "Scheibe DIN 125-8,4", True),
    ("benennung", "Rillenkugellager DIN 625 6001-2RS", False),
    ("benennung", "Rillenkugellager DIN 625-1", False),
])
def test_schutzregel(feld, text, genormt):
    spec = kopie()
    spec[feld] = text
    meldungen = [m for m in _meldungen(spec) if "KAUFTEIL_GENORMT" in m]
    assert bool(meldungen) is genormt


def test_hinweise_ohne_belege_und_masse():
    spec = kopie()
    del spec["masse"]
    for d in (spec["pruefung"]["huellquader"], *spec["pruefung"]["durchmesser_pruefen"],
              *spec["pruefung"]["masse_pruefen"], spec["gewinde"]["flansch"]):
        del d["beleg"]
    arten = [h["art"] for h in hinweise_eintrag(spec)]
    assert arten == ["nicht_belegt"] * 6 + ["kennmasse_nicht_belegt", "masse_aus_material"]


def _cli(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_und_freigeben_ueber_die_weiche(tmp_path, capsys):
    pfad = schreibe(tmp_path)
    code, v = _cli(capsys, "validieren", str(pfad))
    assert code == 0 and v["art"] == "kaufteil" and v["schluessel"] == "SWKI-MUSTER GM42-10" and v["hinweise"] == []
    code, f = _cli(capsys, "freigeben", str(pfad))
    assert code == 0 and f["pruefsumme"] == pruefsumme(EINTRAG) == v["pruefsumme"]
    assert (pfad.parent / "freigabe.json").is_file() and (pfad.parent / "gm42-10.freigegeben.yaml").is_file()
    pruefe_freigabe(pfad, EINTRAG)


def test_freigabe_deckt_den_ganzen_eintrag(tmp_path):
    pfad = schreibe(tmp_path)
    main(["freigeben", str(pfad)])
    anders = kopie()
    anders["einbau"]["EINBAU_FLANSCH"]["ebene"]["nahe"] = [26, 0, 25]
    assert pruefsumme(anders) != pruefsumme(EINTRAG)
    schreibe(tmp_path, anders)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, lade_eintrag(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_ungueltiger_eintrag_meldet_befunde(tmp_path, capsys):
    spec = kopie()
    spec["koerper"] = 0
    pfad = schreibe(tmp_path, spec)
    with pytest.raises(SpecFehler):
        lade_eintrag(pfad)
    code, v = _cli(capsys, "validieren", str(pfad))
    assert code == 1 and v["befunde"][0]["pfad"] == "koerper"


def test_eigenschaften_und_angaben_fuer_bericht():
    from swki.kaufteile.eintrag import angaben_fuer_bericht, eigenschaften

    assert eigenschaften(EINTRAG) == {"Ersteller": "SolidWorks-KI", "Benennung": "Getriebemotor GM42-10",
                                      "Hersteller": "SWKI-MUSTER", "Bestellnummer": "GM42-10"}
    assert angaben_fuer_bericht(EINTRAG) == {"masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
    ohne = kopie()
    del ohne["masse"]
    for d in (ohne["pruefung"]["huellquader"], *ohne["pruefung"]["durchmesser_pruefen"],
              *ohne["pruefung"]["masse_pruefen"], ohne["gewinde"]["flansch"]):
        del d["beleg"]
    assert angaben_fuer_bericht(ohne) == {"masse": "aus Material geschätzt", "kennmasse": "nicht belegt"}
