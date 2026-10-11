"""swki durchlauf ohne SolidWorks: Schritte, Abbruch im richtigen Schritt, kompakte Ausgabe."""

from pathlib import Path

import pytest

from swki import durchlauf as d
from swki.cli import SwkiFehler


class _BauAbbruch(SwkiFehler):
    def __init__(self, daten):
        super().__init__("abbruch")
        self.daten = daten


@pytest.fixture
def schritte(monkeypatch):
    aufrufe = []
    import swki.compiler.bauen as cb
    import swki.pruefung.befehle as pb
    import swki.spec.befehle as sb

    monkeypatch.setattr(sb, "_validieren", lambda a: aufrufe.append("validieren") or {"gueltig": True, "hinweise": []})
    monkeypatch.setattr(sb, "_freigeben", lambda a: aufrufe.append("freigeben") or {"kopie": "x.freigegeben.yaml"})
    monkeypatch.setattr(cb, "_bauen", lambda a: aufrufe.append("bauen") or {"lauf": 3, "dauer_s": 12.0})
    monkeypatch.setattr(cb, "BauAbbruch", _BauAbbruch)
    bericht = {"bestanden": True, "maengel": [], "pruefungen": [{"id": "volumen", "ok": True}, {"id": "v", "ok": None}],
               "bilder": {"iso": "C:/l/bilder/iso.png"}, "steckbrief_text": "Zeile 1\nZeile 2"}
    monkeypatch.setattr(pb, "pruefen", lambda s, n: aufrufe.append(f"pruefen {n}") or bericht)
    monkeypatch.setattr(pb, "status", lambda s, m: {"empfehlung": "pruefer_fehlt", "text": "t"})
    return aufrufe


def test_alle_schritte_in_reihenfolge(schritte, tmp_path):
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert schritte == ["validieren", "freigeben", "bauen", "pruefen 3"]
    assert erg["schritt"] == "fertig" and erg["lauf"] == 3 and erg["pruefung"]["bestanden"] is True
    assert erg["pruefung"]["ohne_urteil"] == ["v"] and erg["pruefung"]["steckbrief"] == ["Zeile 1", "Zeile 2"]
    assert erg["pruefung"]["bilder"] == [str(Path("C:/l/bilder"))]
    assert "Prüfe Lauf 3 von a.yaml" in erg["pruefer_auftrag"] and "Prüfbericht:" in erg["pruefer_auftrag"]


def test_ohne_freigeben_kein_freigabeschritt(schritte, tmp_path):
    d.durchlauf(tmp_path / "a.yaml")
    assert "freigeben" not in schritte


def test_bauabbruch_endet_im_schritt_bauen(schritte, monkeypatch, tmp_path):
    import swki.compiler.bauen as cb

    def wirf(a):
        raise _BauAbbruch({"lauf": 4, "fehler": {"code": "X", "schritt": "f2", "meldung": "m"},
                           "knoten": [{"id": "f1", "status": "ok"}, {"id": "f2", "status": "fehler"}]})
    monkeypatch.setattr(cb, "_bauen", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml")
    assert erg["schritt"] == "bauen" and erg["code"] == "X" and [k["id"] for k in erg["knoten"]] == ["f2"]


def test_validierfehler_endet_vor_dem_bau(schritte, monkeypatch, tmp_path):
    import swki.spec.befehle as sb

    def wirf(a):
        raise SwkiFehler("Schema: x fehlt")
    monkeypatch.setattr(sb, "_validieren", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert erg["schritt"] == "validieren" and "bauen" not in schritte


def test_pruefwert_hinweis_stoppt_vor_der_freigabe(schritte, monkeypatch, tmp_path):
    """Ein Prüfwert, der von der Rechnung aus den Features abweicht, würde nach der Freigabe eine neue Freigabe kosten."""
    import swki.spec.befehle as sb

    hinweis = {"art": "pruefwert", "pfad": "pruefung.huellquader", "meldung": "weicht ab"}
    monkeypatch.setattr(sb, "_validieren", lambda a: schritte.append("validieren") or {"gueltig": True,
                                                                                          "hinweise": [hinweis]})
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True)
    assert erg["schritt"] == "validieren" and erg["pruefwerte"] == [hinweis]
    assert schritte == ["validieren"]


# --- SWKI-10: --neustart (SolidWorks frisch vor Bauen und vor Prüfen) ---

_NEUSTART = {"privat_mb_vorher": 5321.4, "beendet_s": 4.2, "gestartet_s": 31.0, "instanzen": 1, "dokumente": 0,
             "privat_mb": 812.0, "einstellungen": {"toggle_10": False, "integer_6": 1}, "einstellungen_ok": True}


@pytest.fixture
def neustarts(schritte, monkeypatch):
    import werkzeuge.sw_neustart as wn

    monkeypatch.setattr(wn, "neustart", lambda r=None: schritte.append("neustart") or dict(_NEUSTART))
    return schritte


def test_neustart_vor_bauen_und_vor_pruefen(neustarts, tmp_path):
    erg = d.durchlauf(tmp_path / "a.yaml", freigeben=True, neustart=True)
    assert neustarts == ["validieren", "freigeben", "neustart", "bauen", "neustart", "pruefen 3"]
    assert erg["schritt"] == "fertig"
    assert [n["vor"] for n in erg["neustart"]] == ["bauen", "pruefen"]


def test_ohne_option_kein_neustart(neustarts, tmp_path):
    d.durchlauf(tmp_path / "a.yaml")
    assert "neustart" not in neustarts


def test_bauabbruch_mit_neustart_prueft_nicht_und_startet_nicht_erneut(neustarts, monkeypatch, tmp_path):
    import swki.compiler.bauen as cb

    def wirf(a):
        neustarts.append("bauen")
        raise _BauAbbruch({"lauf": 4, "fehler": {"code": "X", "schritt": "v1", "meldung": "m"}, "knoten": []})
    monkeypatch.setattr(cb, "_bauen", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml", neustart=True)
    assert neustarts == ["validieren", "neustart", "bauen"] and erg["schritt"] == "bauen"


def test_neustart_abgelehnt_endet_vor_dem_bau(neustarts, monkeypatch, tmp_path):
    """Offene fremde Dokumente: sw_neustart lehnt ab – dann nicht bauen, Grund melden."""
    import werkzeuge.sw_neustart as wn

    def lehnt_ab(r=None):
        raise wn.NeustartFehler("2 Dokument(e) offen – kein Neustart (fremde Dokumente nie schließen)")
    monkeypatch.setattr(wn, "neustart", lehnt_ab)
    erg = d.durchlauf(tmp_path / "a.yaml", neustart=True)
    assert erg["schritt"] == "neustart" and erg["vor"] == "bauen" and "Dokument(e) offen" in erg["fehler"]
    assert "bauen" not in neustarts


def test_neustart_vor_pruefen_abgelehnt_nennt_den_lauf(neustarts, monkeypatch, tmp_path):
    import werkzeuge.sw_neustart as wn

    zaehler = []

    def zweiter_scheitert(r=None):
        zaehler.append(1)
        if len(zaehler) == 2:
            raise wn.NeustartFehler("SolidWorks beendet sich nicht (120 s)")
        return dict(_NEUSTART)
    monkeypatch.setattr(wn, "neustart", zweiter_scheitert)
    erg = d.durchlauf(tmp_path / "a.yaml", neustart=True)
    assert erg["schritt"] == "neustart" and erg["vor"] == "pruefen" and erg["lauf"] == 3
    assert not any(s.startswith("pruefen") for s in neustarts)


def test_neustart_mit_falschen_einstellungen_endet_vor_dem_bau(neustarts, monkeypatch, tmp_path):
    """einstellungen_ok muss true sein (Skill baugruppe §4) – sonst fragt SolidWorks beim Bau nach Maßen."""
    import werkzeuge.sw_neustart as wn

    monkeypatch.setattr(wn, "neustart", lambda r=None: {**_NEUSTART, "einstellungen": {"toggle_10": True, "integer_6": 1},
                                                        "einstellungen_ok": False})
    erg = d.durchlauf(tmp_path / "a.yaml", neustart=True)
    assert erg["schritt"] == "neustart" and erg["vor"] == "bauen" and "bauen" not in neustarts
    assert erg["einstellungen"] == {"toggle_10": True, "integer_6": 1}


def test_bauabbruch_kompakt_mit_code_meldung_und_nur_auffaelligen_knoten(schritte, monkeypatch, tmp_path):
    import swki.compiler.bauen as cb

    def wirf(a):
        raise _BauAbbruch({"status": "fehler", "lauf": 5, "ordner": "C:/x", "dateien": {"baugruppe": "C:/x/a.sldasm"},
                           "fehler": {"code": "VERKNUEPFUNG_FEHLER", "schritt": "v3", "meldung": "v3: Fläche fehlt"},
                           "knoten": [{"id": "grundplatte/f1", "status": "ok", "sw_name": "Boss1"},
                                      {"id": "v3", "status": "fehler", "sw_name": None},
                                      {"id": "v4", "status": "uebersprungen", "sw_name": None}],
                           "dauer_s": 80.0})
    monkeypatch.setattr(cb, "_bauen", wirf)
    erg = d.durchlauf(tmp_path / "a.yaml")
    assert erg["schritt"] == "bauen" and erg["lauf"] == 5
    assert erg["code"] == "VERKNUEPFUNG_FEHLER" and erg["meldung"] == "v3: Fläche fehlt"
    assert [k["id"] for k in erg["knoten"]] == ["v3"]


def test_cli_option_neustart(monkeypatch):
    from swki import cli

    gesehen = {}
    monkeypatch.setattr(d, "durchlauf", lambda s, f, m, neustart=False: gesehen.update(neustart=neustart) or {})
    assert cli.main(["durchlauf", "a.yaml", "--neustart"]) == 0 and gesehen == {"neustart": True}
    assert cli.main(["durchlauf", "a.yaml"]) == 0 and gesehen == {"neustart": False}
