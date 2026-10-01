"""Live: Normbohrungen über den Bohrungsassistenten – alle Positionen in einem Feature (SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.topologie import flaechen
from swki.pruefung.geometrie import normbohrung_volumen
from swki.spec.normen import normmasse

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}


def _spec(nb):
    return {"art": "teil", "name": "T", "parameter": {"L": 100}, "features": [KLOTZ, nb]}


def _achsen_xz(feature) -> list:
    return sorted({(round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder"})


def test_gewinde_mit_drei_positionen_in_einem_feature():
    nb = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": DECKFLAECHE,
          "positionen": [["=-L/2+20", 10], [0, 10], ["=L/2-20", 10]], "tiefe": 16, "gewindetiefe": 12}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, protokoll):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert [f.Name for f in erg.features] == ["f2"]
        assert erg.punkte == [(-30.0, 20.0, -10.0), (0.0, 20.0, -10.0), (30.0, 20.0, -10.0)]
        assert protokoll.knoten[1].punkte == [[-30.0, 20.0, -10.0], [0.0, 20.0, -10.0], [30.0, 20.0, -10.0]]
        assert erg.features[0].GetDefinition.GetSketchPointCount == 3
        einzeln = normbohrung_volumen("gewinde", normmasse("gewinde", "M8"), 16)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 3 * einzeln, abs=1e-2)
        assert _achsen_xz(erg.features[0]) == [(-30.0, -10.0), (0.0, -10.0), (30.0, -10.0)]
        # Lage der Positionen hängt an L (Gleichungen an der Positionsskizze f2_positionen)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert any("@f2_positionen" in t and '"L"' in t for t in texte)
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"L" = 100'), '"L" = 140')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert _achsen_xz(erg.features[0]) == [(-50.0, -10.0), (0.0, -10.0), (50.0, -10.0)]


@pytest.mark.parametrize(("art", "groesse"), [
    ("zylinderschraube", "M8"), ("senkschraube", "M6"), ("stift", 8), ("gewinde", "M12x1.5"),
])
def test_arten_durch(art, groesse):
    nb = {"id": "f2", "typ": "normbohrung", "art": art, "groesse": groesse, "flaeche": DECKFLAECHE,
          "positionen": [[-20, 0], [20, 0]], "durch": True}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        einzeln = normbohrung_volumen(art, normmasse(art, groesse), None, dicke=20)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 2 * einzeln, abs=1e-2)
        zylinder = zylinder_zu_punkten(flaechen(erg.features[0]), erg.punkte, 0.1)
        assert [round(z.punkt[0], 4) for z in zylinder] == [-20.0, 20.0]


def test_senkschraube_von_unten():
    nb = {"id": "f2", "typ": "normbohrung", "art": "senkschraube", "groesse": "M6",
          "flaeche": {"feature": "f1", "flaeche": "-y"}, "positionen": [[10, 5]], "durch": True}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert erg.punkte == [(10.0, 0.0, -5.0)]
        assert erg.richtung == (0.0, 1.0, 0.0)  # ins Material = gegen die Flächennormale −y
        kegel = [fc for fc in erg.features[0].GetFaces if fc.GetSurface.IsCone]
        assert kegel and all(abs(fc.GetBox[1]) < 1e-9 for fc in kegel)  # Senkung an der Unterseite (Y = 0)
