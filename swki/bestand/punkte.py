"""Punkt-Handler der Änderungs-Spec (Spec Bestandsdateien §4.1, §6): schreibender Kern, Signatur
`(ctx, p, aufnahme) -> list[str]` mit den betroffenen SolidWorks-Namen.

Rückgaben von SolidWorks beweisen nichts (S18c): Ein gesteuertes Maß meldet Status 0 und springt beim Neuaufbau zurück,
`SetEquationAndConfigurationOption` liefert keinen Status, ein doppelter Name scheitert still. Jeder Handler misst darum nach
dem Neuaufbau nach, je Konfiguration. Werte stehen nur in der aktiven Konfiguration verlässlich, also wird umgeschaltet; am
Ende steht wieder die aktive der Aufnahme, und alle gehaltenen `IFeature` werden neu geholt (`_je_konfiguration`).

Ein Handler bricht mit `BauFehler` ab, dann wird nie gespeichert. Neuaufbau-Fehler entscheidet der Bau, nicht der Handler:
Bekannt ist je Konfiguration verschieden. swki räumt nichts auf: keine Gleichungen, keine Eigenschaften, kein Umbenennen außer
den eigenen neuen Features.

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  IModelDoc2.Parameter(1), .FeatureByName(1), .GetEquationMgr(0), .EditRebuild3(0)
  IDimension.GetSystemValue3(2), .SetSystemValue3(3: swSetValue_InAllConfigurations 2, _InSpecificConfigurations 3 →
    swSetValue_Successful 0)
  IEquationMgr.GetCount(0), .Equation(Index), .Value(Index), .SetEquationAndConfigurationOption(4: swAllConfiguration 2)
  IFeature.SetSuppression2(3: swSuppressFeature 0, swUnSuppressFeature 1; swSpecifyConfiguration 3), .IsSuppressed2(2),
    .Select2(2), .GetFirstSubFeature(0), .GetNextSubFeature(0)
  IModelDocExtension.DeleteSelection2(1: swDelete_Children 1 | swDelete_Absorbed 2), .ReorderFeature(3: swMoveAfter 3),
    .CustomPropertyManager(1)
  IPartDoc.SetMaterialPropertyName2(3), .GetMaterialPropertyName2(2)
  ICustomPropertyManager.Add3(4), .Delete2(1)
"""

from collections.abc import Callable
from pathlib import Path

from swki.bestand.fehler import BESTAND_ALTWERT, BESTAND_REFERENZ, KINDER_FEHLEN
from swki.bestand.folgen import gleicher_ausdruck, namen_in, rechte_seite
from swki.bestand.spec import _nahe
from swki.bestand.sw_bestand import (SW_BENANNTE_KONFIGURATIONEN, _eigenschaften, _schalte, _wert, baum_features, bstr_array,
                                     links_von, material_von, unter_namen, unterdrueckt)
from swki.compiler import sw
from swki.compiler.eigenschaften import SW_CUSTOM_INFO_TEXT, SW_CUSTOM_PROPERTY_REPLACE_VALUE, finde_material
from swki.compiler.fehler import (FEATURE_NICHT_ERZEUGT, GLEICHUNG_FEHLER, MATERIAL_UNBEKANNT, UNBEKANNTER_TYP, BauFehler)
from swki.compiler.handler.skript import fuehre_aus
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.registry import alle_handler
from swki.spec.laden import _referenzen
from swki.verbindung import grad, mm

SW_WERT_ALLE, SW_WERT_BENANNT = 2, 3  # swSetValueInConfiguration_e
SW_WERT_ERFOLG = 0                    # swSetValueReturnStatus_e.swSetValue_Successful
SW_KONFIGURATIONEN_ALLE = 2           # swInConfigurationOpts_e.swAllConfiguration
SW_UNTERDRUECKEN, SW_AUFHEBEN = 0, 1  # swFeatureSuppressionAction_e
SW_LOESCHEN = 3                       # swDelete_Children | swDelete_Absorbed: Skizze und Kinder gehen mit (S18c)
SW_NACH = 3                           # swMoveLocation_e.swMoveAfter

PUNKTE: dict[str, Callable] = {}


def punkt(*typen: str):
    def dekorator(funktion):
        for typ in typen:
            PUNKTE[typ] = funktion
        return funktion

    return dekorator


def punkt_handler(typ: str) -> Callable:
    funktion = PUNKTE.get(typ)
    if funktion is None:
        raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für Punkt {typ!r}", schritt="handler")
    return funktion


def fremde_namen(spec: dict) -> list[str]:
    """Features des Bestands, die `feature`-Punkte und `pruefung` nennen: alles, was keine Punkt-ID und kein neuer Name ist."""
    punkte = spec["punkte"]
    neu = [p for p in punkte if p["typ"] == "feature"]
    namen = {ref for p in neu for _, ref in _referenzen(p["feature"], [])}
    namen |= {m[seite]["feature"] for m in spec.get("pruefung", {}).get("masse_pruefen", []) for seite in ("von", "zu")
              if "feature" in m[seite]}
    return sorted(namen - {p["id"] for p in punkte} - {p["name"] for p in neu})


def kontext(app, model, spec: dict, spec_pfad: Path, tol_mm: float) -> Kontext:
    """Kontext wie beim Teil, `feature`-Punkte als Features, fremde Features unter ihrem Namen (Spec §4.2). Gleichungen sind
    aus: swki legt in fremden Dateien keine an."""
    features = [{"id": p["id"], **p["feature"]} if p["typ"] == "feature" else {"id": p["id"], "typ": "skript", "datei": p["datei"]}
                for p in spec["punkte"] if p["typ"] in ("feature", "skript")]  # auch Skripte bemaßen, `ctx.pfad` muss sie kennen
    ctx = Kontext(app, model, {"parameter": spec.get("parameter", {}), "features": features}, spec_pfad, tol_mm,
                  gleichungen=False)
    for name in fremde_namen(spec):
        ctx.ergebnisse[name] = FeatureErgebnis([_feature(model, name)])
    return ctx


def _feature(model, name: str):
    feature = model.FeatureByName(name)
    if feature is None:
        raise BauFehler(BESTAND_REFERENZ, f"Feature {name!r} gibt es in der Datei nicht", schritt="referenz")
    return feature


def _konfigurationen(p: dict, aufnahme: dict) -> list[str]:
    k = p.get("konfigurationen", "alle")
    return list(aufnahme["konfigurationen"]) if k == "alle" else list(k)


def _baum(model) -> list[str]:
    return [f.Name for f in baum_features(model)]


def _frisch(ctx) -> None:
    """Ein vor dem Umschalten geholtes `IFeature` zeigt auf den alten Stand (S18c)."""
    for e in ctx.ergebnisse.values():
        e.features = [ctx.model.FeatureByName(f.Name) for f in e.features]


def _je_konfiguration(ctx, aufnahme: dict, konfigurationen: list[str], messen: Callable[[str], object]) -> dict:
    """`messen(k)` nach Umschalten und Neuaufbau, je Konfiguration; `messen` holt seine Objekte selbst. Am Ende steht die
    aktive der Aufnahme. Kein `finally`: Nach einem Fehler wird ohnehin nicht gespeichert."""
    aus = {}
    for k in konfigurationen:
        _schalte(ctx.model, k)
        ctx.model.EditRebuild3
        aus[k] = messen(k)
    _schalte(ctx.model, aufnahme["aktiv"])
    _frisch(ctx)
    return aus


def _dimension(model, name: str):
    dim = model.Parameter(name)
    if dim is None:
        raise BauFehler(BESTAND_REFERENZ, f"Maß {name!r} gibt es in der Datei nicht", schritt="referenz")
    return dim


def _si(wert: float, einheit: str) -> float:
    return mm(wert) if einheit == "mm" else grad(wert) if einheit == "Grad" else wert


def _werte_text(werte: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in werte.items())


@punkt("mass")
def mass(ctx, p: dict, aufnahme: dict) -> list[str]:
    """`alt` wird live gegengeprüft (Spec §6), `neu` nach dem Neuaufbau: `None` (nicht lesbar) zählt nicht als Abweichung
    (Plan Review Focus 5). Mit Namen läse SolidWorks in nicht aktiven Konfigurationen 0 (S18b), also umschalten."""
    name, model = p["mass"], ctx.model
    einheit = next((m["einheit"] for m in aufnahme["masse"] if m["name"] == name), "mm")
    konfigurationen = _konfigurationen(p, aufnahme)
    neu = ctx.wert(p["neu"])

    def messen(_):
        return _wert(_dimension(model, name), einheit)

    abweichend = {k: v for k, v in _je_konfiguration(ctx, aufnahme, konfigurationen, messen).items()
                  if v is not None and not _nahe(v, p["alt"])}
    if abweichend:
        raise BauFehler(BESTAND_ALTWERT, f"Maß {name}: alt {p['alt']} stimmt nicht mit der Datei überein "
                                         f"({_werte_text(abweichend)})", schritt="alt")
    wo = (SW_WERT_ALLE, None) if p.get("konfigurationen", "alle") == "alle" else (SW_WERT_BENANNT, bstr_array(konfigurationen))
    status = _dimension(model, name).SetSystemValue3(_si(neu, einheit), *wo)
    if status != SW_WERT_ERFOLG:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Maß {name}: SolidWorks lehnt {neu} ab (Status {status})", schritt="setzen")
    lesbar = {k: v for k, v in _je_konfiguration(ctx, aufnahme, konfigurationen, messen).items() if v is not None}
    falsch = {k: v for k, v in lesbar.items() if not _nahe(v, neu)}
    if falsch or not lesbar:  # einzelne None sind erlaubt, aber ein echter Messwert muss `neu` belegen
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Maß {name} steht nach dem Neuaufbau nicht auf {neu} "
                                               f"({_werte_text(falsch) or 'nicht lesbar'}) – gesteuert?", schritt="nachmessen")
    ctx.mass(name, p["neu"], f"punkte[{p['id']}].neu", "winkel" if einheit == "Grad" else "groesse")
    return [name]


def _gleichung_index(gleichungen, links: str) -> int:
    for i in range(int(gleichungen.GetCount)):
        if links_von(gleichungen.Equation(i)) == links:
            return i
    raise BauFehler(BESTAND_REFERENZ, f"Eine Gleichung für {links!r} gibt es in der Datei nicht", schritt="referenz")


def _gleichung_stand(ctx, aufnahme: dict, links: str) -> dict[str, tuple[str, float]]:
    """(Text, Wert) in jeder Konfiguration: Gesetzt wird in allen, also wird auch in allen gegengeprüft; der Kollege kann in
    einer Konfiguration einen eigenen Wert führen."""

    def messen(_):
        mgr = ctx.model.GetEquationMgr
        i = _gleichung_index(mgr, links)
        return mgr.Equation(i), float(mgr.Value(i))

    return _je_konfiguration(ctx, aufnahme, aufnahme["konfigurationen"], messen)


def _setze_gleichung(ctx, aufnahme: dict, links: str, rechts: str, stimmt: Callable) -> None:
    """Setzt die rechte Seite in allen Konfigurationen; die Rückgabe ist kein Status (S18c), es zählt `stimmt(mgr, i)` nach dem
    Neuaufbau. `GetEquationMgr` nach jedem Wechsel neu holen."""
    gleichungen = ctx.model.GetEquationMgr
    gleichungen.SetEquationAndConfigurationOption(_gleichung_index(gleichungen, links), f'"{links}" = {rechts}',
                                                  SW_KONFIGURATIONEN_ALLE, None)

    def messen(_):
        mgr = ctx.model.GetEquationMgr
        return stimmt(mgr, _gleichung_index(mgr, links))

    falsch = [k for k, ok in _je_konfiguration(ctx, aufnahme, aufnahme["konfigurationen"], messen).items() if not ok]
    if falsch:
        raise BauFehler(GLEICHUNG_FEHLER, f"{links} steht nach dem Neuaufbau nicht auf {rechts} ({', '.join(falsch)})",
                        schritt="nachmessen")


def _variable(ctx, p: dict, aufnahme: dict) -> list[str]:
    name = p["variable"]
    stand = _gleichung_stand(ctx, aufnahme, name)
    abhaengig = {k: namen_in(rechte_seite(text)) for k, (text, _) in stand.items()}
    if genannt := sorted({f'"{n}"' for namen in abhaengig.values() for n in namen}):
        wo = ", ".join(k for k, namen in abhaengig.items() if namen)
        raise BauFehler(GLEICHUNG_FEHLER, f"Variable {name} hängt von {', '.join(genannt)} ab ({wo}): Setzen ersetzte den "
                                          "Ausdruck. Stattdessen einen gleichung-Punkt auf den Ausdruck schreiben", schritt="alt")
    if abweichend := {k: wert for k, (_, wert) in stand.items() if not _nahe(wert, p["alt"])}:
        raise BauFehler(BESTAND_ALTWERT, f"Variable {name}: alt {p['alt']} stimmt nicht mit der Datei überein "
                                         f"({_werte_text(abweichend)})", schritt="alt")
    neu = ctx.wert(p["neu"])
    _setze_gleichung(ctx, aufnahme, name, f"{neu:.15g}", lambda mgr, k: _nahe(float(mgr.Value(k)), neu))
    return [name]


def _gleichung(ctx, p: dict, aufnahme: dict) -> list[str]:
    links = p["gleichung"]
    rechts = {k: rechte_seite(text) for k, (text, _) in _gleichung_stand(ctx, aufnahme, links).items()}
    if abweichend := {k: text for k, text in rechts.items() if not gleicher_ausdruck(text, p["alt"])}:
        raise BauFehler(BESTAND_ALTWERT, f"Gleichung {links}: alt {p['alt']!r} stimmt nicht mit der Datei überein "
                                         f"({_werte_text(abweichend)})", schritt="alt")
    _setze_gleichung(ctx, aufnahme, links, p["neu"],
                     lambda mgr, k: gleicher_ausdruck(rechte_seite(mgr.Equation(k)), p["neu"]))
    return [links]


@punkt("gleichung")
def gleichung(ctx, p: dict, aufnahme: dict) -> list[str]:
    return _variable(ctx, p, aufnahme) if "variable" in p else _gleichung(ctx, p, aufnahme)


def _setze_unterdrueckung(ctx, p: dict, aufnahme: dict, aktion: int, soll: bool) -> list[str]:
    """Nur Option 3 mit Namen (S18c: Option 1 trifft bei altem `IFeature` die falsche Konfiguration). Nach dem Neuaufbau je
    Konfiguration nachmessen: Eine Gleichung kann die Unterdrückung steuern und zurücknehmen."""
    name, konfigurationen = p["feature"], _konfigurationen(p, aufnahme)
    _feature(ctx.model, name).SetSuppression2(aktion, SW_BENANNTE_KONFIGURATIONEN, bstr_array(konfigurationen))
    ist = _je_konfiguration(ctx, aufnahme, konfigurationen, lambda k: unterdrueckt(_feature(ctx.model, name), k))
    if falsch := [k for k, wert in ist.items() if wert != soll]:
        zustand = "unterdrückt" if soll else "aufgehoben"
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name} ist nach dem Neuaufbau nicht {zustand} ({', '.join(falsch)}) – von einer "
                                               "Gleichung gesteuert?", schritt="nachmessen")
    return [name]


@punkt("unterdruecken")
def unterdruecken(ctx, p: dict, aufnahme: dict) -> list[str]:
    return _setze_unterdrueckung(ctx, p, aufnahme, SW_UNTERDRUECKEN, True)


@punkt("aufheben")
def aufheben(ctx, p: dict, aufnahme: dict) -> list[str]:
    return _setze_unterdrueckung(ctx, p, aufnahme, SW_AUFHEBEN, False)


@punkt("loeschen")
def loeschen(ctx, p: dict, aufnahme: dict) -> list[str]:
    """Löschen nimmt mehr mit, als `GetChildren` nennt (S18c), darum entscheidet der Baum: Erlaubt sind das Feature, `kinder`
    und ihre Unterfeatures (aufgenommene Skizzen). Löschen wirkt auf alle Konfigurationen; der Rest fällt im Neuaufbau auf."""
    model, name = ctx.model, p["feature"]
    feature = _feature(model, name)
    genannt = {name, *p.get("kinder", ())}
    erlaubt = genannt | {u for n in genannt if (f := model.FeatureByName(n)) is not None for u in unter_namen(f)}
    vorher = _baum(model)
    gehalten = {s: {f.Name for f in e.features} for s, e in ctx.ergebnisse.items()}
    sw.auswahl_leeren(model)
    feature.Select2(False, 0)
    model.Extension.DeleteSelection2(SW_LOESCHEN)
    sw.auswahl_leeren(model)
    nachher = set(_baum(model))
    if name in nachher:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name} wurde nicht gelöscht (eine Skizze mit Kind bleibt stehen)", schritt="loeschen")
    weg = [n for n in vorher if n not in nachher]
    if ungenannt := sorted(set(weg) - erlaubt):
        raise BauFehler(KINDER_FEHLEN, f"Das Löschen von {name} nahm auch {', '.join(ungenannt)} mit: kinder muss sie nennen",
                        schritt="loeschen")
    for s, namen in gehalten.items():
        if namen & set(weg):
            del ctx.ergebnisse[s]
    return weg


def _neuer_name(fid: str, name: str, alt: str) -> str | None:
    """Name eines neuen Features: `p3` → Name, `p3_positionen` und `p3_skizze` → „Name Skizze“, `p3_senkung_skizze` → „Name
    Senkung Skizze“. Was der Handler nicht benennt (weitere Unterskizzen, Gewinde), behält den SolidWorks-Namen."""
    if alt == fid:
        return name
    if not alt.startswith(f"{fid}_"):
        return None
    rest = alt[len(fid) + 1:]
    return f"{name} {('skizze' if rest == 'positionen' else rest).replace('_', ' ').title()}"


def _benenne(neue: list, fid: str, name: str) -> dict[str, str]:
    """Benennt um und liest zurück: Ein doppelter Name bleibt ohne Ausnahme still alt (S18c)."""
    umbenannt = {}
    for f in neue:
        alt = f.Name
        soll = _neuer_name(fid, name, alt)
        if soll is None:
            continue
        f.Name = soll
        if f.Name != soll:
            raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{alt} ließ sich nicht {soll!r} nennen – gibt es den Namen schon?",
                            schritt="umbenennen")
        umbenannt[alt] = soll
    return umbenannt


def _protokoll_nachziehen(ctx, fid: str, ziel: str, umbenannt: dict[str, str]) -> None:
    """Maßnamen enthalten die Skizze, `Parameter` fände sie sonst nicht mehr; Handler kennen nur ihren Pfad in `features`,
    in der Spec steht er unter `ziel`."""
    for m in ctx.masse.get(fid, ()):
        kurz, _, ort = m["name"].rpartition("@")
        m["name"] = f"{kurz}@{umbenannt.get(ort, ort)}"
        m["pfad"] = m["pfad"].replace(ctx.pfad(fid), ziel, 1)


def _in_allen_aufheben(ctx, ergebnis: FeatureErgebnis, neue: list, aufnahme: dict) -> None:
    """Ein Feature ist in den Konfigurationen unterdrückt, in denen es nicht entstand (S18c). Unterfeatures folgen (Sonde
    Task 6), nachgemessen wird trotzdem jedes neue."""
    konfigurationen = aufnahme["konfigurationen"]
    for f in ergebnis.features:
        f.SetSuppression2(SW_AUFHEBEN, SW_BENANNTE_KONFIGURATIONEN, bstr_array(konfigurationen))
    if falsch := [f"{f.Name} in {k}" for f in neue for k in konfigurationen if unterdrueckt(f, k)]:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Neues Feature bleibt unterdrückt: {', '.join(falsch)}", schritt="aufheben")


def _soll_nach(vorher: list[str], neue: set[str], ziel: str, unter_ziel: list[str]) -> list[str]:
    """Erwartete Reihenfolge: die neuen als Block hinter `ziel` und dessen Unterfeatures außerhalb der Kette."""
    rest = [n for n in vorher if n not in neue]
    i = rest.index(ziel) + 1
    while i < len(rest) and rest[i] in unter_ziel:
        i += 1
    return rest[:i] + [n for n in vorher if n in neue] + rest[i:]


def _verschiebe(ctx, p: dict, ergebnis: FeatureErgebnis, neue: set[str], aufnahme: dict) -> None:
    """`ReorderFeature` wirkt nur in der aktiven Konfiguration (Sonde Task 6), also in jeder einzeln. False beschädigt sie
    dauerhaft, `Save3` meldet trotzdem Erfolg (S18c3): sofort abbrechen, der Lauf wird nie gespeichert."""
    ziel = p["nach"]
    unter_ziel = unter_namen(_feature(ctx.model, ziel))
    namen = [f.Name for f in ergebnis.features]

    def messen(k):
        vorher = _baum(ctx.model)
        anker = ziel
        for name in namen:
            if not ctx.model.Extension.ReorderFeature(name, anker, SW_NACH):
                raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name} lässt sich nicht hinter {anker} verschieben ({k}): Die "
                                                       "Konfiguration ist damit beschädigt, der Lauf wird nicht gespeichert",
                                schritt="nach")
            anker = name
        return _baum(ctx.model) == _soll_nach(vorher, neue, ziel, unter_ziel)

    falsch = [k for k, ok in _je_konfiguration(ctx, aufnahme, aufnahme["konfigurationen"], messen).items() if not ok]
    if falsch:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{p['name']} steht nicht hinter {ziel} ({', '.join(falsch)})", schritt="nach")


@punkt("feature")
def feature(ctx, p: dict, aufnahme: dict) -> list[str]:
    """Neues Feature über die Handler der Teil-Spec, am Ende des Baums oder hinter `nach`."""
    fid, inhalt = p["id"], {"id": p["id"], **p["feature"]}
    funktion = alle_handler().get(inhalt["typ"])
    if funktion is None:
        raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für typ {inhalt['typ']!r}", schritt="handler")
    vorher = set(_baum(ctx.model))
    with sw.schnell(ctx.app, ctx.model):
        ergebnis = funktion(ctx, inhalt)
    ctx.ergebnisse[fid] = ergebnis
    neue = [f for f in baum_features(ctx.model) if f.Name not in vorher]
    _protokoll_nachziehen(ctx, fid, f"punkte[{fid}].feature", _benenne(neue, fid, p["name"]))
    _in_allen_aufheben(ctx, ergebnis, neue, aufnahme)
    namen = [f.Name for f in neue]
    if "nach" in p:
        _verschiebe(ctx, p, ergebnis, set(namen), aufnahme)
    return namen


@punkt("material")
def material(ctx, p: dict, aufnahme: dict) -> list[str]:
    """Je Konfiguration über den Namen: `""` träfe nur die aktive (Sonde Task 6). Die Rückgabe ist immer leer, also zurücklesen."""
    datenbank, name = finde_material(list(ctx.app.GetMaterialDatabases or ()), p["neu"])
    konfigurationen = aufnahme["konfigurationen"]
    for k in konfigurationen:
        ctx.model.SetMaterialPropertyName2(k, datenbank, name)
    if falsch := [k for k in konfigurationen if material_von(ctx.model, k) != name]:
        raise BauFehler(MATERIAL_UNBEKANNT, f"Material {name!r} ließ sich nicht zuweisen ({', '.join(falsch)})", schritt="material")
    return [name]


@punkt("eigenschaft")
def eigenschaft(ctx, p: dict, aufnahme: dict) -> list[str]:
    """`neu: null` entfernt. Zurückgelesen wird in beiden Fällen: `Delete2` meldet 1, wenn es die Eigenschaft nicht gibt, das
    Ziel ist dann trotzdem erreicht (Sonde Task 6)."""
    name, neu, wo = p["name"], p["neu"], p.get("konfiguration", "")
    verwalter = ctx.model.Extension.CustomPropertyManager(wo)
    if neu is None:
        verwalter.Delete2(name)
    else:
        verwalter.Add3(name, SW_CUSTOM_INFO_TEXT, neu, SW_CUSTOM_PROPERTY_REPLACE_VALUE)
    if _eigenschaften(ctx.model, wo).get(name) != neu:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Eigenschaft {name} ließ sich nicht {'entfernen' if neu is None else 'setzen'}",
                        schritt="eigenschaft")
    return [name]


@punkt("skript")
def skript(ctx, p: dict, aufnahme: dict) -> list[str]:
    """Notausgang: Ein Eingriff in ein fremdes Feature darf nichts liefern und benennt nichts um (Präzisierung 6)."""
    ergebnis = fuehre_aus(ctx, {"id": p["id"], "datei": p["datei"]})
    _protokoll_nachziehen(ctx, p["id"], f"punkte[{p['id']}]", {})
    features = ergebnis if isinstance(ergebnis, (list, tuple)) else [] if ergebnis is None else [ergebnis]
    return [f.Name for f in features]
