"""S9b Baustein 17: Material zuweisen und zurücklesen.

Datenbanken: ISldWorks.GetMaterialDatabases (volle Pfade) + config/rechner.yaml materialdatenbank.
*.sldmat sind XML (UTF-16 mit BOM) -> Materialnamen je Klassifikation. Quader 100 x 60 x 20 = 120 cm³.
SetMaterialPropertyName2(Config, Database, Name) mit verschiedenen Schreibweisen von Database/Name,
GetMaterialPropertyName2 / MaterialIdName zurücklesen, Masse vorher/nachher.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import kasten_oben, start, teil
from spikes.s9b_gemeinsam import byref_str


def materialien(pfad: str) -> list:
    root = ET.fromstring(Path(pfad).read_bytes())   # Bytes: BOM/Deklaration (UTF-16) wertet der Parser aus
    return [(c.get("name"), m.get("name")) for c in root.iter("classification") for m in c.iter("material")]


def masse(model) -> dict:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return {"masse_kg": round(mp.Mass, 6), "dichte_kg_m3": round(mp.Density, 3), "volumen_mm3": round(mp.Volume * 1e9, 3)}


def lies(model) -> dict:
    db = byref_str()
    name = model.GetMaterialPropertyName2("", db)
    return {"name": name, "db": db.value, "material_id_name": model.MaterialIdName}


def pruefen() -> dict:
    r, app = start()
    dbs = list(app.GetMaterialDatabases)
    d: dict = {"datenbanken": dbs, "rechner_yaml_materialdatenbank": str(r.materialdatenbank)}
    d["inhalt"] = {}
    for p in dbs:
        mats = materialien(p)
        d["inhalt"][Path(p).name] = {"anzahl": len(mats), "erste": mats[:3],
                                     "treffer_2312": [m for m in mats if "1.2312" in (m[1] or "")]}
    d["versuche"] = []
    versuche = [
        ("SolidWorks DIN Materials", "1.2312 (40CrMnMoS8-6)"),
        ("solidworks din materials.sldmat", "1.2312 (40CrMnMoS8-6)"),
        ("solidworks din materials", "1.2312"),
        (dbs[1] if len(dbs) > 1 else "", "1.2312 (40CrMnMoS8-6)"),
        ("SOLIDWORKS Materials", "AISI 1020"),
        ("Benutzerdefinierte Materialien", "XPS"),
        ("gibtsnicht", "1.2312 (40CrMnMoS8-6)"),
    ]
    for db, name in versuche:
        with teil(app, r) as model:
            kasten_oben(model, 100, 60, 20)
            vorher = {**masse(model), **lies(model)}
            try:
                ret = model.SetMaterialPropertyName2("", db, name)
                model.EditRebuild3
                nachher = {**masse(model), **lies(model)}
                d["versuche"].append({"database": db, "name": name, "rueckgabe": ret, "vorher": vorher, "nachher": nachher})
            except Exception as e:
                d["versuche"].append({"database": db, "name": name, "fehler": repr(e)})
    return d


if __name__ == "__main__":
    lauf("s9b_b17_material", pruefen)
