"""Änderungserkennung (Spec 3b §8): manuelle Änderungen an gebauten Dateien erkennen, bevor ein neuer Lauf sie still
verliert.

swki bauen schreibt den SHA-256 jeder gespeicherten Datei ins Protokoll (Feld sha256). Vor dem nächsten Bau vergleicht
pruefe_unveraendert den höchsten durchgebauten Lauf (Protokollstatus ok) damit. Läufe ohne Prüfsummen (vor Stufe 3b) und
ganz entfernte Lauf-Ordner gelten als unverändert. swki aenderungen liest geänderte Dateien aus (mit SolidWorks, nur
lesend, unsichtbar): bei Läufen mit Maßprotokoll (Knoten.masse) die einzelnen Maße und schlägt Spec-Änderungen vor, bei älteren Läufen
die globalen Variablen; bei Teilen dazu den Baum (neue und fehlende Features, Material, Eigenschaften, swki.bestand.abgleich).
Verglichen wird mit dem Protokoll bzw. der freigegebenen Spezifikation. Ein Lauf, aus dem eine Bestandsaufnahme stammt
(swki bestand aufnehmen, Spec Bestandsdateien §8.5), wird nie geöffnet: Dort vergleicht swki bestand abgleich über die Kopie."""

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_nummern_dateien, lauf_ordner
from swki.cli import SwkiFehler, ganzzahl_ab
from swki.compiler import sw
from swki.compiler.kontext import einheit_der_art
from swki.konfig import Rechner, lade_rechner, lade_standard
from swki.spec.ausdruck import auswerten
from swki.spec.freigabe import freigabe_pfad, freigegebene_spec
from swki.spec.laden import art_der_datei
from swki.verbindung import in_mm, verbinde

MANUELL_GEAENDERT = "MANUELL_GEAENDERT"
# Eigener Code (nicht MANUELL_GEAENDERT): MANUELL_GEAENDERT löst die Rückfrage übernehmen/verwerfen aus, diese
# Meldung hat eine andere Abhilfe (Spezifikation übernehmen und neu freigeben).
UEBERNAHME_OHNE_NEUE_FREIGABE = "UEBERNAHME_OHNE_NEUE_FREIGABE"
_TOL = 1e-6
_SW_DATEIEN = (".sldprt", ".sldasm")
_LAUF_DATEIEN = (*_SW_DATEIEN, ".slddrw")  # SolidWorks-Dateien, die im Lauf-Ordner neu auftauchen können
_TEXT_AENDERUNG = ("Änderungs-Spec (art: aenderung): swki liest hier keine Maße aus, die Abweichung zeigt nur die SHA-256. Ein neuer "
                   "Lauf entsteht immer ab der Bestandskopie, nie aus der geänderten Lauf-Datei; sie bleibt unberührt. Der Befund "
                   "bleibt MANUELL_GEAENDERT, bis der Nutzer entscheidet. Nutzer fragen, was geändert wurde: übernehmen (den Punkt in "
                   "der Spec ergänzen, validieren, Nutzer-OK, swki freigeben, dann swki bauen --uebernommen) oder verwerfen "
                   "(swki bauen --verwerfen, nur auf ausdrückliche Anweisung)")


class AenderungFehler(SwkiFehler):
    def __init__(self, meldung: str, code: str = MANUELL_GEAENDERT, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}


def sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pruefsummen(ordner: Path, dateien) -> dict[str, str]:
    """{Pfad relativ zum Lauf-Ordner: SHA-256} der vorhandenen Dateien."""
    return {Path(d).relative_to(ordner).as_posix(): sha256_datei(Path(d)) for d in dateien if Path(d).is_file()}


def letzter_gebauter_lauf(spec_pfad: Path) -> tuple[int, dict] | None:
    """(Nummer, Protokoll) des höchsten Laufs mit Status ok, wenn er Prüfsummen hat; sonst None."""
    for n in sorted(lauf_nummern_dateien(spec_pfad), reverse=True):
        try:
            protokoll = json.loads(lauf_datei(spec_pfad, n, "protokoll").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(protokoll, dict) and protokoll.get("status") == "ok":
            return (n, protokoll) if protokoll.get("sha256") else None
    return None


def abweichungen(ordner: Path, soll: dict[str, str]) -> dict[str, list[str]]:
    geaendert, fehlend = [], []
    for name, summe in sorted(soll.items()):
        pfad = ordner / name
        if not pfad.is_file():
            fehlend.append(name)
        elif sha256_datei(pfad) != summe:
            geaendert.append(name)
    return {"geaendert": geaendert, "fehlend": fehlend}


def befund(r: Rechner, auftrag: str, spec_pfad: Path) -> dict | None:
    letzter = letzter_gebauter_lauf(spec_pfad)
    if letzter is None:
        return None
    n, protokoll = letzter
    ordner = lauf_ordner(r, auftrag, n)
    if not ordner.is_dir():
        return None  # Lauf-Ordner aufgeräumt: es gibt nichts, was verloren gehen könnte
    a = abweichungen(ordner, protokoll["sha256"])
    return {"lauf": n, **a} if a["geaendert"] or a["fehlend"] else None


def _lauf_zeitpunkt(spec_pfad: Path, n: int) -> datetime:
    """Beginn von Lauf n laut Protokoll (Feld gestartet); fehlt es, die Änderungszeit der Protokolldatei (sie wird am
    Ende des Laufs geschrieben, ist also nie früher als der Beginn)."""
    datei = lauf_datei(spec_pfad, n, "protokoll")
    try:
        return datetime.fromisoformat(json.loads(datei.read_text(encoding="utf-8"))["gestartet"])
    except (OSError, ValueError, KeyError, TypeError):
        return datetime.fromtimestamp(datei.stat().st_mtime)


def _freigabe_zeitpunkt(spec_pfad: Path) -> datetime | None:
    try:
        eintrag = json.loads(freigabe_pfad(spec_pfad).read_text(encoding="utf-8"))[spec_pfad.name]
        return datetime.fromisoformat(eintrag["freigegeben"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def aufnahmen_des_laufs(r: Rechner, auftrag: str, lauf: int) -> list[dict]:
    """`[{auftrag, aufnahme}]` der Bestandsaufnahmen, deren Original aus diesem Lauf stammt (`herkunft.json`, Spec Bestandsdateien
    §8.5). Der Lauf-Ordner wird nicht gelesen."""
    from swki.bestand.ablage import aufnahmen_aus_lauf  # spät importiert: swki.bestand.ablage nutzt sha256_datei

    return [{"auftrag": t["auftrag"], "aufnahme": t["nummer"]} for t in aufnahmen_aus_lauf(r, lauf_ordner(r, auftrag, lauf))]


def unlesbare_herkunft_des_rechners(r: Rechner) -> list[dict]:
    """`[{pfad, grund}]` unlesbarer `herkunft.json` im Arbeitsordner. Ob sie zu einem Lauf gehört, ist nicht zu erkennen: Der Lauf
    gilt dann als möglicherweise aufgenommen und wird nicht geöffnet (Spec Bestandsdateien §8.5)."""
    from swki.bestand.ablage import unlesbare_herkunft  # spät importiert: swki.bestand.ablage nutzt sha256_datei

    return unlesbare_herkunft(r)


def _kommandozeile(pfad: Path) -> str:
    text = str(pfad)
    return f'"{text}"' if " " in text else text


def _abgleich_befehl(aufnahme: dict, spec_pfad: Path) -> str:
    return f"swki bestand abgleich {aufnahme['auftrag']} --spec {_kommandozeile(spec_pfad)}"


def _text_geaendert(b: dict, genannt: str, aufnahmen: list[dict], spec_pfad: Path, unlesbar: list[dict]) -> str:
    """Meldung der Sperre MANUELL_GEAENDERT mit den drei Wegen (Spec §8.5). Hat der Lauf eine Aufnahme, steht dort `swki bestand
    abgleich` statt `swki aenderungen` (das den Lauf in SolidWorks öffnen würde)."""
    kopf = f"Lauf {b['lauf']} wurde nach dem Bau verändert ({genannt}). "
    if unlesbar and not aufnahmen:
        dateien = ", ".join(u["pfad"] for u in unlesbar)
        return (kopf + f"Eine herkunft.json ist nicht lesbar ({dateien}): Ob der Lauf aufgenommen wurde, ist unklar, darum öffnet swki "
                       "ihn nicht in SolidWorks. Die Datei prüfen (korrigieren oder die Aufnahme neu anlegen), "
                       "dann den Nutzer fragen: übernehmen (Spezifikation ändern, validieren, neu freigeben, swki bauen --uebernommen) "
                       "oder verwerfen (swki bauen --verwerfen)")
    if aufnahmen:
        nennung = ", ".join(f"Auftrag {a['auftrag']}, Aufnahme {a['aufnahme']}" for a in aufnahmen)
        return (kopf + f"Er ist schon aufgenommen ({nennung}); was geändert wurde, zeigt {_abgleich_befehl(aufnahmen[-1], spec_pfad)} "
                       "über die Bestandskopie, ohne den Lauf zu öffnen. Ist die Datei der Stand, arbeitet der Skill aendern in dem "
                       "Auftrag der Aufnahme weiter und diese Spec bleibt eingefroren. Nutzer fragen: übernehmen "
                       "(Spezifikation ändern, validieren, neu freigeben, swki bauen --uebernommen) oder verwerfen "
                       "(swki bauen --verwerfen)")
    return (kopf + "swki aenderungen zeigt, was geändert wurde (nur lesend). Nutzer fragen: übernehmen (Spezifikation ändern, "
                   "validieren, neu freigeben, swki bauen --uebernommen), verwerfen (swki bauen --verwerfen) oder, wenn die "
                   "geänderte Datei der Stand ist, aufnehmen (swki bestand aufnehmen in einem neuen Auftrag, Skill aendern; "
                   "diese Spec bleibt eingefroren)")


def pruefe_unveraendert(r: Rechner, auftrag: str, spec_pfad: Path, verwerfen: bool = False,
                        uebernommen: bool = False) -> dict | None:
    """Wirft AenderungFehler, wenn Dateien des letzten durchgebauten Laufs geändert wurden oder fehlen.

    verwerfen (ausdrückliche Anweisung des Nutzers) gibt den Befund nur zurück (fürs Protokoll). uebernommen gilt
    nur, wenn die aktuelle Freigabe NACH Beginn dieses Laufs erteilt wurde (die Änderung also in die Spezifikation
    übernommen und neu freigegeben ist); sonst UEBERNAHME_OHNE_NEUE_FREIGABE. Ohne Abweichung sind beide wirkungslos."""
    if verwerfen and uebernommen:
        raise SwkiFehler("--verwerfen und --uebernommen schließen sich aus: entweder die manuelle Änderung wird "
                         "verworfen oder in die Spezifikation übernommen")
    b = befund(r, auftrag, spec_pfad)
    if b is None or verwerfen:
        return b
    genannt = ", ".join(b["geaendert"] + b["fehlend"])
    aufnahmen = aufnahmen_des_laufs(r, auftrag, b["lauf"])
    unlesbar = unlesbare_herkunft_des_rechners(r)
    if uebernommen:
        freigabe, lauf = _freigabe_zeitpunkt(spec_pfad), _lauf_zeitpunkt(spec_pfad, b["lauf"])
        if freigabe is not None and freigabe > lauf:
            return b
        raise AenderungFehler(
            f"Freigabe ist nicht neuer als Lauf {b['lauf']} (geändert: {genannt}) – erst die Änderung in die "
            "Spezifikation übernehmen, validieren, vom Nutzer bestätigen lassen und per swki freigeben neu freigeben, "
            "dann swki bauen --uebernommen", code=UEBERNAHME_OHNE_NEUE_FREIGABE, aufnahmen=aufnahmen,
            herkunft_unlesbar=unlesbar, **b)
    raise AenderungFehler(_text_geaendert(b, genannt, aufnahmen, spec_pfad, unlesbar), aufnahmen=aufnahmen,
                          herkunft_unlesbar=unlesbar, **b)


def vermerke_befund(protokoll, b: dict | None, verwerfen: bool) -> None:
    """Hält den übergangenen Befund im Bauprotokoll fest: verworfen (--verwerfen) oder uebernommen (--uebernommen)."""
    protokoll.verworfen = b if verwerfen else None
    protokoll.uebernommen = None if verwerfen else b


def parameter_differenz(soll: dict, ist: dict) -> list[dict]:
    """Parameter, die fehlen, neu sind oder sich um mehr als 1e-6 unterscheiden (alphabetisch)."""
    differenz = []
    for name in sorted(set(soll) | set(ist)):
        s, i = soll.get(name), ist.get(name)
        if s is None or i is None or abs(float(s) - float(i)) > _TOL:
            differenz.append({"name": name, "soll": s, "ist": i})
    return differenz


def lies_globale_variablen(model) -> dict[str, float]:
    """Globale Variablen (Name → Wert in mm bzw. Grad; IEquationMgr.Value wie in Spike S9a Baustein 5)."""
    gleichungen = model.GetEquationMgr
    werte = {}
    for i in range(gleichungen.GetCount):
        if gleichungen.GlobalVariable(i):
            werte[gleichungen.Equation(i).split('"')[1]] = float(gleichungen.Value(i))
    return werte


def _hat_masse(protokoll: dict) -> bool:
    """Trägt ein Bauprotokoll das Maßprotokoll? Neue Läufe schreiben das Feld masse an jedem Knoten (auch ohne Maße als
    null), Läufe vor dem Bemaßungsbezug kennen es nicht."""
    return any("masse" in k for k in protokoll.get("knoten") or [])


def _alle_masse(protokoll: dict) -> list[dict]:
    return [m for k in protokoll.get("knoten") or [] for m in k.get("masse") or []]


def soll_masse(protokoll: dict, spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, list[dict]]:
    """Dateiname im Lauf → Maße aus dem Bauprotokoll (Teil: alle Knoten; Baugruppe: je Teil aus protokoll["teile"], das
    Baugruppendokument selbst mit leerer Liste, es hat nur Verknüpfungen). Nur Dateien, deren Protokoll das Maßprotokoll
    kennt – die übrigen (alte Läufe) fehlen im Ergebnis und gehen den alten Weg über globale Variablen."""
    teile = protokoll.get("teile") or {}
    if not (_hat_masse(protokoll) or any(_hat_masse(t) for t in teile.values())):
        return {}  # kein Maßprotokoll: nicht einmal die Freigabe lesen
    soll = freigegebene_spec(spec_pfad)
    ergebnis = {}
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.laden import lade_baugruppe  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        if _hat_masse(protokoll):
            ergebnis[f"{dateiname(soll, auftrag, standard)}.sldasm"] = _alle_masse(protokoll)
        for datei, teil in teile.items():
            if _hat_masse(teil):
                ergebnis[dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard)] = _alle_masse(teil)
    elif _hat_masse(protokoll):
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldprt"] = _alle_masse(protokoll)
    return ergebnis


def lies_masse(model, masse: list[dict]) -> dict[str, float]:
    """Aktuelle Werte der protokollierten Maße (Name → Betrag in mm bzw. Grad). Die Einheit steht im Feld einheit
    (auch bei Skriptmaßen, deren art "skript" ist); ältere Protokolle ohne einheit: winkel in Grad, sonst mm. Ein Maß, das
    es nicht mehr gibt, fehlt im Ergebnis. IDimension.SystemValue liefert m bzw. rad (Spike S17 Fall 7)."""
    werte = {}
    for m in masse:
        dimension = model.Parameter(m["name"])
        if dimension is not None:
            wert = float(dimension.SystemValue)
            grad = (m.get("einheit") or einheit_der_art(m["art"])) == "grad"
            werte[m["name"]] = abs(math.degrees(wert) if grad else in_mm(wert))
    return werte


def mass_differenz(masse: list[dict], ist: dict[str, float]) -> list[dict]:
    """Maße, die sich um mehr als 1e-6 vom Protokoll unterscheiden oder fehlen (ist und delta dann None), in der
    Reihenfolge des Protokolls. delta = ist − soll."""
    differenz = []
    for m in masse:
        i = ist.get(m["name"])
        if i is None or abs(i - m["wert"]) > _TOL:
            differenz.append({"name": m["name"], "pfad": m["pfad"], "art": m["art"], "bezug": m["bezug"], "roh": m["roh"],
                              "vorzeichen": m["vorzeichen"], "soll": m["wert"], "ist": i,
                              "delta": None if i is None else i - m["wert"]})
    return differenz


_DIREKT = re.compile(r"=\s*-?\s*([A-Za-z_]\w*)")
_LAGEN = {"lage": 1, "paarabstand": 2}  # art → Maß je mm Koordinatenänderung (Paarabstand: 2 × Koordinate)


def vorschlaege(differenz: list[dict], parameter: dict) -> list[dict]:
    """Spec-Änderungen, die zu den geänderten Maßen passen (nur ein Vorschlag, der Nutzer entscheidet).

    parameter: die freigegebenen Parameter der Spezifikation. Größen-, Tiefen-, Radius-, Winkel-, Abstands- und
    Versatzmaße mit roh genau =P oder =-P, P ein numerischer freigegebener Parameter → {"parameter": P, "neu": w}.
    Maße sind Beträge, ein Parameter behält bei der Handänderung sein Vorzeichen: w = ist mit dem Vorzeichen des
    freigegebenen P (bei P = 0 positiv), unabhängig vom − im Ausdruck. Verlangen zwei Maße verschiedene Werte →
    {"parameter": P, "konflikt": [w1, w2, …]}.
    Lagemaße und Paarabstände nie als Parameter, sondern {"pfad", "bezug", "delta", "vorzeichen",
    "koordinate_delta"}: koordinate_delta ist die Änderung der Spec-Koordinate am pfad. vorzeichen ist die Richtung
    vom Bezug zum Punkt (Koordinate − Bezugslage = vorzeichen × Maß; Rand/Fläche: die Kante, sonst der Ursprung), also
    lage: vorzeichen × delta. Ein Paarabstand ist 2 × Koordinate des festlegenden Punkts (der Partner liegt
    spiegelbildlich), also paarabstand: vorzeichen × delta / 2 (Ruling 11).
    Konstruktions- und Skriptmaße, nicht numerische oder unbekannte Parameter und fehlende Maße ergeben keinen
    Vorschlag."""
    ergebnis, je_parameter = [], {}
    for d in differenz:
        if d["ist"] is None or d["art"] in ("konstruktion", "skript"):
            continue
        if d["art"] in _LAGEN:
            ergebnis.append({"pfad": d["pfad"], "bezug": d["bezug"], "delta": d["delta"],
                             "vorzeichen": d["vorzeichen"],
                             "koordinate_delta": d["vorzeichen"] * d["delta"] / _LAGEN[d["art"]]})
            continue
        treffer = _DIREKT.fullmatch(d["roh"].strip()) if isinstance(d["roh"], str) else None
        if treffer is None or treffer[1] not in parameter:
            continue
        name = treffer[1]
        frei = parameter[name]
        if isinstance(frei, bool) or not isinstance(frei, (int, float)):
            continue
        wert = -d["ist"] if frei < 0 else d["ist"]
        eintrag = je_parameter.get(name)
        if eintrag is None:
            je_parameter[name] = eintrag = {"parameter": name, "neu": wert}
            ergebnis.append(eintrag)
        elif "neu" in eintrag and abs(eintrag["neu"] - wert) > _TOL:
            eintrag["konflikt"] = [eintrag.pop("neu"), wert]
        elif "konflikt" in eintrag and all(abs(w - wert) > _TOL for w in eintrag["konflikt"]):
            eintrag["konflikt"].append(wert)
    return ergebnis


def soll_verknuepfungswerte(spec: dict, quellen: dict, parameter: dict | None = None) -> dict[str, float]:
    """Abstands- und Winkelwerte der aufgelösten Verknüpfungen (mm bzw. Grad) nach Verknüpfungs-ID; die Ausdrücke
    werden mit parameter ausgewertet (Vorgabe: die Parameter von spec). Eine Grenzverknüpfung steht mit ihrem Wert in
    Grundstellung (min), so speichert swki bauen sie (Spec 4a §7)."""
    from swki.baugruppe.aufloesen import verknuepfungen  # spät importiert (Kreisimport)

    p = spec.get("parameter", {}) if parameter is None else parameter
    return {v.id: auswerten(v.wert if v.wert is not None else v.min, p) for v in verknuepfungen(spec, quellen)
            if v.wert is not None or v.min is not None}


def soll_verknuepfungen(spec: dict, quellen: dict, parameter: dict | None, komponenten: list[dict]) -> dict[str, dict]:
    """Soll je aufgelöster Verknüpfung für swki.bestand.abgleich.abgleich_baugruppe: Verknüpfungs-ID → `{typ, partner, ausrichtung,
    wert, min, max}`. `partner` sind die SolidWorks-Namen der beiden Seiten aus `komponenten` (Bauprotokoll: `[{id, sw_name}]`, None
    ohne Namen); `ausrichtung` ist `gleich`/`entgegengesetzt` oder None, wenn die Spec keine nennt; Zahlen in mm bzw. Grad, die
    Ausdrücke mit `parameter` (die freigegebenen) ausgewertet. Eine Grenzverknüpfung trägt min, max und in `wert` ihren Wert in
    Grundstellung (min), wie `soll_verknuepfungswerte`. Rein, ohne SolidWorks."""
    from swki.baugruppe.aufloesen import verknuepfungen  # spät importiert (Kreisimport)

    p = spec.get("parameter", {}) if parameter is None else parameter
    namen = {k["id"]: k.get("sw_name") for k in komponenten}

    def zahl(x):
        return None if x is None else auswerten(x, p)

    return {v.id: {"typ": v.typ, "partner": [namen.get(seite["komponente"]) for seite in (v.a, v.b)],
                   "ausrichtung": v.ausrichtung, "wert": zahl(v.wert if v.wert is not None else v.min), "min": zahl(v.min),
                   "max": zahl(v.max)}
            for v in verknuepfungen(spec, quellen)}


def soll_parameter(spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, dict]:
    """Dateiname im Lauf → Parameter der freigegebenen Spezifikation (Teil bzw. Baugruppe und ihre Teile)."""
    soll = freigegebene_spec(spec_pfad)
    ergebnis = {}
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.freigabe import freigegebene_teile  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.laden import lade_baugruppe
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        # Verknüpfungen sind Bauweg (aktuelle Spec), ihre Ausdrücke gelten aber mit den freigegebenen Parametern (Spec §8)
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldasm"] = {
            **soll.get("parameter", {}),
            **{f"verknuepfung:{n}": w
               for n, w in soll_verknuepfungswerte(bg.spec, bg.quellen, soll.get("parameter", {})).items()}}
        for datei, teil in freigegebene_teile(bg).items():
            ergebnis[dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard)] = teil.get("parameter", {})
    else:
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldprt"] = soll.get("parameter", {})
    return ergebnis


def soll_teile(protokoll: dict, spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, tuple[dict, dict]]:
    """Dateiname im Lauf → (Bauprotokoll, freigegebene Spec) je Teil, gegen die swki.bestand.abgleich den Baum vergleicht (Teil:
    der Lauf selbst; Baugruppe: je Teil aus protokoll["teile"]). Normteil- und Kaufteil-Kopien tragen kein Soll."""
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.freigabe import freigegebene_teile  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.laden import lade_baugruppe
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        freigegeben = freigegebene_teile(bg)
        return {dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard): (teil, freigegeben[datei])
                for datei, teil in (protokoll.get("teile") or {}).items() if datei in freigegeben}
    soll = freigegebene_spec(spec_pfad)
    return {f"{dateiname(soll, auftrag, standard)}.sldprt": (protokoll, soll)}


def teil_specs(protokoll: dict, spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, tuple[dict, Path]]:
    """Dateiname im Lauf → (freigegebene Teil-Spec, Pfad der Spec) für `--referenzbau`; Eigenteile wie `soll_teile`."""
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.freigabe import freigegebene_teile  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.laden import lade_baugruppe
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        freigegeben = freigegebene_teile(bg)
        return {dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard): (freigegeben[datei],
                                                                                         bg.pfad.parent / datei)
                for datei in (protokoll.get("teile") or {}) if datei in freigegeben}
    soll = freigegebene_spec(spec_pfad)
    return {f"{dateiname(soll, auftrag, standard)}.sldprt": (soll, spec_pfad)}


def soll_verknuepfungen_lauf(spec_pfad: Path, protokoll: dict) -> dict[str, dict]:
    """`soll_verknuepfungen` eines Laufs: Verknüpfungen aus der Spec (Bauweg), Ausdrücke mit den freigegebenen Parametern, Namen
    aus `protokoll["komponenten"]`."""
    from swki.baugruppe.laden import lade_baugruppe  # spät importiert: swki.baugruppe nutzt swki.compiler

    bg = lade_baugruppe(spec_pfad)
    return soll_verknuepfungen(bg.spec, bg.quellen, freigegebene_spec(spec_pfad).get("parameter", {}),
                               protokoll.get("komponenten") or [])


def soll_lagen(spec_pfad: Path, lauf: int) -> dict | None:
    """Prüfbericht des Laufs als Soll-Lagen (`lagen`, swki.bestand.abgleich.normalisiere_lagen); ältere Läufe tragen keine."""
    try:
        bericht = json.loads(lauf_datei(spec_pfad, lauf, "pruefbericht").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return bericht if isinstance(bericht, dict) else None


def neue_dateien(ordner: Path, soll_sha: dict[str, str]) -> list[dict]:
    """SolidWorks-Dateien im Lauf-Ordner, die das Bauprotokoll nicht kennt (`[{datei, sha256}]`): ein neues Teil, das jemand dort
    abgelegt hat. Nur lesend; Sperrdateien (`~$`) zählen nicht."""
    from swki.bestand.abgleich import abgleich_dateien  # spät importiert: abgleich importiert dieses Modul

    bekannt = {n.replace("\\", "/").lower() for n in soll_sha}
    ist = {rel: sha256_datei(p) for p in sorted(ordner.rglob("*"))
           if p.is_file() and p.suffix.lower() in _LAUF_DATEIEN and not p.name.startswith("~$")
           and (rel := p.relative_to(ordner).as_posix()).lower() not in bekannt}
    return [{"datei": rel, "sha256": ist[rel]} for rel in abgleich_dateien({}, ist)["neu"]]


def baum_gegen_soll(name: str, soll_t: dict, ist_bestand: dict | None, lesefehler: str | None, auftrag: str) -> dict:
    """Der Baum eines gelesenen Teils gegen das Bauprotokoll; wo ein Vergleich nicht möglich war, steht der Grund da (nie ein
    „unverändert“)."""
    from swki.bestand.abgleich import abgleich_teil, ungeprueft_teil  # spät importiert: abgleich importiert dieses Modul

    if name not in soll_t:
        return ungeprueft_teil("kein Soll für dieses Teil im Bauprotokoll – Baum nicht verglichen")
    if ist_bestand is None:
        return ungeprueft_teil(f"Baum nicht lesbar ({lesefehler})")
    protokoll_teil, spec_teil = soll_t[name]
    return abgleich_teil(protokoll_teil, spec_teil, ist_bestand, auftrag)


def _lies_baum(app, model) -> tuple[dict | None, str | None]:
    """Aufnahme eines offenen Teils (swki.bestand.sw_bestand.lies_bestand, nur im Speicher); ein Lesefehler ist ein Befund, kein
    Abbruch."""
    from swki.bestand import sw_bestand  # spät importiert: sw_bestand zieht Bilder und Topologie nach

    try:
        return sw_bestand.lies_bestand(app, model), None
    except Exception as e:  # COM-Fehler beim Lesen → der Baum bleibt unerklärt, die Maße gelten weiter
        return None, f"{type(e).__name__}: {e}"


def oeffne_lauf(app, pfad: Path, ordner: Path):
    """Eine Datei des Laufs unsichtbar, schreibgeschützt und voll geladen über den Pfadschutz (Spec Bestandsdateien §8.1a):
    Sperre 1 vor dem Öffnen, Sperre 2 danach, und `lies_baugruppe` darf umschalten (`sperre_beim_umschalten` kennt das
    Dokument). Mit `oeffne` fiel der Baugruppen-Block still auf `ungeprueft_baugruppe`."""
    from swki.bestand.pfade import oeffne_in  # spät importiert: swki.bestand.ablage braucht dieses Modul

    return oeffne_in(app, pfad, ordner, sichtbar=False, nur_lesen=True)


def _baugruppe_block(app, model, spec_pfad: Path, lauf: int, protokoll: dict) -> dict:
    """Der Block `baugruppe` einer geöffneten Baugruppe (swki.bestand.abgleich.abgleich_baugruppe, nur im Speicher gelesen). Ein
    Lesefehler ist ein Befund, kein Abbruch: Die Maße gelten weiter, die Baugruppe bleibt unerklärt."""
    from swki.bestand import sw_baugruppe_bestand  # spät importiert: zieht die Mechanik nach
    from swki.bestand.abgleich import abgleich_baugruppe, ungeprueft_baugruppe  # spät importiert: abgleich braucht dieses Modul

    try:
        ist = sw_baugruppe_bestand.lies_baugruppe(app, model)
    except Exception as e:  # COM-Fehler beim Lesen
        return ungeprueft_baugruppe(f"Baugruppe nicht lesbar ({type(e).__name__}: {e})")
    return abgleich_baugruppe(protokoll, soll_verknuepfungen_lauf(spec_pfad, protokoll), ist, soll_lagen(spec_pfad, lauf))


def aenderungen(spec_pfad: Path, lauf: int | None = None) -> dict:
    """Geänderte Dateien eines Laufs mit Abweichungen von der Freigabe; öffnet SolidWorks nur bei geänderten
    .sldprt/.sldasm (unsichtbar und schreibgeschützt) und speichert nie. Ohne Lauf-Ordner oder ohne geänderte Datei wird nichts
    geöffnet und keine Freigabe gebraucht; Normteil-Kopien (ohne Soll) werden nur genannt.

    Je SW-Datei: parameter (Differenz zu den freigegebenen Parametern bzw. – im Baugruppendokument – Verknüpfungswerten),
    masse (geänderte oder fehlende Maße des Maßprotokolls) und vorschlaege (Spec-Änderungen, nur zu freigegebenen
    Parametern, siehe vorschlaege). Läufe mit Maßprotokoll lesen keine globalen Variablen: Teile vergleichen nur Maße,
    das Baugruppendokument nur Verknüpfungswerte; ältere Läufe vergleichen die globalen Variablen wie bisher.

    Je Teil kommt baum dazu (swki.bestand.abgleich.abgleich_teil: neue und fehlende Features, neue Maße, Material,
    Eigenschaften), je Baugruppe baugruppe (abgleich_baugruppe: Komponenten, Verknüpfungen, Lagen). „Datei geändert, Maße
    gleich“ steht nur noch da, wenn auch sie nichts erklären, dann mit nicht_erklaert: true. neu nennt SolidWorks-Dateien im
    Lauf-Ordner ohne Protokolleintrag. Hat der Lauf eine Bestandsaufnahme (Spec Bestandsdateien §8.5), öffnet aenderungen
    nichts: geaendert nennt die SHA-256, abgleich den Befehl swki bestand abgleich."""
    spec_pfad = spec_pfad.resolve()
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        letzter = letzter_gebauter_lauf(spec_pfad)
        if letzter is None:
            return {"spec": spec_pfad.name, "lauf": None, "geaendert": [], "fehlend": [],
                    "text": "kein durchgebauter Lauf mit Prüfsummen"}
        lauf, protokoll = letzter
    else:
        protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    ordner = lauf_ordner(r, auftrag, lauf)
    if not ordner.is_dir():
        return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": [], "fehlend": [],
                "text": f"Lauf-Ordner {ordner} fehlt (aufgeräumt) – nichts auszulesen"}
    soll_sha = protokoll.get("sha256", {})
    a = abweichungen(ordner, soll_sha)
    neu = neue_dateien(ordner, soll_sha)
    neu_feld = {"neu": neu} if neu else {}  # das Feld erscheint nur, wenn es etwas zu melden gibt
    if not a["geaendert"]:
        return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": [], "fehlend": a["fehlend"], **neu_feld}
    if art_der_datei(spec_pfad) == "aenderung":  # Bestandsdatei (Spec Bestandsdateien §6): kein Soll aus Parametern, nichts zu lesen
        return {"spec": spec_pfad.name, "lauf": lauf, "fehlend": a["fehlend"], **neu_feld, "text": _TEXT_AENDERUNG,
                "geaendert": [{"datei": n, "parameter": [], "hinweis": "Datei geändert (nicht ausgelesen)"} for n in a["geaendert"]]}
    aufnahmen = aufnahmen_des_laufs(r, auftrag, lauf)
    unlesbar = unlesbare_herkunft_des_rechners(r)
    if aufnahmen or unlesbar:  # Lauf = Original einer Aufnahme (§8.5), oder ob er es ist, ist unklar: nichts öffnen
        text = ("Der Lauf hat eine Bestandsaufnahme: swki öffnet ihn nicht in SolidWorks. Geändert ist laut SHA-256:" if aufnahmen else
                "Eine herkunft.json ist nicht lesbar (" + ", ".join(u["pfad"] for u in unlesbar) + "): Ob der Lauf aufgenommen wurde, "
                "ist unklar, darum öffnet swki ihn nicht in SolidWorks. Geändert ist laut SHA-256:")
        hinweis = ("Datei geändert (SHA-256) – Befund über swki bestand abgleich, siehe abgleich" if aufnahmen else
                   "Datei geändert (SHA-256) – herkunft.json prüfen, dann entscheiden")
        return {"spec": spec_pfad.name, "lauf": lauf, "fehlend": a["fehlend"], **neu_feld, "text": text,
                **({"aufnahmen": aufnahmen, "abgleich": _abgleich_befehl(aufnahmen[-1], spec_pfad)} if aufnahmen else {}),
                **({"unlesbar": unlesbar} if unlesbar else {}),
                "geaendert": [{"datei": n, "parameter": [], "sha256": {"soll": soll_sha[n], "ist": sha256_datei(ordner / n)},
                               "hinweis": hinweis} for n in a["geaendert"]]}
    soll = soll_parameter(spec_pfad, auftrag, standard)  # erst jetzt: braucht eine gültige Freigabe
    soll_m = soll_masse(protokoll, spec_pfad, auftrag, standard)
    ergebnis = []
    sw_dateien = [n for n in a["geaendert"] if n.lower().endswith(_SW_DATEIEN) and n in soll]
    if sw_dateien:
        soll_t = soll_teile(protokoll, spec_pfad, auftrag, standard) if any(n.lower().endswith(".sldprt") for n in sw_dateien) else {}
        app = verbinde(r.sw_jahr)
        for name in sw_dateien:
            massweg = name in soll_m  # Lauf mit Maßprotokoll: einzelne Maße, keine globalen Variablen
            ist_teil = name.lower().endswith(".sldprt")
            ist_bestand, lesefehler, block = None, None, None
            # unsichtbar, schreibgeschützt, voll geladen, nie gespeichert, über den Pfadschutz
            model = oeffne_lauf(app, ordner / name, ordner)
            try:
                ist = {} if massweg else lies_globale_variablen(model)
                if name.lower().endswith(".sldasm"):
                    from swki.baugruppe import sw_baugruppe  # spät importiert (Kreisimport)

                    ist |= {f"verknuepfung:{n}": w for n, w in sw_baugruppe.verknuepfungswerte(model).items()}
                    block = _baugruppe_block(app, model, spec_pfad, lauf, protokoll)
                ist_masse = lies_masse(model, soll_m[name]) if massweg else {}
                if ist_teil and name in soll_t:
                    ist_bestand, lesefehler = _lies_baum(app, model)
            finally:
                sw.schliesse(app, model)  # schließt ohne zu speichern (S9b)
            soll_p = soll[name]
            if massweg:  # Parameter ohne Variablen nicht lesbar; die Maße tragen sie. Bleiben: Verknüpfungswerte
                soll_p = {n: w for n, w in soll_p.items() if n.startswith("verknuepfung:")}
            differenz = parameter_differenz(soll_p, ist)
            masse_diff = mass_differenz(soll_m[name], ist_masse) if massweg else []
            eintrag = {"datei": name, "parameter": differenz, "masse": masse_diff,
                       "vorschlaege": vorschlaege(masse_diff, soll[name])}
            baum = baum_gegen_soll(name, soll_t, ist_bestand, lesefehler, auftrag) if ist_teil else None
            if baum is not None:
                eintrag["baum"] = baum
            if block is not None:
                eintrag["baugruppe"] = block
            gefunden = baum if baum is not None else block
            if not differenz and masse_diff and all(d["ist"] is None for d in masse_diff):
                namen = ", ".join(d["name"] for d in masse_diff)
                eintrag["hinweis"] = ((f"Maß {namen} fehlt" if len(masse_diff) == 1 else f"Maße {namen} fehlen")
                                      + " (Feature gelöscht?) – Nutzer fragen")
            elif not differenz and not masse_diff and (gefunden is None or gefunden["nicht_erklaert"]):
                gleich = (("Verknüpfungswerte gleich" if name.lower().endswith(".sldasm") else "Maße gleich")
                          if massweg else "Parameter gleich")
                wo = "Baum, Material und Eigenschaften" if baum is not None else "Komponenten, Verknüpfungen und Lagen"
                eintrag["hinweis"] = f"Datei geändert, {gleich}, nicht erklärt durch {wo} – den Nutzer fragen, was geändert wurde"
                eintrag["nicht_erklaert"] = True
            ergebnis.append(eintrag)
    for n in a["geaendert"]:
        if n in sw_dateien:
            continue
        hinweis = ("keine Spezifikation zu dieser Datei (Normteil- oder Kaufteil-Kopie)" if n.lower().endswith(_SW_DATEIEN)
                   else "Datei geändert (nicht ausgelesen)")
        ergebnis.append({"datei": n, "parameter": [], "hinweis": hinweis})
    return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": ergebnis, "fehlend": a["fehlend"], **neu_feld}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("aenderungen", help="manuelle Änderungen am letzten Lauf auslesen (nur lesend)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter durchgebauter Lauf")
    p.set_defaults(func=lambda a: aenderungen(Path(a.spec), a.lauf))
