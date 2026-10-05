import json

from swki.aenderungen import soll_parameter, soll_verknuepfungswerte
from swki.baugruppe.freigabe import freigeben_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import gewindebohrungen_teil, teil_messpunkte
from swki.konfig import lade_standard
from swki.pruefung.befehle import schreibe_pruefbericht, status
from swki.pruefung.bericht import bericht_markdown
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def test_gewindebohrungen_aus_dem_protokoll():
    protokoll = {"knoten": [{"id": "f1", "punkte": None}, {"id": "f2", "punkte": [[-30, 20, 0], [30, 20, 0]]},
                            {"id": "f3", "punkte": [[0, 20, -15]]}]}
    assert gewindebohrungen_teil(PLATTE, protokoll) == [{"feature": "f2", "instanz": 1, "punkt": (-30, 20, 0)},
                                                        {"feature": "f2", "instanz": 2, "punkt": (30, 20, 0)}]


def test_teil_messpunkte(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    bedarf = teil_messpunkte(bg)
    assert bedarf["platte.yaml"] == [{"feature": "f1", "flaeche": "-y"}]
    assert bedarf["deckel.yaml"] == [{"feature": "f1", "flaeche": "+y"}]
    assert bedarf["ISO4762_M8x16_8_8"] == [{"referenz": "EINBAU_EBENE"}]


def test_pruefbericht_verwirft_altes_urteil(tmp_path):
    spec_pfad = tmp_path / "A" / "probe.yaml"
    urteil = spec_pfad.parent / "protokolle" / "probe.lauf-1.pruefer.json"
    urteil.parent.mkdir(parents=True)
    urteil.write_text("{}", encoding="utf-8")
    ordner = tmp_path / "lauf-1"
    ordner.mkdir()
    schreibe_pruefbericht(spec_pfad, 1, ordner, bericht := {"bestanden": True, "maengel": []})
    assert not urteil.exists() and bericht["pruefer_urteil_verworfen"] is True
    assert json.loads((ordner / "pruefbericht.json").read_text(encoding="utf-8"))["bestanden"] is True


def test_status_einer_baugruppe(tmp_path):
    assert status(schreibe(tmp_path / "A"))["empfehlung"] == "bauen"


def test_bericht_abschnitte():
    bericht = {"maengel": [], "bilder": {}, "stueckliste": {"A_Platte.sldprt": 1},
               "normteile": {"ISO4762_M8x16_8_8": {"gebaut": False, "pruefsumme": "abc"}},
               "gewindepaarungen": [{"schraube": "schraube.1", "teil": "platte", "bohrung": "f2.1",
                                     "einschraublaenge": 9.6, "volumen": 133.1, "soll": 133.0, "gewindetiefe": 12}],
               "teilpruefungen": {"platte": {"bestanden": True, "maengel": 0}}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Stückliste", "| A_Platte.sldprt | 1 |", "## Normteile", "## Gewindepaarungen", "| schraube.1 |",
                 "## Teilprüfungen", "| platte | ja | 0 |"):
        assert teil in text


def test_soll_verknuepfungswerte(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0] = {**spec["verknuepfungen"][0], "typ": "abstand", "wert": "=ABST/7"}
    bg = lade_baugruppe(schreibe(tmp_path / "A", baugruppe=spec))
    assert soll_verknuepfungswerte(bg.spec, bg.quellen) == {"v1": 5.0}


def test_soll_verknuepfungswerte_nutzt_die_freigegebenen_parameter(tmp_path):
    """Spec 3b §8: Differenz zur freigegebenen Spec. Wurde ABST nach der Freigabe schon in der Spec geändert (begonnene
    Übernahme), muss der Soll-Wert der Verknüpfung trotzdem aus der Freigabe-Kopie (35) stammen, nicht aus der Spec (70)."""
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0] = {**spec["verknuepfungen"][0], "typ": "abstand", "wert": "=ABST/7"}
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    freigeben_baugruppe(lade_baugruppe(pfad))
    neu = kopie(spec)
    neu["parameter"]["ABST"] = 70
    schreibe(tmp_path / "A", baugruppe=neu)
    standard = lade_standard()
    soll = soll_parameter(pfad, "A", standard)
    assert soll["A_Probe.sldasm"]["ABST"] == 35 and soll["A_Probe.sldasm"]["verknuepfung:v1"] == 5.0
    bg = lade_baugruppe(pfad)
    assert soll_verknuepfungswerte(bg.spec, bg.quellen) == {"v1": 10.0}      # ohne Parameter: aktuelle Spec
    assert soll_verknuepfungswerte(bg.spec, bg.quellen, {"ABST": 35}) == {"v1": 5.0}


def test_freiheitsgrad_1_erlaubt_unterbestimmt():
    from swki.baugruppe.bewertung import _erlaubt_unterbestimmt

    spec = {"komponenten": [{"id": "schieber"}, {"id": "hebel"}], "freiheitsgrade": {"schieber": 1}}
    assert _erlaubt_unterbestimmt(spec, "schieber") and not _erlaubt_unterbestimmt(spec, "hebel")


def test_dokumente_der_grenzen_bleiben_offen(tmp_path):
    from swki.baugruppe import pruefen as pruefen_modul
    from swki.baugruppe.laden import lade_baugruppe
    from tests.baugruppe.beispiel_bewegung import schreibe as schreibe_bewegung

    bg = lade_baugruppe(schreibe_bewegung(tmp_path / "B"))
    assert pruefen_modul._dokumente_der_grenzen(bg) == {"schieber.yaml", "grundplatte.yaml", "hebel.yaml"}


def test_bericht_bewegungen():
    laeufe = [{"bewegung": "Hub", "grenz_id": "g1", "bereich": [0.0, 220.0], "gegen": {}, "stellungen": 17,
               "bewegt": ["schlitten", "hebel"], "kollisionen": 0, "grenze": {"oben": False, "unten": None}, "dauer_s": 12.5},
              {"bewegung": "Hub", "gegen": {"Schwenk": "max"}, "stellungen": 17, "bewegt": [], "kollisionen": 1,
               "grenze": {}, "dauer_s": 9.0}]
    pruefungen = [{"id": "endlage:Hub:schlitten", "ok": True, "knoten": []},
                  {"id": "sollweg:Hub:schlitten", "ok": False, "ist": {"erste_abweichung": {"stellung": 55.0}},
                   "hinweis": "weg bei 55", "knoten": ["schlitten"]},
                  {"id": "sollweg:Hub:hebel", "ok": None, "hinweis": "Lauf abgebrochen", "knoten": []}]
    bericht = {"maengel": [], "bilder": {}, "pruefungen": pruefungen,
               "bewegungen": {"laeufe": laeufe, "paare": [{"bewegungen": ["Hub", "Schwenk"], "schnitt": [0] * 6}]}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Bewegungen (letzter Lauf)",
                 "| Hub | g1 | 0 … 220 | Grundstellung | 17 | schlitten, hebel | 0 | wirkt / – | 12.5 |",
                 "| Hub | – | – | Schwenk auf max | 17 | – | 1 | – / – | 9.0 |", "Paarläufe für: Hub × Schwenk",
                 "## Endlagen und Sollweg (letzter Lauf)", "| endlage:Hub:schlitten | bestanden | – |",
                 "| sollweg:Hub:schlitten | Mangel | sollweg:Hub:schlitten: weg bei 55 |",
                 "| sollweg:Hub:hebel | nicht geprüft | sollweg:Hub:hebel: Lauf abgebrochen |"):
        assert teil in text, text


def test_bericht_ohne_gefahrene_bewegungen_hat_keinen_abschnitt():
    bericht = {"maengel": [], "bilder": {}, "bewegungen": {"laeufe": [], "paare": []}}
    assert "## Bewegungen" not in bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
