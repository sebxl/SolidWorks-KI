"""S8: Early Binding über EnsureModule + CastTo.

Untersucht, ob echtes Early Binding (gencache.EnsureModule(sldworks.tlb) + CastTo) gegenüber dem
in S1 gesetzten Late Binding (GetActiveObject, dynamischer Dispatch) Vorteile bringt. Siehe
docs/stufe0/ergebnisse.md ("Offene Punkte") und swki/wissen/pywin32-fallstricke.md.
"""

import time
from pathlib import Path

import pythoncom
import win32com
import win32com.client
import win32com.client.dynamic as dynamic
import win32com.client.gencache as gencache

from spikes._gemeinsam import lauf, letztes_feature, neues_teil, schliesse, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import callout_leer, in_mm3, mm, wert


def _typelib_attr(pfad: Path) -> tuple[str, int, int, int]:
    tlb = pythoncom.LoadTypeLib(str(pfad))
    guid, lcid, _syskind, major, minor, _flags = tlb.GetLibAttr()
    return str(guid), lcid, major, minor


def _cache_datei(gen_path: Path, guid: str, lcid: int, major: int, minor: int) -> Path:
    kern = guid.strip("{}")
    return gen_path / f"{kern}x{lcid}x{major}x{minor}.py"


def _pyc_datei(gen_path: Path, guid: str, lcid: int, major: int, minor: int) -> Path:
    kern = guid.strip("{}")
    import sys

    return gen_path / "__pycache__" / f"{kern}x{lcid}x{major}x{minor}.cpython-{sys.version_info[0]}{sys.version_info[1]}.pyc"


def _ensure_module_timing(pfad_tlb: Path, gen_path: Path) -> dict:
    guid, lcid, major, minor = _typelib_attr(pfad_tlb)
    cache_datei = _cache_datei(gen_path, guid, lcid, major, minor)
    pyc_datei = _pyc_datei(gen_path, guid, lcid, major, minor)
    war_gecacht_vor_lauf = cache_datei.exists()
    # Erzwingt einen echten Kaltstart: EnsureModule kann eine verwaiste __pycache__-.pyc-Datei
    # weiterverwenden, auch wenn die .py-Quelle bereits geloescht ist (eigener Mechanismus,
    # nicht der normale Python-Import - ein reines "import modulname" schlaegt dabei fehl,
    # siehe Notiz unten) - fuer eine belastbare Kaltstart-Messung muss daher auch die .pyc weg.
    if war_gecacht_vor_lauf:
        cache_datei.unlink()
    if pyc_datei.exists():
        pyc_datei.unlink()
    t0 = time.time()
    gencache.EnsureModule(guid, lcid, major, minor)
    dauer_kalt = time.time() - t0
    t0 = time.time()
    gencache.EnsureModule(guid, lcid, major, minor)
    dauer_warm = time.time() - t0
    return {
        "datei": pfad_tlb.name,
        "guid": guid,
        "lcid": lcid,
        "major": major,
        "minor": minor,
        "cache_datei": str(cache_datei),
        "pyc_datei": str(pyc_datei),
        "war_bereits_gecacht_vor_diesem_lauf": war_gecacht_vor_lauf,
        "dauer_erster_lauf_s_echter_kaltstart": round(dauer_kalt, 3),
        "dauer_zweiter_lauf_s_selber_prozess": round(dauer_warm, 3),
        "cache_datei_existiert_danach": cache_datei.exists(),
    }


def _typ(obj) -> str:
    return f"{type(obj).__module__}.{type(obj).__qualname__}"


def _ist_frueh_gebunden(obj) -> bool:
    return isinstance(obj, win32com.client.DispatchBaseClass)


def pruefen() -> dict:
    from swki.konfig import lade_rechner

    r = lade_rechner()
    db = api_db(r.sw_jahr)
    daten: dict = {}

    # --- Frage 1: EnsureModule (Ort, Dauer, erster/zweiter Lauf) ---
    # WICHTIG: Diese Messung muss VOR dem ersten verbinde()/GetActiveObject()-Aufruf laufen.
    # GetActiveObject() importiert (sobald der gen_py-Plattencache eine passende .py-Datei enthaelt)
    # das generierte Modul intern selbst per __import__ - danach steckt es in sys.modules und jeder
    # spaetere gencache.EnsureModule()-Aufruf im selben Prozess ist ein reiner sys.modules-Treffer
    # (Millisekunden), UNABHAENGIG davon, ob die Quelldatei auf der Platte zwischenzeitlich geloescht
    # wurde. Ein erster, aussagekraeftiger Kaltstart-Messwert ist also nur vor start() moeglich.
    gen_path = Path(win32com.__gen_path__)
    daten["frage1_ensuremodule"] = {
        "gencache_pfad": str(gen_path),
        "sldworks_tlb": _ensure_module_timing(r.installationsordner / "sldworks.tlb", gen_path),
        "swconst_tlb": _ensure_module_timing(r.installationsordner / "swconst.tlb", gen_path),
    }

    r, app = start()

    # --- Frage 2: CastTo(app, "ISldWorks") und Verhalten zurückgegebener Objekte ---
    frage2: dict = {"varianten": []}

    # Variante A: CastTo direkt auf das von verbinde() gelieferte app-Objekt. Da der gen_py-Cache
    # jetzt (nach EnsureModule oben) auf der Platte liegt, liefert GetActiveObject (ProgID-basiert)
    # bereits automatisch ein getyptes CoClass-Objekt (kein reiner dynamischer Dispatch mehr) –
    # unabhängig davon, ob dieser Prozess selbst EnsureModule aufgerufen hat (der Cache ist
    # prozessübergreifend auf der Platte persistent).
    frage2["app_typ_nach_ensuremodule"] = _typ(app)
    frage2["app_ist_coclass"] = not isinstance(app, win32com.client.DispatchBaseClass) and hasattr(app, "_dispobj_")
    try:
        cast_a = win32com.client.CastTo(app, "ISldWorks")
        try:
            rev_a = cast_a.RevisionNumber()
            frage2["varianten"].append({"variante": "CastTo(app, 'ISldWorks')", "cast_ok": True,
                                          "aufruf_ok": True, "ergebnis": rev_a})
        except Exception as e:
            frage2["varianten"].append({"variante": "CastTo(app, 'ISldWorks')", "cast_ok": True,
                                          "aufruf_ok": False, "fehler": repr(e),
                                          "befund": "CastTo liefert ein Objekt, dessen _oleobj_ auf "
                                                    "das CoClass-Objekt selbst zeigt statt auf einen "
                                                    "echten IDispatch-Zeiger (DispatchBaseClass.__init__ "
                                                    "prueft nur isinstance(oobj, (DispatchBaseClass, "
                                                    "PyIDispatchType)); ein CoClass-Objekt erfuellt "
                                                    "keine der beiden Bedingungen, daher wird oobj "
                                                    "unveraendert als _oleobj_ uebernommen)."})
    except Exception as e:
        frage2["varianten"].append({"variante": "CastTo(app, 'ISldWorks')", "cast_ok": False, "fehler": repr(e)})

    # Variante B (Workaround): CastTo auf app._dispobj_ (das intern vom CoClass-Wrapper gehaltene
    # DispatchBaseClass-Objekt der Default-Schnittstelle) statt auf app selbst.
    try:
        cast_b = win32com.client.CastTo(app._dispobj_, "ISldWorks")
        rev_b = cast_b.RevisionNumber()
        frage2["varianten"].append({"variante": "CastTo(app._dispobj_, 'ISldWorks')", "cast_ok": True,
                                      "aufruf_ok": True, "ergebnis": rev_b,
                                      "befund": "Funktioniert: app._dispobj_ ist ein echtes "
                                                "DispatchBaseClass-Objekt, CastTo QueryInterface't "
                                                "dessen echten _oleobj_ korrekt."})
    except Exception as e:
        frage2["varianten"].append({"variante": "CastTo(app._dispobj_, 'ISldWorks')", "cast_ok": False,
                                      "fehler": repr(e)})

    # Variante C: CastTo auf einen erzwungenen rein dynamischen (nicht getypten) Wrapper des
    # rohen COM-Zeigers - simuliert den Fall "frischer Prozess ohne Plattencache".
    try:
        dyn_app = dynamic.Dispatch(app._oleobj_)
        win32com.client.CastTo(dyn_app, "ISldWorks")
        frage2["varianten"].append({"variante": "CastTo(dynamic.Dispatch(app._oleobj_), 'ISldWorks')",
                                      "cast_ok": True})
    except Exception as e:
        frage2["varianten"].append({"variante": "CastTo(dynamic.Dispatch(app._oleobj_), 'ISldWorks')",
                                      "cast_ok": False, "fehler": repr(e),
                                      "befund": "Gleicher Fehler wie S1 (EnsureDispatch auf das "
                                                "laufende Objekt): CastTo ruft fuer nicht-getypte "
                                                "Objekte intern gencache.EnsureDispatch(ob) auf, was "
                                                "ob._oleobj_.GetTypeInfo() braucht - scheitert, weil "
                                                "SOLIDWORKS-COM-Objekte GetTypeInfo() nicht nutzbar "
                                                "implementieren."})

    daten["frage2_castto_app"] = frage2

    # --- Realistische Sequenz: neues Teil, Skizze, Extrusion, Feature-Baum, Masse ---
    early_app = win32com.client.CastTo(app._dispobj_, "ISldWorks")  # funktionierender Workaround (s.o.)
    sequenz: dict = {}
    model = None
    try:
        model = neues_teil(early_app, r)
        sequenz["model_typ"] = _typ(model)
        sequenz["model_ist_frueh_gebunden"] = _ist_frueh_gebunden(model)
        try:
            cast_model = win32com.client.CastTo(model, "IPartDoc")
            sequenz["castto_model"] = {"cast_ok": True, "typ": _typ(cast_model)}
        except Exception as e:
            sequenz["castto_model"] = {"cast_ok": False, "fehler": repr(e)}

        # weitere Kindobjekte: nur getypt (DispatchBaseClass), wenn die generierte Methode eine
        # feste IID an Dispatch() uebergibt (z. B. IComponent2.FirstFeature) statt None (z. B.
        # IModelDoc2.FirstFeature/NewDocument) - letzteres erfordert dispatch.GetTypeInfo(), das bei
        # SOLIDWORKS scheitert, wodurch pywin32 automatisch auf dynamischen Dispatch zurueckfaellt.
        sequenz["sketchmanager_typ"] = _typ(model.SketchManager)
        sequenz["featuremanager_typ"] = _typ(model.FeatureManager)
        sequenz["extension_typ"] = _typ(model.Extension)

        # Standardebene (oben) + Skizze + FullyDefineSketch + Extrusion - identischer Code wie S3,
        # da model/SketchManager weiterhin dynamisch gebunden sind (siehe oben).
        ebenen = standardebenen(model)
        oben = ebenen[1]
        oben.Select2(False, 0)
        sm = model.SketchManager
        sm.InsertSketch(True)
        sm.CreateCenterRectangle(0.0, 0.0, 0.0, mm(50), mm(30), 0.0)

        relations_alle = sum(e["wert"] for e in enum(db, "swSketchFullyDefineRelationType_e"))

        # Frage 4a: FullyDefineSketch mit rohem None statt callout_leer() - erneuter Test unter
        # "frueh gebunden" (app-Ebene), um zu pruefen, ob sich am Verhalten etwas aendert.
        try:
            sm.FullyDefineSketch(True, True, relations_alle, True, 1, None, 1, None, 1, 1)
            sequenz["fullydefinesketch_mit_none"] = {"ok": True}
        except Exception as e:
            sequenz["fullydefinesketch_mit_none"] = {"ok": False, "fehler": repr(e)}

        rueckgabe = sm.FullyDefineSketch(
            True, True, relations_alle, True, 1, callout_leer(), 1, callout_leer(), 1, 1
        )
        sequenz["fullydefinesketch_mit_callout_leer"] = {"ok": True, "rueckgabe": rueckgabe}

        sm.InsertSketch(True)
        skizze = letztes_feature(model)
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, mm(20), 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0.0, False,
        )
        sequenz["extrusion"] = wert(feat.Name) if feat is not None else None
        sequenz["extrusion_typ"] = _typ(feat) if feat is not None else None

        # Feature-Baum iterieren: FirstFeature/GetNextFeature ohne Klammern (wie in _gemeinsam.py
        # dokumentiert) - model bleibt dynamisch, daher unveraendertes Verhalten.
        namen = []
        f = model.FirstFeature
        while f is not None:
            namen.append(wert(f.GetTypeName2))
            f = f.GetNextFeature
        sequenz["feature_baum"] = namen

        # Masse (wie S4): CreateMassProperty ohne Klammern (Bindungs-Eigenart).
        mp = model.Extension.CreateMassProperty
        sequenz["volumen_mm3"] = in_mm3(wert(mp.Volume))

        # Frage 4b: ByRef-Ausgabeparameter (Fehler/Warnungen) von IModelDocExtension.SaveAs -
        # nur sinnvoll pruefbar, wenn Extension frueh gebunden waere; da extension_typ oben
        # bereits als dynamisch erwartet wird, wird hier stattdessen dokumentiert, dass die in
        # S1-S7 genutzte SaveAs3-Variante (einzelner int-Rueckgabewert, keine ByRef-Parameter)
        # unveraendert funktioniert.
        speicherpfad = r.arbeitsordner / "stufe0" / "s8" / "s8_teil.sldprt"
        speicherpfad.parent.mkdir(parents=True, exist_ok=True)
        fehler_saveas3 = int(model.SaveAs3(str(speicherpfad), 0, 1))
        sequenz["saveas3_fehlercode"] = fehler_saveas3
        sequenz["saveas3_datei_existiert"] = speicherpfad.exists()

    finally:
        if model is not None:
            schliesse(early_app, model)

    daten["sequenz"] = sequenz

    # --- Frage 3: nullargumentige Member mit () aufrufen (frueh gebunden) ---
    frage3 = {}
    ok_faelle = []
    for bezeichner, aufruf in [
        ("early_app.RevisionNumber() mit Klammern", lambda: early_app.RevisionNumber()),
    ]:
        try:
            ok_faelle.append({"member": bezeichner, "mit_klammern_ok": True, "ergebnis": aufruf()})
        except Exception as e:
            ok_faelle.append({"member": bezeichner, "mit_klammern_ok": False, "fehler": repr(e)})
    try:
        early_app.RevisionNumber
        ohne_klammern_ergebnis = "liefert gebundene Methode, ruft NICHT auf (Attributzugriff allein reicht nicht)"
    except Exception as e:
        ohne_klammern_ergebnis = repr(e)
    frage3["frueh_gebundene_app_ebene"] = {
        "mit_klammern": ok_faelle,
        "ohne_klammern_verhalten": ohne_klammern_ergebnis,
        "befund": "Bei frueh gebundenen (DispatchBaseClass-)Objekten sind generierte Member fuer "
                  "nullargumentige Methoden (z. B. RevisionNumber, FirstFeature, EditRebuild3, "
                  "GetSpecificFeature2, CreateMassProperty) normale Python-def-Methoden, die "
                  "self._oleobj_.InvokeTypes(...) aufrufen - sie MUESSEN mit () aufgerufen werden. "
                  "Das ist das exakte Gegenteil der in swki/wissen/pywin32-fallstricke.md fuer "
                  "dynamisch gebundene Objekte dokumentierten Regel (dort: ohne () aufrufen). Da "
                  "ALLE in dieser Sitzung erreichbaren Kindobjekte (model, SketchManager, "
                  "FeatureManager, Extension, Feature, ...) trotz frueh gebundenem app-Handle "
                  "dynamisch bleiben (siehe frage2/sequenz), gilt fuer sie weiterhin die alte Regel "
                  "OHNE Klammern - nur fuer das (mit CastTo(app._dispobj_,...) gewonnene) "
                  "Application-Handle selbst gilt MIT Klammern. Gemischter Code muss also wissen, "
                  "welcher Objekttyp gerade vorliegt.",
    }
    daten["frage3_nullargumentige_member"] = frage3

    # --- Frage 5: swconst-Konstanten nach EnsureModule per Name nutzbar ---
    frage5 = {}
    proben = ["swEndCondBlind", "swEndCondThroughAll", "swThisConfiguration", "swFullyConstrained"]
    ergebnisse = {}
    for name in proben:
        try:
            ergebnisse[name] = getattr(win32com.client.constants, name)
        except Exception as e:
            ergebnisse[name] = repr(e)
    # Abgleich mit dem lokalen API-Index (swEndConditions_e, swConstrainedStatus_e)
    index_werte = {e["name"]: e["wert"] for e in enum(db, "swEndConditions_e")}
    index_werte.update({e["name"]: e["wert"] for e in enum(db, "swConstrainedStatus_e")})
    frage5["konstanten"] = ergebnisse
    frage5["stimmen_mit_api_index_ueberein"] = all(
        ergebnisse.get(k) == index_werte.get(k) for k in ("swEndCondBlind", "swEndCondThroughAll", "swFullyConstrained")
        if k in index_werte
    )
    daten["frage5_swconst_konstanten"] = frage5

    # --- Frage 6: Mischbetrieb (frueh + spaet gebundene Objekte) ---
    daten["frage6_mischbetrieb"] = {
        "befund": "Mischbetrieb ist unproblematisch, weil er in der Praxis kaum vermeidbar ist: "
                  "das app-Handle wird (sobald der gen_py-Plattencache existiert - auch aus einem "
                  "frueheren Prozess) automatisch getypt zurueckgegeben, waehrend praktisch alle "
                  "Kindobjekte (Modelle, Features, Manager) dynamisch bleiben, weil ihre generierten "
                  "Rueckgabe-Handler kein festes IID kennen und GetTypeInfo() auf SOLIDWORKS-"
                  "Objekten scheitert. swki.verbindung.wert() funktioniert in beiden Faellen korrekt, "
                  "weil es callable() prueft: bei frueh gebundenen Methoden (echte Python-Funktion, "
                  "callable) wird aufgerufen, bei dynamisch bereits aufgeloesten Attributen (nicht "
                  "erneut callable im relevanten Sinn fuer Primitivwerte) wird durchgereicht. Objekte "
                  "beider Art koennen in derselben Sitzung nebeneinander verwendet werden, ohne dass "
                  "COM-Fehler auftreten - lediglich die Klammer-Konvention fuer nullargumentige "
                  "Member unterscheidet sich je Objekt (siehe Frage 3).",
        "seiteneffekt": "Nach diesem Spike liegt der gen_py-Cache fuer sldworks.tlb/swconst.tlb "
                        "dauerhaft unter %TEMP%\\gen_py\\3.14 auf der Platte. Das bewirkt, dass "
                        "kuenftige Prozesse (auch S1-S7, ohne eigenen EnsureModule-Aufruf) ueber "
                        "GetActiveObject automatisch ein getyptes app-Handle erhalten statt eines "
                        "rein dynamischen. Das ist unschaedlich fuer bestehenden Code, da dieser "
                        "app-seitige Nullargument-Zugriffe ausschliesslich ueber wert() macht (siehe "
                        "oben) und nie ungeklammert direkt auf app aufruft.",
    }

    # --- Frage 7: Empfehlung ---
    daten["frage7_empfehlung"] = {
        "empfehlung": "Late Binding bleibt fuer Stufe 2 gesetzt; EnsureModule + CastTo wird NICHT "
                      "eingefuehrt.",
        "begruendung": [
            "CastTo(app, 'ISldWorks') liefert scheinbar ein Ergebnis, das aber bei jedem Aufruf mit "
            "AttributeError bricht (_oleobj_ zeigt auf das CoClass-Objekt selbst); ein funktionierender "
            "Weg existiert nur ueber den undokumentierten Umweg CastTo(app._dispobj_, ...).",
            "CastTo auf jedes zurueckgegebene Kindobjekt (Modell, Feature, SketchManager, Extension, "
            "...) scheitert grundsaetzlich mit demselben Fehler wie in S1 ('can not automate the "
            "makepy process'), weil SOLIDWORKS-COM-Objekte GetTypeInfo() nicht liefern - das ist der "
            "Kern der Sache und nicht auf das Application-Objekt beschraenkt.",
            "Dadurch bleiben praktisch alle fuer den Compiler relevanten Objekte (Modell, Feature, "
            "SketchManager, FeatureManager, Extension) so oder so dynamisch gebunden - der einzige "
            "erreichbare Vorteil eines fruehen Application-Handles (Klammerpflicht bei Nullargument-"
            "Membern) kollidiert mit der bestehenden, bereits verifizierten Regel fuer alle anderen "
            "Objekte und wuerde Code fehleranfaelliger statt klarer machen.",
            "Der einzige echte, verifizierte Zusatznutzen ist die Verfuegbarkeit benannter "
            "swconst-Konstanten (win32com.client.constants.swEndCondBlind etc.) - dafuer ist kein "
            "CastTo noetig, nur EnsureModule(swconst.tlb); der Nutzen ist gering, da der lokale "
            "API-Index (`swki api enum`) dieselben Werte bereits nachschlagbar bereitstellt.",
            "Der gen_py-Plattencache ist rechnerabhaengig (Pfad, Python-Version, SW-Jahr/Revision); "
            "auf Rechner B mit SW 2026 waere die Typbibliotheks-GUID/Version anders (major=34 "
            "vermutlich) und muesste dort neu generiert werden - ein weiterer Betriebsaufwand ohne "
            "belegten Gegenwert.",
        ],
    }

    return daten


if __name__ == "__main__":
    lauf("s8_early_binding", pruefen)
