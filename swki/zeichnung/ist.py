"""Ist-Modell der zurückgelesenen Zeichnung (Design §8.1). Werte in mm, Winkel in Grad, Koordinaten in Blatt-mm."""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class IstToleranz:
    typ: str  # keine | bilateral | grenz | symmetrisch | passung
    passung: str | None
    oben: float | None
    unten: float | None


@dataclass(frozen=True)
class IstMass:
    name: str
    ansicht: str
    art: str  # laenge | durchmesser | radius | winkel
    wert: float
    praefix: str
    suffix: str
    klammer: bool
    toleranz: IstToleranz
    richtung: str | None  # "h" | "v", nur bei laenge
    punkte: tuple[tuple[float, float], tuple[float, float]] | None  # zwei Bezugspunkte
    verdeckt: bool | None  # None: nicht ermittelbar


@dataclass(frozen=True)
class IstAngabe:
    art: str  # hinweis | rauheit | form_lage | bezug
    ansicht: str
    text: str
    symbol: str | None
    wert: str | None
    bezug: tuple[str, ...]


@dataclass(frozen=True)
class IstAnsicht:
    name: str
    rolle: str | None
    art: str  # ansicht | schnitt | einzelheit
    massstab: str
    beschriftung: str | None


@dataclass(frozen=True)
class Ist:
    format_: str
    massstab: str
    ansichten: tuple[IstAnsicht, ...]
    masse: tuple[IstMass, ...]
    angaben: tuple[IstAngabe, ...]
    eigenschaften: dict[str, str] = field(default_factory=dict)
    sha256_slddrw: str = ""


def ist_zu_dict(ist: Ist) -> dict:
    """Verschachteltes dict (asdict behält Tupel; erst json.dumps macht Listen daraus, ist_aus_dict nimmt beides)."""
    return asdict(ist)


def _mass(d: dict) -> IstMass:
    punkte = d["punkte"]
    return IstMass(**{**d, "toleranz": IstToleranz(**d["toleranz"]),
                      "punkte": None if punkte is None else tuple(tuple(p) for p in punkte)})


def ist_aus_dict(d: dict) -> Ist:
    return Ist(
        format_=d["format_"], massstab=d["massstab"],
        ansichten=tuple(IstAnsicht(**a) for a in d["ansichten"]),
        masse=tuple(_mass(m) for m in d["masse"]),
        angaben=tuple(IstAngabe(**{**a, "bezug": tuple(a["bezug"])}) for a in d["angaben"]),
        eigenschaften=dict(d["eigenschaften"]), sha256_slddrw=d["sha256_slddrw"],
    )
