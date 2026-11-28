"""Spike Z1.3 Stufe 4, Teil i (Nachbesserung C, Task 5): Lagen und Hindernisse der Anmerkungen im Schnitt.

1. Bezugsdreieck auf der Verlängerung der Fläche (ISO 5459): Bezug „B“ über `IAnnotation.SetPosition2` über das
   Kantenende hinaus setzen – bleibt die Lage (`GetPosition`), zeichnet SolidWorks die Verlängerung? (PDF je Lage)
2. Schraffierte Schnittfläche: `IView.GetFaceHatches` → `IFaceHatch.Face` → `IFace2.GetEdges` in Blatt-mm.
3. Eckpunkte: `IView.GetVisibleEntities2(…, swViewEntityType_Vertex = 2)` + `IVertex.GetPoint` über
   `ModelToViewTransform` – liegen sie auf den Kantenenden?

Arbeitet auf einer Kopie der Zeichnung (`<name>_spike4i.SLDDRW` im selben Ordner), schließt ohne das Teil zu speichern
und prüft die Teil-SHA.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4i <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from swki.compiler import sw
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung import anforderungen_setzen as an
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

ECKPUNKT = 2  # swViewEntityType_e.swViewEntityType_Vertex


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _lage(ann) -> list:
    return [round(c * 1000, 2) for c in list(_ruf(ann, "GetPosition"))[:2]]


def main(quelle: Path, teil: Path) -> None:
    vorher = _sha(teil)
    kopie = quelle.with_name(quelle.stem + "_spike4i.SLDDRW")
    shutil.copy2(quelle, kopie)
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(kopie), 3, 1, "", f, w)
    aus: dict = {}
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and not _ruf(v, "GetName2").startswith("Schnitt"):
            v = _ruf(v, "GetNextView")
        # 1. Bezug B auf der Verlängerung
        d, tags = _ruf(v, "GetFirstDatumTag"), {}
        while d is not None:
            tags[_ruf(d, "GetLabel")] = d
            d = _ruf(d, "GetNext")
        kanten = an.sichtbare_kanten(mu, v)
        links = min((k for k in kanten if not k.kreis and not k.punkt and abs(k.a[0] - k.e[0]) < 1e-3),
                    key=lambda k: k.a[0])
        x, oben, unten = links.a[0], max(links.a[1], links.e[1]), min(links.a[1], links.e[1])
        ann = _ruf(tags["B"], "GetAnnotation")
        aus["kante_links"] = [round(x, 2), round(unten, 2), round(oben, 2)]
        ext = _ruf(drw, "Extension")
        for i, soll in enumerate([(x - 6.0, oben + 6.5), (x - 6.0, unten - 6.5)]):
            ann.SetPosition2(soll[0] / 1000, soll[1] / 1000, 0)
            _ruf(drw, "EditRebuild3")
            pdf = kopie.with_name(f"{quelle.stem}_spike4i_{i}.pdf")
            ext.SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), f, w)
            aus[f"bezug_soll_{i}"] = {"soll": [round(c, 2) for c in soll], "ist": _lage(ann), "pdf": str(pdf)}
        # 2. Schraffur
        aus["schraffur"] = [[[round(c, 2) for c in p] for p in s] for s in an.schraffur_strecken(mu, v)]
        # 3. Eckpunkte gegen Kantenenden
        t = _ruf(v, "ModelToViewTransform")
        enden = [p for k in kanten if not k.punkt for p in (k.a, k.e)]
        abstaende = []
        for p in list(v.GetVisibleEntities2(callout_leer(), ECKPUNKT) or ()):
            q = mu.CreatePoint(r8_array(list(_ruf(p, "GetPoint"))[:3])).MultiplyTransform(t).ArrayData
            b = (q[0] * 1000, q[1] * 1000)
            abstaende.append(round(min(((b[0] - e[0]) ** 2 + (b[1] - e[1]) ** 2) ** 0.5 for e in enden), 2))
        aus["eckpunkt_abstand_zum_naechsten_kantenende_mm"] = abstaende
    finally:
        sw.schliesse(app, drw)
        for doc in list(app.GetDocuments or ()):
            try:
                if Path(doc.GetPathName).resolve() == teil.resolve():
                    sw.schliesse(app, doc)
            except Exception:  # noqa: BLE001 – COM: Dokument ohne Pfad
                pass
    aus["teil_unveraendert"] = _sha(teil) == vorher
    print(json.dumps(aus, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
