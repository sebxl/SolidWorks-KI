"""Enger Hüllquader über die Extrempunkte (AP 6.8: GetPartBox/GetBox schätzen bei der Ausformung des Trichters
1–2 mm zu groß, die Extrempunkte treffen die Geometrie genau)."""

import pytest

from swki.compiler import sw


class Koerper:
    """Attrappe IBody2: Extrempunkte (m) je Richtung aus einer Punktwolke."""

    def __init__(self, punkte_mm):
        self.punkte = [tuple(c / 1000 for c in p) for p in punkte_mm]

    def GetExtremePoint(self, dx, dy, dz):
        p = max(self.punkte, key=lambda q: q[0] * dx + q[1] * dy + q[2] * dz)
        return (True, *p)


class Teil:
    def __init__(self, koerper, box_mm):
        self.koerper, self.box = koerper, box_mm

    def GetBodies2(self, art, nur_sichtbar):
        return tuple(self.koerper)

    def GetPartBox(self, _):
        return tuple(c / 1000 for c in self.box)


def test_box_aus_extrempunkten():
    assert sw.box_aus_punkten([(1, 2, 3), (-4, 5, 0), (2, -1, 9)]) == [-4, -1, 0, 2, 5, 9]


def test_huellquader_eng_ueber_alle_koerper():
    a = Koerper([(-300, 29, -348), (-167.19, 122, -291.95)])
    b = Koerper([(-181.8, 122, -277.465), (-209, 29, -281)])
    teil = Teil([a, b], [-300, 29, -348.649, -166.176, 122.003, -276.618])  # GetPartBox zu groß
    assert sw.huellquader_eng_mm(teil) == pytest.approx([-300, 29, -348, -167.19, 122, -277.465])


def test_ohne_koerper_teilebox():
    assert sw.huellquader_eng_mm(Teil([], [0, 0, 0, 1, 2, 3])) == pytest.approx([0, 0, 0, 1, 2, 3])


class Kopie(Koerper):
    def ApplyTransform(self, xform):
        self.punkte = [tuple(c + v for c, v in zip(p, xform.verschiebung)) for p in self.punkte]


class KomponentenKoerper(Koerper):
    def Copy(self):
        return Kopie([tuple(c * 1000 for c in p) for p in self.punkte])


class Transform:
    def __init__(self, verschiebung_mm):
        self.verschiebung = tuple(c / 1000 for c in verschiebung_mm)


class Komponente:
    def __init__(self, koerper, verschiebung_mm):
        self.koerper, self.Transform2 = koerper, Transform(verschiebung_mm)

    def GetBodies3(self, art, info):
        return tuple(self.koerper) if self.koerper else None


class Baugruppe:
    def __init__(self, komponenten, box_mm):
        self.komponenten, self.box = komponenten, box_mm

    def GetComponents(self, oberste):
        return tuple(self.komponenten)

    def GetBox(self, _):
        return tuple(c / 1000 for c in self.box)


def test_baugruppe_eng_in_baugruppenkoordinaten():
    from swki.baugruppe import sw_baugruppe
    asm = Baugruppe([Komponente([KomponentenKoerper([(0, 0, 0), (10, 5, 2)])], (100, 0, 0)),
                     Komponente([KomponentenKoerper([(-1, -1, -1), (1, 1, 1)])], (0, 0, 0)),
                     Komponente([], (0, 0, 0))], [-9, -9, -9, 999, 9, 9])
    assert sw_baugruppe.huellquader(asm) == pytest.approx([-1, -1, -1, 110, 5, 2])
    assert sw_baugruppe.huellquader(Baugruppe([], [0, 0, 0, 1, 2, 3])) == pytest.approx([0, 0, 0, 1, 2, 3])
