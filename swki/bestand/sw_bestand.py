"""Bestand in SolidWorks lesen und zeigen (Spec Bestandsdateien §5, Wege aus Spike S18, docs/bestandsdateien/ergebnisse.md).

`lies_bestand` ist das Herzstück: Es liest Bestandskopie und Lauf gleich (Plan, Format `bestand.json`) und ändert nur den
Speicher, gespeichert wird hier nie. Werte stehen nur in der aktiven Konfiguration verlässlich (`GetSystemValue3` mit Namen
liefert 0 für nicht aktive), Fehler und Reihenfolge ebenso, also wird jede Konfiguration aktiv geschaltet.

`zustand` eines Maßes ist die einzige Quelle für `MASS_GESTEUERT` in `validieren`, die Ableitung ist deshalb rein
(`leite_masse`): `DrivenState` ist bei Gleichung und Referenzmaß gleich 1, nur die linke Gleichungsseite trennt sie.

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  ISldWorks.VersionHistory(1), .GetLatestSupportedFileVersion(0), .GetDocumentDependencies2(4)
  IModelDoc2.ShowConfiguration2(1), .GetConfigurationNames(0), .EditRebuild3(0), .GetEquationMgr(0), .ShowNamedView2(2),
    .ViewZoomtofit2(0), .ViewDisplayWireframe(0), .GetMaterialPropertyName2(2)
  IModelDocExtension.HasDesignTable(0), .GetWhatsWrong(3), .GetWhatsWrongCount(0), .ListExternalFileReferences(9, alle
    Ausgabe), .GetUserPreferenceInteger(2: swUnitSystem 263), .SetUserPreferenceToggle(3: swDisplayAnnotations 31,
    swDisplayFeatureDimensions 32), .CreateMassProperty2(0), .CustomPropertyManager(1)
  ICustomPropertyManager.GetAll3(5)
  IFeature.GetFirstDisplayDimension(0), .GetNextDisplayDimension(1), .GetFirstSubFeature(0), .GetNextSubFeature(0),
    .GetParents(0), .GetChildren(0), .IsSuppressed2(2: swSpecifyConfiguration 3), .GetSpecificFeature2(0), .Select2(2)
  IDisplayDimension.GetDimension2(1), .IsLinked, .GetLinkedText(0), .GetAnnotation(0); IAnnotation.Color
  IDimension.FullName, .GetType(0: swDimensionParamType_e Linear 0, Angular 1, Integer 2), .DrivenState (swDimensionDriven
    1), .IsDesignTableDimension(0), .GetSystemValue3(2: swSetValue_InThisConfiguration 1), .ReferencePoints
  IEquationMgr.GetCount(0), .Equation(Index), .GlobalVariable(Index), .Value(Index)
  ISketch.ModelToSketchTransform; IMathVector.MultiplyTransform(1); IModelView.Scale2
"""

import math
import re
from pathlib import Path

from swki.bestand.fehler import BESTAND_NICHT_LESBAR, BESTAND_REFERENZ, BESTAND_VERSION_NEUER, BestandFehler
from swki.bestand.folgen import rechte_seite
from swki.compiler import sw
from swki.compiler.topologie import koerper
from swki.pruefung.bilder import ANSICHT_DER_ACHSE, ANSICHTEN, _aufnahme
from swki.pruefung.messen import skizzenstatus
from swki.verbindung import byref_long, byref_str, byref_variant, in_mm, in_mm3, r8_array

SW_WERT_AKTIV = 1              # swSetValueInConfiguration_e.swSetValue_InThisConfiguration
SW_BENANNTE_KONFIGURATIONEN = 3  # swInConfigurationOpts_e.swSpecifyConfiguration
SW_DIMENSION_DRIVEN = 1        # swDimensionDrivenState_e
SW_LINEAR, SW_WINKEL = 0, 1    # swDimensionParamType_e
SW_EINHEITENSYSTEM = 263       # swUserPreferenceIntegerValue_e.swUnitSystem
SW_BESCHRIFTUNGEN, SW_FEATURE_MASSE = 31, 32  # swUserPreferenceToggle_e (S18e: sonst sind Maße im Bild unsichtbar)
ROT = 0x0000FF                 # IAnnotation.Color: 0x00BBGGRR
ZOOM_RAND = 0.8                # ViewZoomtofit2 passt nur die Geometrie ein, Maße ragen darüber hinaus (S18e)
EINHEITEN = {SW_LINEAR: "mm", SW_WINKEL: "Grad"}  # ganzzahlige Maße (Anzahl im Muster) ohne Einheit

_LINKS = re.compile(r'\s*"([^"]+)"')
_NUR_NAME = re.compile(r'"([^"]+)"')
_VERSION = re.compile(r"\d+")


def bstr_array(namen):
    """VT_ARRAY|VT_BSTR für Konfigurationsnamen (IsSuppressed2, SetSystemValue3 …)."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, list(namen))


def massname(voll: str) -> str:
    """Maßname ohne Dokument: `FullName` endet auf `@Lagerdeckel.Part` bzw. `@Teil8.Part` (S18b)."""
    return voll.rsplit("@", 1)[0]


def links_von(text: str) -> str:
    """Linke Seite einer Gleichung `"links" = rechts`; ohne Anführungszeichen der ganze Text."""
    m = _LINKS.match(text)
    return m.group(1) if m else text.strip()


def _quelle(gleichung: dict, variablen: set[str]) -> dict:
    """Quelle eines gesteuerten Maßes: `variable` nur, wenn die rechte Seite genau die Variable ist; ein Ausdruck bleibt
    `gleichung`, sonst schlüge `validieren` vor, die Variable zu ändern, ohne den Ausdruck zu nennen."""
    m = _NUR_NAME.fullmatch(rechte_seite(gleichung["text"]))
    if m and m.group(1) in variablen:
        return {"art": "variable", "name": m.group(1)}
    return {"art": "gleichung", "name": gleichung["links"]}


def _schluessel(name: str) -> str:
    """Vergleichsform der Maßnamen aus Gleichungen und `FullName`: ohne Dokument, ohne Groß-/Kleinschreibung."""
    if re.search(r"@[^@]*\.(part|assembly)$", name, re.IGNORECASE):
        name = massname(name)
    return name.casefold()


def leite_masse(roh: list[dict], gleichungen: list[dict]) -> list[dict]:
    """`masse` aus gelesenen Rohdaten (rein). `roh` je Maß: `name`, `feature`, `werte`, `einheit`, `punkte`, `driven`
    (DrivenState), `tabelle` (IsDesignTableDimension), `verknuepft` (Gruppenname oder None).

    Reihenfolge (S18b): linke Seite einer Gleichung und Tabellenmaß → gesteuert, sonst DrivenState 1 → getrieben, sonst
    treibend. Eine Gruppe verknüpfter Maße hat einen Wert: Ist ein Mitglied gesteuert, sind es alle (Partner ließen sich
    sonst setzen, und der Neuaufbau dreht den Wert still zurück, S18c)."""
    variablen = {g["links"] for g in gleichungen if g["global"]}
    links = {_schluessel(g["links"]): g for g in gleichungen}
    aus = []
    for m in roh:
        g = links.get(_schluessel(m["name"]))
        if g is not None:
            zustand, quelle = "gesteuert", _quelle(g, variablen)
        elif m["tabelle"]:
            zustand, quelle = "gesteuert", {"art": "tabelle", "name": None}
        else:
            zustand, quelle = ("getrieben" if m["driven"] == SW_DIMENSION_DRIVEN else "treibend"), None
        aus.append({"name": m["name"], "feature": m["feature"], "werte": m["werte"], "einheit": m["einheit"],
                    "zustand": zustand, "quelle": quelle, "gruppe": m["verknuepft"], "punkte": m["punkte"]})
    gesteuert = {m["gruppe"]: m["quelle"] for m in aus if m["gruppe"] and m["zustand"] == "gesteuert"}
    for m in aus:
        if m["gruppe"] in gesteuert:
            m["zustand"], m["quelle"] = "gesteuert", gesteuert[m["gruppe"]]
    return aus


def pruefe_version(app, pfad: Path) -> tuple[list[str], bool]:
    """Versionsverlauf ohne Öffnen (S18b): `['18000[2025/268]']`. Neuer als dieses SolidWorks → `BESTAND_VERSION_NEUER`.
    Rückgabe (Verlauf, Datei ist älter)."""
    versionen = list(app.VersionHistory(str(pfad)) or ())
    nummern = [int(m.group()) for v in versionen if (m := _VERSION.match(v))]
    if not nummern:
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"{pfad.name}: kein Versionsverlauf lesbar – ist das eine SolidWorks-Datei?",
                            pfad=str(pfad))
    neueste, aktuell = max(nummern), app.GetLatestSupportedFileVersion
    if neueste > aktuell:
        raise BestandFehler(BESTAND_VERSION_NEUER, f"{pfad.name} stammt aus einer neueren SolidWorks-Version ({neueste}) als "
                                                   f"dieses SolidWorks liest ({aktuell})", datei=neueste, solidworks=aktuell)
    return versionen, neueste < aktuell


def externe_referenzen(app, pfad: Path) -> list[str]:
    """Pfade der Dateien, von denen `pfad` abhängt, ohne sie zu öffnen. Paare Titel/Pfad, `None` ohne Referenz (S18b)."""
    return list((app.GetDocumentDependencies2(str(pfad), True, False, False) or ())[1::2])


def whats_wrong(model) -> list[dict]:
    """Neuaufbau-Fehler und -Warnungen, sieht nur die aktive Konfiguration (S18c)."""
    if not model.Extension.GetWhatsWrongCount:
        return []
    features, codes, warnungen = byref_variant(), byref_variant(), byref_variant()
    model.Extension.GetWhatsWrong(features, codes, warnungen)
    return [{"feature": f.Name, "code": c, "warnung": bool(w)}
            for f, c, w in zip(features.value or (), codes.value or (), warnungen.value or ())]


def _ist_ordner(typ: str) -> bool:
    return typ.endswith("Folder") or typ == "DetailCabinet"


def baum_features(model) -> list:
    """Features in der Reihenfolge der aktiven Konfiguration, ohne Ordner. Unterfeatures, die nicht in der Kette stehen
    (Unterskizzen und Gewinde eines `HoleWzd`, S18b), folgen ihrem Feature. Nach jedem Umschalten neu holen (S18c)."""
    kette, f = [], model.FirstFeature
    while f is not None:
        if not _ist_ordner(f.GetTypeName2):
            kette.append(f)
        f = f.GetNextFeature
    bekannt, aus = {f.Name for f in kette}, []
    for f in kette:
        aus.append(f)
        u = f.GetFirstSubFeature
        while u is not None:
            if u.Name not in bekannt:
                bekannt.add(u.Name)
                aus.append(u)
            u = u.GetNextSubFeature
    return aus


def _schalte(model, konfiguration: str) -> None:
    """Aktiviert eine Konfiguration; ob es geklappt hat, zeigt nur das Zurücklesen (S18c: Rückgaben nicht glauben)."""
    model.ShowConfiguration2(konfiguration)
    ist = model.ConfigurationManager.ActiveConfiguration.Name
    if ist != konfiguration:
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"Konfiguration {konfiguration!r} ließ sich nicht aktivieren (aktiv: "
                                                  f"{ist!r})", konfiguration=konfiguration)


def _wert(dim, einheit: str) -> float | None:
    """Wert in der aktiven Konfiguration in mm bzw. Grad. Maße unterdrückter Features sind gemessen lesbar (S18b); liefert
    SolidWorks trotzdem nichts, bleibt es `None`, nie ein Abbruch (Plan Review Focus 5)."""
    try:
        wert = dim.GetSystemValue3(SW_WERT_AKTIV, None)[0]
    except Exception:
        return None
    if wert is None:
        return None
    if einheit == "mm":
        return round(in_mm(wert), 6)
    return round(math.degrees(wert), 6) if einheit == "Grad" else wert


def _punkte(dim) -> list[list[float]]:
    """Lage: die beiden Enden in mm, bis 0,1 mm neben der Geometrie (S18b). Nicht lesbar → leer."""
    try:
        return [[round(in_mm(c), 3) for c in p.ArrayData] for p in dim.ReferencePoints][:2]
    except Exception:
        return []


def _lies_masse(features: list, konfiguration: str, konfigurationen: list[str], roh: dict[str, dict]) -> None:
    """Maße der aktiven Konfiguration in `roh` eintragen. Skizzenmaße stehen unter Skizze und Feature: Dubletten nach Namen
    zusammenlegen, sie tragen die Skizze (steht im Baum zuerst)."""
    for f in features:
        dd = f.GetFirstDisplayDimension
        while dd is not None:
            dim = dd.GetDimension2(0)
            name = massname(dim.FullName)
            e = roh.get(name)
            if e is None:
                e = roh[name] = {"name": name, "feature": f.Name, "werte": dict.fromkeys(konfigurationen),
                                 "einheit": EINHEITEN.get(dim.GetType, ""), "punkte": _punkte(dim),
                                 "driven": dim.DrivenState, "tabelle": bool(dim.IsDesignTableDimension),
                                 "verknuepft": (dd.GetLinkedText or None) if dd.IsLinked else None}
            if e["werte"][konfiguration] is None:
                e["werte"][konfiguration] = _wert(dim, e["einheit"])
            dd = f.GetNextDisplayDimension(dd)


def _feature_eintrag(f, konfigurationen: list[str], tabelle: bool) -> dict:
    """`IsSuppressed2` liefert in Dokumentreihenfolge, egal wie die Namen geordnet sind (live gemessen): je Name einzeln
    fragen. `tabelle`: Tabellengesteuerte Unterdrückung lässt sich ohne Excel nicht lesen (S18b, Offen), jedes Feature einer
    Datei mit Tabelle gilt deshalb als möglicherweise gesteuert."""
    unterdrueckt = {k: bool(f.IsSuppressed2(SW_BENANNTE_KONFIGURATIONEN, bstr_array([k]))[0]) for k in konfigurationen}
    return {"name": f.Name, "typ": f.GetTypeName2, "eltern": [p.Name for p in f.GetParents or ()],
            "kinder": [c.Name for c in f.GetChildren or ()], "unterdrueckt": unterdrueckt, "tabelle": tabelle}


def _gleichungen(model) -> tuple[list[dict], dict[str, float]]:
    gl = model.GetEquationMgr
    eintraege, variablen = [], {}
    for i in range(int(gl.GetCount)):
        text, ist_global = gl.Equation(i), bool(gl.GlobalVariable(i))
        eintraege.append({"index": i, "text": text, "links": links_von(text), "global": ist_global})
        if ist_global:
            variablen[links_von(text)] = gl.Value(i)
    return eintraege, variablen


def _eigenschaften(model, konfiguration: str) -> dict[str, str]:
    """Eigenschaften (Rohtext, nicht aufgelöst) einer Konfiguration, "" = Datei."""
    namen, typen, werte, aufgeloest, verknuepft = (byref_variant() for _ in range(5))
    model.Extension.CustomPropertyManager(konfiguration).GetAll3(namen, typen, werte, aufgeloest, verknuepft)
    return dict(zip(namen.value or (), werte.value or ()))


def _datei_referenzen(model) -> list[str]:
    """Was das offene Dokument selbst als externe Referenz nennt."""
    ausgaben = [byref_variant() for _ in range(7)]
    model.Extension.ListExternalFileReferences(*ausgaben, byref_long(), byref_str())
    return list(ausgaben[0].value or ())


def _geometrie(model) -> dict:
    """Körper, Volumen (mm³), Hüllquader, Schwerpunkt (mm) der aktiven Konfiguration; ohne Volumenkörper `None`."""
    mp = model.Extension.CreateMassProperty2
    if mp is not None:
        mp.UseSystemUnits = True
    return {"koerper": len(koerper(model)), "volumen": None if mp is None else round(in_mm3(mp.Volume), 3),
            "box": [round(c, 6) for c in sw.huellquader_eng_mm(model)],
            "schwerpunkt": None if mp is None else [round(in_mm(c), 6) for c in mp.CenterOfMass]}


def lies_bestand(app, model) -> dict:
    """Aufnahme eines offenen Teils im Format `bestand.json` ohne `datei` und `sw_jahr` (setzt der Aufrufer). Die aktive
    Konfiguration steht vorn und ist danach wieder aktiv, auch nach einem Fehler (Plan Review Focus 4). Der Neuaufbau je
    Konfiguration bleibt im Speicher. `reihenfolge` je Konfiguration ergänzt `features` (Reihenfolge der aktiven): Die
    Feature-Reihenfolge gilt je Konfiguration und kann abweichen (S18c)."""
    aktiv = model.ConfigurationManager.ActiveConfiguration.Name
    konfigurationen = [aktiv] + [k for k in model.GetConfigurationNames if k != aktiv]
    tabelle = bool(model.Extension.HasDesignTable)
    gleichungen, variablen = _gleichungen(model)
    d: dict = {"version": 1, "konfigurationen": konfigurationen, "aktiv": aktiv,
               "einheitensystem": model.Extension.GetUserPreferenceInteger(SW_EINHEITENSYSTEM, 0),
               "material": model.GetMaterialPropertyName2(aktiv, byref_str()) or "",
               "eigenschaften": {"datei": _eigenschaften(model, ""),
                                 "konfiguration": {k: _eigenschaften(model, k) for k in konfigurationen}},
               "externe_referenzen": _datei_referenzen(model), "gleichungen": gleichungen, "variablen": variablen,
               "skizzen": skizzenstatus(model), "tabelle": tabelle}
    neuaufbau, reihenfolge, geometrie, roh = [], {}, {}, {}
    try:
        for k in konfigurationen:
            _schalte(model, k)
            model.EditRebuild3
            neuaufbau += [{"konfiguration": k, **f} for f in whats_wrong(model)]
            features = baum_features(model)
            if k == aktiv:
                d["features"] = [_feature_eintrag(f, konfigurationen, tabelle) for f in features]
            reihenfolge[k] = [f.Name for f in features]
            geometrie[k] = _geometrie(model)
            _lies_masse(features, k, konfigurationen, roh)
    finally:
        _schalte(model, aktiv)
    return d | {"reihenfolge": reihenfolge, "masse": leite_masse(list(roh.values()), gleichungen), "neuaufbau": neuaufbau,
                "geometrie": geometrie}


def _ansicht(app, feature) -> str:
    """Skizzen-Ansicht (S18e: in der Isometrie überlagern sich die Maße): Standardansicht entlang der Modellachse, die der
    Skizzennormalen am nächsten liegt. Feature-Maße: Isometrie."""
    if feature.GetTypeName2 != "ProfileFeature":
        return "iso"
    transform = feature.GetSpecificFeature2.ModelToSketchTransform
    mu = sw.mathutil(app)
    anteil = [abs(mu.CreateVector(r8_array(achse)).MultiplyTransform(transform).ArrayData[2])
              for achse in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))]
    return ANSICHT_DER_ACHSE[max(range(3), key=anteil.__getitem__)]


def _anzeige(feature, name: str):
    dd = feature.GetFirstDisplayDimension
    while dd is not None:
        if massname(dd.GetDimension2(0).FullName) == name:
            return dd
        dd = feature.GetNextDisplayDimension(dd)
    return None


def _einpassen(model, ansicht: str) -> None:
    model._FlagAsMethod("ViewZoomtofit2")  # nur als echter Methodenaufruf wird eingepasst (swki.pruefung.bilder)
    model.ShowNamedView2("", ANSICHTEN[ansicht])
    model.ViewZoomtofit2()


def zeige_mass(app, model, mass: dict, pfad: Path) -> None:
    """Bild mit rot hervorgehobenem Maß (S18e, Lauf e2): Bloße Auswahl zeigt nichts. Beschriftungen und Farbe gelten nur im
    offenen Dokument, es wird nicht gespeichert. `mass`: Eintrag aus `masse` der Aufnahme."""
    feature = model.FeatureByName(mass["feature"])
    dd = _anzeige(feature, mass["name"]) if feature is not None else None
    if dd is None:
        raise BestandFehler(BESTAND_REFERENZ, f"Maß {mass['name']!r} steht nicht mehr an {mass['feature']!r}",
                            mass=mass["name"], feature=mass["feature"])
    model.Extension.SetUserPreferenceToggle(SW_BESCHRIFTUNGEN, 0, True)
    model.Extension.SetUserPreferenceToggle(SW_FEATURE_MASSE, 0, True)
    with _aufnahme(app, model):
        _einpassen(model, _ansicht(app, feature))
        ansicht = model.ActiveView
        ansicht.Scale2 = ansicht.Scale2 * ZOOM_RAND
        model._FlagAsMethod("ViewDisplayWireframe")
        model.ViewDisplayWireframe()  # schattiert verdeckt der Körper Maße im Innern, etwa die Tiefe einer Tasche
        dd.GetAnnotation.Color = ROT
        sw.speichere(model, pfad, kopie=True)


def zeige_feature(app, model, name: str, pfad: Path) -> None:
    """Bild mit ausgewähltem Feature: `Select2` genügt, die Flächen erscheinen farbig (S18e)."""
    with _aufnahme(app, model):
        _einpassen(model, "iso")
        model.FeatureByName(name).Select2(False, 0)
        sw.speichere(model, pfad, kopie=True)
    sw.auswahl_leeren(model)
