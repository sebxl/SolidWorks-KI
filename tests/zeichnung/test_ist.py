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


def test_ist_rundreise_mit_rueckleserfeldern():
    """Task 4b: Instanzzahl über dem Rahmen, Feature-Namen der angehängten Kante, Meldungen des Rücklesers."""
    ist = _ist()
    angaben = ist.angaben + (IstAngabe("form_lage", "Schnitt C-C", "<IGTOL-PARA> 0,05", "<IGTOL-PARA>", "0,05", ("A",),
                                       None, 2, ("Schnitt1", "s1")),)
    ist = Ist(ist.format_, ist.massstab, ist.ansichten, ist.masse, angaben, ist.eigenschaften, ist.sha256_slddrw,
              ("RUECKLESEN_UNVOLLSTAENDIG: Maß D9 ohne Wert",))
    d = json.loads(json.dumps(ist_zu_dict(ist)))
    zurueck = ist_aus_dict(d)
    assert zurueck == ist
    assert zurueck.angaben[-1].features == ("Schnitt1", "s1") and zurueck.angaben[-1].anzahl == 2


def test_ist_aus_altem_dict():
    """Ein Bericht von vor Task 4b (ohne die neuen Felder) bleibt lesbar."""
    d = json.loads(json.dumps(ist_zu_dict(_ist())))
    for a in d["angaben"]:
        a.pop("anzahl"), a.pop("features")
    d.pop("meldungen")
    assert ist_aus_dict(d) == _ist()
