"""Live: Zeichnungsprüfung Z1.4 – Spannplatte Z und Buchse Z bauen, zeichnen, zurücklesen und prüfen
(Plan docs/superpowers/plans/2026-11-27-zeichnungsableitung-z14-pruefen.md, Task 4b und Task 6; SolidWorks muss laufen,
frisch gestartet).

`test_zeichnung_pruefen` (Task 4b): Der Rückleser ändert nichts (SHA von Teil und Zeichnung gleich, danach sind nur die
vorher offenen Dokumente offen), `verdeckt` ist für jedes lineare Maß bestimmt (auch die Ø-Maße im Längsschnitt der
Buchse), jede Rauheit, Form/Lage und jeder Bezug hängt an einer Kante mit Merkmal, und kein harter Mangel stammt aus dem
Rücklesen selbst – harte Mängel kommen nur aus Meldungen der Übergabe (`swki zeichnen`, z. B. RAUHEIT_NUR_EINE_INSTANZ
der Spannplatte Z).

Negativfälle (Task 6, Design §10): eine Kopie der Zeichnung im Laufordner wird per COM verändert und gespeichert, dann
über dieselbe Kette wie `swki zeichnung pruefen` (`zeichnung_pruefen` mit einem Leser, der die Kopie liest: Maßnamen
aus der Übergabe, Merkmal je Angabe) geprüft. Verglichen wird mit dem Bericht des unveränderten Originals: die neuen
Mängel sind genau die erwarteten, je am manipulierten Merkmal. Original (Teil und Zeichnung) bleibt unverändert (SHA).
Die Fälle „geschlossene Kette“ (Z-UEB-1) und „Maß an verdeckter Kante“ (Z-ANS-1) stehen nur als Unit-Tests
(`tests/zeichnung/test_pruefen_masse.py`): `swki zeichnen` erzeugt keines von beiden, und die Regeln sind reine
Funktionen über das Ist (Ist → Mängel), dort abgedeckt. Live gezeigt ist der Anteil des Rücklesers: Bezugspunkte,
Richtung und `verdeckt` sind für jedes lineare Maß bestimmt, `ueberbestimmt` und `ansichten` sind auf den Referenzen
ok. Ein Live-Negativfall bräuchte ein per COM neu gesetztes Maß an einer Kette bzw. einer verdeckten Kante – nicht
gemacht.

API (swki api methode, SW 2025): ISldWorks.OpenDoc6 (6; swOpenDocOptions_Silent = 1, ohne ReadOnly), IModelDoc2.Save3
(3; swSaveAsOptions_Silent = 1), IAnnotation.Select2 (2) + IModelDocExtension.DeleteSelection2 (1; 0), INote.SetText
(1), IDisplayDimension.SetText (2; swDimensionTextSuffix = 2), IDimensionTolerance.SetFitValues (2, 2006),
IDrawingDoc.EditSheet (0), IModelDoc2.ClearSelection2 (1), IModelDoc2.InsertNote (1), IAnnotation.SetPosition2 (3,
2014), IAnnotation.GetPosition (0), ICustomPropertyManager.Set2 (2, 2014; swCustomInfoSetResult_OK = 0)."""

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from swki.cli import main
from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, verbinde
from swki.zeichnung.bemassen import _anzeige, _ruf, kurzname
from swki.zeichnung.rueckleser import BLATT, DOC_ZEICHNUNG, lies_zeichnung
from swki.zeichnung.zeichnung_pruefen import zeichnung_pruefen

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).parents[1] / "referenz" / "zeichnung"
FAELLE = [("spannplatte_z.yaml", False), ("buchse_z.yaml", True)]
OEFFNEN_SCHREIBEN = 1     # swOpenDocOptions_Silent (ohne ReadOnly: die Kopie wird verändert)
SPEICHERN_STILL = 1       # swSaveAsOptions_Silent
SUFFIX = 2                # swDimensionTextParts_e.swDimensionTextSuffix
ANFORDERUNGEN = ("rauheit", "form_lage", "bezug")


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _offen() -> list[str]:
    return sorted(str(d.GetPathName) for d in list(verbinde(lade_rechner().sw_jahr).GetDocuments or ()))


def _gezeichnet(capsys, auftrag: Path, spec: str):
    """Spec in den Auftrag kopieren, validieren, freigeben, bauen, zeichnen (ungeprüft: nur zur Ansicht)."""
    spec_pfad = auftrag / spec
    shutil.copy2(REFERENZ / spec, spec_pfad)
    assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    lauf = str(bau["lauf"])
    code, z = _lauf(capsys, "zeichnen", str(spec_pfad), "--lauf", lauf)
    assert code == 0, z
    teil, drw = next(Path(bau["ordner"]).glob("*.SLDPRT")), Path(z["zeichnung"])
    return spec_pfad, lauf, teil, drw, z


@pytest.mark.parametrize(("spec", "bestanden"), FAELLE)
def test_zeichnung_pruefen(capsys, tmp_path, spec, bestanden):
    auftrag = tmp_path / f"Z1-STUFE4-{Path(spec).stem}"
    auftrag.mkdir()
    try:
        spec_pfad, lauf, teil, drw, z = _gezeichnet(capsys, auftrag, spec)
        vorher, offen = (_sha(teil), _sha(drw)), _offen()
        code, b = _lauf(capsys, "zeichnung", "pruefen", str(spec_pfad), "--lauf", lauf)
        assert code == 0, b
        assert (_sha(teil), _sha(drw)) == vorher, "der Rückleser hat Teil oder Zeichnung verändert"
        assert _offen() == offen, "der Rückleser hat Dokumente offen gelassen oder geschlossen"
        assert not [m for m in b["meldungen"] if m.startswith("RUECKLESEN_")], b["meldungen"]
        ziel = Path(spec_pfad.parent / "protokolle" / f"{spec_pfad.stem}.lauf-{lauf}.zeichnung.pruefbericht.json")
        assert json.loads(ziel.read_text(encoding="utf-8"))["bestanden"] == b["bestanden"]
        ist = b["ist"]
        assert ist["sha256_slddrw"] == vorher[1] and ist["format_"] == z["format"] and ist["massstab"] == z["massstab"]
        assert {a["rolle"] for a in ist["ansichten"] if a["rolle"]} == {a["rolle"] for a in z["ansichten"]}
        assert not ist["meldungen"], ist["meldungen"]
        laengen = [m for m in ist["masse"] if m["art"] == "laenge"]
        assert laengen and all(m["verdeckt"] is not None for m in laengen), [m["name"] for m in laengen]
        # Ø an Linearmaßen des Längsschnitts (Präfix <MOD-DIAM>): Hilfslinien lesbar, `verdeckt` bestimmt (Review 4b, M3)
        oe_linear = [m for m in ist["masse"] if m["art"] == "durchmesser" and "<MOD-DIAM>" in m["praefix"]]
        assert all(m["verdeckt"] is False for m in oe_linear), [(m["name"], m["verdeckt"]) for m in oe_linear]
        # jede Rauheit, Form/Lage und jeder Bezug hängt an einer Kante mit Merkmal (Review 4b, I1/I2)
        anf = [a for a in ist["angaben"] if a["art"] in ANFORDERUNGEN]
        assert all(a["features"] and a["merkmal"] for a in anf), [(a["art"], a["text"]) for a in anf
                                                                 if not (a["features"] and a["merkmal"])]
        if spec == "spannplatte_z.yaml":   # die Buchse Z hat keine Rauheit, Form/Lage oder Bezüge
            assert len(anf) == 6, [(a["art"], a["text"]) for a in anf]
        # kein Maß an verdeckter Kante oder ohne sichtbaren Bezug (auch nicht an der gedachten Ecke der R4-Tasche)
        assert next(p for p in b["pruefungen"] if p["id"] == "ansichten")["ok"] is True
        assert next(p for p in b["pruefungen"] if p["id"] == "ueberbestimmt")["ok"] is True
        # Blatt (Review 4b, M5): der Rückleser erfindet keine Eigenschaft; fehlt sie, ist das Feld nicht geprüft
        if "Blatt" not in ist["eigenschaften"]:
            sf = next(p for p in b["pruefungen"] if p["id"] == "schriftfeld")
            assert "Blatt nicht gelesen" in (sf.get("hinweis") or ""), sf
        assert len(ist["masse"]) == z["masse"]["gesetzt"], (len(ist["masse"]), z["masse"])
        uebergabe = set(z["meldungen"])
        aus_dem_lesen = [m for m in b["maengel"] if m["text"] not in uebergabe
                         and next(p for p in b["pruefungen"] if p["id"] == m["pruefung"])["ok"] is False]
        assert aus_dem_lesen == [], aus_dem_lesen
        if spec == "buchse_z.yaml":
            assert oe_linear, "Längsschnitt der Buchse ohne lineare Ø-Maße"
        if bestanden:
            assert b["bestanden"] is True, b["maengel"]
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)


# --- Negativfälle (Task 6) ---------------------------------------------------------------------------------------------

def _ansichten(drw) -> dict:
    aus, v = {}, _ruf(drw, "GetFirstView")
    while v is not None:
        aus[str(_ruf(v, "GetName2"))] = v
        v = _ruf(v, "GetNextView")
    return aus


def _blatt(drw):
    return next(v for v in _ansichten(drw).values() if int(_ruf(v, "Type")) == BLATT)


def _mass(view, name: str):
    treffer = [dd for dd in _anzeige(view) if kurzname(dd) == name]
    assert len(treffer) == 1, (name, [kurzname(dd) for dd in _anzeige(view)])
    return treffer[0]


def _notiz(view, beginnt: str = "", enthaelt: str = ""):
    treffer = [n for n in list(_ruf(view, "GetNotes") or ())
               if str(_ruf(n, "GetText") or "").startswith(beginnt) and enthaelt in str(_ruf(n, "GetText") or "")]
    assert len(treffer) == 1, (beginnt, enthaelt, [str(_ruf(n, "GetText")) for n in list(_ruf(view, "GetNotes") or ())])
    return treffer[0]


def _veraendere(drw: Path, name: str, aendern) -> Path:
    """Kopie der Zeichnung neben dem Original anlegen, schreibbar öffnen, `aendern(doc)` anwenden, nur die Zeichnung
    speichern und alles selbst Geöffnete ohne Speichern schließen (das Teil wird nie gespeichert)."""
    kopie = drw.with_name(f"{drw.stem}_{name}{drw.suffix}")
    shutil.copy2(drw, kopie)
    app = verbinde(lade_rechner().sw_jahr)
    vorher = {str(d.GetPathName).lower() for d in list(app.GetDocuments or ())}
    fehler, warnungen = byref_long(), byref_long()
    doc = app.OpenDoc6(str(kopie), DOC_ZEICHNUNG, OEFFNEN_SCHREIBEN, "", fehler, warnungen)
    try:
        assert doc is not None, f"{kopie.name} nicht geöffnet (Fehler {fehler.value})"
        aendern(doc)
        e, w = byref_long(), byref_long()
        assert doc.Save3(SPEICHERN_STILL, e, w), f"Speichern abgelehnt (Fehler {e.value}, Warnung {w.value})"
    finally:
        eigene = [d for d in list(app.GetDocuments or ()) if str(d.GetPathName).lower() not in vorher]
        for d in sorted(eigene, key=lambda d: not str(d.GetPathName).lower().endswith(".slddrw")):
            sw.schliesse(app, d)
    assert {str(d.GetPathName).lower() for d in list(app.GetDocuments or ())} == vorher
    return kopie


def _mangelmenge(bericht: dict) -> Counter:
    return Counter((m["pruefung"], m["regel"], m["merkmal"], m["text"]) for m in bericht["maengel"])


def _neue_maengel(capsys, spec_pfad: Path, lauf: str, kopie: Path) -> tuple[list[tuple], dict]:
    """Bericht des Originals (CLI) und der Kopie (dieselbe Kette mit einem Leser, der die Kopie liest); zurück: die
    Mängel, die nur die Kopie hat, und ihr Bericht."""
    code, basis = _lauf(capsys, "zeichnung", "pruefen", str(spec_pfad), "--lauf", lauf)
    assert code == 0, basis
    bericht = zeichnung_pruefen(spec_pfad, int(lauf), leser=lambda _pfad, rollen: lies_zeichnung(kopie, rollen))
    assert not [m for m in bericht["meldungen"] if m.startswith("RUECKLESEN_")], bericht["meldungen"]
    assert not bericht["ist"]["meldungen"], bericht["ist"]["meldungen"]
    assert not bericht["kopf"]["meldungen"], bericht["kopf"]
    weg = _mangelmenge(basis) - _mangelmenge(bericht)
    assert not weg, f"Mängel des Originals fehlen in der Kopie: {sorted(weg.elements())}"
    return sorted((_mangelmenge(bericht) - _mangelmenge(basis)).elements()), bericht


def test_negativ_spannplatte_z(capsys, tmp_path):
    """Maß löschen (27, k1), Passung H7 → H8 im Bohrungshinweis (st), „ Ⓔ“ an 150 ± 0,02 (st), Notiz „ISO 2768-mK“,
    Benennung leeren. Die Passung der Spannplatte steht nur im Hinweis „2 × Ø8 H7 Ⓔ – 15 tief“ (Plan-Quelle angabe,
    kein Maß mit Passung): eine falsche Passung dort ist „fehlt: Angabe …“ (Z-VOLL-1); Z-TOL-1 an einem Passmaß
    belegt `test_negativ_passung_buchse_z`."""
    auftrag = tmp_path / "Z1-Z14NEG-spannplatte_z"
    auftrag.mkdir()
    try:
        spec_pfad, lauf, teil, drw, z = _gezeichnet(capsys, auftrag, "spannplatte_z.yaml")
        vorher = (_sha(teil), _sha(drw))
        uebergabe = json.loads((drw.parent / "zeichnung.json").read_text(encoding="utf-8"))
        haupt = uebergabe["ansichten"]["haupt"]
        name_150 = uebergabe["zeichnungsmasse"].get("D1@st_positionen", "D1@st_positionen")

        def aendern(doc):
            v = _ansichten(doc)[haupt]
            _ruf(_mass(v, "D2@k1_pfad"), "GetAnnotation").Select2(False, 0)
            assert _ruf(doc, "Extension").DeleteSelection2(0), "Maß 27 nicht gelöscht"
            assert not [dd for dd in _anzeige(v) if kurzname(dd) == "D2@k1_pfad"]
            n = _notiz(v, enthaelt="H7")
            assert n.SetText(str(_ruf(n, "GetText")).replace("H7", "H8")), "Hinweis nicht geändert"
            _mass(v, name_150).SetText(SUFFIX, " <MOD-EP>")
            _ruf(doc, "EditSheet")
            doc.ClearSelection2(True)
            note = doc.InsertNote("ISO 2768-mK")
            assert note is not None, "InsertNote abgelehnt"
            _ruf(note, "GetAnnotation").SetPosition2(0.03, 0.27, 0)
            cpm = _ruf(doc, "Extension").CustomPropertyManager("")
            assert cpm.Set2("Benennung", "") == 0, "Benennung nicht geleert"

        kopie = _veraendere(drw, "negativ", aendern)
        neu, bericht = _neue_maengel(capsys, spec_pfad, lauf, kopie)
        assert (_sha(teil), _sha(drw)) == vorher, "das Original (Teil oder Zeichnung) wurde verändert"
        assert bericht["bestanden"] is False
        regeln = Counter((p, r, m) for p, r, m, _ in neu)
        assert regeln == Counter({("vollstaendig", "Z-VOLL-1", "k1"): 1, ("vollstaendig", "Z-VOLL-1", "st"): 1,
                                  ("toleranzen", "Z-TOL-2", "st"): 1, ("sammelangaben", "Z-SAM-3", "sammelangabe"): 1,
                                  ("schriftfeld", "Z-SCH-1", "Benennung"): 1}), neu
        text = {(r, m): t for _, r, m, t in neu}
        assert "27" in text[("Z-VOLL-1", "k1")]
        assert "H7" in text[("Z-VOLL-1", "st")]
        assert "150" in text[("Z-TOL-2", "st")]
        assert "2768-mK" in text[("Z-SAM-3", "sammelangabe")]
        assert "Benennung" in text[("Z-SCH-1", "Benennung")]
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)


def test_negativ_passung_buchse_z(capsys, tmp_path):
    """Passung H7 → H8 am Zeichnungsmaß Ø20 (D_innen, `IDimensionTolerance.SetFitValues`) → genau Z-TOL-1 an f1."""
    auftrag = tmp_path / "Z1-Z14NEG-buchse_z"
    auftrag.mkdir()
    try:
        spec_pfad, lauf, teil, drw, z = _gezeichnet(capsys, auftrag, "buchse_z.yaml")
        vorher = (_sha(teil), _sha(drw))
        gesetzt = []

        def aendern(doc):
            for v in _ansichten(doc).values():
                for dd in _anzeige(v):
                    tol = _ruf(dd.GetDimension2(0), "Tolerance")
                    if str(_ruf(tol, "GetHoleFitValue") or "").strip() == "H7":
                        assert tol.SetFitValues("H8", str(_ruf(tol, "GetShaftFitValue") or ""))
                        gesetzt.append(str(_ruf(tol, "GetHoleFitValue")))
            assert gesetzt == ["H8"], gesetzt

        kopie = _veraendere(drw, "negativ", aendern)
        neu, bericht = _neue_maengel(capsys, spec_pfad, lauf, kopie)
        assert (_sha(teil), _sha(drw)) == vorher, "das Original (Teil oder Zeichnung) wurde verändert"
        assert bericht["bestanden"] is False
        assert [(p, r, m) for p, r, m, _ in neu] == [("toleranzen", "Z-TOL-1", "f1")], neu
        assert "H8" in neu[0][3] and "H7" in neu[0][3], neu
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)


def test_sammelnotiz_ausserhalb_des_blatts(capsys, tmp_path):
    """Fix-Runde 4b, I3: Sammelangaben-Notiz der Kopie per `SetPosition2` unter das Blatt. Erwartet wäre Z-SAM-1
    (SAMMELANGABE_FEHLT). Die Lage prüft aber nur `swki zeichnen` am PDF; der Rückleser liest Text, nicht Lage, und
    `pruefe_sammelangaben` prüft nur den Text. Im CLI-Weg hält eine solche Handänderung nur `ZEICHNUNG_GEAENDERT`
    (SHA ≠ Übergabe) auf, keine Regel. Befund Task 6 (nicht wegdefiniert): xfail, solange kein neuer Mangel entsteht."""
    auftrag = tmp_path / "Z1-Z14NEG-sammel"
    auftrag.mkdir()
    try:
        spec_pfad, lauf, teil, drw, z = _gezeichnet(capsys, auftrag, "spannplatte_z.yaml")
        vorher = (_sha(teil), _sha(drw))
        lage = []

        def aendern(doc):
            ann = _ruf(_notiz(_blatt(doc), beginnt="Allgemeintoleranzen"), "GetAnnotation")
            x = list(_ruf(ann, "GetPosition"))[0]
            assert ann.SetPosition2(x, -0.05, 0)
            lage.append(list(_ruf(ann, "GetPosition"))[1])
            assert lage[0] < 0, lage

        kopie = _veraendere(drw, "sammel", aendern)
        neu, bericht = _neue_maengel(capsys, spec_pfad, lauf, kopie)
        assert (_sha(teil), _sha(drw)) == vorher, "das Original (Teil oder Zeichnung) wurde verändert"
        if any(r == "Z-SAM-1" for _, r, _, _ in neu):
            return
        assert neu == [], neu
        pytest.xfail(f"Befund: Sammelangabe bei y = {lage[0] * 1000:.0f} mm (unter dem Blatt) ergibt keinen Mangel – "
                     "die Lage prüft nur swki zeichnen am PDF (SAMMELANGABE_FEHLT)")
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)
