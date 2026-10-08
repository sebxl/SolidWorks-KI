"""Fremde Deckungsbeziehungen nach CreateSketchSlot (AP 6.8 Durchlicht, Lauf 7): SolidWorks legte sporadisch die
Bogenmitte eines Langlochs auf die Mittellinie eines anderen derselben Reihe – die Skizze wurde überbestimmt."""

from swki.compiler.skizze import SW_DECKUNGSGLEICH, fremde_deckungen, schluessel_element


class _Punkt:
    def __init__(self, i):
        self.GetID = (1, i)


class _Linie:
    GetType = 0

    def __init__(self, i):
        self.GetID = (2, i)


class _Beziehung:
    def __init__(self, typ, elemente, typen):
        self.GetRelationType = typ
        self.GetEntities = elemente
        self.GetEntitiesType = typen


def test_schluessel_unterscheidet_punkt_und_segment_mit_gleicher_id():
    p, linie = _Punkt(5), _Linie(5)
    linie.GetID = (1, 5)
    assert schluessel_element(p, 2) != schluessel_element(linie, 3)


def test_deckung_zwischen_neuem_und_altem_element_ist_fremd():
    alt_punkt, neue_mittellinie = _Punkt(1), _Linie(9)
    fremd = _Beziehung(SW_DECKUNGSGLEICH, (neue_mittellinie, alt_punkt), (3, 2))
    alte = {schluessel_element(alt_punkt, 2)}
    assert fremde_deckungen([fremd], alte) == [fremd]


def test_deckung_nur_unter_neuen_elementen_und_andere_typen_bleiben():
    neu_a, neu_b, alt = _Punkt(7), _Linie(8), _Punkt(1)
    intern = _Beziehung(SW_DECKUNGSGLEICH, (neu_b, neu_a), (3, 2))
    waagrecht = _Beziehung(4, (alt,), (2,))
    alte = {schluessel_element(alt, 2)}
    assert fremde_deckungen([intern, waagrecht], alte) == []
