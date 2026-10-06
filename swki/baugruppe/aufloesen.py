"""je_position auflösen (Spec 3b §4.2): Instanzen der Komponenten und vervielfältigte Verknüpfungen.

Setzt eine plausible Spezifikation voraus (swki.baugruppe.plausibel prüft vorher)."""

from dataclasses import dataclass

from swki.baugruppe.modell import Quelle


@dataclass(frozen=True)
class Instanz:
    id: str               # "platte" bzw. "schraube.2"
    komponente: str       # Komponenten-ID der Spezifikation
    position: int | None  # Position im Feature von je_position (1 …), sonst None


@dataclass(frozen=True)
class Verknuepfung:
    id: str                 # "v1" bzw. "v4.2"
    vorlage: str            # ID in der Spezifikation
    typ: str
    a: dict                 # Referenz mit komponente = Instanz-ID und konkreter instanz
    b: dict
    ausrichtung: str | None
    wert: object            # Zahl, "=Ausdruck" oder None
    drehung_sperren: bool
    min: object = None      # grenze_abstand/grenze_winkel: Zahl oder "=Ausdruck" (mm bzw. Grad)
    max: object = None


def basis(instanz_id: str) -> str:
    """Komponenten-ID einer Instanz: "schraube.2" → "schraube"."""
    return instanz_id.split(".")[0]


GRENZEN = ("grenze_abstand", "grenze_winkel")
ANLAGE = ".anlage"  # Endung der zweiten SolidWorks-Verknüpfung eines Scharniers (Präzisierung 1)


def je_position(spec: dict, kid: str) -> dict | None:
    return next((k.get("je_position") for k in spec["komponenten"] if k["id"] == kid), None)


def anzahl_positionen(spec: dict, quellen: dict[str, Quelle], kid: str) -> int:
    """Positionen des je_position: Bohrungs-Feature eines Eigenteils oder Gewindegruppe eines Kaufteils (Spec 3c §8.1)."""
    je = je_position(spec, kid)
    if "gewinde" in je:
        return len(quellen[je["komponente"]].spec["gewinde"][je["gewinde"]]["positionen"])
    feature = next(f for f in quellen[je["komponente"]].spec["features"] if f["id"] == je["feature"])
    return len(feature["positionen"])


def instanzen(spec: dict, quellen: dict[str, Quelle]) -> list[Instanz]:
    ergebnis = []
    for k in spec["komponenten"]:
        if k.get("je_position"):
            n = anzahl_positionen(spec, quellen, k["id"])
            ergebnis += [Instanz(f"{k['id']}.{i}", k["id"], i) for i in range(1, n + 1)]
        else:
            ergebnis.append(Instanz(k["id"], k["id"], None))
    return ergebnis


def _drehung_sperren(v: dict, quellen: dict[str, Quelle]) -> bool:
    """Vorgabe true bei konzentrisch mit einem Norm- oder Kaufteil (Spec 3b §4.4, 3c §8.1), sonst false; ausdrücklich
    angegeben gilt."""
    if "drehung_sperren" in v:
        return v["drehung_sperren"]
    return v["typ"] == "konzentrisch" and any(quellen[basis(v[s]["komponente"])].art in ("normteil", "kaufteil")
                                              for s in ("a", "b"))


def _setze(seite: dict, je: set[str], i: int) -> dict:
    neu = dict(seite)
    if neu["komponente"] in je:
        neu["komponente"] = f"{neu['komponente']}.{i}"
    if neu.get("instanz") == "je":
        neu["instanz"] = i
    return neu


def _einzeln(v: dict, vid: str, a: dict, b: dict, quellen: dict[str, Quelle], anlage_a: dict | None,
             anlage_b: dict | None) -> list[Verknuepfung]:
    """Eine Verknüpfung der Spezifikation als SolidWorks-Verknüpfungen. Ein Scharnier wird zu konzentrisch (ohne
    Drehsperre, die Drehung bleibt frei) und deckungsgleich der Anlageflächen (Präzisierung 1)."""
    if v["typ"] == "scharnier":
        return [Verknuepfung(vid, v["id"], "konzentrisch", a, b, None, None, False),
                Verknuepfung(f"{vid}{ANLAGE}", v["id"], "deckungsgleich", anlage_a, anlage_b,
                             v.get("ausrichtung", "entgegengesetzt"), None, False)]
    return [Verknuepfung(vid, v["id"], v["typ"], a, b, v.get("ausrichtung"), v.get("wert"), _drehung_sperren(v, quellen),
                         v.get("min"), v.get("max"))]


def verknuepfungen(spec: dict, quellen: dict[str, Quelle]) -> list[Verknuepfung]:
    """Aufgelöste Verknüpfungen in Spec-Reihenfolge; je_position vervielfältigt (Grenzen und Scharniere nennen keine
    Komponente mit je_position, das prüft swki.baugruppe.plausibel)."""
    ergebnis = []
    for v in spec.get("verknuepfungen", []):
        je = {v[s]["komponente"] for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
        if not je:
            ergebnis += _einzeln(v, v["id"], dict(v["a"]), dict(v["b"]), quellen,
                                 dict(v["anlage_a"]) if "anlage_a" in v else None,
                                 dict(v["anlage_b"]) if "anlage_b" in v else None)
            continue
        for i in range(1, anzahl_positionen(spec, quellen, next(iter(je))) + 1):
            ergebnis += _einzeln(v, f"{v['id']}.{i}", _setze(v["a"], je, i), _setze(v["b"], je, i), quellen, None, None)
    return ergebnis
