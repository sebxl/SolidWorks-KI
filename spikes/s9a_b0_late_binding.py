"""S9a Baustein 0: erzwungenes Late Binding, auch bei vorhandenem gen_py-Cache.

Ablauf: (1) Probe ohne Cache, (2) gencache.EnsureModule(sldworks.tlb), (3) Probe mit Cache in
frischem Prozess, (4) erzeugte SW-Cache-Dateien löschen (dicts.dat auf Stand vor dem Lauf
zurücksetzen), (5) Probe nach dem Aufräumen.
Probe-Läufe laufen jeweils in einem frischen Python-Prozess (sys.modules unbelastet).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from spikes._gemeinsam import lauf

PY = sys.executable


def _probe() -> dict:
    """Wird im Unterprozess ausgeführt."""
    import pythoncom
    import win32com.client
    import win32com.client.dynamic

    from spikes.s9a_gemeinsam import start

    from swki.konfig import lade_rechner

    d = {}
    # Standardweg (wie swki.verbindung): getypt, sobald Cache vorhanden
    std = win32com.client.GetActiveObject(f"SldWorks.Application.{lade_rechner().sw_jahr - 1992}")
    d["standard_getactiveobject_typ"] = f"{type(std).__module__}.{type(std).__qualname__}"
    # Erzwungener Weg
    r, app = start()
    d["erzwungen_app_typ"] = f"{type(app).__module__}.{type(app).__qualname__}"
    d["revision_ohne_klammern"] = app.RevisionNumber
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    titel = model.GetTitle
    try:
        d["model_typ"] = f"{type(model).__module__}.{type(model).__qualname__}"
        f = model.FirstFeature
        d["feature_typ"] = f"{type(f).__module__}.{type(f).__qualname__}"
        d["feature_typname_ohne_klammern"] = f.GetTypeName2
        d["featuremanager_typ"] = type(model.FeatureManager).__qualname__
        d["alle_cdispatch"] = all(type(x) is win32com.client.dynamic.CDispatch for x in (app, model, f, model.FeatureManager, model.Extension))
    finally:
        app.CloseDoc(titel)
    return d


def _probe_extern() -> dict:
    out = subprocess.run([PY, "-m", "spikes.s9a_b0_late_binding", "--probe"], capture_output=True, text=True,
                         cwd=str(Path(__file__).resolve().parent.parent))
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"stdout": out.stdout[-2000:], "stderr": out.stderr[-2000:]}


def pruefen() -> dict:
    import pythoncom
    import win32com
    import win32com.client.gencache as gencache

    from swki.konfig import lade_rechner

    r = lade_rechner()
    gen = Path(win32com.__gen_path__)
    daten: dict = {"gen_path": str(gen)}
    vorher = sorted(p.name for p in gen.rglob("*"))
    daten["gen_py_vorher"] = vorher
    dicts_backup = gen.parent / "dicts.dat.s9a_backup"
    shutil.copy2(gen / "dicts.dat", dicts_backup)

    daten["probe_ohne_cache"] = _probe_extern()

    tlb = pythoncom.LoadTypeLib(str(r.installationsordner / "sldworks.tlb"))
    guid, lcid, _sk, major, minor, _fl = tlb.GetLibAttr()
    gencache.EnsureModule(str(guid), lcid, major, minor)
    neu = sorted(p.name for p in gen.rglob("*") if p.name not in vorher)
    daten["ensuremodule_sldworks"] = {"guid": str(guid), "neue_dateien": neu}

    daten["probe_mit_cache"] = _probe_extern()

    # Aufräumen: nur SW-Typbibliotheken (83A33D31 = sldworks, 4687F359 = swconst)
    geloescht = []
    for p in list(gen.rglob("*")):
        if p.is_file() and (p.name.startswith("83A33D31") or p.name.startswith("4687F359")):
            p.unlink()
            geloescht.append(p.name)
    shutil.copy2(dicts_backup, gen / "dicts.dat")
    dicts_backup.unlink()
    daten["geloescht"] = geloescht
    daten["dicts_dat_zurueckgesetzt"] = True
    daten["gen_py_nachher"] = sorted(p.name for p in gen.rglob("*"))
    daten["probe_nach_aufraeumen"] = _probe_extern()
    return daten


if __name__ == "__main__":
    if "--probe" in sys.argv:
        print(json.dumps(_probe(), default=str))
    else:
        lauf("s9a_b0_late_binding", pruefen)
