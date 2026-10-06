import json

import pytest
import yaml

from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.freigabe import freigeben_baugruppe, pruefe_freigabe_baugruppe, teil_summen
from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import dokument_name
from swki.kaufteile.eintrag import freigeben as freigeben_eintrag
from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, pruefsumme
from swki.spec.laden import SpecFehler
from tests.baugruppe.beispiel_kaufteil import katalog, kopie, schreibe
from tests.kaufteile.beispiel import EINTRAG, kopie as eintrag_kopie, schreibe as schreibe_eintrag


def _befunde(pfad) -> list[str]:
    with pytest.raises(SpecFehler) as e:
        lade_baugruppe(pfad)
    return [f"{b['pfad']}: {b['meldung']}" for b in e.value.daten["befunde"]]


def test_laedt_kaufteil(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    q = bg.quellen["motor"]
    assert (q.art, q.schluessel, q.kaufteil) == ("kaufteil", "SWKI-MUSTER_GM42-10", "SWKI-MUSTER GM42-10")
    assert q.referenzen == {"EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE"} and q.eintrag == EINTRAG
    assert list(q.spec["gewinde"]) == ["flansch"] and list(bg.teile) == ["halter.yaml"]
    assert dokument_name(q, "A", {"namensschema": {"datei": "{auftrag}_{name}"}}) == "SWKI-MUSTER_GM42-10.sldprt"
    assert hinweise_baugruppe(bg) == []


def test_unbekannt_nicht_freigegeben_ungeprueft(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch, geprueft=False)
    spec = kopie()
    [b] = _befunde(schreibe(tmp_path / "A", spec))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_UNGEPRUEFT")
    spec["komponenten"][1]["quelle"] = {"kaufteil": "SWKI-MUSTER GM99"}
    [b] = _befunde(schreibe(tmp_path / "B", spec))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_UNBEKANNT")
    anders = eintrag_kopie()
    anders["koerper"] = 3
    schreibe_eintrag(tmp_path / "kat", anders)  # geändert, nicht neu freigegeben
    [b] = _befunde(schreibe(tmp_path / "C"))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_NICHT_FREIGEGEBEN")


def test_kaufteil_nur_ueber_einbau_und_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = kopie()
    spec["verknuepfungen"][0]["a"] = {"komponente": "motor", "feature": "f1", "flaeche": "+y"}
    spec["verknuepfungen"][1]["a"] = {"komponente": "motor", "referenz": "EINBAU_FEHLT"}
    spec["verknuepfungen"][2]["b"] = {"komponente": "halter", "gewinde": "flansch", "instanz": 1, "achse": True}
    befunde = _befunde(schreibe(tmp_path / "A", spec))
    assert befunde[0].startswith("verknuepfungen[0].a: motor ist ein Kaufteil: nur über Einbaureferenzen")
    assert befunde[1].startswith("verknuepfungen[1].a.referenz: SWKI-MUSTER GM42-10 hat keine Einbaureferenz 'EINBAU_FEHLT'")
    assert befunde[2] == "verknuepfungen[2].b.gewinde: halter ist kein Kaufteil: Gewindepositionen nur bei Kaufteilen"


def _ins_gewinde(spec: dict, groesse: str = "M5x12") -> dict:
    spec["komponenten"][2] = {"id": "schraube", "quelle": {"normteil": f"ISO 4762 {groesse}"},
                              "je_position": {"komponente": "motor", "gewinde": "flansch"}}
    spec["verknuepfungen"][3]["b"] = {"komponente": "halter", "feature": "f1", "flaeche": "-y"}
    spec["verknuepfungen"][4]["b"] = {"komponente": "motor", "gewinde": "flansch", "instanz": "je", "achse": True}
    return spec


def test_je_position_auf_kaufteil_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    assert [i.id for i in instanzen(bg.spec, bg.quellen)][2:] == ["schraube.1", "schraube.2", "schraube.3", "schraube.4"]
    v = {x.id: x for x in verknuepfungen(bg.spec, bg.quellen)}
    assert v["v5.3"].b == {"komponente": "motor", "gewinde": "flansch", "instanz": 3, "achse": True}
    assert v["v5.3"].drehung_sperren is True and v["v2"].drehung_sperren is False


def test_gewinde_befunde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = _ins_gewinde(kopie())
    spec["komponenten"][2]["je_position"] = {"komponente": "halter", "gewinde": "flansch"}
    assert "komponenten[2].je_position.komponente: 'halter' ist kein Kaufteil (gewinde)" in _befunde(schreibe(tmp_path / "A", spec))
    spec = _ins_gewinde(kopie())
    spec["komponenten"][2]["je_position"]["gewinde"] = "fuss"
    assert _befunde(schreibe(tmp_path / "B", spec))[0] == ("komponenten[2].je_position.gewinde: SWKI-MUSTER GM42-10 hat "
                                                         "keine Gewindegruppe 'fuss'")


def test_passung_im_kaufteil_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    [b] = _befunde(schreibe(tmp_path / "A", _ins_gewinde(kopie(), "M6x12")))
    assert b == "verknuepfungen[4]: Passung: ISO 4762 M6 passt nicht in Gewinde M5 von SWKI-MUSTER GM42-10"


def test_hinweis_drehlage_doppelt(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = kopie()
    del spec["verknuepfungen"][1]["drehung_sperren"]
    [h] = hinweise_baugruppe(lade_baugruppe(schreibe(tmp_path / "A", spec)))
    assert (h["art"], h["pfad"]) == ("drehlage_doppelt", "verknuepfungen[1].drehung_sperren")


def test_freigabe_schuetzt_den_eintrag(tmp_path, monkeypatch):
    eintrag_pfad = katalog(tmp_path / "kat", monkeypatch)
    pfad = schreibe(tmp_path / "A")
    bg = lade_baugruppe(pfad)
    assert teil_summen(bg)["kaufteil:SWKI-MUSTER GM42-10"] == pruefsumme(EINTRAG)
    freigeben_baugruppe(bg)
    daten = json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))
    assert daten["motorprobe.yaml"]["kaufteile"] == {"kaufteil:SWKI-MUSTER GM42-10": pruefsumme(EINTRAG)}
    pruefe_freigabe_baugruppe(bg)
    anders = eintrag_kopie()
    anders["pruefung"]["huellquader"]["tol"] = 0.2
    schreibe_eintrag(tmp_path / "kat", anders)
    freigeben_eintrag(eintrag_pfad)  # der Eintrag ist neu freigegeben, die Baugruppe nicht
    katalog(tmp_path / "kat", monkeypatch, anders)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_baugruppe(lade_baugruppe(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET" and str(e.value).startswith("SWKI-MUSTER GM42-10: Katalogeintrag")


def test_baugruppe_ohne_kaufteile_unveraendert(tmp_path):
    from tests.baugruppe.beispiel import schreibe as schreibe_probe

    pfad = schreibe_probe(tmp_path / "A")
    eintrag = freigeben_baugruppe(lade_baugruppe(pfad))
    assert "kaufteile" not in json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))["probe.yaml"]
    assert set(eintrag) == {"pruefsumme", "freigegeben", "kopie_sha256", "teile"}
    assert yaml.safe_load((tmp_path / "A" / "probe.freigegeben.yaml").read_text(encoding="utf-8"))["name"] == "Probe"
