"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 3): Zuordnung Maß → Ansicht mit Obergrenze."""

from swki.zeichnung.zuordnung import max_je_ansicht, ordne_zu

ANSICHTEN = ["haupt", "drauf", "seite"]


def test_jedes_mass_genau_einer_kandidatenansicht():
    z = ordne_zu({"a": ["haupt", "drauf"], "b": ["drauf"], "c": ["seite", "haupt"]}, ANSICHTEN, 12)
    zugeordnet = {m: r for r, ms in z.je_ansicht.items() for m in ms}
    assert zugeordnet["b"] == "drauf" and zugeordnet["a"] in ("haupt", "drauf") and zugeordnet["c"] in ("seite", "haupt")
    assert sorted(zugeordnet) == ["a", "b", "c"] and z.ohne_ansicht == [] and not z.weitere_ansicht


def test_ueberlauf_nur_hauptansicht():
    z = ordne_zu({f"m{i:02d}": ["haupt"] for i in range(15)}, ANSICHTEN, 12)
    assert len(z.je_ansicht["haupt"]) == 12 and z.weitere_ansicht
    assert len(z.meldungen) == 3 and all("haupt" in m or "Obergrenze" in m for m in z.meldungen)


def test_verteilung_auf_zwei_ansichten():
    z = ordne_zu({f"m{i:02d}": ["haupt", "drauf"] for i in range(15)}, ANSICHTEN, 12)
    assert sorted((len(z.je_ansicht["haupt"]), len(z.je_ansicht["drauf"]))) == [7, 8] and not z.weitere_ansicht


def test_mass_ohne_kandidat_gemeldet():
    z = ordne_zu({"x": []}, ANSICHTEN, 12)
    assert z.ohne_ansicht == ["x"] and any("x" in m for m in z.meldungen) and z.weitere_ansicht


def test_leere_ansichten_bleiben_sichtbar():
    z = ordne_zu({"a": ["haupt"]}, ANSICHTEN, 12)
    assert z.je_ansicht == {"haupt": ["a"], "drauf": [], "seite": []}


def test_einzelkandidaten_zuerst():
    # b und c passen nur in haupt, a überall: a darf haupt nicht belegen, wenn die Obergrenze knapp ist
    z = ordne_zu({"a": ["haupt", "drauf"], "b": ["haupt"], "c": ["haupt"]}, ANSICHTEN, 2)
    assert sorted(z.je_ansicht["haupt"]) == ["b", "c"] and z.je_ansicht["drauf"] == ["a"]


def test_obergrenze_aus_standard():
    assert max_je_ansicht({"zeichnung": {"max_masse_je_ansicht": 9}}) == 9 and max_je_ansicht({}) == 12
