# pywin32 + SolidWorks: geprüfte Muster

Stand: 2026-09-26, SW 2025, Python 3.14. Nur Einträge, die in `docs/stufe0/ergebnisse.md` und den
zugehörigen `docs/stufe0/ergebnisse/*.json` belegt sind.

## Verbindung

- An laufendes SolidWorks hängen: `win32com.client.GetActiveObject("SldWorks.Application.<rev>")`
  (`swki.verbindung.verbinde`).
- Binding: **Late Binding** (dynamischer Dispatch über `GetActiveObject`) funktioniert einwandfrei
  unter Python 3.14 (S1). **Early Binding** über `win32com.client.gencache.EnsureDispatch` auf ein
  bereits laufendes Objekt schlägt fehl (`TypeError("This COM object can not automate the makepy
  process – please run makepy manually for this object")`) – `gencache` kann für ein schon
  existierendes OLE-Objekt keine passende generierte Wrapperklasse automatisch erzeugen; müsste
  vorher explizit per `makepy`/`EnsureModule` generiert werden. Für Stufe 0/1/2 nicht nötig, da Late
  Binding ausreicht.

## Einheiten

- API: Meter, Radiant, m³. Hilfen: `swki.verbindung.mm` / `in_mm` / `in_mm3` / `grad`.

## Auswahl ohne Namen (deutsche Oberfläche)

- Standardebenen: erste drei `RefPlane`-Features liefern sprachunabhängig „Ebene vorne“,
  „Ebene oben“, „Ebene rechts“ (S2).
- Flächen: `IModelDocExtension.SelectByRay` (S6).

## Parameter-Eigenheiten

- Callout: `callout_leer()` = `VARIANT(VT_DISPATCH, None)`. Nötig für `System.Object`-Parameter,
  die laut Doku optional sind: rohes Python-`None` löst dort `com_error(-2147352571,
  'Typenkonflikt.')` aus. Belegt für `ISketchManager.FullyDefineSketch` (`HorizontalDatumDisp`/
  `VerticalDatumDisp`, S3) und `IComponent2.Select4` (`Data`, S5).
- ByRef-long (z. B. `ErrorStatus`): `byref_long()`; Wert danach in `.value`.
- **Nullargumentige COM-Member ohne `()` aufrufen:** pywin32s dynamischer Dispatch ruft
  nullargumentige Member (unabhängig davon, ob die VBA-Doku sie als `Function` oder `Sub` führt und
  unabhängig vom Rückgabetyp) bereits beim reinen Attributzugriff auf. Ein zusätzliches `()` versucht
  dann, das bereits zurückgegebene Ergebnis selbst aufzurufen, und scheitert:
  - liefert der Member ein COM-Objekt: `com_error('Mitglied nicht gefunden.')`, weil jedes
    `win32com.client.CDispatch`-Objekt selbst `__call__` definiert (COM-Default-Member), das
    zurückgegebene Objekt aber keinen eigenen Default-Member hat. Belegt für
    `IModelDoc2.FirstFeature`, `IFeature.GetNextFeature` (S2/S3/S4), `IFeature.GetSpecificFeature2`
    (S3), `IModelDocExtension.CreateMassProperty` (S4), `IAssemblyDoc.InterferenceDetectionManager`
    (S5).
  - liefert der Member einen primitiven Wert (z. B. `bool`): `TypeError("'bool' object is not
    callable")`. Belegt für `IModelDoc2.ViewZoomtofit2` (S4) und `IAssemblyDoc.EditRebuild3` (S6).

  **`swki.verbindung.wert()` ist für diesen Fall NICHT geeignet** (Ruling R11): `wert()` prüft nur
  `callable(x)`, und jedes COM-Objekt ist wegen `__call__` `callable` – auch ein bereits fertiges
  Ergebnis. `wert()` würde es also fälschlich nochmal aufrufen. `wert()` eignet sich nur für
  Getter/Properties mit **primitivem** Rückgabewert, bei denen kein COM-Objekt zurückkommt (z. B.
  `RevisionNumber`, `GetTitle`). Für nullargumentige Member, die ein COM-Objekt liefern, reinen
  Attributzugriff ohne `wert()` und ohne `()` verwenden, z. B. `model.FirstFeature` statt
  `wert(model.FirstFeature)` oder `model.FirstFeature()`.
- `IAssemblyDoc.AddComponent5` (`X`/`Y`/`Z`): positioniert laut API-Doku das **Zentrum der
  Bauteil-Bounding-Box**, nicht den Bauteil-Ursprung (S6, live per `Transform2` vor/nach dem Mate
  nachgemessen: konstanter Versatz von der halben Bauteiltiefe). Wer eine Komponente an einer
  bestimmten Ursprungsposition braucht, muss den Bounding-Box-Versatz selbst herausrechnen oder nach
  dem Einfügen per `Component2.Transform2`/Mates exakt positionieren.

## Bekannte Fehlschläge

- Early Binding (`gencache.EnsureDispatch`) auf ein bereits laufendes SolidWorks-Objekt (S1, siehe
  „Verbindung“ oben).
- `FullyDefineSketch` mit rohem Python-`None` für `HorizontalDatumDisp`/`VerticalDatumDisp`:
  `com_error` „Typenkonflikt“ (arg 6) (S3) → `callout_leer()` verwenden.
- `IComponent2.Select4` mit rohem Python-`None` für `Data`: derselbe „Typenkonflikt“-Fehler (S5) →
  `callout_leer()` verwenden.
- `IAssemblyDoc.EditRebuild3()` mit Klammern: `TypeError("'bool' object is not callable")` (S6) →
  ohne Klammern (`assy.EditRebuild3`).
- Toolbox-Teil aus Norm+Größe per API erzeugen: keine Methode im indizierten API-Bereich
  (`sldworks.tlb`/`swconst.tlb`) gefunden; die Erzeugungsfunktionalität liegt in einem eigenen,
  nicht indizierten Add-in (S7). Rückfallweg: manuell erzeugen, per `swki normteil aufnehmen`
  übernehmen.
