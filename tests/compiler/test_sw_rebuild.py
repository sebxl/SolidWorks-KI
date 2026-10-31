"""sw.rebuild mit bekannten Fehlern (Plan Bestandsdateien, Review Focus 2): Eine fremde Datei hat schon Neuaufbau-Fehler, die
weder den Bau noch die Handler-internen Neuaufbauten stoppen dürfen; neue Fehler schon."""

from types import SimpleNamespace

import pytest

from swki.compiler import sw
from swki.compiler.fehler import REBUILD_FEHLER, BauFehler


def model_mit_fehler(*fehler, ok=None):
    """fehler: (Feature, Code) oder (Feature, Code, Warnung)."""
    zeilen = [(*f, False)[:3] for f in fehler]

    def lies(features, codes, warnungen):
        features.value = tuple(SimpleNamespace(Name=f) for f, _, _ in zeilen)
        codes.value = tuple(c for _, c, _ in zeilen)
        warnungen.value = tuple(w for _, _, w in zeilen)

    return SimpleNamespace(EditRebuild3=(not zeilen) if ok is None else ok,
                           Extension=SimpleNamespace(GetWhatsWrongCount=len(zeilen), GetWhatsWrong=lies))


def test_rebuild_ignoriert_bekannte_fehler():
    model = model_mit_fehler(("Fase3", 12))
    with sw.bekannte_fehler({"Fase3"}):
        sw.rebuild(model)
    with pytest.raises(BauFehler) as e:
        sw.rebuild(model)
    assert e.value.code == REBUILD_FEHLER and "Fase3: Code 12" in str(e.value)


def test_rebuild_neuer_fehler_trotz_bekannter():
    model = model_mit_fehler(("Fase3", 12), ("Bohrung2", 1))
    with sw.bekannte_fehler({"Fase3"}), pytest.raises(BauFehler) as e:
        sw.rebuild(model)
    assert "Bohrung2: Code 1" in str(e.value) and "Fase3" not in str(e.value)


def test_rebuild_ohne_liste_und_ohne_erfolg_bleibt_fehler():
    """Nur eine Fehlerliste rechtfertigt False: bekannte Fehler entschuldigen keinen Neuaufbau ohne Befund."""
    with sw.bekannte_fehler({"Fase3"}), pytest.raises(BauFehler, match="EditRebuild3 meldet Fehler"):
        sw.rebuild(model_mit_fehler(ok=False))


def test_rebuild_warnung_stoppt_weiterhin_nicht():
    sw.rebuild(model_mit_fehler(("Fase3", 12, True), ok=True))


def test_bekannte_fehler_gelten_nur_im_block_auch_nach_ausnahme():
    model = model_mit_fehler(("Fase3", 12))
    with pytest.raises(RuntimeError), sw.bekannte_fehler({"Fase3"}):
        raise RuntimeError("Handler kaputt")
    with pytest.raises(BauFehler):
        sw.rebuild(model)


def test_bekannte_fehler_ersetzen_den_aeusseren_stand():
    """Bekannt ist je Konfiguration verschieden: Der innere Block gilt allein, der äußere danach wieder."""
    model = model_mit_fehler(("Fase3", 12))
    with sw.bekannte_fehler({"Fase3"}):
        with sw.bekannte_fehler({"Bohrung2"}), pytest.raises(BauFehler):
            sw.rebuild(model)
        sw.rebuild(model)
