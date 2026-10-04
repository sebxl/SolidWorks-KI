"""S13b (Stufe 4a): Nachtrag zu S13 – Bestimmtheit ohne Grenzen / mit unterdrückten Grenzen, Gleichung auf Grenzmaße,
Zeit und Private Bytes je Teilschritt.

Blöcke (einzeln aufrufen, zwischen den Blöcken Speicher prüfen):
  E     Probe (Grenzen g1/g2, Antriebe a1/a2 wie in S13): Private Bytes nach Teilen/Probe, 20 Schritte, 4 Teilschritte getrennt
  E100  Probe + Antrieb + 96 fixierte Stifte (~100 Komponenten), 20 Schritte, 4 Teilschritte getrennt
  AB    A: Probe ohne Grenzen, mit Antrieb g1, mit beiden Antrieben; B: Grenzen unterdrücken / entdrücken
  C     Probe ohne v2 (seitliche Führung): Schieber nur mit Grenze, mit Antrieb, mit unterdrückter Grenze + Antrieb
  D     Gleichung direkt auf D1/D2/D3@g1

Aufruf: .venv\\Scripts\\python.exe -m spikes.s13b_bewegung <Block>
"""

import json
import shutil
import sys
import time
import traceback

from spikes import s13_bewegung as s
from spikes._gemeinsam import ERGEBNISSE, lauf
from swki.baugruppe import sw_baugruppe
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.verbindung import in_mm, mm, r8_array, verbinde

AUFTRAG = "S13b"
DATEI = ERGEBNISSE / "s13b_bewegung.json"
F1 = {"feature": "f1"}
_ERGEBNIS = {}


def _start(block):
    """Ordner, Verbindung, Teile; Private Bytes nach den Teilen festhalten."""
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    pid = int(app.GetProcessID)
    ordner = r.arbeitsordner / AUFTRAG / block
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    ergebnis = _ERGEBNIS.setdefault(block, {})
    ergebnis["privat_mb_start"] = s._privat_mb(pid)
    s.AUFTRAG = AUFTRAG  # Protokollname der Teilbauten
    teile = s._teile(app, r, standard, ordner)
    ergebnis["privat_mb_nach_teilen"] = s._privat_mb(pid)
    return r, app, pid, ordner, teile, ergebnis


def _ende(app, pid, teile, ergebnis):
    for model, _ in reversed(list(teile.values())):
        sw.schliesse(app, model)
    ergebnis["privat_mb_ende"] = s._privat_mb(pid)


def _status(k):
    return s._status(k)


def _antrieb_abstand(asm, e):
    return sw_baugruppe.verknuepfe(asm, s._v("g1.antrieb", "abstand", "gleich", 0), e("schieber", {**F1, "flaeche": "-x"}),
                                   e("platte", {**F1, "flaeche": "-x"}), {})


def _antrieb_winkel(asm, e):
    return sw_baugruppe.verknuepfe(asm, s._v("g2.antrieb", "winkel", "gleich", 0), e("hebel", {**F1, "flaeche": "+z"}),
                                   e("schieber", {**F1, "flaeche": "+z"}), {})


def _grenzen(asm, e):
    g1, e1 = s._grenze(asm, "g1", "abstand", e("schieber", {**F1, "flaeche": "-x"}), e("platte", {**F1, "flaeche": "-x"}),
                       "gleich", 0, 100)
    g2, e2 = s._grenze(asm, "g2", "winkel", e("hebel", {**F1, "flaeche": "+z"}), e("schieber", {**F1, "flaeche": "+z"}),
                       "gleich", 0, 90)
    return g1, g2, e1, e2


def _unterdruecke(features, aktion):
    """aktion 0 = swSuppressFeature, 1 = swUnSuppressFeature; SetSuppression2(Zustand, swThisConfiguration = 1, None)."""
    ergebnis = []
    for f in features:
        try:
            ergebnis.append({"name": f.Name, "rueckgabe": f.SetSuppression2(aktion, 1, None)})
        except Exception as ex:  # Spike: festhalten
            ergebnis.append({"name": f.Name, "fehler": repr(ex)})
    return ergebnis


def _ist_unterdrueckt(features):
    ergebnis = []
    for f in features:
        try:
            ergebnis.append(bool(f.IsSuppressed))
        except Exception as ex:  # Spike: festhalten
            ergebnis.append(repr(ex))
    return ergebnis


def _lagen(k):
    return {n: sw_baugruppe.transform(x) for n, x in k.items()}


def _lage_diff(vorher, k):
    return {n: max(abs(p - q) for p, q in zip(vorher[n], sw_baugruppe.transform(x))) for n, x in k.items()}


def _fehlercodes(asm):
    return {f.Name: c for f in sw_baugruppe.verknuepfungen(asm) if (c := sw_baugruppe.fehlercode(f))}


# ---------------------------------------------------------------- E
def _teilschritte(app, asm, antrieb, pid, n=20):
    """Je Schritt vier Teilschritte getrennt: Zeit und Private-Bytes-Änderung; die Komponentenliste (GetComponents) gesondert."""
    namen = ("0_komponentenliste", "1_stellen_rebuild", "2_interferenzen", "3_transform2", "4_getbox")
    zeit = dict.fromkeys(namen, 0.0)
    speicher = dict.fromkeys(namen, 0.0)
    verlauf = [s._privat_mb(pid)]
    vorher = verlauf[0]

    def messe(name, fn):
        m0 = s._privat_mb(pid)
        t0 = time.perf_counter()
        ergebnis = fn()
        zeit[name] += time.perf_counter() - t0
        speicher[name] += s._privat_mb(pid) - m0
        return ergebnis

    for i in range(n):
        komp = messe("0_komponentenliste", lambda: sw_baugruppe.komponenten(asm))

        def stellen(i=i):
            antrieb.Parameter("D1").SetSystemValue3(mm((i % 5) * 20), 1, None)
            s._rebuild(asm)

        messe("1_stellen_rebuild", stellen)
        messe("2_interferenzen", lambda: sw_baugruppe.interferenzen(asm))
        messe("3_transform2", lambda: [sw_baugruppe.transform(x) for x in komp])
        messe("4_getbox", lambda: [x.GetBox(False, False) for x in komp])
        verlauf.append(s._privat_mb(pid))
    return {"schritte": n, "komponenten": len(komp), "s_je_schritt": {k: round(v / n, 4) for k, v in zeit.items()},
            "privat_mb_summe_je_teilschritt": {k: round(v, 1) for k, v in speicher.items()},
            "privat_mb_vorher": vorher, "privat_mb_nachher": verlauf[-1], "privat_mb_verlauf": verlauf}


def _block_e():
    r, app, pid, ordner, teile, ergebnis = _start("E")
    try:
        asm, k, e = s._probe(app, r, teile)
        try:
            ergebnis["privat_mb_nach_probe"] = s._privat_mb(pid)
            _grenzen(asm, e)
            a1 = _antrieb_abstand(asm, e)
            _antrieb_winkel(asm, e)
            ergebnis["privat_mb_nach_grenzen_antrieben"] = s._privat_mb(pid)
            ergebnis["probe"] = _teilschritte(app, asm, a1, pid)
        finally:
            sw.schliesse(app, asm)
    finally:
        _ende(app, pid, teile, ergebnis)


def _block_e100():
    r, app, pid, ordner, teile, ergebnis = _start("E100")
    try:
        asm, k, e = s._probe(app, r, teile)
        try:
            ergebnis["privat_mb_nach_probe"] = s._privat_mb(pid)
            a1 = _antrieb_abstand(asm, e)
            bolzen = s.Path(teile["bolzen"][0].GetPathName)
            box = sw.teilebox_mm(teile["bolzen"][0])
            mu = sw.mathutil(app)
            for i in range(96):
                x = sw_baugruppe.fuege_ein(app, asm, bolzen, box)
                lage = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
                        mm(-90 + (i % 12) * 16), mm(-60), mm(-60 - (i // 12) * 16), 1.0, 0.0, 0.0, 0.0]
                x.SetTransformAndSolve2(mu.CreateTransform(r8_array(lage)))
                sw_baugruppe.fixiere(asm, x)
            ergebnis["privat_mb_nach_100_komponenten"] = s._privat_mb(pid)
            ergebnis["probe100"] = _teilschritte(app, asm, a1, pid)
        finally:
            sw.schliesse(app, asm)
    finally:
        _ende(app, pid, teile, ergebnis)


# ---------------------------------------------------------------- A, B
def _block_ab():
    r, app, pid, ordner, teile, ergebnis = _start("AB")
    try:
        asm, k, e = s._probe(app, r, teile)
        try:
            a = ergebnis["A"] = {}
            a["0_ohne_grenzen_ohne_antrieb"] = _status(k)
            a1 = _antrieb_abstand(asm, e)
            a["1_nur_antrieb_g1"] = _status(k)
            a2 = _antrieb_winkel(asm, e)
            a["2_beide_antriebe"] = _status(k)
            a["3_beide_antriebe_hub_50_winkel_45"] = None
            t0, th = sw_baugruppe.transform(k["schieber"]), sw_baugruppe.transform(k["hebel"])
            s._stelle(asm, a1, "abstand", 50, k["schieber"], t0)
            s._stelle(asm, a2, "winkel", 45, k["hebel"], th)
            a["3_beide_antriebe_hub_50_winkel_45"] = _status(k)
            s._stelle(asm, a2, "winkel", 0, k["hebel"], th)
            s._stelle(asm, a1, "abstand", 0, k["schieber"], t0)
            for x in (a2, a1):
                sw_baugruppe._loesche(asm, x)
            a["4_rebuild_nach_loeschen"] = s._rebuild(asm)
            a["4_status_nach_loeschen"] = _status(k)

            b = ergebnis["B"] = {}
            g1, g2, b["g1"], b["g2"] = _grenzen(asm, e)
            b["1_grenzen_status"] = _status(k)
            vor = _lagen(k)
            b["2_unterdruecken"] = _unterdruecke((g1, g2), 0)
            b["2_ist_unterdrueckt"] = _ist_unterdrueckt((g1, g2))
            b["2_rebuild"] = s._rebuild(asm)
            b["2_status_unterdrueckt"] = _status(k)
            a1 = _antrieb_abstand(asm, e)
            a2 = _antrieb_winkel(asm, e)
            b["3_status_unterdrueckt_beide_antriebe"] = _status(k)
            b["3_stellen_ueber_grenze_unterdrueckt"] = {
                "hub_120": s._stelle(asm, a1, "abstand", 120, k["schieber"], t0),
                "winkel_100": s._stelle(asm, a2, "winkel", 100, k["hebel"], th)}
            b["3_status_nach_ueber_grenze"] = _status(k)
            s._stelle(asm, a2, "winkel", 0, k["hebel"], th)
            s._stelle(asm, a1, "abstand", 0, k["schieber"], t0)
            b["3_lage_zurueck_diff"] = _lage_diff(vor, k)
            b["4_entdruecken"] = _unterdruecke((g1, g2), 1)
            b["4_ist_unterdrueckt"] = _ist_unterdrueckt((g1, g2))
            b["4_rebuild"] = s._rebuild(asm)
            b["4_fehlercodes"] = _fehlercodes(asm)
            b["4_status_entdrueckt_mit_antrieben"] = _status(k)
            b["4_lage_unveraendert_diff"] = _lage_diff(vor, k)
            b["4_grenze_max"] = [g1.GetSpecificFeature2.MaximumVariation, g2.GetSpecificFeature2.MaximumVariation]
            b["5_ueber_grenze_nach_entdruecken"] = s._stelle(asm, a1, "abstand", 120, k["schieber"], t0)
            s._stelle(asm, a1, "abstand", 0, k["schieber"], t0)
        finally:
            sw.schliesse(app, asm)
    finally:
        _ende(app, pid, teile, ergebnis)


# ---------------------------------------------------------------- C
def _block_c():
    r, app, pid, ordner, teile, ergebnis = _start("C")
    try:
        asm, k, e = s._probe(app, r, teile)
        try:
            c = ergebnis["C"] = {}
            v2 = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "v2")
            sw_baugruppe._loesche(asm, v2)
            c["0_rebuild_ohne_v2"] = s._rebuild(asm)
            c["0_ohne_v2_ohne_grenze"] = _status(k)
            g1, e1 = s._grenze(asm, "g1", "abstand", e("schieber", {**F1, "flaeche": "-x"}),
                               e("platte", {**F1, "flaeche": "-x"}), "gleich", 0, 100)
            c["g1"] = {key: e1.get(key) for key in ("status", "rebuild", "fehlercode")}
            c["1_nur_grenze"] = _status(k)
            a1 = _antrieb_abstand(asm, e)
            c["2_grenze_und_antrieb"] = _status(k)
            vor = _lagen(k)
            c["3_unterdrueckt"] = _unterdruecke((g1,), 0)
            c["3_rebuild"] = s._rebuild(asm)
            c["3_status_unterdrueckte_grenze_antrieb"] = _status(k)
            c["3_lage_diff"] = _lage_diff(vor, k)
            c["4_entdruecken"] = _unterdruecke((g1,), 1)
            c["4_rebuild"] = s._rebuild(asm)
            c["4_status"] = _status(k)
            c["5_antrieb_geloescht"] = None
            sw_baugruppe._loesche(asm, a1)
            c["5_rebuild"] = s._rebuild(asm)
            c["5_status_grenze_ohne_antrieb"] = _status(k)
        finally:
            sw.schliesse(app, asm)
    finally:
        _ende(app, pid, teile, ergebnis)


# ---------------------------------------------------------------- D
def _gleichungen(gl):
    return [gl.Equation(i) for i in range(gl.GetCount)]


def _block_d():
    r, app, pid, ordner, teile, ergebnis = _start("D")
    try:
        asm, k, e = s._probe(app, r, teile)
        try:
            d = ergebnis["D"] = {}
            g1, e1 = s._grenze(asm, "g1", "abstand", e("schieber", {**F1, "flaeche": "-x"}),
                               e("platte", {**F1, "flaeche": "-x"}), "gleich", 0, 100)
            spez = g1.GetSpecificFeature2
            d["0_masse_per_name"] = {}
            for n in ("D1", "D2", "D3", "D4"):
                try:
                    p = asm.Parameter(f"{n}@g1")
                    d["0_masse_per_name"][n] = None if p is None else {"voll": p.FullName, "wert": p.SystemValue}
                except Exception as ex:  # Spike: festhalten
                    d["0_masse_per_name"][n] = repr(ex)
            gl = asm.GetEquationMgr
            d["1_add_hub"] = gl.Add2(-1, '"HUB" = 100', True)
            d["1_rebuild"] = s._rebuild(asm)
            for ziel in ("D2@g1", "D3@g1", "D1@g1"):
                x = d[ziel] = {}
                try:
                    x["add"] = gl.Add2(-1, f'"{ziel}" = "HUB"', True)
                    x["gleichungen"] = _gleichungen(gl)
                    x["rebuild"] = s._rebuild(asm)
                    x["max_min_vorher"] = [spez.MaximumVariation, spez.MinimumVariation]
                    x["masse_vorher"] = s._masse(g1)
                    x["rebuild_hub_120"] = s._setze_gv(asm, "HUB", 120)
                    x["gleichungen_nach_120"] = _gleichungen(gl)
                    x["gleichungswerte_nach_120"] = [gl.Value(i) for i in range(gl.GetCount)]
                    x["max_min_nach_120"] = [spez.MaximumVariation, spez.MinimumVariation]
                    x["masse_nach_120"] = s._masse(g1)
                    x["rebuild_hub_100"] = s._setze_gv(asm, "HUB", 100)
                    x["max_min_nach_100"] = [spez.MaximumVariation, spez.MinimumVariation]
                    if x["add"] is not None and x["add"] >= 0:
                        x["delete"] = gl.Delete(x["add"])
                        x["rebuild_nach_delete"] = s._rebuild(asm)
                        x["max_min_nach_delete"] = [spez.MaximumVariation, spez.MinimumVariation]
                except Exception as ex:  # Spike: festhalten und weiter
                    x["fehler"] = repr(ex)
                    x["trace"] = traceback.format_exc()
        finally:
            sw.schliesse(app, asm)
    finally:
        _ende(app, pid, teile, ergebnis)


BLOECKE = {"E": _block_e, "E100": _block_e100, "AB": _block_ab, "C": _block_c, "D": _block_d}


def _untersuche():
    block = sys.argv[1]
    if DATEI.exists():
        _ERGEBNIS.update(json.loads(DATEI.read_text(encoding="utf-8")))
        _ERGEBNIS.pop("ok", None)
        _ERGEBNIS.pop("abbruch", None)
    try:
        BLOECKE[block]()
    except Exception:  # Spike: bis dahin Gemessenes nicht verlieren
        _ERGEBNIS.setdefault(block, {})["abbruch"] = traceback.format_exc()
    return _ERGEBNIS


if __name__ == "__main__":
    lauf("s13b_bewegung", _untersuche)
