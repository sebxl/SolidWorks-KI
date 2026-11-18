"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 3): Zuordnung Maß → Ansicht mit Obergrenze."""

from swki.zeichnung.zuordnung import max_je_ansicht, ordne_zu

ANSICHTEN = ["haupt", "drauf", "seite"]


def test_jedes_mass_genau_einer_kandidatenansicht():
    z = ordne_zu({"a": ["haupt", "drauf"], "b": ["drauf"], "c": ["seite", "haupt"]}, ANSICHTEN, 12)
    zugeordnet = {m: r for r, ms in z.je_ansicht.items() for m in ms}
    assert zugeordnet["b"] == "drauf" and zugeordnet["a"] in ("haupt", "drauf") and zugeordnet["c"] in ("seite", "haupt")
    assert sorted(zugeordnet) == ["a", "b", "c"] and z.ohne_ansicht == [] and not z.weitere_ansicht


def test_ueberlauf_nur_hauptansicht():
    """Live 18.11.2026: kein Pflichtmaß verwerfen – über der Obergrenze trotzdem setzen, melden, weitere Ansicht verlangen."""
    z = ordne_zu({f"m{i:02d}": ["haupt"] for i in range(15)}, ANSICHTEN, 12)
    assert len(z.je_ansicht["haupt"]) == 15 and z.weitere_ansicht
    assert len(z.meldungen) == 3 and all(m.startswith("ANSICHT_DICHT") and "haupt" in m for m in z.meldungen)


def test_verteilung_auf_zwei_ansichten():
    z = ordne_zu({f"m{i:02d}": ["haupt", "drauf"] for i in range(15)}, ANSICHTEN, 12)
    assert sorted((len(z.je_ansicht["haupt"]), len(z.je_ansicht["drauf"]))) == [7, 8] and not z.weitere_ansicht


def test_mass_ohne_kandidat_gemeldet():
    z = ordne_zu({"x": []}, ANSICHTEN, 12)
    assert z.ohne_ansicht == ["x"] and any("x" in m for m in z.meldungen)


def test_leere_ansichten_bleiben_sichtbar():
    z = ordne_zu({"a": ["haupt"]}, ANSICHTEN, 12)
    assert z.je_ansicht == {"haupt": ["a"], "drauf": [], "seite": []}


def test_einzelkandidaten_zuerst():
    # b und c passen nur in haupt, a überall: a darf haupt nicht belegen, wenn die Obergrenze knapp ist
    z = ordne_zu({"a": ["haupt", "drauf"], "b": ["haupt"], "c": ["haupt"]}, ANSICHTEN, 2)
    assert sorted(z.je_ansicht["haupt"]) == ["b", "c"] and z.je_ansicht["drauf"] == ["a"]


def test_obergrenze_aus_standard():
    assert max_je_ansicht({"zeichnung": {"max_masse_je_ansicht": 9}}) == 9 and max_je_ansicht({}) == 12


def test_vorzugsansicht_vor_geringster_belegung():
    """Live Z1.3 Stufe 2: Lagemaße von Bohrungen landeten in der Dickenansicht (nur verdeckt sichtbar). Ein Maß geht
    bevorzugt in die Ansicht, die auf die Fläche seines Merkmals schaut, solange dort Platz ist."""
    kand = {"a": ["haupt", "drauf"], "b": ["haupt", "drauf"], "c": ["haupt", "drauf"]}
    z = ordne_zu(kand, ANSICHTEN, 12, vorzug={"a": "haupt", "b": "haupt", "c": "haupt"})
    assert z.je_ansicht["haupt"] == ["a", "b", "c"] and z.je_ansicht["drauf"] == []


def test_vorzug_voll_dann_andere_kandidaten():
    kand = {"a": ["haupt", "drauf"], "b": ["haupt", "drauf"]}
    z = ordne_zu(kand, ANSICHTEN, 1, vorzug={"a": "haupt", "b": "haupt"})
    assert z.je_ansicht["haupt"] == ["a"] and z.je_ansicht["drauf"] == ["b"] and not z.weitere_ansicht


def test_ohne_ansicht_verlangt_keine_weitere_ansicht():
    """Review I3: ein nicht darstellbares Maß erzeugt keine Zusatzansichten."""
    z = ordne_zu({"x": [], "a": ["haupt"]}, ANSICHTEN, 12)
    assert z.ohne_ansicht == ["x"] and not z.weitere_ansicht


def test_zusatzansicht_erst_wenn_grundansichten_voll():
    kand = {f"m{i}": ["haupt", "unter"] for i in range(3)}
    z = ordne_zu(kand, ["haupt", "unter"], 12, zusatz={"unter"})
    assert len(z.je_ansicht["haupt"]) == 3 and z.je_ansicht["unter"] == []


def test_vorbelegung_zaehlt_gegen_obergrenze():
    """Review I2: neue Drehteil-Maße belegen die Hauptansicht vor."""
    z = ordne_zu({"a": ["haupt", "seite"], "b": ["haupt", "seite"]}, ["haupt", "seite"], 12, belegt={"haupt": 11},
                 vorzug={"a": "haupt", "b": "haupt"})
    assert len(z.je_ansicht["haupt"]) == 1 and len(z.je_ansicht["seite"]) == 1
