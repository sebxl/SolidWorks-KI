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


def basis(instanz_id: str) -> str:
    """Komponenten-ID einer Instanz: "schraube.2" → "schraube"."""
    return instanz_id.split(".")[0]


def je_position(spec: dict, kid: str) -> dict | None:
    return next((k.get("je_position") for k in spec["komponenten"] if k["id"] == kid), None)


def anzahl_positionen(spec: dict, quellen: dict[str, Quelle], kid: str) -> int:
    je = je_position(spec, kid)
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
    """Vorgabe true bei konzentrisch mit einem Normteil (Spec 3b §4.4), sonst false; ausdrücklich angegeben gilt."""
    if "drehung_sperren" in v:
        return v["drehung_sperren"]
    return v["typ"] == "konzentrisch" and any(quellen[v[s]["komponente"]].art == "normteil" for s in ("a", "b"))


def _setze(seite: dict, je: set[str], i: int) -> dict:
    neu = dict(seite)
    if neu["komponente"] in je:
        neu["komponente"] = f"{neu['komponente']}.{i}"
    if neu.get("instanz") == "je":
        neu["instanz"] = i
    return neu


def verknuepfungen(spec: dict, quellen: dict[str, Quelle]) -> list[Verknuepfung]:
    ergebnis = []
    for v in spec.get("verknuepfungen", []):
        je = {v[s]["komponente"] for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
        sperren = _drehung_sperren(v, quellen)
        if not je:
            ergebnis.append(Verknuepfung(v["id"], v["id"], v["typ"], dict(v["a"]), dict(v["b"]), v.get("ausrichtung"),
                                         v.get("wert"), sperren))
            continue
        for i in range(1, anzahl_positionen(spec, quellen, next(iter(je))) + 1):
            ergebnis.append(Verknuepfung(f"{v['id']}.{i}", v["id"], v["typ"], _setze(v["a"], je, i), _setze(v["b"], je, i),
                                         v.get("ausrichtung"), v.get("wert"), sperren))
    return ergebnis
