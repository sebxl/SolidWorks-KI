"""Neue Features der Punkte gegen die freigegebene Kopie (Spec Bestandsdateien §7.1): Was beim Teil `normbohrungen`, `verzahnungen` und
`formschraegen` prüfen, steckt hier in `punkt:<id>`, je Konfiguration. Sonst belegte der Eintrag nur, dass das Feature da ist; ein
Gewinde sieht man weder in der Differenz noch im Bild (Prüfer, Referenz Lauf 1).

Reine Logik über Messwerte, ohne SolidWorks; gemessen wird in `swki.bestand.pruefen`. Die Bausteine des Teils bleiben dieselben, nur
heißt ein Feature hier wie sein `name`, nicht wie seine ID (`teil_spec`). Dazu die Achsen einer Normbohrung gegen `positionen`, bei
einem Teil belegt das `masse_pruefen`, das Änderungs-Schema kennt aber keinen Messpunkt auf einer Bohrungsachse.

Andere Feature-Typen haben hier kein Soll: `messart` liefert `None`, `punkt:<id>` nennt das (`nicht_gemessen`)."""

from swki.compiler.anker import laenge
from swki.compiler.fehler import BauFehler
from swki.compiler.skizze import orientierung_der_normale
from swki.formschraege import schraege
from swki.kaufteile.bewertung import TOL_MASS
from swki.pruefung.bewertung import formschraege_abweichungen, normbohrung_abweichungen, verzahnung_abweichungen
from swki.spec.ausdruck import auswerten
from swki.spec.normen import groesse_text, norm_von, normmasse

_GENAUIGKEIT = 6  # Stellen; Achsen aus zwei Halbzylindern fallen damit zusammen


def messart(f: dict) -> str | None:
    """Wogegen ein Feature-Inhalt gemessen wird, `None`: Der Typ hat hier kein Soll."""
    if f.get("typ") in ("normbohrung", "verzahnung"):
        return f["typ"]
    return "formschraege" if schraege(f) is not None else None


def nicht_gemessen(f: dict) -> str:
    return f"Typ {f.get('typ')}: Maße nicht gemessen, belegt sind nur Vorhandensein, Lage im Baum, Bereich und Differenz"


def feature_punkte(spec: dict) -> list[dict]:
    return [p for p in spec["punkte"] if p["typ"] == "feature"]


def teil_spec(spec: dict) -> dict:
    """Die `feature`-Punkte als Teil-Spec für die Messbausteine: `id` ist der Name im Baum."""
    return {"parameter": spec.get("parameter", {}), "features": [{**p["feature"], "id": p["name"]} for p in feature_punkte(spec)]}


def _uv(punkt: tuple, orientierung: str) -> tuple[float, float]:
    """Umkehrung von `swki.compiler.skizze.modellpunkt`."""
    x, y, z = punkt
    return {"vorne": (x, y), "oben": (x, -z), "rechts": (-z, y)}[orientierung]


def _achsen_uv(achsen: list) -> list[list[float]]:
    """Je Achse einmal, in Skizzenkoordinaten: Ein Zylinder zerfällt oft in zwei Flächen, eine Senkung ist koaxial."""
    aus: list[list[float]] = []
    for punkt, achse in achsen:
        n = laenge(achse)
        uv = [round(c, _GENAUIGKEIT) for c in _uv(punkt, orientierung_der_normale(tuple(c / n for c in achse)))]
        if not any(max(abs(uv[0] - q[0]), abs(uv[1] - q[1])) < TOL_MASS / 10 for q in aus):
            aus.append(uv)
    return aus


def _abstand(a: list[float], b: list[float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def achsen_abweichungen(soll: list[list[float]], ist: list[list[float]]) -> list[str]:
    """Jede Position braucht eine Achse, jede Achse eine Position."""
    if not ist:
        return ["keine Bohrungsachse gefunden"]
    fehler = [f"Position [{u:g}, {v:g}]: keine Achse (nächste [{q[0]:g}, {q[1]:g}])"
              for u, v in soll if _abstand([u, v], q := min(ist, key=lambda x: _abstand(x, [u, v]))) > TOL_MASS]
    return fehler + [f"Achse [{u:g}, {v:g}] steht in keiner Position" for u, v in ist if all(_abstand([u, v], s) > TOL_MASS for s in soll)]


def _normbohrung_soll(f: dict, p: dict) -> dict:
    masse = normmasse(f["art"], f["groesse"], norm_von(f)) or {}
    return {"art": f["art"], "groesse": masse.get("sw_groesse", groesse_text(f["groesse"])),
            **{feld: auswerten(f[feld], p) for feld in ("tiefe", "gewindetiefe") if feld in f},
            "positionen": [[auswerten(u, p), auswerten(v, p)] for u, v in f["positionen"]]}


def _normbohrung(f: dict, ist: dict, p: dict, soll: dict) -> tuple[dict, list[str]]:
    wert = {k: ist.get(k) for k in ("groesse", "tiefe", "gewindetiefe")}
    fehler = normbohrung_abweichungen(f, ist, p)
    if isinstance(ist["achsen"], str):
        return {**wert, "positionen": ist["achsen"]}, [*fehler, ist["achsen"]]
    try:
        achsen = _achsen_uv(ist["achsen"])
    except BauFehler as e:
        return {**wert, "positionen": str(e)}, [*fehler, str(e)]
    return {**wert, "positionen": achsen}, fehler + achsen_abweichungen(soll["positionen"], achsen)


def _soll(art: str, f: dict, p: dict) -> dict:
    if art == "normbohrung":
        return _normbohrung_soll(f, p)
    if art == "verzahnung":
        return {"art": f["art"], "modul": auswerten(f["modul"], p), "zaehne": auswerten(f["zaehne"], p)}
    s = schraege(f)
    return {"winkel": auswerten(s["winkel"], p), "querschnitt": s["querschnitt"]}


def _vergleiche(art: str, f: dict, ist: dict, p: dict, soll: dict, toleranzen: dict) -> tuple:
    """(Messwert für den Bericht, Abweichungen)."""
    if art == "normbohrung":
        return _normbohrung(f, ist, p, soll)
    if art == "verzahnung":
        return ist, verzahnung_abweichungen(f, ist, p, toleranzen["verzahnung_mm"])
    return sorted({round(x["winkel"], 3) for x in ist["flaechen"]}), formschraege_abweichungen(f, ist, p, toleranzen["winkel_grad"])


def bewerte(spec: dict, gemessen: dict[str, dict], toleranzen: dict) -> dict[str, dict]:
    """Punkt-ID → `{"ist": {Konfiguration: Wert}, "soll": {...}, "fehler": [...]}`, nur für messbare Features. `spec`: die freigegebene
    Kopie. `gemessen`: Konfiguration → Featurename → Messwerte oder Fehlertext; was fehlt, ist ein Fehler, nie ein stilles Bestanden."""
    p, aus = spec.get("parameter", {}), {}
    for punkt, f in zip(feature_punkte(spec), teil_spec(spec)["features"]):
        if (art := messart(f)) is None:
            continue
        soll, ist, fehler = _soll(art, f, p), {}, [] if gemessen else ["nicht gemessen"]
        for k, werte in gemessen.items():
            wert = werte.get(punkt["name"], "nicht gemessen")
            if isinstance(wert, dict):
                ist[k], abweichungen = _vergleiche(art, f, wert, p, soll, toleranzen)
            else:
                ist[k], abweichungen = wert, [wert]
            fehler += [f"{k}: {t}" for t in abweichungen]
        aus[punkt["id"]] = {"ist": ist, "soll": soll, "fehler": fehler}
    return aus
