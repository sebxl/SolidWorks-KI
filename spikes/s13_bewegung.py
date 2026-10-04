"""S13 (Stufe 4a): Grenzverknüpfungen, treibende Verknüpfung, Bestimmtheit, Lage, Hüllquader, Zeit und Speicher.

1 AddMate5 swMateDISTANCE mit Grenzen (Distance = min, DistanceAbsUpperLimit = max, DistanceAbsLowerLimit = min):
  Status, IMate2.MinimumVariation/MaximumVariation, Maße des Features (Name, Wert), Maß D1.
2 Gleichung auf das Maß der oberen Grenze ("<Name>@g1" = "HUB") bindet; nach HUB = 120 ist die Grenze 120? Dito Winkel.
3 Treibende Verknüpfung (Abstand an denselben Flächen) neben der Grenze: innerhalb verstellen (Weg = Wert?), über max
  hinaus (Rebuild, Fehlercodes, Weg), zurück auf max (wieder gelöst?).
4 GetConstrainedStatus: nur Grenzen, mit Antrieb des Schiebers, mit beiden Antrieben; Mitfahrer (Bolzen) jeweils.
5 Antriebe löschen: Lage bleibt; speichern, schließen, öffnen, verstellen, ohne Speichern schließen → SHA-256 gleich.
6 IComponent2.GetBox(False, False) gegen die mit Transform2 umgerechnete Teilebox.
7 Drehsinn: Winkelantrieb 0 → 45 → 90 an den Flächen +z/+z (gleich): Drehachse und Winkel aus Transform2.
8 Zeit und Private Bytes je Schritt (stellen + Rebuild, Kollision, Lage und Hüllquader) an der Probe und an der Probe
  mit 96 zusätzlichen fixierten Stiften (~100 Komponenten), je 20 Schritte.
9 Iso-Bild mit aktivem Antrieb.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s13_bewegung
"""

import ctypes
import hashlib
import math
import shutil
import time
from ctypes import wintypes
from pathlib import Path

import pythoncom

from spikes._gemeinsam import lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.referenzen import loese_im_teil
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import loese_auf
from swki.pruefung.bilder import ANSICHTEN, SW_TIFF_SCREEN_OR_PRINT_CAPTURE
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import byref_long, grad, in_mm, mm, r8_array, verbinde

AUFTRAG = "S13"
_ERGEBNIS = {}  # Teilergebnisse bleiben bei einem Abbruch erhalten
TYP = {"abstand": 5, "winkel": 6}  # swMateType_e


def _block(name, laenge, breite, hoehe, weitere):
    return {"art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
            "parameter": {"L": laenge, "B": breite, "H": hoehe},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "oben",
                                     "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                          "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


PLATTE = _block("S13_Platte", 200, 60, 20, [])
SCHIEBER = _block("S13_Schieber", 60, 40, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durch": True}])
HEBEL = _block("S13_Hebel", 50, 12, 8, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]],
     "durchmesser": 8.5, "durch": True}])


class _Speicher(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]


def _privat_mb(pid):
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Speicher), wintypes.DWORD)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    try:
        z = _Speicher()
        z.cb = ctypes.sizeof(z)
        if not k32.K32GetProcessMemoryInfo(h, ctypes.byref(z), z.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(z.PrivateUsage / 2 ** 20, 1)
    finally:
        k32.CloseHandle(h)


def _v(vid, typ, ausrichtung=None, wert=None, sperren=False):
    return Verknuepfung(vid, vid, typ, {}, {}, ausrichtung, wert, sperren)


def _rebuild(asm):
    try:
        sw.rebuild(asm)
        return "ok"
    except BauFehler as e:
        return str(e)


def _sha(ordner):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ordner.glob("*.SLD*"))
            if p.suffix.lower() in (".sldprt", ".sldasm")}


def _teile(app, r, standard, ordner):
    """Platte, Schieber, Hebel bauen und speichern (bleiben offen), Bolzen ISO 8734 8 × 30 holen und öffnen."""
    teile = {}
    for name, spec in (("platte", PLATTE), ("schieber", SCHIEBER), ("hebel", HEBEL)):
        model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, ordner / f"{name}.yaml", AUFTRAG,
                                                Protokoll(AUFTRAG, f"{name}.yaml", 0, r.sw_jahr))
        if fehler is not None:
            raise fehler
        sw.speichere(model, ordner / f"{spec['name']}.sldprt")
        teile[name] = (model, ctx)
    t, a = loese_auf("ISO 8734", "8x30", None)
    ziel = ordner / f"{a.schluessel}.sldprt"
    shutil.copy2(normteil_befehle.hole("ISO 8734", "8x30", None)["pfad"], ziel)
    model = oeffne(app, ziel)
    teile["bolzen"] = (model, kontext_aus_datei(app, model, erzeuge_spec(t, a, vorlage_text(t)), ziel.with_suffix(".yaml"),
                                                standard["toleranzen"]["anker_mm"], {"knoten": []}))
    return teile


def _probe(app, r, teile):
    """Bewegungsprobe ohne Grenzen: Schieber auf der Platte (bündig -z), Bolzen im Schieber, Hebel (Scharnier als
    konzentrisch + Anlage). Liefert (asm, Komponenten, Entität-Funktion)."""
    asm = sw_baugruppe.neue_baugruppe(app, r.vorlage_baugruppe)
    k = {}
    for name in ("platte", "schieber", "bolzen", "hebel"):
        model = teile[name][0]
        k[name] = sw_baugruppe.fuege_ein(app, asm, Path(model.GetPathName), sw.teilebox_mm(model))
    sw_baugruppe.fixiere(asm, k["platte"])

    def e(name, seite):
        return sw_baugruppe.in_baugruppe(k[name], loese_im_teil(teile[name][1], seite))

    f1 = {"feature": "f1"}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "entgegengesetzt"), e("schieber", {**f1, "flaeche": "-y"}),
                            e("platte", {**f1, "flaeche": "+y"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), e("schieber", {**f1, "flaeche": "-z"}),
                            e("platte", {**f1, "flaeche": "-z"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v3", "deckungsgleich", "entgegengesetzt"), e("bolzen", {"referenz": "EINBAU_EBENE_1"}),
                            e("schieber", {**f1, "flaeche": "-y"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v4", "konzentrisch", sperren=True), e("bolzen", {"referenz": "EINBAU_ACHSE"}),
                            e("schieber", {"feature": "f2", "instanz": 1, "achse": True}), {})
    sw_baugruppe.verknuepfe(asm, _v("s1", "konzentrisch"), e("hebel", {"feature": "f2", "instanz": 1, "achse": True}),
                            e("bolzen", {"referenz": "EINBAU_ACHSE"}), {})
    sw_baugruppe.verknuepfe(asm, _v("s1.anlage", "deckungsgleich", "entgegengesetzt"), e("hebel", {**f1, "flaeche": "-y"}),
                            e("schieber", {**f1, "flaeche": "+y"}), {})
    return asm, k, e


def _masse(feature):
    ergebnis = []
    d = feature.GetFirstDisplayDimension
    while d is not None:
        dim = d.GetDimension2(0)
        ergebnis.append({"name": dim.Name, "voll": dim.FullName, "wert": dim.SystemValue})
        d = feature.GetNextDisplayDimension(d)
    for n in ("D1", "D2", "D3", "D4"):
        p = feature.Parameter(n)
        ergebnis.append({"parameter": n, "wert": None if p is None else p.SystemValue})
    return ergebnis


def _grenze(asm, name, art, a, b, ausrichtung, unten, oben):
    """Grenzverknüpfung direkt über AddMate5 (der Handler kommt mit Task 6)."""
    sw.auswahl_leeren(asm)
    sw_baugruppe.waehle(asm, a, False)
    sw_baugruppe.waehle(asm, b, True)
    status = byref_long()
    if art == "abstand":
        w = (mm(unten), mm(oben), mm(unten), 0.0, 0.0, 0.0)
    else:
        w = (0.0, 0.0, 0.0, grad(unten), grad(oben), grad(unten))
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    mate = asm.AddMate5(TYP[art], sw_baugruppe.AUSRICHTUNG[ausrichtung], False, w[0], w[1], w[2], 1, 1, w[3], w[4], w[5],
                        False, False, 0, status)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    e = {"status": status.value, "mate": mate is not None, "neu": neu is not None}
    if neu is not None:
        neu.Name = name
        e["name"] = neu.Name
        e["rebuild"] = _rebuild(asm)
        e["fehlercode"] = sw_baugruppe.fehlercode(neu)
        spez = neu.GetSpecificFeature2
        for attr in ("Type", "MinimumVariation", "MaximumVariation", "Alignment"):
            try:
                e[attr] = getattr(spez, attr)
            except Exception as ex:  # Spike: festhalten
                e[attr] = repr(ex)
        e["masse"] = _masse(neu)
    return neu, e


def _setze_gv(asm, name, wert):
    gl = asm.GetEquationMgr
    index = next(i for i in range(gl.GetCount) if gl.Equation(i).startswith(f'"{name}"'))
    dispid = gl._oleobj_.GetIDsOfNames("Equation")
    gl._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
    gl.EvaluateAll
    return _rebuild(asm)


def _binde(asm, grenze, masse, oben_sw, gv, gv_wert, gv_neu):
    """Gleichung auf das Maß mit dem Wert der oberen Grenze; danach gv ändern und die Grenze lesen."""
    name = next((m["name"] for m in masse if "name" in m and abs(m["wert"] - oben_sw) < 1e-9), None)
    e = {"mass_obere_grenze": name}
    if name is None:
        return e
    gl = asm.GetEquationMgr
    e["add_gv"] = gl.Add2(-1, f'"{gv}" = {gv_wert}', True)
    e["add_bindung"] = gl.Add2(-1, f'"{name}@{grenze.Name}" = "{gv}"', True)
    e["rebuild"] = _rebuild(asm)
    e["rebuild_nach_aenderung"] = _setze_gv(asm, gv, gv_neu)
    spez = grenze.GetSpecificFeature2
    e["MaximumVariation_nach_aenderung"] = spez.MaximumVariation
    e["masse_nach_aenderung"] = _masse(grenze)
    e["rebuild_zurueck"] = _setze_gv(asm, gv, gv_wert)
    return e


def _drehung(t):
    return [[t[3 * j + i] for j in range(3)] for i in range(3)]


def _achse_winkel(t0, t1):
    c0, c1 = _drehung(t0), _drehung(t1)
    q = [[sum(c1[i][k] * c0[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    w = math.degrees(math.acos(max(-1.0, min(1.0, (q[0][0] + q[1][1] + q[2][2] - 1) / 2))))
    v = (q[2][1] - q[1][2], q[0][2] - q[2][0], q[1][0] - q[0][1])
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [round(c / n, 6) for c in v], round(w, 4)


def _weg(t0, t1):
    return round(math.sqrt(sum(in_mm(t1[9 + i] - t0[9 + i]) ** 2 for i in range(3))), 4)


def _stelle(asm, antrieb, art, wert, k, t0):
    mass = antrieb.Parameter("D1")
    mass.SetSystemValue3(mm(wert) if art == "abstand" else grad(wert), 1, None)
    e = {"wert": wert, "rebuild": _rebuild(asm),
         "fehlercodes": {f.Name: c for f in sw_baugruppe.verknuepfungen(asm) if (c := sw_baugruppe.fehlercode(f))}}
    t = sw_baugruppe.transform(k)
    e["weg"] = _weg(t0, t) if art == "abstand" else _achse_winkel(t0, t)
    return e


def _status(k):
    return {n: sw_baugruppe.status(x) for n, x in k.items()}


def _kiste_aus_transform(k, model):
    box = sw.teilebox_mm(model)
    t = sw_baugruppe.transform(k)
    ecken = [(x, y, z) for x in (box[0], box[3]) for y in (box[1], box[4]) for z in (box[2], box[5])]
    welt = [tuple(p[0] * t[i] + p[1] * t[3 + i] + p[2] * t[6 + i] + in_mm(t[9 + i]) for i in range(3)) for p in ecken]
    return [round(min(w[i] for w in welt), 4) for i in range(3)] + [round(max(w[i] for w in welt), 4) for i in range(3)]


def _schritte(app, asm, antrieb, k, n=20):
    pid = int(app.GetProcessID)
    vorher = _privat_mb(pid)
    zeiten = {"stellen": 0.0, "kollision": 0.0, "lage": 0.0}
    for i in range(n):
        t = time.perf_counter()
        antrieb.Parameter("D1").SetSystemValue3(mm((i % 5) * 20), 1, None)
        _rebuild(asm)
        zeiten["stellen"] += time.perf_counter() - t
        t = time.perf_counter()
        sw_baugruppe.interferenzen(asm)
        zeiten["kollision"] += time.perf_counter() - t
        t = time.perf_counter()
        for x in sw_baugruppe.komponenten(asm):
            sw_baugruppe.transform(x)
            x.GetBox(False, False)
        zeiten["lage"] += time.perf_counter() - t
    return {"schritte": n, "komponenten": len(k) if isinstance(k, dict) else k, "s_je_schritt":
            {n_: round(z / n, 4) for n_, z in zeiten.items()}, "privat_mb_vorher": vorher, "privat_mb_nachher": _privat_mb(pid)}


def _iso(app, asm, pfad):
    asm._FlagAsMethod("ViewZoomtofit2")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        asm.ShowNamedView2("", ANSICHTEN["iso"])
        asm.ViewZoomtofit2()
        sw.speichere(asm, pfad, kopie=True)
    return pfad.stat().st_size


def _untersuche():
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / AUFTRAG
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    ergebnis = _ERGEBNIS
    ergebnis["privat_mb_start"] = _privat_mb(int(app.GetProcessID))
    teile = _teile(app, r, standard, ordner)
    try:
        asm, k, e = _probe(app, r, teile)
        try:
            f1 = {"feature": "f1"}
            g1, ergebnis["1_grenze_abstand"] = _grenze(asm, "g1", "abstand", e("schieber", {**f1, "flaeche": "-x"}),
                                                       e("platte", {**f1, "flaeche": "-x"}), "gleich", 0, 100)
            g2, ergebnis["1_grenze_winkel"] = _grenze(asm, "g2", "winkel", e("hebel", {**f1, "flaeche": "+z"}),
                                                      e("schieber", {**f1, "flaeche": "+z"}), "gleich", 0, 90)
            ergebnis["2_bindung_abstand"] = _binde(asm, g1, ergebnis["1_grenze_abstand"].get("masse", []), mm(100),
                                                   "HUB", 100, 120)
            ergebnis["2_bindung_winkel"] = _binde(asm, g2, ergebnis["1_grenze_winkel"].get("masse", []), grad(90),
                                                  "SCHWENK", 90, 80)
            ergebnis["4_status_nur_grenzen"] = _status(k)
            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0), e("schieber", {**f1, "flaeche": "-x"}),
                                         e("platte", {**f1, "flaeche": "-x"}), {})
            ergebnis["4_status_antrieb_hub_auf_min"] = _status(k)
            t0 = sw_baugruppe.transform(k["schieber"])
            ergebnis["3_antrieb_hub"] = [_stelle(asm, a1, "abstand", w, k["schieber"], t0)
                                         for w in (25, 50, 100, 103.125, 100, 120, 100, 0)]
            a2 = sw_baugruppe.verknuepfe(asm, _v("g2.antrieb", "winkel", "gleich", 0), e("hebel", {**f1, "flaeche": "+z"}),
                                         e("schieber", {**f1, "flaeche": "+z"}), {})
            ergebnis["4_status_beide_antriebe"] = _status(k)
            th = sw_baugruppe.transform(k["hebel"])
            ergebnis["7_drehsinn"] = [_stelle(asm, a2, "winkel", w, k["hebel"], th) for w in (45, 90, 92.8125, 90, 0)]
            _stelle(asm, a2, "winkel", 90, k["hebel"], th)
            ergebnis["6_getbox_hebel"] = [round(in_mm(x), 4) for x in k["hebel"].GetBox(False, False)]
            ergebnis["6_teilebox_umgerechnet_hebel"] = _kiste_aus_transform(k["hebel"], teile["hebel"][0])
            (ordner / "bilder").mkdir(exist_ok=True)
            ergebnis["9_iso_bytes"] = _iso(app, asm, ordner / "bilder" / "s13_iso.png")
            _stelle(asm, a2, "winkel", 0, k["hebel"], th)
            ergebnis["8_probe"] = _schritte(app, asm, a1, k)
            _stelle(asm, a1, "abstand", 0, k["schieber"], t0)
            vor_loeschen = {n: sw_baugruppe.transform(x) for n, x in k.items()}
            for a in (a2, a1):
                sw_baugruppe._loesche(asm, a)
            ergebnis["5_rebuild_nach_loeschen"] = _rebuild(asm)
            ergebnis["5_lage_unveraendert"] = {
                n: max(abs(p - q) for p, q in zip(vor_loeschen[n], sw_baugruppe.transform(x))) for n, x in k.items()}
            ergebnis["5_status_nach_loeschen"] = _status(k)
            sw.speichere(asm, ordner / "S13_Probe.sldasm")
            namen = {x.Name2: n for n, x in k.items()}  # vor dem Schließen lesen (danach sind die Objekte tot)
        finally:
            sw.schliesse(app, asm)
        vorher = _sha(ordner)
        asm = oeffne(app, ordner / "S13_Probe.sldasm")
        try:
            sw_baugruppe.aufloesen(asm)
            k2 = {namen.get(x.Name2, x.Name2): x for x in sw_baugruppe.komponenten(asm)}

            def e2(name, seite):
                return sw_baugruppe.in_baugruppe(k2[name], loese_im_teil(teile[name][1], seite))

            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0),
                                         e2("schieber", {"feature": "f1", "flaeche": "-x"}),
                                         e2("platte", {"feature": "f1", "flaeche": "-x"}), {})
            t0 = sw_baugruppe.transform(k2["schieber"])
            ergebnis["5_nach_oeffnen_verstellen"] = _stelle(asm, a1, "abstand", 60, k2["schieber"], t0)
        finally:
            sw.schliesse(app, asm)
        ergebnis["5_sha_unveraendert"] = _sha(ordner) == vorher
        asm, k, e = _probe(app, r, teile)
        try:
            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0),
                                         e("schieber", {"feature": "f1", "flaeche": "-x"}),
                                         e("platte", {"feature": "f1", "flaeche": "-x"}), {})
            bolzen = Path(teile["bolzen"][0].GetPathName)
            box = sw.teilebox_mm(teile["bolzen"][0])
            mu = sw.mathutil(app)
            for i in range(96):
                x = sw_baugruppe.fuege_ein(app, asm, bolzen, box)
                lage = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
                        mm(-90 + (i % 12) * 16), mm(-60), mm(-60 - (i // 12) * 16), 1.0, 0.0, 0.0, 0.0]
                x.SetTransformAndSolve2(mu.CreateTransform(r8_array(lage)))
                sw_baugruppe.fixiere(asm, x)
            ergebnis["8_hundert_komponenten"] = _schritte(app, asm, a1, len(sw_baugruppe.komponenten(asm)))
        finally:
            sw.schliesse(app, asm)
    finally:
        for model, _ in reversed(list(teile.values())):
            sw.schliesse(app, model)
    ergebnis["privat_mb_ende"] = _privat_mb(int(app.GetProcessID))
    return ergebnis


def _mit_teilergebnis():
    try:
        return _untersuche()
    except Exception:  # Spike: bis dahin Gemessenes nicht verlieren
        import traceback
        _ERGEBNIS["abbruch"] = traceback.format_exc()
        return _ERGEBNIS


if __name__ == "__main__":
    lauf("s13_bewegung", _mit_teilergebnis)
