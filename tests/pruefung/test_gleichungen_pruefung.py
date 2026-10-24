"""Prüfpunkt gleichungen (Spec Bemaßungsbezug §4): ohne Schalter gleichungen darf das Modell keine Gleichungen und
globalen Variablen haben (GLEICHUNGEN_VORHANDEN)."""

from swki.baugruppe.aufloesen import verknuepfungen
from swki.baugruppe.bewertung import bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.pruefung.bewertung import bewerte
from tests.baugruppe.beispiel import schreibe
from tests.baugruppe.test_bewertung_baugruppe import STANDARD as STANDARD_BG, _messwerte as _messwerte_bg
from tests.pruefung.test_bewertung import SPEC, STANDARD, _messwerte


def _eintrag(bericht: dict) -> dict | None:
    return next((p for p in bericht["pruefungen"] if p["id"] == "gleichungen"), None)


def test_ohne_gleichungen_ok():
    bericht = bewerte(SPEC, _messwerte(gleichungen=0), STANDARD)
    eintrag = _eintrag(bericht)
    assert eintrag["ok"] is True and eintrag["ist"] == 0
    assert bericht["bestanden"], bericht["maengel"]


def test_gleichungen_vorhanden_ist_mangel():
    bericht = bewerte(SPEC, _messwerte(gleichungen=3), STANDARD)
    assert _eintrag(bericht)["ok"] is False and _eintrag(bericht)["ist"] == 3
    mangel = next(m for m in bericht["maengel"] if m["pruefung"] == "gleichungen")
    assert "GLEICHUNGEN_VORHANDEN: 3 Gleichungen" in mangel["beschreibung"]
    assert bericht["bestanden"] is False


def test_mit_gleichungen_an_kein_pruefpunkt():
    spec = {**SPEC, "gleichungen": True}
    bericht = bewerte(spec, _messwerte(gleichungen=3), STANDARD)
    assert _eintrag(bericht) is None
    assert bericht["bestanden"], bericht["maengel"]
    # auch der Standard schaltet sie an
    bericht = bewerte(SPEC, _messwerte(gleichungen=3), {**STANDARD, "gleichungen": True})
    assert _eintrag(bericht) is None and bericht["bestanden"]


def test_baugruppe_prueft_nur_baugruppendokument(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    soll = stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD_BG)

    def bewerte_bg(m, spec=None):
        return bewerte_baugruppe(spec or bg.spec, bg.quellen, m, STANDARD_BG, soll)

    # Normteil-Komponenten mit globalen Variablen stehen nur in den Teilberichten bzw. gar nicht in den Messwerten:
    # das Baugruppendokument selbst ist leer → ok
    bericht = bewerte_bg(_messwerte_bg(bg, gleichungen=0))
    assert _eintrag(bericht)["ok"] is True
    assert bericht["bestanden"], bericht["maengel"]

    bericht = bewerte_bg(_messwerte_bg(bg, gleichungen=2))
    mangel = next(m for m in bericht["maengel"] if m["pruefung"] == "gleichungen")
    assert "GLEICHUNGEN_VORHANDEN: 2 Gleichungen" in mangel["beschreibung"]

    spec = {**bg.spec, "gleichungen": True}
    assert _eintrag(bewerte_bg(_messwerte_bg(bg, gleichungen=2), spec)) is None


def test_baugruppe_teilbericht_eigenteil_mit_mangel_bleibt_sichtbar(tmp_path):
    """Gleichungen in einem Eigenteil melden dessen Teilprüfung (Präfix <komponente>:), nicht das Baugruppendokument."""
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    soll = stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD_BG)
    teil = bewerte(SPEC, _messwerte(gleichungen=1), STANDARD)
    m = _messwerte_bg(bg, teilberichte={"platte.yaml": teil, "deckel.yaml": bewerte(SPEC, _messwerte(), STANDARD)})
    bericht = bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD_BG, soll)
    ids = {mg["pruefung"] for mg in bericht["maengel"]}
    assert "platte: gleichungen" in ids and "gleichungen" not in ids
