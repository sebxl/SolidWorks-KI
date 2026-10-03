"""swki bauen für Baugruppen (Spec 3b §7): Eigenteile frisch bauen und speichern, Normteile holen und in den Lauf
kopieren, Komponenten einfügen (Ursprung auf Ursprung, die fixierte zuerst), Verknüpfungen setzen, speichern,
protokollieren. Der Lauf-Ordner ist in sich geschlossen; die Bibliothek wird nur gelesen."""

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from swki.aenderungen import pruefe_unveraendert, pruefsummen, vermerke_befund
from swki.auftrag import auftrag_name, dateiname, lauf_belegt, lauf_datei, lauf_ordner, naechster_lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import Instanz, Verknuepfung, basis, instanzen, verknuepfungen
from swki.baugruppe.fehler import KOMPONENTE_FEHLER, SCHLIESSEN_FEHLER, TEIL_BAU, VERKNUEPFUNG_FEHLER
from swki.baugruppe.freigabe import pruefe_freigabe_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import Baugruppe, Quelle, dokument_name
from swki.baugruppe.referenzen import loese_im_teil
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.bauen import BauAbbruch, baue_teil_dokument
from swki.compiler.eigenschaften import eigenschaften_fuer, globale_variablen, setze_eigenschaften
from swki.compiler.fehler import BauFehler, fehler_dict
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
from swki.normteile.bibliothek import bibliotheksordner, lies_eintrag
from swki.normteile.fehler import NormteilFehler
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import verbinde


@dataclass
class Baulauf:
    app: object
    bg: Baugruppe
    auftrag: str
    ordner: Path
    standard: dict
    protokoll: Protokoll
    asm: object = None
    kontexte: dict = field(default_factory=dict)     # Quelldokument (Teil-Spec bzw. Normteil-Schlüssel) → Kontext
    offen: list = field(default_factory=list)        # selbst geöffnete Teildokumente, am Ende schließen
    dateien: dict = field(default_factory=dict)      # "teil:<datei>" | "normteil:<schluessel>" | "baugruppe" → Pfad
    komponenten: dict = field(default_factory=dict)  # Instanz-ID → IComponent2 (aus AddComponent5, nie über GetComponents)
    gesetzt: dict = field(default_factory=dict)      # Verknüpfungs-ID → ausdrücklich gesetzte Ausrichtung, ein Dict je Lauf


def _baue_teile(b: Baulauf, r) -> Exception | None:
    for datei, teil_spec in b.bg.teile.items():
        tp = Protokoll(b.auftrag, datei, b.protokoll.lauf, r.sw_jahr)
        model, ctx, fehler = baue_teil_dokument(b.app, r, b.standard, teil_spec, b.bg.pfad.parent / datei, b.auftrag, tp)
        b.offen.append(model)
        b.kontexte[datei] = ctx
        ziel = b.ordner / dokument_name(b.bg.quellen[b.bg.komponente_von(datei)], b.auftrag, b.standard)
        try:
            sw.speichere(model, ziel)  # auch nach einem Fehler: Teilstand zur Diagnose
            b.dateien[f"teil:{datei}"] = ziel
        except Exception as e:
            fehler = fehler or e
        tp.status = "fehler" if fehler else "ok"
        tp.fehler = fehler_dict(fehler) if fehler else None
        b.protokoll.teile[datei] = tp.als_dict()
        if fehler is not None:
            knoten = next((k.id for k in tp.knoten if k.status == "fehler"), "speichern")
            f = fehler_dict(fehler)
            return BauFehler(TEIL_BAU, f"{b.bg.komponente_von(datei)}/{knoten}: {f['code']} – {f['meldung']}", schritt="teil")
    return None


def _hole_normteile(b: Baulauf, r, tol_mm: float) -> Exception | None:
    erledigt = set()
    for kid, q in b.bg.quellen.items():
        if q.art != "normteil" or q.schluessel in erledigt:
            continue
        erledigt.add(q.schluessel)
        try:
            ergebnis = normteil_befehle.hole(q.norm, q.hole_groesse, q.variante)
        except NormteilFehler as e:
            return BauFehler(e.daten["code"], f"{kid}: {e}", schritt="normteil")
        ziel = b.ordner / dokument_name(q, b.auftrag, b.standard)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ergebnis["pfad"], ziel)
        eintrag = lies_eintrag(bibliotheksordner(r), q.schluessel) or {}
        b.protokoll.normteile[q.schluessel] = {"bibliothek": ergebnis["pfad"], "gebaut": ergebnis["gebaut"],
                                               "pruefsumme": eintrag.get("pruefsumme")}
        b.dateien[f"normteil:{q.schluessel}"] = ziel
        model = oeffne(b.app, ziel)
        b.offen.append(model)
        b.kontexte[q.schluessel] = kontext_aus_datei(b.app, model, q.spec, ziel.with_suffix(".yaml"), tol_mm, {"knoten": []})
    return None


def _gespeichert(b: Baulauf, q: Quelle) -> Path:
    """Pfad, unter dem swki die Quelldatei im Lauf-Ordner gespeichert hat (GetPathName schreibt .SLDPRT groß, Spike S12)."""
    return b.dateien[f"teil:{q.datei}" if q.art == "teil" else f"normteil:{q.schluessel}"]


def _mit_kontext(e: Exception, code: str, kontext: str, schritt: str) -> BauFehler:
    """Meldung um den Kontext (Komponente, Knoten, Datei) ergänzen. Ein BauFehler behält Code und Schritt; fremde
    Ausnahmen (z. B. COM) bekommen `code` statt ihres Typnamens (Spec 3b §11)."""
    if isinstance(e, BauFehler):
        return BauFehler(e.code, f"{kontext}: {e}", e.schritt or schritt)
    return BauFehler(code, f"{kontext}: {type(e).__name__}: {e}", schritt)


def _einfuege_reihenfolge(b: Baulauf, alle: list[Instanz]) -> list[Instanz]:
    """Die fixierte Komponente zuerst, sonst Spec-Reihenfolge, Instanzen in Positionsreihenfolge (stabil sortiert)."""
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    return sorted(alle, key=lambda x: x.komponente not in fixiert)


def _ueberspringe_komponenten(b: Baulauf, alle: list[Instanz]) -> None:
    """Komponenten ohne Knoten (Abbruch vor oder beim Einfügen) als übersprungen vermerken – wie die Verknüpfungen."""
    erfasst = {k.id for k in b.protokoll.knoten}
    for i in _einfuege_reihenfolge(b, alle):
        if i.id not in erfasst:
            b.protokoll.uebersprungen(i.id, "komponente")


def _fuege_ein(b: Baulauf, alle: list[Instanz]) -> Exception | None:
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    for i in _einfuege_reihenfolge(b, alle):
        q = b.bg.quellen[i.komponente]
        try:
            with b.protokoll.knoten_lauf(i.id, "komponente") as knoten:
                try:
                    model = b.kontexte[q.schluessel_dokument].model
                    pfad = Path(model.GetPathName)
                    komp = sw_baugruppe.fuege_ein(b.app, b.asm, pfad, sw.teilebox_mm(model))
                    if i.komponente in fixiert:
                        sw_baugruppe.fixiere(b.asm, komp)
                    knoten.sw_name = komp.Name2
                    b.komponenten[i.id] = komp
                    b.protokoll.komponenten.append({"id": i.id, "sw_name": komp.Name2,
                                                    "datei": _gespeichert(b, q).name})
                except Exception as e:
                    datei = dokument_name(q, b.auftrag, b.standard)
                    raise _mit_kontext(e, KOMPONENTE_FEHLER, f"Komponente {i.id} ({datei})", "einfuegen") from e
        except Exception as e:
            return e
    return None


def _entitaet(b: Baulauf, seite: dict) -> tuple[object, bool]:
    try:
        ctx = b.kontexte[b.bg.quellen[basis(seite["komponente"])].schluessel_dokument]
        ref = loese_im_teil(ctx, {k: v for k, v in seite.items() if k != "komponente"})
        return sw_baugruppe.in_baugruppe(b.komponenten[seite["komponente"]], ref)
    except Exception as e:  # Komponente nennen: die Referenz-Meldungen kennen sie nicht
        raise _mit_kontext(e, VERKNUEPFUNG_FEHLER, f"Komponente {seite['komponente']}", "referenz") from e


def _verknuepfe(b: Baulauf, alle: list[Verknuepfung]) -> Exception | None:
    fehler = None
    for v in alle:
        if fehler is not None:
            b.protokoll.uebersprungen(v.id, v.typ)
            continue
        try:
            with b.protokoll.knoten_lauf(v.id, v.typ) as knoten:
                try:
                    feature = sw_baugruppe.verknuepfe(b.asm, v, _entitaet(b, v.a), _entitaet(b, v.b),
                                                      b.bg.spec.get("parameter", {}), b.gesetzt)
                    knoten.sw_name = feature.Name
                except Exception as e:
                    if isinstance(e, BauFehler) and str(e).startswith(f"{v.id} "):
                        raise  # schon mit Verknüpfungs-ID (verknuepfe)
                    raise _mit_kontext(e, VERKNUEPFUNG_FEHLER, f"Verknüpfung {v.id} ({v.typ})", "verknuepfung") from e
        except Exception as e:  # jeder Fehler (auch COM) beendet den Lauf und steht im Protokoll
            fehler = e
    return fehler


def _schliesse_alle(b: Baulauf) -> BauFehler | None:
    """Baugruppe, dann die Teile in umgekehrter Öffnungsreihenfolge; jedes Dokument einzeln, ein Fehler hält die übrigen
    nicht auf. Liefert den ersten Schließfehler (oder None)."""
    erster = None
    for model in ([b.asm] if b.asm is not None else []) + list(reversed(b.offen)):
        try:
            sw.schliesse(b.app, model)
        except Exception as e:
            erster = erster or BauFehler(SCHLIESSEN_FEHLER, f"Dokument ließ sich nicht schließen: {type(e).__name__}: {e}",
                                         schritt="schliessen")
    return erster


def bauen(spec_pfad: Path, lauf: int | None = None, verwerfen: bool = False, uebernommen: bool = False) -> dict:
    spec_pfad = spec_pfad.resolve()
    bg = lade_baugruppe(spec_pfad)
    pruefe_freigabe_baugruppe(bg)
    r, standard = lade_rechner(), lade_standard()
    if r.vorlage_baugruppe is None:
        raise SwkiFehler("config/rechner.yaml: vorlage_baugruppe fehlt (swki rechner init)")
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    uebergangen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen, uebernommen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    vermerke_befund(protokoll, uebergangen, verwerfen)
    alle_instanzen, alle_verknuepfungen = instanzen(bg.spec, bg.quellen), verknuepfungen(bg.spec, bg.quellen)
    beginn = time.perf_counter()
    b = Baulauf(verbinde(r.sw_jahr), bg, auftrag, ordner, standard, protokoll)
    fehler = None
    try:
        with protokoll.phase("teile"):
            fehler = _baue_teile(b, r)
        if fehler is None:
            with protokoll.phase("normteile"):
                fehler = _hole_normteile(b, r, standard["toleranzen"]["anker_mm"])
        if fehler is None:
            with protokoll.phase("einfuegen"):
                b.asm = sw_baugruppe.neue_baugruppe(b.app, r.vorlage_baugruppe)
                globale_variablen(b.asm, bg.spec.get("parameter", {}))
                setze_eigenschaften(b.asm, eigenschaften_fuer(bg.spec, auftrag))
                fehler = _fuege_ein(b, alle_instanzen)
        if fehler is not None:
            _ueberspringe_komponenten(b, alle_instanzen)
        with protokoll.phase("verknuepfen"):
            if fehler is None:
                fehler = _verknuepfe(b, alle_verknuepfungen)
            else:
                for v in alle_verknuepfungen:
                    protokoll.uebersprungen(v.id, v.typ)
        if b.asm is not None:
            with protokoll.phase("speichern"):
                ziel = ordner / f"{dateiname(bg.spec, auftrag, standard)}.sldasm"
                try:
                    sw.speichere(b.asm, ziel)  # auch nach einem Fehler: Stand zur Diagnose
                    b.dateien["baugruppe"] = ziel
                except Exception as e:
                    fehler = fehler or e
    except Exception as e:  # z. B. Vorlage, Gleichungen oder Eigenschaften der Baugruppe
        fehler = fehler or e
    finally:
        schliessfehler = _schliesse_alle(b)
    if schliessfehler is not None and fehler is None:
        fehler = schliessfehler  # ein früherer Fehler bleibt erhalten und wird nicht verdeckt
    protokoll.dateien = {art: str(p) for art, p in b.dateien.items()}
    protokoll.sha256 = pruefsummen(ordner, b.dateien.values())
    protokoll.status = "fehler" if fehler else "ok"
    protokoll.fehler = fehler_dict(fehler) if fehler else None
    protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
    protokoll.schreibe(ordner / "protokoll.json")
    protokoll.schreibe(lauf_datei(spec_pfad, lauf, "protokoll"))
    ergebnis = {
        "status": protokoll.status, "art": "baugruppe", "auftrag": auftrag, "lauf": lauf, "ordner": str(ordner),
        "dateien": protokoll.dateien,
        "knoten": [{"id": k.id, "status": k.status, "sw_name": k.sw_name} for k in protokoll.knoten],
        "fehler": protokoll.fehler, "dauer_s": protokoll.dauer_s,
    }
    if fehler:
        raise BauAbbruch(ergebnis)
    return ergebnis
