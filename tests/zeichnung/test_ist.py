"""Ist-Modell der zurückgelesenen Zeichnung."""

import json

from swki.zeichnung.ist import Ist, IstAngabe, IstAnsicht, IstMass, IstToleranz, ist_aus_dict, ist_zu_dict


def _ist() -> Ist:
    masse = (
        IstMass("D1@Skizze1", "haupt", "durchmesser", 20.0, "Ø", " Ⓔ", False,
                IstToleranz("passung", "H7", 0.021, 0.0), None, None, False),
        IstMass("D2@Skizze2", "oben", "laenge", 80.0, "", "", True,
                IstToleranz("keine", None, None, None), "h", ((10.0, 20.0), (90.0, 20.0)), None),
    )
    angaben = (
        IstAngabe("hinweis", "haupt", "M6 tief 12", None, None, ()),
        IstAngabe("rauheit", "haupt", "Ra 1,6", "Ra", "1,6", ()),
        IstAngabe("form_lage", "haupt", "Ebenheit 0,02", "ebenheit", "0,02", ("A",)),
        IstAngabe("bezug", "haupt", "A", None, None, ("A",)),
    )
    ansichten = (
        IstAnsicht("haupt", "vorn", "ansicht", "1:1", None),
        IstAnsicht("Schnitt A-A", None, "schnitt", "1:1", "A-A"),
    )
    return Ist("A4", "1:1", ansichten, masse, angaben, {"Benennung": "Platte"}, "ab" * 32)


def test_ist_rundreise():
    ist = _ist()
    d = json.loads(json.dumps(ist_zu_dict(ist)))
    assert ist_aus_dict(d) == ist
    assert isinstance(ist_aus_dict(d).masse[1].punkte[0], tuple)
