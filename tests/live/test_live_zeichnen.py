"""Live: Zeichnungsableitung Z1.3 – Buchse (Drehteil) und Spannplatte (Frästeil) zeichnen (Stufe 1–3, Plan 2026-11-17
Task 5 ff.), dazu die Stufe-4-Referenzen SpannplatteZ und BuchseZ mit Toleranzen, Passungen, Ⓔ, Rauheit, Form/Lage und
Sammelangaben (Plan 2026-11-27 Task 6). SolidWorks muss laufen, frisch gestartet.

In jedem Fall wird die gespeicherte SLDDRW danach über den Rückleser der Zeichnungsprüfung wieder geöffnet (Stufe-4-
Befund 27.11.2026: Toleranz und Zusätze am Modellmaß gingen beim Wiederöffnen verloren); Toleranzen und Zusätze müssen
am Zeichnungsmaß erhalten sein. Die Prüfung der Zeichnung selbst (`swki zeichnung pruefen`) testet
`test_live_zeichnung_pruefen.py`."""

import hashlib
import json
import re
import shutil
from itertools import combinations
from pathlib import Path

import pytest

from swki.auftrag import lauf_datei
from swki.cli import main
from swki.konfig import lade_rechner, lade_standard
from swki.spec.freigabe import freigegebene_spec
from swki.zeichnung.blatt import MASSSTAEBE, SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.massplan import massplan
from swki.zeichnung.pruefen import (_huelle_plan, _toleranz_ok, _traegt_huelle, _zusatz_ok, angabentext,
                                    masse_umbenennen, meldungscode, normtext, zuordnen)
from swki.zeichnung.toleranzangaben import sammelangaben
from swki.zeichnung.zuordnung import max_je_ansicht
from tests.live.test_live_zeichnung_pruefen import _offen

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).parents[1] / "referenz"
FAELLE = [("buchse", "buchse.yaml", True), ("stil", "spannplatte.yaml", False)]

# Erlaubte Restmeldungen der Stufe-4-Fälle, nach Code (live 28.11.2026). Jeder andere Code – und jede Meldung ohne
# Code – lässt den Test scheitern. Ra 0,8 an den Stiftbohrungen ohne freie Lage (ANMERKUNG_KREUZT) und die Rauheit an
# nur einer von n Instanzen (RAUHEIT_NUR_EINE_INSTANZ) sind offene Nutzerentscheidungen (ergebnisse.md, Stufe 4).
REST_SPANNPLATTE_Z = {
    "ANMERKUNG_KREUZT",          # nur „st rauheit „Ra 0,8““, siehe unten
    "RAUHEIT_NUR_EINE_INSTANZ",  # Taschenboden (t1/s1) und Stiftbohrungen: SolidWorks setzt eine Hinweislinie
    "FUNKTION_UNBESTAETIGT",     # stiftbohrung: C-Werte bestätigt der Nutzer
    "ANSICHT_DICHT",             # Nutzer 19.11.2026: „13 Maße hinnehmen“
    "EINZELHEIT_NICHT_FUER",     # Protokoll der Ansichtswahl
    "EINZELHEIT",                # Protokoll: Tasche in die Einzelheit ausgelagert
    "LAUF_NICHT_BESTANDEN",      # der Test zeichnet ohne Prüfer-Urteil
}
REST_BUCHSE_Z = {"LAUF_NICHT_BESTANDEN"}
FAELLE_Z = [
    # spec, drehteil, erlaubte Codes, mindestens tolerierte Maße / Maße mit Zusatz / Maße mit Ⓔ (Wiederöffnen)
    pytest.param("spannplatte_z.yaml", False, REST_SPANNPLATTE_Z, 1, 1, 0, id="spannplatte_z"),
    pytest.param("buchse_z.yaml", True, REST_BUCHSE_Z, 2, 2, 2, id="buchse_z"),
]


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _ueberlappt(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _bauen_und_zeichnen(capsys, spec_pfad: Path, ablage: str):
    """validieren → freigeben → bauen → zeichnen (ungeprüft: nur zur Ansicht); PDF und PNG für die Durchsicht durch den
    Nutzer nach `<arbeitsordner>/<ablage>` (vor den Prüfungen, damit ein Befund sichtbar bleibt)."""
    assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    teil = next(Path(bau["ordner"]).glob("*.SLDPRT"))
    sha = _sha(teil)
    code, z = _lauf(capsys, "zeichnen", str(spec_pfad), "--lauf", str(bau["lauf"]))
    assert code == 0, z
    ziel = lade_rechner().arbeitsordner / ablage
    ziel.mkdir(exist_ok=True)
    for schluessel in ("pdf", "png"):
        shutil.copy2(z[schluessel], ziel / Path(z[schluessel]).name)
    # Übergabe samt Meldungen neben das PDF (der Auftrag wird nach dem Test gelöscht)
    shutil.copy2(z["uebergabe"], ziel / f"{Path(z['zeichnung']).stem}.zeichnung.json")
    for schluessel in ("zeichnung", "pdf", "png"):
        assert Path(z[schluessel]).stat().st_size > 0, schluessel
    return bau, teil, sha, z


def _pruefe_blatt(z) -> None:
    """Ansichten im Zeichenfeld, nicht im Schriftfeld, nicht übereinander."""
    x0, y0, x1, y1 = zeichenfeld(z["format"])
    schrift = (x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])
    umrisse = [a["umriss_mm"] for a in z["ansichten"]]
    for u in umrisse:
        assert x0 <= u[0] and u[2] <= x1 and y0 <= u[1] and u[3] <= y1, u
        assert not _ueberlappt(u, schrift), u
    for a, b in combinations(umrisse, 2):
        assert not _ueberlappt(a, b), (a, b)


def _pruefe_wiedergeoeffnet(spec_pfad: Path, lauf: int, z: dict, teil: Path) -> dict[str, int]:
    """Eigener Schritt: die gespeicherte SLDDRW schreibgeschützt öffnen (Rückleser Z1.4) und je Plan-Maß mit Toleranz
    oder Textzusatz prüfen, dass Toleranz, Zusatz und Ⓔ erhalten sind; umgewandelte Modellmaße müssen
    Zeichnungsmaße sein. Bohrungsangaben (Hinweise) müssen mit ihrem Text erhalten sein. Rückgabe: Anzahl der
    geprüften Maße mit Toleranz, Zusatz, Ⓔ."""
    from swki.zeichnung.rueckleser import lies_zeichnung  # spät: COM

    daten = json.loads(Path(z["uebergabe"]).read_text(encoding="utf-8"))
    drw = Path(z["zeichnung"])
    vorher, offen = (_sha(teil), _sha(drw)), _offen()
    ist = lies_zeichnung(drw, dict(daten.get("ansichten") or {}))
    assert (_sha(teil), _sha(drw)) == vorher, "das Wiederöffnen hat Teil oder Zeichnung verändert"
    assert _offen() == offen, "das Wiederöffnen hat Dokumente offen gelassen oder geschlossen"
    assert not ist.meldungen, ist.meldungen
    umgewandelt = daten.get("zeichnungsmasse") or {}
    ist = masse_umbenennen(ist, umgewandelt)
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    plan = massplan(freigegebene_spec(spec_pfad), protokoll)
    zuordnung = zuordnen(ist, plan)
    zahl = {"toleranz": 0, "zusatz": 0, "huelle": 0}
    fehler = []
    for m in plan:
        if m.quelle not in ("modell", "neu"):
            continue
        zusatz = bool(normtext(m.praefix) or normtext(m.suffix))
        if m.toleranz is None and not zusatz:
            continue
        c = zuordnung.get(m.id)
        if c is None:
            fehler.append(f"{m.id}: nach dem Wiederöffnen kein Maß {m.wert}")
            continue
        if m.quelle == "modell" and m.name not in umgewandelt:
            fehler.append(f"{m.id}: {m.name} ist kein Zeichnungsmaß (Toleranz/Zusatz am Modellmaß)")
        if not _toleranz_ok(c, m):
            fehler.append(f"{m.id}: Toleranz {c.toleranz} statt {m.toleranz}")
        if not _zusatz_ok(c, m):
            fehler.append(f"{m.id}: Zusatz „{c.praefix}|{c.suffix}“ statt „{m.praefix}|{m.suffix}“")
        if _traegt_huelle(c) != _huelle_plan(m):
            fehler.append(f"{m.id}: Ⓔ {'fehlt' if _huelle_plan(m) else 'zu viel'} („{c.suffix}“)")
        zahl["toleranz"] += m.toleranz is not None
        zahl["zusatz"] += zusatz
        zahl["huelle"] += _huelle_plan(m)
    hinweise = [angabentext(a.text) for a in ist.angaben if a.art == "hinweis"]
    for m in plan:
        if m.quelle == "angabe" and angabentext(m.text) not in hinweise:
            fehler.append(f"{m.id}: Bohrungsangabe „{angabentext(m.text)}“ nach dem Wiederöffnen nicht gefunden")
    assert not fehler, fehler
    return zahl


def _pdf_text(pdf: str) -> str:
    import pymupdf
    with pymupdf.open(pdf) as doc:
        return doc[0].get_text()


def _huellsymbole(pdf: str) -> list[str]:
    """Zeilen des PDFs mit einem Hüllsymbol `<MOD-EP>`: pymupdf liest es als alleinstehendes „E“ (Live 27.11.:
    „32,00 k6 E“); gezählt wird es nur mit seinem Ring aus kurzen Strichen (`lesbarkeit._huellringe/_ringstrich`)."""
    import pymupdf

    from swki.zeichnung.lesbarkeit import PT_MM, _huellringe, _ringstrich
    aus = []
    with pymupdf.open(pdf) as doc:
        page = doc[0]
        hoehe = page.rect.height * PT_MM

        def mm(x, y):
            return (x * PT_MM, hoehe - y * PT_MM)

        linien = [(mm(e[1].x, e[1].y), mm(e[2].x, e[2].y)) for d in page.get_drawings() for e in d["items"]
                  if e[0] == "l"]
        for block in page.get_text("rawdict")["blocks"]:
            for zeile in block.get("lines", []):
                zeichen = [{**c, "groesse": s["size"]} for s in zeile["spans"] for c in s["chars"]]
                ringe = _huellringe(zeichen, mm)
                if ringe and sum(_ringstrich(a, b, ringe) for a, b in linien) >= 8:
                    aus.append("".join(c["c"] for c in zeichen).strip())
    return aus


@pytest.mark.parametrize(("ordner", "spec", "drehteil"), FAELLE)
def test_zeichnen(capsys, tmp_path, ordner, spec, drehteil):
    auftrag = tmp_path / f"SWKI-LIVE-ZEICHNEN-{ordner}"
    shutil.copytree(REFERENZ / ordner, auftrag)
    spec_pfad = auftrag / spec
    try:
        bau, teil, sha, z = _bauen_und_zeichnen(capsys, spec_pfad, "Z1-STUFE1")  # Stufe-3-Stand für die Durchsicht
        assert z["format"] in ("A4", "A3quer")
        assert tuple(int(x) for x in z["massstab"].split(":")) in MASSSTAEBE
        rollen = [a["rolle"] for a in z["ansichten"]]
        assert "haupt" in rollen
        assert any(m.startswith("LAUF_NICHT_BESTANDEN") for m in z["meldungen"])
        # Stufe 2: Maßplan vollständig gesetzt oder jede Lücke gemeldet; keine Ansicht über der Obergrenze
        masse = z["masse"]
        # Live 18.11.2026: kein Pflichtmaß verwerfen – über der Obergrenze nur mit ANSICHT_DICHT
        assert masse["gesetzt"] == masse["plan"], z["meldungen"]
        assert max(masse["je_ansicht"].values()) <= max_je_ansicht(lade_standard()) or any(
            m.startswith("ANSICHT_DICHT") for m in z["meldungen"]), masse
        assert not any(m.startswith(("MASS_NICHT_GELOESCHT", "MASS_NICHT_GESETZT")) for m in z["meldungen"]), z["meldungen"]
        # Nutzer 18.11.2026: lesbar – kein Text auf Text, keine Linie durch eine Maßzahl (Prüfung am PDF)
        assert not any(m.startswith("LESBARKEIT") for m in z["meldungen"]), z["meldungen"]
        # Schriftfeld zeigt den Dateinamen = Zeichnungsnummer (18.11.: PDF vor der Zeichnung gespeichert → „Zeichn1“)
        import pymupdf
        with pymupdf.open(z["pdf"]) as doc:
            assert Path(z["zeichnung"]).stem in doc[0].get_text(), "Zeichnungsnummer fehlt im Schriftfeld"
        # Stufe 3: Bohrungsangaben als Hinweise mit Hinweislinie, Textzusätze an Maßen; im PDF Zeile für Zeile
        angaben = z["angaben"]
        assert angaben["plan"] >= 1 and angaben["gesetzt"] == angaben["plan"], (angaben, z["meldungen"])
        assert not any(m.startswith("ANGABE_") for m in z["meldungen"]), z["meldungen"]
        with pymupdf.open(z["pdf"]) as doc:
            text = doc[0].get_text()
        erwartet = (["5 × M6 – 10 tief", "Senkung Ø6 × 90°", "2 × Ø8 – 15 tief", "Fase 0,5 × 45°",
                     "4 × 30,00 (= 120)", "EINZELHEIT"] if not drehteil
                    else ["4 × Ø6 – durch", "TK Ø40"])
        for zeile in erwartet:
            assert zeile in text, (zeile, text)
        if drehteil:
            assert text.count("× 45°") >= 2, text
        if not drehteil:
            # Nutzer 18.11.2026: dichte Hauptansicht → Einzelheit; nur Maße mit beiden Bezügen im Rahmen (19.11.: die
            # Nutmaße hängen an der Plattenmitte) → Tasche samt Eckradius. Höchstens ein Maß über der Obergrenze, gemeldet
            # („60,00“ der Nut; Nutzer 19.11.2026: „13 Maße hinnehmen“)
            assert sorted(rollen) == ["drauf", "einzelheit", "haupt", "seite"], rollen
            # Nutzer 19.11.2026: untere Ansicht als Schnitt durch die Taschen, Taschentiefe mit sichtbarem Bezug
            assert z["schnitt"] and z["schnitt"].startswith("Schnitt"), z["schnitt"]
            assert not any(m.startswith(("BEZUG_OHNE_KANTE", "SCHNITT_")) for m in z["meldungen"]), z["meldungen"]
            assert any(m.startswith("EINZELHEIT: t1") for m in z["meldungen"]), z["meldungen"]
            assert max(masse["je_ansicht"].values()) <= max_je_ansicht(lade_standard()) + 1, masse
            assert (max(masse["je_ansicht"].values()) <= max_je_ansicht(lade_standard())
                    or any(m.startswith("ANSICHT_DICHT") for m in z["meldungen"])), z["meldungen"]
            # Nutzer 18.11.2026: Mittellinien für Maße ab Teilmitte – Haupt- und Seitenansicht, als Strichpunktlinie
            assert not any(m.startswith(("MITTELLINIE_", "HILFSLINIE_NICHT")) for m in z["meldungen"]), z["meldungen"]
            with pymupdf.open(z["pdf"]) as doc:
                strichpunkt = [it for d in doc[0].get_drawings() if "43.2" in str(d.get("dashes"))
                               for it in d["items"] if it[0] == "l" and abs(it[1] - it[2]) * 25.4 / 72 > 30]
            assert len(strichpunkt) >= 3, len(strichpunkt)  # waagrecht + senkrecht (haupt), waagrecht (seite)
            # „Details werden in der Regel vergrößert, sonst braucht man kein Detail.“ (Nutzer 18.11.2026)
            f = {a["rolle"]: a["massstab"] for a in z["ansichten"]}
            blatt = int(z["massstab"].split(":")[0]) / int(z["massstab"].split(":")[1])
            assert f["einzelheit"] >= 2 * blatt - 1e-9 and f["haupt"] == blatt, (f, z["massstab"])
        if drehteil:
            assert z["schnitt"] and z["schnitt"].startswith("Schnitt") and "seite" in rollen
        _pruefe_blatt(z)
        # Stufe 4: auch die Zusätze der Stufe 3 („4 × 30,00 (= 120)“, „× 45°“) überleben das Wiederöffnen
        assert _pruefe_wiedergeoeffnet(spec_pfad, bau["lauf"], z, teil)["zusatz"] >= 1
        assert _sha(teil) == sha
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)


@pytest.mark.parametrize(("spec", "drehteil", "erlaubt", "min_tol", "min_zusatz", "min_huelle"), FAELLE_Z)
def test_zeichnen_stufe4(capsys, tmp_path, spec, drehteil, erlaubt, min_tol, min_zusatz, min_huelle):
    """Stufe 4 (Plan 2026-11-27 Task 6): Anforderungen und Sammelangaben im PDF, erhalten nach dem Wiederöffnen,
    nur die erlaubten Restmeldungen. Ablage `Z1-STUFE4` (die Stufe-3-PDFs bleiben in `Z1-STUFE1`)."""
    auftrag = tmp_path / f"SWKI-LIVE-ZEICHNEN-{Path(spec).stem}"  # nie „Z1-STUFE4“: das finally löscht den Auftrag
    auftrag.mkdir()
    spec_pfad = auftrag / spec
    shutil.copy2(REFERENZ / "zeichnung" / spec, spec_pfad)
    offen = _offen()
    try:
        bau, teil, sha, z = _bauen_und_zeichnen(capsys, spec_pfad, "Z1-STUFE4")
        assert z["format"] in ("A4", "A3quer")
        assert tuple(int(x) for x in z["massstab"].split(":")) in MASSSTAEBE
        meldungen = z["meldungen"]
        fremd = [m for m in meldungen if meldungscode(m) not in erlaubt]
        assert not fremd, fremd
        # Ra 0,8 an den Stiftbohrungen findet keine freie Lage (Nutzerentscheidung); jede andere Kreuzung ist neu
        kreuzt = [m for m in meldungen if meldungscode(m) == "ANMERKUNG_KREUZT"]
        assert all(m.startswith("ANMERKUNG_KREUZT: st rauheit „Ra 0,8“") for m in kreuzt), kreuzt
        assert any(m.startswith("LAUF_NICHT_BESTANDEN") for m in meldungen), meldungen
        assert z["masse"]["gesetzt"] == z["masse"]["plan"], (z["masse"], meldungen)
        assert z["angaben"]["plan"] >= 1 and z["angaben"]["gesetzt"] == z["angaben"]["plan"], (z["angaben"], meldungen)
        # Rauheit, Rahmen, Bezüge: nur die SpannplatteZ hat welche (BuchseZ: Passungen, Behandlung, Halbzeug)
        assert z["anmerkungen"]["gesetzt"] == z["anmerkungen"]["plan"], (z["anmerkungen"], meldungen)
        assert drehteil or z["anmerkungen"]["plan"] >= 1, z["anmerkungen"]
        roh = _pdf_text(z["pdf"])
        assert Path(z["zeichnung"]).stem in roh, "Zeichnungsnummer fehlt im Schriftfeld"
        text = " ".join(roh.split())
        spec_daten = freigegebene_spec(spec_pfad)
        from swki.zeichnung.anforderungen_setzen import SAMMEL_RAUHEIT_ZEILE  # spät: pywin32
        erwartet = list(sammelangaben({})[:4])  # die vier immer geltenden Sammelzeilen
        assert erwartet == sammelangaben(spec_daten)[:4]
        erwartet += sammelangaben(spec_daten)[4:] + [SAMMEL_RAUHEIT_ZEILE]  # Behandlung, Halbzeug, allgemeine Rauheit
        if drehteil:
            erwartet += ["4 × Ø6 – durch", "TK Ø40", "H7", "k6", "einsatzgehärtet und angelassen (60 ± 2) HRC"]
        else:
            # Stiftangabe dreizeilig ohne Strich am Zeilenende (Nachbesserung D), Ⓔ als Hüllsymbol (unten)
            erwartet += ["2 × Ø8 H7", "15 tief", "Fase 0,5 × 45°", "±0,02", "4 × 30,00 (= 120)", "SCHNITT C-C",
                         "EINZELHEIT Z"]
            # Anmerkungen als ganze Zeilen (sonst erfüllt „±0,02“ schon „0,02“): Rauheit, ▱-Rahmen, //-Rahmen mit Bezug
            zeilen = {" ".join(z.split()) for z in roh.splitlines()}
            fehlt = [z for z in ("Ra 0,8", "Ra 1,6", "0,02", "0,05 A", "2 ×") if z not in zeilen]
            assert not fehlt, (fehlt, roh)
        fehlt = [zeile for zeile in erwartet if zeile not in text]
        assert not fehlt, (fehlt, roh)
        assert "– 15 tief" not in text, "Stiftangabe mit Strich am Zeilenende (vor Nachbesserung D)"
        huelle = _huellsymbole(z["pdf"])
        if drehteil:
            assert any(re.search(r"\bH7 E$", h) for h in huelle) and any(re.search(r"\bk6 E$", h) for h in huelle), huelle
        else:
            assert any(re.search(r"2 × Ø8 H7 E$", h) for h in huelle), huelle
        if not drehteil:
            # Schnittbuchstaben meiden die Bezugsbuchstaben A, B (Nachbesserung E), Einzelheit ab Z rückwärts (D)
            assert z["schnitt"] and z["schnitt"].startswith("Schnitt"), z["schnitt"]
            assert "einzelheit" in [a["rolle"] for a in z["ansichten"]], z["ansichten"]
        _pruefe_blatt(z)
        zahl = _pruefe_wiedergeoeffnet(spec_pfad, bau["lauf"], z, teil)
        assert zahl["toleranz"] >= min_tol and zahl["zusatz"] >= min_zusatz and zahl["huelle"] >= min_huelle, zahl
        assert _sha(teil) == sha
        assert _offen() == offen, "nach dem Zeichnen sind andere Dokumente offen als vorher"
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)
