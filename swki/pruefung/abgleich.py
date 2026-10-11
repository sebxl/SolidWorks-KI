"""Abgleich der freigegebenen Spezifikation mit dem Merkmalsbericht der STEP (Prüfung `merkmale` in swki pruefen).

Ersetzt den Blick des Prüfers auf die Screenshots für die Fragen „ist jedes Feature gebaut?“ und „sitzt es auf der
richtigen Seite?“: Jede Bohrung, Normbohrung und jeder Kreis einer Extrusion bzw. eines Schnitts wird mit Achse, Lage
(aus den (u, v)-Positionen, Zuordnung wie im Skill: vorne X=u, Y=v · oben X=u, Z=−v · rechts Z=−u, Y=v), Ø, durch/blind,
Eintrittsseite, Tiefe und Senkung gesucht; Muster und Spiegelungen werden aufgelöst. Verrundungen und Fasen werden auf
Vorhandensein geprüft (Radius bzw. Winkel). Unerwartete Bohrungen sind ein Mangel, wenn alle Features abgebildet sind,
sonst nur ein Hinweis. Was der Abgleich nicht abbildet, steht unter `nicht_geprueft` (kein Mangel).
"""

import math

from swki.formschraege import schraege
from swki.pruefung.huellquader import profil_umriss
from swki.pruefung.merkmale import ACHSEN, bohrung_von
from swki.spec.ausdruck import auswerten

TOL_LAGE = 0.05    # mm
TOL_D = 0.02       # mm
TOL_TIEFE = 0.05   # mm
TOL_WINKEL = 0.1   # Grad

_ACHSE_DER_EBENE = {"vorne": "Z", "oben": "Y", "rechts": "X"}
_BEKANNT = {"extrusion", "schnitt", "bohrung", "normbohrung", "verrundung", "fase", "muster_linear", "muster_kreis",
            "spiegeln", "referenz"}


def _mitte(achse: str, u: float, v: float) -> dict:
    if achse == "Y":
        return {"X": u, "Z": -v}
    if achse == "Z":
        return {"X": u, "Y": v}
    return {"Y": v, "Z": -u}


def _z(v: float) -> str:
    t = f"{v:.2f}".rstrip("0").rstrip(".")
    return ("0" if t in ("-0", "") else t).replace(".", ",")


def _lage_text(mitte: dict) -> str:
    return "(" + " | ".join(f"{k} {_z(v)}" for k, v in mitte.items()) + ")"


class _Abgleich:
    def __init__(self, soll: dict, m: dict):
        self.spec, self.m = soll, m
        self.p = soll.get("parameter", {})
        self.erwartet: dict[str, list[dict]] = {}
        self.nicht_geprueft: list[str] = []
        self.abweichend: dict[str, list[str]] = {}

    def w(self, wert) -> float:
        return auswerten(wert, self.p)

    # --- Anker -------------------------------------------------------------------------------------------------------

    def _flaeche_nahe(self, punkt) -> tuple[str, str] | None:
        p = [self.w(c) for c in punkt]
        for name, hoehen in self.m["ebenen"].items():
            i = ACHSEN.index(name[1])
            for e in hoehen:
                if abs(e["hoehe"] - p[i]) <= TOL_LAGE and all(
                        b[0] - TOL_LAGE <= p[ACHSEN.index(k)] <= b[1] + TOL_LAGE for k, b in e["bereich"].items()):
                    return name[1], name[0]
        return None

    def anker(self, anker: dict) -> tuple[str, str] | None:
        """(Achse, Eintrittsseite) einer Fläche {feature, flaeche} oder {nahe}."""
        if "feature" in anker:
            return anker["flaeche"][1].upper(), anker["flaeche"][0]
        return self._flaeche_nahe(anker["nahe"])

    def skizzenachse(self, ebene) -> str | None:
        if isinstance(ebene, str):
            return _ACHSE_DER_EBENE.get(ebene)
        if "versatz" in ebene:
            return self.skizzenachse(ebene["versatz"]["ebene"])
        gefunden = self.anker(ebene)
        return gefunden[0] if gefunden else None

    # --- Erwartungen -------------------------------------------------------------------------------------------------

    def _bohrung(self, f: dict) -> None:
        lage = self.anker(f["flaeche"])
        if lage is None:
            self.nicht_geprueft.append(f"{f['id']}: Fläche über nahe nicht gefunden")
            return
        achse, eintritt = lage
        basis = {"knoten": [f["id"]], "art": f["typ"], "achse": achse, "eintritt": eintritt,
                 "durch": bool(f.get("durch"))}
        if f["typ"] == "bohrung":
            basis["d"] = self.w(f["durchmesser"])
            if "tiefe" in f:
                basis["tiefe"] = self.w(f["tiefe"])
            if "senkung" in f:
                basis["senkung"] = (self.w(f["senkung"]["durchmesser"]), self.w(f["senkung"]["tiefe"]))
        self.erwartet[f["id"]] = [{**basis, "mitte": _mitte(achse, self.w(u), self.w(v))} for u, v in f["positionen"]]

    def _kreise(self, f: dict) -> None:
        if schraege(f) is not None:
            self.nicht_geprueft.append(f"{f['id']}: Formschräge (Prüfung formschraegen)")
            return
        elemente = f["skizze"]["elemente"]
        kreise = [e for e in elemente if "kreis" in e]
        if any("kontur" in e for e in elemente):
            self.nicht_geprueft.append(f"{f['id']}: Kontur")
        if not kreise:
            return
        achse = self.skizzenachse(f["skizze"]["ebene"])
        if achse is None:
            self.nicht_geprueft.append(f"{f['id']}: Skizzenebene über nahe nicht gefunden")
            return
        umrisse = [(e, profil_umriss(e, self.p)) for e in elemente]
        liste = []
        for k in kreise:
            u0, v0, u1, v1 = profil_umriss(k, self.p)
            innen = sum(1 for e, b in umrisse if e is not k and b is not None and b[0] <= u0 and b[1] <= v0
                        and b[2] >= u1 and b[3] >= v1) % 2 == 1
            loch = innen if f["typ"] == "extrusion" else not innen
            mitte = _mitte(achse, self.w(k["kreis"]["mitte"][0]), self.w(k["kreis"]["mitte"][1]))
            liste.append({"knoten": [f["id"]], "art": "kreis_innen" if loch else "zapfen", "achse": achse,
                          "mitte": mitte, "d": self.w(k["kreis"]["durchmesser"])})
        self.erwartet[f["id"]] = liste

    def _muster(self, f: dict) -> None:
        quellen = [e for fid in f["features"] for e in self.erwartet.get(fid, [])]
        neu = []
        if f["typ"] == "muster_linear":
            r1, r2 = f["richtung1"], f.get("richtung2")
            kombis = [(i, j) for i in range(r1["anzahl"]) for j in range(r2["anzahl"] if r2 else 1)]
            for e in quellen:
                for i, j in kombis:
                    if i == j == 0:
                        continue
                    kopie = dict(e, mitte=dict(e["mitte"]), knoten=e["knoten"] + [f["id"]])
                    for r, n in ((r1, i), (r2, j)):
                        if not r or n == 0:
                            continue
                        k = r["achse"].upper()
                        weg = n * self.w(r["abstand"]) * (-1 if r.get("umkehren") else 1)
                        if k == e["achse"]:
                            self.nicht_geprueft.append(f"{f['id']}: Muster entlang der Bohrungsachse")
                            break
                        kopie["mitte"][k] += weg
                    else:
                        neu.append(kopie)
        elif f["typ"] == "spiegeln":
            if not isinstance(f["ebene"], str) or f["ebene"] not in _ACHSE_DER_EBENE:
                self.nicht_geprueft.append(f"{f['id']}: Spiegelebene keine Standardebene")
                return
            k = _ACHSE_DER_EBENE[f["ebene"]]
            for e in quellen:
                kopie = dict(e, mitte=dict(e["mitte"]), knoten=e["knoten"] + [f["id"]])
                if k == e["achse"]:
                    if "eintritt" in e:
                        kopie["eintritt"] = "-" if e["eintritt"] == "+" else "+"
                else:
                    kopie["mitte"][k] = -kopie["mitte"][k]
                neu.append(kopie)
        else:   # muster_kreis um die Modellachse durch den Ursprung, gleichmäßig verteilt
            gesamt = self.w(f["winkel"]) if "winkel" in f else 360.0
            if abs(gesamt - 360) > 1e-6:
                self.nicht_geprueft.append(f"{f['id']}: Kreismuster mit Gesamtwinkel {_z(gesamt)}°")
                return
            k = f["achse"].upper()
            for e in quellen:
                if e["achse"] != k:
                    self.nicht_geprueft.append(f"{f['id']}: Kreismuster quer zur Achse von {e['knoten'][0]}")
                    continue
                a, b = [ACHSEN[i] for i in range(3) if ACHSEN[i] != k]
                if k == "Y":   # rechtshändig um Y: Z → X
                    a, b = b, a
                for n in range(1, f["anzahl"]):
                    t = math.radians(360 * n / f["anzahl"])
                    x, y = e["mitte"][a], e["mitte"][b]
                    neu.append(dict(e, knoten=e["knoten"] + [f["id"]],
                                    mitte={a: x * math.cos(t) - y * math.sin(t), b: x * math.sin(t) + y * math.cos(t)}))
        self.erwartet[f["id"]] = neu

    def erwartungen(self) -> None:
        for f in self.spec["features"]:
            typ = f["typ"]
            if typ not in _BEKANNT:
                self.nicht_geprueft.append(f"{f['id']}: Typ {typ}")
            elif typ in ("bohrung", "normbohrung"):
                self._bohrung(f)
            elif typ in ("extrusion", "schnitt"):
                self._kreise(f)
            elif typ in ("muster_linear", "muster_kreis", "spiegeln"):
                self._muster(f)

    # --- Suchen ------------------------------------------------------------------------------------------------------

    def _gleiche_lage(self, merkmal_mitte: dict, mitte: dict) -> bool:
        return all(abs(merkmal_mitte.get(k, math.inf) - v) <= TOL_LAGE for k, v in mitte.items())

    def _rundung_auf_linie(self, e: dict, art: str) -> bool:
        return any(r.get("achse") == e["achse"] and r["art"] == art and abs(2 * r["r"] - e["d"]) <= TOL_D
                   and "mitte" in r and self._gleiche_lage(r["mitte"], e["mitte"]) for r in self.m["rundungen"])

    def _melde(self, e: dict, text: str) -> None:
        self.abweichend.setdefault(e["knoten"][0], []).append(text)

    def _pruefe_bohrung(self, e: dict, b: dict) -> None:
        lage = _lage_text(e["mitte"])
        zyl = [t["d"] for t in b["abschnitte"] if t["art"] == "zylinder"]
        if "d" in e and not any(abs(d - e["d"]) <= TOL_D for d in zyl):
            self._melde(e, f"Bohrung {lage}: Ø {', '.join(_z(d) for d in zyl) or '–'} statt {_z(e['d'])}")
        if e["art"] == "kreis_innen":
            return
        offen = [s for s, ende in b["enden"].items() if ende == "offen"]
        if e["durch"]:
            if not b["durch"]:
                self._melde(e, f"Bohrung {lage}: blind statt durch (Enden {b['enden']['-']}/{b['enden']['+']})")
        elif b["durch"]:
            self._melde(e, f"Bohrung {lage}: durch statt blind")
        elif e["eintritt"] not in offen:
            von = f"{offen[0]}{e['achse']}" if offen else "keiner Seite"
            self._melde(e, f"Bohrung {lage}: offen von {von} statt von {e['eintritt']}{e['achse']} (Seite vertauscht?)")
            return
        sicht = bohrung_von(b, e["eintritt"])
        if "tiefe" in e and not b["durch"] and abs(sicht["tiefe"] - e["tiefe"]) > TOL_TIEFE:
            self._melde(e, f"Bohrung {lage}: Tiefe {_z(sicht['tiefe'])} statt {_z(e['tiefe'])}")
        if "senkung" in e:
            d, t = e["senkung"]
            erste = sicht["zylinder"][0] if sicht["zylinder"] else None
            if erste is None or abs(erste["d"] - d) > TOL_D or abs(erste["laenge"] - t) > TOL_TIEFE:
                ist = f"Ø {_z(erste['d'])} × {_z(erste['laenge'])}" if erste else "keine"
                self._melde(e, f"Bohrung {lage}: Senkung {ist} statt Ø {_z(d)} × {_z(t)} von {e['eintritt']}{e['achse']}")

    def _naechste(self, e: dict) -> str:
        kandidaten = [b for b in self.m["bohrungen"] if b["achse"] == e["achse"] and "mitte" in b]
        if not kandidaten:
            return f"keine Bohrung mit Achse {e['achse']} im Teil"
        b = min(kandidaten, key=lambda b: math.dist([b["mitte"][k] for k in e["mitte"]], list(e["mitte"].values())))
        return f"nächste Bohrung mit Achse {e['achse']} bei {_lage_text(b['mitte'])}"

    def suchen(self) -> list[dict]:
        benutzt: set[int] = set()
        for liste in self.erwartet.values():
            for e in liste:
                if e["art"] == "zapfen":
                    if not any(z["achse"] == e["achse"] and abs(z["d"] - e["d"]) <= TOL_D
                               and self._gleiche_lage(z["mitte"], e["mitte"]) for z in self.m["zapfen"]) \
                            and not self._rundung_auf_linie(e, "konvex"):
                        self._melde(e, f"Zapfen Ø {_z(e['d'])} Achse {e['achse']} bei {_lage_text(e['mitte'])} fehlt")
                    continue
                treffer = [i for i, b in enumerate(self.m["bohrungen"])
                           if b["achse"] == e["achse"] and "mitte" in b and self._gleiche_lage(b["mitte"], e["mitte"])]
                if not treffer:
                    if e["art"] == "kreis_innen" and self._rundung_auf_linie(e, "konkav"):
                        continue
                    self._melde(e, f"keine Bohrung mit Achse {e['achse']} bei {_lage_text(e['mitte'])} "
                                   f"({self._naechste(e)})")
                    continue
                benutzt.update(treffer)
                self._pruefe_bohrung(e, self.m["bohrungen"][treffer[0]])
        return [b for i, b in enumerate(self.m["bohrungen"]) if i not in benutzt]

    def kanten(self) -> None:
        kegel_halb = [k["winkel"] / 2 for k in self.m["kegel"]] + [
            t["winkel"] / 2 for b in self.m["bohrungen"] for t in b["abschnitte"] if t["art"] == "kegel"]
        for f in self.spec["features"]:
            if f["typ"] == "verrundung":
                r = self.w(f["radius"])
                if not any(abs(x["r"] - r) <= TOL_D for x in self.m["rundungen"]):
                    self.abweichend.setdefault(f["id"], []).append(f"keine Rundung R {_z(r)} im Teil")
            elif f["typ"] == "fase":
                w = self.w(f.get("winkel", 45))
                ziel = min(w, 90 - w)
                if not (any(abs(s["winkel"] - ziel) <= TOL_WINKEL for s in self.m["schraege"])
                        or any(min(abs(h - w), abs(h - (90 - w))) <= TOL_WINKEL for h in kegel_halb)):
                    self.abweichend.setdefault(f["id"], []).append(f"keine Fasenfläche mit {_z(w)}° im Teil")


def abgleich(soll: dict, m: dict) -> dict:
    """Prüfungseintrag `merkmale` (Form wie bewertung.eintrag) aus freigegebener Spec und Merkmalsbericht."""
    a = _Abgleich(soll, m)
    a.erwartungen()
    unerwartet = a.suchen()
    a.kanten()
    if m["koerper"] != 1:
        a.nicht_geprueft.append(f"{m['koerper']} Volumenkörper (Prüfung koerper)")
    a.nicht_geprueft = list(dict.fromkeys(a.nicht_geprueft))
    streng = not a.nicht_geprueft
    lagen = [f"{b['achse']} {_lage_text(b['mitte']) if 'mitte' in b else b.get('linie')}" for b in unerwartet]
    ok = not a.abweichend and not (streng and unerwartet)
    erg = {"id": "merkmale", "ok": ok, "ist": a.abweichend,
           "geprueft": sum(len(v) for v in a.erwartet.values()), "knoten": sorted(a.abweichend)}
    if unerwartet:
        erg["unerwartet"] = lagen
        if streng:
            erg["hinweis"] = "Bohrung ohne Feature in der Spezifikation: " + ", ".join(lagen)
    if a.nicht_geprueft:
        erg["nicht_geprueft"] = a.nicht_geprueft
    if a.abweichend:
        erg["hinweis"] = "; ".join(t for v in a.abweichend.values() for t in v) + (
            f"; {erg['hinweis']}" if "hinweis" in erg else "")
    return erg
