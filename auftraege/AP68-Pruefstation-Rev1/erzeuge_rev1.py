"""Erzeugt auftraege/AP68-Pruefstation-Rev1/pruefstation_rev1.yaml (Änderungs-Spec Runde 1) aus einer Tabelle.
Wiederholte Punkte (Stifte, Schrauben, Verknüpfungen) stehen hier als Schleifen, damit keine Instanz verrutscht."""
import json
import sys
from pathlib import Path

ZIEL = Path(sys.argv[1])
AP, AW, KT = "AP68-Pruefstation_Anschlussplatte.SLDPRT", "AP68-Pruefstation_Anschlusswinkel.SLDPRT", "AP68-Pruefstation_Kanaltraeger.SLDPRT"
KS, KH, TS = "AP68-Pruefstation_Kamerasaeule.SLDPRT", "AP68-Pruefstation_Kamerahalter.SLDPRT", "AP68-Pruefstation_Trichtersaeule.SLDPRT"
ZA, TR, FS = "AP68-Pruefstation_Zylinderaufnahme.SLDPRT", "AP68-Pruefstation_Trichter.SLDPRT", "AP68-Pruefstation_Fallschacht.SLDPRT"
RU, WK, PK = "AP68-Pruefstation_Rutsche.SLDPRT", "AP68-Pruefstation_Weichenkeil.SLDPRT", "AP68-Pruefstation_Pruefkanal.SLDPRT"
DL = "AP68-Pruefstation_Durchlichtlasche.SLDPRT"
C = lambda n: f"AP68-Pruefstation_{n}-1"          # Komponentenname der Eigenteile
S = lambda n, i: f"ISO4762_{n}_8_8-{i}"           # Komponentenname der Bestandsschrauben
PLATTE = C("Anschlussplatte")

def j(x):
    return json.dumps(x, ensure_ascii=False)

zeilen = []
def kommentar(t):
    zeilen.append(f"  # --- {t}")
def punkt(**p):
    zeilen.append("  - " + j(p))

# ------------------------------------------------------------------ Anschlussplatte
kommentar("Anschlussplatte: 33 näher an den Kanal (Nutzer: Licht drehen, Abstand verringern)")
punkt(id="ap1", was="Anschlussplatte 33 mm nach +X (Vorderseite X −212 statt −245)", typ="mass", in_datei=AP,
      mass="D1@Ebene1", alt=257, neu="=257-NAEHER")
# Die kosmetischen Gewinde der beiden M5 verschwinden mit ihren Positionen (Lauf 1: Bestandsfeature fehlt); sie gehören zu den
# alten Gewinden, die der Nutzer entfernt haben will, und werden vor dem Skript gelöscht.
for i, g in enumerate(("Bohrungsgewinde13", "Bohrungsgewinde14"), 1):
    punkt(id=f"ag{i}", was="Kosmetisches Gewinde einer der beiden entfallenden M5 (Kanalträger)", typ="loeschen", in_datei=AP,
          feature=g)
punkt(id="ap2", was="Die beiden Gewinde M5 für den Kanalträger (Y 293,75 / 368,75, Z −160) entfallen", typ="skript", in_datei=AP,
      datei="skripte/ap_gewinde_weg.py", luecke="Einzelne Positionen einer fremden Bohrungsassistent-Bohrung löschen")
punkt(id="ap3", was="Dort Durchgang mit Flachsenkung für M5 von hinten in den Kanalträger", typ="feature", in_datei=AP,
      name="Senkung Kanaltraeger",
      feature={"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M5", "flaeche": {"feature": "f1", "flaeche": "-x"},
               "positionen": [[293.75, -160], [368.75, -160]], "durch": True, "bezug": {"u": "-rand", "v": "-rand"}})
STIFTE_AP = [("Kanalträger", 310, -160), ("Kanalträger", 352, -160), ("Trichtersäule", 303, -105), ("Trichtersäule", 322, -105),
             ("Kamerasäule", 177.5, -110), ("Kamerasäule", 177.5, -95), ("Zylinderaufnahme", 401.5, -141),
             ("Zylinderaufnahme", 412.9, -141), ("Rutschenwinkel", 179, -190), ("Rutschenwinkel", 201, -190)]
punkt(id="ap4", was="Stiftbohrungen Ø 4 für alle angeschraubten Teile (Nutzer: verstiften)", typ="feature", in_datei=AP,
      name="Stifte Anbauteile",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f1", "flaeche": "+x"},
               "positionen": [[y, z] for _, y, z in STIFTE_AP], "durch": True, "bezug": {"u": "-rand", "v": "-rand"}})
# ------------------------------------------------------------------ Anschlusswinkel
kommentar("Anschlusswinkel wandert mit der Platte (Bohrungen in der Bettrückwand werden vor Ort gebohrt); keine Stifte (Langlöcher)")
# Erst der Wandschenkel, dann der Plattenschenkel: umgekehrt zerfällt der Winkel kurz in zwei Körper, und die Bohrung f4
# schneidet nicht (Lauf 3, Code 71). Bauweg, die Reihenfolge der Punkte steht nicht in der Prüfsumme.
punkt(id="aw2", was="Schenkel an der Wand 33 nach +X", typ="mass", in_datei=AW, mass="D3@f2_skizze", alt=265, neu="=265-NAEHER")
punkt(id="aw1", was="Schenkel an der Platte 33 nach +X", typ="mass", in_datei=AW, mass="D1@Ebene1", alt=265, neu="=265-NAEHER",
      lage_folgen=[S("M5x20", 1), S("M5x20", 2), S("M5x20", 3)])
# ------------------------------------------------------------------ Kanalträger
kommentar("Kanalträger: Steg 61 lang, von hinten verschraubt, verstiftet; Gewinde und Stifte für den Weichenwinkel")
punkt(id="kt1", was="Steg endet an der neuen Plattenvorderseite (94 → 61)", typ="mass", in_datei=KT, mass="D1@f1_skizze", alt=94,
      neu="=94-NAEHER")
punkt(id="kt2", was="2 × M5 in der Stirn für die Schrauben von hinten", typ="feature", in_datei=KT, name="Gewinde Platte",
      feature={"typ": "normbohrung", "art": "gewinde", "groesse": "M5", "flaeche": {"feature": "f1", "flaeche": "-x"},
               "positionen": [[293.75, -160], [368.75, -160]], "tiefe": 16, "gewindetiefe": 14, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="kt3", was="2 Stiftbohrungen Ø 4 in der Stirn", typ="feature", in_datei=KT, name="Stifte Platte",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f1", "flaeche": "-x"},
               "positionen": [[310, -160], [352, -160]], "tiefe": 9, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="kt4", was="2 × M4 von unten für den Weichenwinkel", typ="feature", in_datei=KT, name="Gewinde Weichenwinkel",
      feature={"typ": "normbohrung", "art": "gewinde", "groesse": "M4", "flaeche": {"feature": "f1", "flaeche": "-y"},
               # 8,5 statt 9: Bei 9 ließ die Bohrspitze nur 0,01 Boden zum Kanal (Lauf 11)
               "positionen": [[-176, 340.7], [-164, 340.7]], "tiefe": 8.5, "gewindetiefe": 7, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="kt5", was="2 Stiftbohrungen Ø 4 von unten für den Weichenwinkel", typ="feature", in_datei=KT, name="Stifte Weichenwinkel",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f1", "flaeche": "-y"},
               "positionen": [[-184, 340.7], [-156, 340.7]], "tiefe": 8.5, "bezug": {"u": "-rand", "v": "-rand"}})
# ------------------------------------------------------------------ Kamerasäule, Kamerahalter
kommentar("Kamerasäule mit der Platte; Kamerahalter: Schenkel A bis X −172, Anlagekante an der Säule (Nutzer: 30 × 60, 1–2 tief)")
punkt(id="ks1", was="Kamerasäule 33 nach +X", typ="mass", in_datei=KS, mass="D3@f1_skizze", alt=215, neu="=215-NAEHER",
      lage_folgen=[S("M5x35", 1), S("M5x35", 2), S("M5x20", 8)])
punkt(id="ks2", was="2 Stiftbohrungen Ø 4 zur Platte", typ="feature", in_datei=KS, name="Stifte Platte",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f1", "flaeche": "-x"},
               "positionen": [[177.5, -110], [177.5, -95]], "tiefe": 9, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="kh1", was="Schenkel A beginnt an der Plattenvorderseite (60,5 → 40)", typ="mass", in_datei=KH, mass="D1@f1_skizze",
      alt=60.5, neu=40)
punkt(id="kh2", was="Schenkel A reicht bis X −172 (10 über die Säule hinaus)", typ="mass", in_datei=KH, mass="D3@f1_skizze",
      alt=184.5, neu=172)
punkt(id="kh3", was="Neben der Säule 1,5 dicker: Kante liegt an der +X-Fläche der Säule (= Vertiefung 30 × 60 × 1,5, Kamera bleibt)",
      typ="feature", in_datei=KH, name="Anlage Saeule",
      feature={"typ": "extrusion", "skizze": {"ebene": {"feature": "f1", "flaeche": "+z"},
               "elemente": [{"rechteck": {"mitte": [-177, 47.9], "breite": 10, "hoehe": 60}}]},
               "ende": {"typ": "blind", "tiefe": "=KH_TIEFE"}})
# Variante A (Nutzer 07.11.2026, nach Lauf 11): Mit der Säule rückt ihr zweites Gewinde nach X −190 hinter Schenkel B; es bleibt
# eine Klemmschraube M5 bei X −204, der Halter ist zwischen Plattenfront und Anlagekante gefangen. Das neue Langloch liegt wie das
# alte erste (5,5 breit, 30 Hub). Anker nahe: Die −z-Fläche von f1 ist nach der Verlängerung durch Schenkel B zweigeteilt.
punkt(id="kh4", was="Beide Langlöcher entfallen (das zweite läge nach der Verschiebung in Schenkel B)", typ="loeschen", in_datei=KH,
      feature="f2")
punkt(id="kh5", was="Ein Langloch für die Klemmschraube M5 bei X −204 (5,5 breit, 30 Hub, wie das alte erste)", typ="feature",
      in_datei=KH, name="Langloch Klemmung",
      feature={"typ": "schnitt", "skizze": {"ebene": {"nahe": [-204, 47.9, -202.5]},
               "elemente": [{"langloch": {"mitte": [-204, 47.9], "laenge": 30, "breite": 5.5, "winkel": 90,
                                          "bezug": {"u": "-rand", "v": "-rand"}}}]},
               "ende": {"typ": "durch_alles"}})
# ------------------------------------------------------------------ Trichtersäule
kommentar("Trichtersäule mit der Platte; Gewinde für Lasche 2 (Flansch) und Lasche 3 (Ecke)")
punkt(id="ts1", was="Trichtersäule 33 nach +X", typ="mass", in_datei=TS, mass="D3@f1_skizze", alt=230, neu="=230-NAEHER",
      lage_folgen=[S("M5x20", 4), S("M5x20", 5), S("M5x20", 6), S("M5x20", 7)])
punkt(id="ts2", was="2 Stiftbohrungen Ø 4 zur Platte", typ="feature", in_datei=TS, name="Stifte Platte",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f1", "flaeche": "-x"},
               "positionen": [[303, -105], [322, -105]], "tiefe": 9, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="ts3", was="4 × M5 auf der +X-Seite für Lasche 2 und Lasche 3", typ="feature", in_datei=TS, name="Gewinde Laschen",
      feature={"typ": "normbohrung", "art": "gewinde", "groesse": "M5", "flaeche": {"feature": "f1", "flaeche": "+x"},
               "positionen": [[305, 37], [320, 37], [305, -87], [305, -75]], "tiefe": 12, "gewindetiefe": 10,
               "bezug": {"u": "-rand", "v": "-rand"}})
# ------------------------------------------------------------------ Zylinderaufnahme
kommentar("Zylinderaufnahme: Flansch an der neuen Plattenvorderseite, verstiftet")
punkt(id="za1", was="Flansch 33 nach +X", typ="mass", in_datei=ZA, mass="D3@f2_skizze", alt=235, neu="=235-NAEHER",
      lage_folgen=[S("M5x16", 5), S("M5x16", 6)])
punkt(id="za2", was="Platte 33 kürzer (94,75 → 61,75)", typ="mass", in_datei=ZA, mass="D1@f1_skizze", alt=94.75, neu="=94.75-NAEHER")
punkt(id="za3", was="2 Stiftbohrungen Ø 4 zur Platte", typ="feature", in_datei=ZA, name="Stifte Platte",
      feature={"typ": "normbohrung", "art": "stift", "groesse": "4", "flaeche": {"feature": "f2", "flaeche": "-x"},
               "positionen": [[401.5, -141], [412.9, -141]], "tiefe": 9, "bezug": {"u": "-rand", "v": "-rand"}})
# ------------------------------------------------------------------ Trichter
kommentar("Trichter innen 40 in X (Nutzer: ein Drittel), mittig unter dem Rohr; Lasche 1 kürzer")
# Erst die Lasche, dann die Wand, zuletzt die Breite: In der Reihenfolge der Spec schwebt die Lasche zwischendurch
# frei, und die Bohrung f6 schneidet nicht (Lauf 4, Code 71); tr3, tr4, tr2, tr1 an einer Kopie ohne Fehler. Bauweg.
punkt(id="tr3", was="Lasche 1 kürzer: von der Säule bis in die neue −X-Wand", typ="mass", in_datei=TR, mass="D1@f5_skizze",
      alt=23.1, neu=19.7)
punkt(id="tr4", was="Lasche 1 endet bei X −192,3 (0,4 in der Wand)", typ="mass", in_datei=TR, mass="D3@f5_skizze", alt=221.9, neu=192.3)
punkt(id="tr2", was="+X-Kante der Öffnung X −115 → −151,4 (Mitte X −171,4 unter dem Rohraustritt)", typ="mass", in_datei=TR,
      mass="D3@f1_oben", alt=115, neu="=171.4-TRICHTER_X/2")
punkt(id="tr1", was="Öffnung innen 109 → 40 in X", typ="mass", in_datei=TR, mass="D1@f1_oben", alt=109, neu="=TRICHTER_X")
# ------------------------------------------------------------------ Fallschacht
kommentar("Fallschacht: Bohrung durch alles weg, Einschmelzmuttern, Ecke gefüllt, +X-Seite abnehmbar, Laschen 2 und 3")
punkt(id="fs1", was="M3-Gewinde im Flansch reichten 167,5 tief (die „merkwürdige Bohrung“): entfernen", typ="loeschen", in_datei=FS,
      feature="f4")
punkt(id="fs2", was="2 × Bohrung Ø 4 × 6 für Einschmelzmuttern M3 im Flansch", typ="feature", in_datei=FS, name="Einschmelz Flansch",
      feature={"typ": "bohrung", "flaeche": {"feature": "f2", "flaeche": "+y"}, "positionen": [[-170, 286], [-170, 325]],
               "durchmesser": "=EM3_D", "tiefe": "=EM3_T", "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="fs3", was="Ecke hinten über dem senkrechten Ende füllen (Nutzer, Schnittbild)", typ="feature", in_datei=FS, name="Fuellung Ecke",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": -182}},
               "elemente": [{"polygon": {"punkte": [[266.0, -91.0], [276.07, -91.0], [276.07, -66.64]]}}]},
               "ende": {"typ": "blind", "tiefe": 22}})
punkt(id="fs4", was="+X-Wand entfällt, sie wird der Schachtdeckel", typ="feature", in_datei=FS, name="Seite offen",
      feature={"typ": "schnitt", "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": -158}},
               "elemente": [{"polygon": {"punkte": [[239.974, -139], [276.37, -139], [276.37, -66.64], [313.332, 23],
                                                    [286.772, 23], [239.974, -90.5]]}}]},
               "ende": {"typ": "blind", "tiefe": 2}})
# Augen und Deckelohren aus einer Quelle (Konstruktionsreview: Lochlagen wichen bis 0,78 ab). Außenflächen der Wände in der
# Deckelebene (Y, Z): vorn senkrecht Y 240,274 bis Z −90,5, dann geneigt bis Y 287,072 bei Z 23; hinten senkrecht Y 276,07 bis
# Z −66,64, dann geneigt bis Y 313,032 bei Z 23. Auge: 9 aus der Wand heraus, 1 in die Wand (2 dick), 10 hoch, 8 tief (Boden 2
# unter der Einschmelzmutter); Loch 4,5 vor der Wand. Gleiche Zahlen in schachtdeckel.yaml (YVU, YHU, YVOO, YHOO, Ohren).
def _yv(z):   # Vorderwand außen
    return 240.274 if z <= -90.5 else 240.274 + (z + 90.5) * (287.072 - 240.274) / (23 + 90.5)
def _yh(z):   # Rückwand außen
    return 276.07 if z <= -66.64 else 276.07 + (z + 66.64) * (313.032 - 276.07) / (23 + 66.64)
OB, OH, IN = 9, 10, 1
def _auge(wand, aussen, z):   # aussen −1: Ohr nach −Y (Vorderwand), +1: nach +Y (Rückwand)
    pts = []
    for zz in (z - OH / 2, z + OH / 2):
        w = wand(zz)
        pts.append(((round(w + aussen * OB, 3), zz), (round(w - aussen * IN, 3), zz)))
    (a0, b0), (a1, b1) = pts
    return [list(a0), list(b0), list(b1), list(a1)], [round(wand(z) + aussen * OB / 2, 3), z]
AUGEN = [_auge(_yv, -1, -115), _auge(_yh, 1, -115), _auge(_yv, -1, 10), _auge(_yh, 1, 10)]
punkt(id="fs5", was="4 Augen für den Deckel hinter der Deckelebene", typ="feature", in_datei=FS, name="Augen Deckel",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": -160}},
               "elemente": [{"polygon": {"punkte": p}} for p, _ in AUGEN]},
               "ende": {"typ": "blind", "tiefe": 8, "umkehren": True}})
punkt(id="fs6", was="4 × Bohrung Ø 4 × 6 für Einschmelzmuttern M3 (Deckel)", typ="feature", in_datei=FS, name="Einschmelz Deckel",
      feature={"typ": "bohrung", "flaeche": {"nahe": [-160, AUGEN[0][1][1], -(AUGEN[0][1][0] + 0.5)]},
               "positionen": [loch for _, loch in AUGEN], "durchmesser": "=EM3_D",
               "tiefe": "=EM3_T", "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="fs7", was="Lasche 2 am Flansch zur Trichtersäule", typ="feature", in_datei=FS, name="Lasche Flansch",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "vorne", "abstand": -327.5}},
               "elemente": [{"polygon": {"punkte": [[-197, 23], [-185.5, 23], [-185.5, 29], [-191, 29], [-191, 45], [-197, 45]]}}]},
               "ende": {"typ": "blind", "tiefe": 30}})
punkt(id="fs8", was="Lasche 3: Strebe von der gefüllten Ecke zur Trichtersäule", typ="feature", in_datei=FS, name="Lasche Ecke",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": -92}},
               "elemente": [{"polygon": {"punkte": [[-197, 297.5], [-197, 312], [-189, 312], [-189, 299], [-180.5, 278],
                                                    [-180.5, 270], [-187.5, 270]]}}]},
               "ende": {"typ": "blind", "tiefe": 22}})
punkt(id="fs9", was="2 × Durchgang M5 in Lasche 2", typ="feature", in_datei=FS, name="Durchgang Lasche Flansch",
      feature={"typ": "bohrung", "flaeche": {"nahe": [-191, 40, -312.5]}, "positionen": [[305, 37], [320, 37]],
               "durchmesser": 5.5, "tiefe": 6})
punkt(id="fs10", was="2 × Durchgang M5 in Lasche 3", typ="feature", in_datei=FS, name="Durchgang Lasche Ecke",
      feature={"typ": "bohrung", "flaeche": {"nahe": [-189, -81, -305.5]}, "positionen": [[305, -87], [305, -75]],
               "durchmesser": 5.5, "tiefe": 8})
# ------------------------------------------------------------------ Rutsche
kommentar("Rutsche: n.i.O. innen 26 (Rückwand an der Abgabekante), Lasche unten weg, Auflage für den Rutschenwinkel, Endstück mit Steg 20")
punkt(id="ru1", was="Rückwand 9 nach vorn (Y 218,5 → 209,5)", typ="mass", in_datei=RU, mass="D1@Ebene1", alt=218.5, neu="=218.5-NIO_WEG")
punkt(id="ru2", was="Rutsche 62 → 53 tief", typ="mass", in_datei=RU, mass="D1@f1", alt=62, neu="=62-NIO_WEG")
punkt(id="ru3", was="n.i.O. innen 35 → 26", typ="mass", in_datei=RU, mass="D1@nio", alt=35, neu="=35-NIO_WEG")
for i, m in enumerate(("D6@fw_skizze", "D8@fw_skizze", "D14@fw_skizze", "D16@fw_skizze"), 4):
    punkt(id=f"ru{i}", was="Fangwand und Wangen enden an der neuen Rückwand", typ="mass", in_datei=RU, mass=m, alt=218.5,
          neu="=218.5-NIO_WEG")
punkt(id="ru8", was="Lasche unten entfällt (Rutschenträger entfällt)", typ="loeschen", in_datei=RU, feature="lasche", kinder=["f5"])
punkt(id="ru9", was="Auflage für den Rutschenwinkel auf der −X-Wand", typ="feature", in_datei=RU, name="Auflage Winkel",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "vorne", "abstand": -208}},
               "elemente": [{"polygon": {"punkte": [[-206, -213], [-191.16, -213], [-206, -238.7]]}}]},
               "ende": {"typ": "blind", "tiefe": 36}})
punkt(id="ru10", was="2 × Bohrung Ø 6,4 × 10 für Einschmelzmuttern M5", typ="feature", in_datei=RU, name="Einschmelz Winkel",
      feature={"typ": "bohrung", "flaeche": {"feature": "ru9", "flaeche": "+y"}, "positionen": [[-200, 182], [-200, 200]],
               "durchmesser": "=EM5_D", "tiefe": "=EM5_T", "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="ru11", was="Endstück unter dem Auslauf, 18 hoch", typ="feature", in_datei=RU, name="Endstueck",
      feature={"typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": -255.309}},
               "elemente": [{"polygon": {"punkte": [[156.5, -323.244], [209.5, -323.244], [227.5, -341.244], [156.5, -341.244]]}}]},
               "ende": {"typ": "blind", "tiefe": 27.712}})
punkt(id="ru12", was="Kanäle im Endstück: i.O. gerade, n.i.O. 18 nach +Y versetzt, Steg 2 → 20", typ="feature", in_datei=RU,
      name="Endstueck Kanaele",
      feature={"typ": "schnitt", "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": -229.906}},
               "elemente": [{"polygon": {"punkte": [[158.5, -323.244], [179.5, -323.244], [179.5, -342], [158.5, -342]]}},
                            {"polygon": {"punkte": [[181.5, -323.244], [207.5, -323.244], [226.26, -342], [200.26, -342]]}}]},
               "ende": {"typ": "blind", "tiefe": 23.097}})
# ------------------------------------------------------------------ Weichenkeil
kommentar("Weichenkeil: schmaler Teil 1 länger, Nuten entfallen (Wangen enden 9 früher)")
punkt(id="wk1", was="Schmaler Teil −X bis Y 236", typ="mass", in_datei=WK, mass="D2@seite_mx_skizze", alt=31.5, neu=32.5)
punkt(id="wk2", was="Schmaler Teil +X bis Y 236", typ="mass", in_datei=WK, mass="D2@seite_px_skizze", alt=31.5, neu=32.5)
punkt(id="wk3", was="Nut für die Wange −X entfällt", typ="loeschen", in_datei=WK, feature="nut_mx")
punkt(id="wk4", was="Nut für die Wange +X entfällt", typ="loeschen", in_datei=WK, feature="nut_px")
# ------------------------------------------------------------------ Prüfkanal, Durchlichtlasche, Durchlicht
kommentar("Durchlicht gedreht (Stecker nach +X, Nutzer): Lasche an die +X-Wand des Kanals")
punkt(id="pk1", was="2 × M4 in der +X-Wand für die Durchlichtlasche", typ="feature", in_datei=PK, name="Gewinde Lasche PX",
      feature={"typ": "normbohrung", "art": "gewinde", "groesse": "M4", "flaeche": {"feature": "f1", "flaeche": "+x"},
               "positionen": [[284, -144.5], [294, -144.5]], "tiefe": 6.5, "gewindetiefe": 6, "bezug": {"u": "-rand", "v": "-rand"}})
punkt(id="dl1", was="Lasche an die +X-Wand (X −151 … −131)", typ="mass", in_datei=DL, mass="D1@Ebene1", alt=189, neu=131,
      lage_folgen=[S("M4x16", i) for i in range(1, 5)] + [S("M4x20", 1), S("M4x20", 2)])
for i, m in enumerate(("D1@m4_positionen", "D3@m4_positionen", "D5@m4_positionen", "D7@m4_positionen"), 2):
    punkt(id=f"dl{i}", was="M4 zum Licht bei X −137,6 (gedrehtes Licht)", typ="mass", in_datei=DL, mass=m, alt=6.6, neu=13.4)
punkt(id="dl6", was="Bohrungen zur −X-Wand entfallen", typ="loeschen", in_datei=DL, feature="kanal")
punkt(id="dl7", was="2 × Durchgang M4 mit Flachsenkung zur +X-Wand", typ="feature", in_datei=DL, name="Kanal PX",
      feature={"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M4", "flaeche": {"feature": "f1", "flaeche": "+x"},
               "positionen": [[284, -144.5], [294, -144.5]], "durch": True, "bezug": {"u": "-rand", "v": "-rand"}})
# Zuerst: Die Verknüpfungen der Lasche-Schrauben an den gelöschten Bohrungen (dl6) sind nach den Teilpunkten gebrochen
# (Lauf 6, Code 48 schon beim ersten Punkt der Hauptbaugruppe). Bauweg.
for n in ("v188.1", "v188.2", "v189.1", "v189.2"):
    punkt(id="vl" + n.replace(".", "_")[1:], was="Lasche-Schrauben: alte Bohrung entfällt", typ="verknuepfung_loeschen", verknuepfung=n)
punkt(id="vd1", was="Durchlicht: alte Lochzuordnung entfällt", typ="verknuepfung_loeschen", verknuepfung="v133")
punkt(id="vd2", was="Durchlicht: alte Drehlage entfällt", typ="verknuepfung_loeschen", verknuepfung="v134")
punkt(id="vd3", was="Durchlicht um 180° gedreht: äußere M4 des Lichts in die M4 der Lasche bei Y 257,4", typ="verknuepfung_neu", art="konzentrisch",
      # nahe statt instanz: fremde Bohrungen kennen ihre Instanzen nicht (Lauf 8). Licht: Kernlochwand M4 bei z +22,5 (Teil);
      # Lasche: Durchgang bei X −137,6 / Y 257,4, nach der Drehung um 180° genau darüber.
      a={"komponente": C("DurchlichtEffilux"), "nahe": [-25.95, 5, 22.5]},
      b={"komponente": C("Durchlichtlasche"), "nahe": [-135.35, -147, -257.4]}, lage_folgen=[C("DurchlichtEffilux")])
punkt(id="vd4", was="Durchlicht: Stecker nach +X", typ="verknuepfung_neu", art="parallel",
      a={"komponente": C("DurchlichtEffilux"), "ebene": "vorne"}, b={"komponente": PLATTE, "ebene": "vorne"},
      ausrichtung="entgegengesetzt")
for i in (1, 2):
    punkt(id=f"vlk{i}", was=f"M4x20-{i} in Kanal PX {i}", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": S("M4x20", i), "referenz": "EINBAU_ACHSE"},
          b={"komponente": C("Durchlichtlasche"), "feature": "dl7", "instanz": i, "achse": True})
    punkt(id=f"vle{i}", was=f"M4x20-{i} Kopf auf der Flachsenkung", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": S("M4x20", i), "referenz": "EINBAU_EBENE"},
          b={"komponente": C("Durchlichtlasche"), "feature": "dl7", "instanz": i, "flaeche": "+x"}, ausrichtung="gleich")
# ------------------------------------------------------------------ Kamera, Klemmschraube (Variante A)
kommentar("Kamera an Schenkel B statt an der Stirn von Schenkel A (die wandert mit kh2 nach X −172); zweite Klemmschraube entfällt")
punkt(id="vk1", was="Kamera: Anlage an der Stirn von Schenkel A entfällt (nahm die Kamera 12,5 nach +X mit, Lauf 11)",
      typ="verknuepfung_loeschen", verknuepfung="v96")
punkt(id="vk2", was="Kamera liegt an der +X-Fläche von Schenkel B (X −184,5, Kamera bleibt auf X −170)", typ="verknuepfung_neu",
      art="deckungsgleich",
      # Kamera: −z-Fläche (Teil, z −14,5) zwischen den M3; Halter: Schenkel B bei Y 225, frei von den Bohrungen f3
      a={"komponente": C("Kamera"), "nahe": [0, 30, -14.5]},
      b={"komponente": C("Kamerahalter"), "nahe": [-184.5, 47.9, -225]}, ausrichtung="entgegengesetzt")
punkt(id="km1", was="Zweite Klemmschraube entfällt (Gewinde der Säule bei X −190 liegt hinter Schenkel B)",
      typ="komponente_entfernen", komponente=S("M5x20", 9), verknuepfungen=["v112.2", "v113.2"])
# ------------------------------------------------------------------ Verknüpfungen ohne Partner (Handumbau lauf-30)
kommentar("Verknüpfungen ohne Partner aus dem Handumbau (Zylinderhalter, Kanalschrauben): ersetzt durch die neuen unten")
for n in ("v56.1", "v56.2", "v57.1", "v57.2", "v123", "v124", "v125", "v140", "v141", "v162.1", "v162.2", "v163.1", "v163.2",
          "v172.1", "v172.2", "v173.1", "v173.2"):
    punkt(id="vx" + n.replace(".", "_")[1:], was="Verknüpfung ohne Partner (Handumbau)", typ="verknuepfung_loeschen", verknuepfung=n)
# Platziert1 (Typ und Partner unlesbar) hängt am Platzhalter-Winkel und ging in Lauf 9 mit wz1; validieren kann sie wz1 nicht
# zuordnen, darum ein eigener Löschpunkt vor wz1 (UEBERGABE §5.4).
punkt(id="vxp", was="Verknüpfung Platziert1 des Platzhalter-Winkels (Handumbau, Typ und Partner unlesbar)", typ="verknuepfung_loeschen",
      verknuepfung="Platziert1")
# ------------------------------------------------------------------ Kanalträger-Schrauben
kommentar("Die alten Schrauben M5x20-10/11 neu: von hinten durch die Platte in den Kanalträger (Nutzer)")
for i, s in ((1, 10), (2, 11)):
    punkt(id=f"kv{i}a", was=f"M5x20-{s} in Senkung Kanaltraeger {i}", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": S("M5x20", s), "referenz": "EINBAU_ACHSE"}, b={"komponente": PLATTE, "feature": "ap3", "instanz": i, "achse": True},
          lage_folgen=[S("M5x20", s)])
    punkt(id=f"kv{i}b", was=f"M5x20-{s} Kopf auf der Flachsenkung", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": S("M5x20", s), "referenz": "EINBAU_EBENE"},
          b={"komponente": PLATTE, "feature": "ap3", "instanz": i, "flaeche": "-x"}, ausrichtung="gleich")
# ------------------------------------------------------------------ Weichenwinkel
kommentar("Weichenwinkel statt Platzhalter Weichenzylinderhalter; ADNGF und seine Schrauben daran")
punkt(id="wz1", was="Platzhalter-Winkel aus lauf-30 entfällt", typ="komponente_entfernen", komponente=C("Weichenzylinderhalter"),
      verknuepfungen=[])
punkt(id="ww", was="Weichenwinkel L 40 × 30 × 4", typ="komponente_neu", quelle={"teil": "weichenwinkel.yaml"})
for e in ("rechts", "oben", "vorne"):
    punkt(id=f"ww{e[0]}", was=f"Weichenwinkel in Maschinenkoordinaten ({e})", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": "ww", "ebene": e}, b={"komponente": PLATTE, "ebene": e}, ausrichtung="gleich")
punkt(id="wa1", was="ADNGF-Rückseite am Winkel", typ="verknuepfung_neu", art="deckungsgleich",
      a={"komponente": "Festo_ADNGF-16-25-P-A-1", "referenz": "EINBAU_RUECKSEITE"}, b={"komponente": "ww", "feature": "f1", "flaeche": "+z"},
      ausrichtung="entgegengesetzt")
punkt(id="wa2", was="ADNGF-Befestigung 1 (X −161 / Z −196) in Winkelbohrung 2", typ="verknuepfung_neu", art="konzentrisch",
      # nahe statt gewinde: im Bestand ist der ADNGF eine fremde Komponente ohne Katalogbezug (Lauf 10, KeyError gewinde).
      # Kernlochwand Ø 3,242 der Befestigung 1 (Katalog: −9/−9, z −56,5 … −43) bei z −50, Teilkoordinaten.
      a={"komponente": "Festo_ADNGF-16-25-P-A-1", "nahe": [-7.379, -9, -50]},
      b={"komponente": "ww", "feature": "f3", "instanz": 2, "achse": True})
for s, inst in ((3, 2), (4, 1)):
    punkt(id=f"wa{s}a", was=f"M4x20-{s} in Winkelbohrung {inst}", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": S("M4x20", s), "referenz": "EINBAU_ACHSE"}, b={"komponente": "ww", "feature": "f3", "instanz": inst, "achse": True},
          lage_folgen=[S("M4x20", s)])
    punkt(id=f"wa{s}b", was=f"M4x20-{s} Kopf am Winkel", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": S("M4x20", s), "referenz": "EINBAU_EBENE"}, b={"komponente": "ww", "feature": "f1", "flaeche": "-z"},
          ausrichtung="gleich")
for i in (1, 2):
    punkt(id=f"wb{i}", was=f"Schraube Winkel → Steg {i}", typ="komponente_neu", quelle={"normteil": "ISO 4762 M4x10"})
    punkt(id=f"wb{i}a", was="in die Winkelbohrung", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": f"wb{i}", "referenz": "EINBAU_ACHSE"}, b={"komponente": "ww", "feature": "f4", "instanz": i, "achse": True})
    punkt(id=f"wb{i}b", was="Kopf unter dem Winkel", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": f"wb{i}", "referenz": "EINBAU_EBENE"}, b={"komponente": "ww", "feature": "f2", "flaeche": "-y"}, ausrichtung="gleich")
    punkt(id=f"wp{i}", was=f"Stift Winkel → Steg {i}", typ="komponente_neu", quelle={"normteil": "ISO 8734 4x12"})
    punkt(id=f"wp{i}a", was="in die Stiftbohrung", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": f"wp{i}", "referenz": "EINBAU_ACHSE"}, b={"komponente": "ww", "feature": "f5", "instanz": i, "achse": True})
    punkt(id=f"wp{i}b", was="bündig mit der Winkelunterseite", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": f"wp{i}", "referenz": "EINBAU_EBENE_1"}, b={"komponente": "ww", "feature": "f2", "flaeche": "-y"},
          ausrichtung="entgegengesetzt")
# ------------------------------------------------------------------ Rutschenwinkel statt Rutschenträger
kommentar("Rutschenträger entfällt, Rutschenwinkel oben an der Plattenvorderseite; Schrauben weiter verwendet")
punkt(id="rt1", was="Rutschenträger entfällt (hinge nach der Plattenverschiebung in der Rutsche)", typ="komponente_entfernen",
      komponente=C("Rutschentraeger"),
      verknuepfungen=["v126", "v127", "v128", "v164.1", "v164.2", "v165.1", "v165.2", "v166.1", "v166.2", "v167.1", "v167.2"])
punkt(id="rw", was="Rutschenwinkel L 30 × 20 × 4", typ="komponente_neu", quelle={"teil": "rutschenwinkel.yaml"})
for e in ("rechts", "oben", "vorne"):
    punkt(id=f"rw{e[0]}", was=f"Rutschenwinkel in Maschinenkoordinaten ({e})", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": "rw", "ebene": e}, b={"komponente": PLATTE, "ebene": e}, ausrichtung="gleich")
for i, s in ((1, 9), (2, 10)):
    punkt(id=f"rs{i}a", was=f"M5x16-{s} durch den Winkel in die Platte", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": S("M5x16", s), "referenz": "EINBAU_ACHSE"}, b={"komponente": "rw", "feature": "f3", "instanz": i, "achse": True},
          lage_folgen=[S("M5x16", s)])
    punkt(id=f"rs{i}b", was=f"M5x16-{s} Kopf am Winkel", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": S("M5x16", s), "referenz": "EINBAU_EBENE"}, b={"komponente": "rw", "feature": "f1", "flaeche": "+x"},
          ausrichtung="gleich")
for i, s in ((1, 3), (2, 4)):
    punkt(id=f"rr{i}a", was=f"M5x12-{s} durch den Winkel in die Einschmelzmutter der Rutsche", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": S("M5x12", s), "referenz": "EINBAU_ACHSE"}, b={"komponente": "rw", "feature": "f5", "instanz": i, "achse": True},
          lage_folgen=[S("M5x12", s)])
    punkt(id=f"rr{i}b", was=f"M5x12-{s} Kopf auf dem Winkel", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": S("M5x12", s), "referenz": "EINBAU_EBENE"}, b={"komponente": "rw", "feature": "f2", "flaeche": "+y"},
          ausrichtung="gleich")
# ------------------------------------------------------------------ Stifte an der Platte
kommentar("Stifte ISO 8734 Ø 4 an der Platte, bündig mit der Plattenrückseite")
for k, (teil, y, z) in enumerate(STIFTE_AP, 1):
    norm = "ISO 8734 4x16" if teil == "Rutschenwinkel" else "ISO 8734 4x20"
    punkt(id=f"sp{k}", was=f"Stift Platte → {teil}", typ="komponente_neu", quelle={"normteil": norm})
    punkt(id=f"sp{k}a", was="in die Stiftbohrung der Platte", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": f"sp{k}", "referenz": "EINBAU_ACHSE"}, b={"komponente": PLATTE, "feature": "ap4", "instanz": k, "achse": True})
    punkt(id=f"sp{k}b", was="bündig mit der Plattenrückseite", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": f"sp{k}", "referenz": "EINBAU_EBENE_1"}, b={"komponente": PLATTE, "feature": "f1", "flaeche": "-x"},
          ausrichtung="entgegengesetzt")
# ------------------------------------------------------------------ Schachtdeckel, Laschen-Schrauben
kommentar("Schachtdeckel mit 4 × M3x8; Laschen 2 und 3 mit je 2 × M5x16 an der Säule")
punkt(id="sd", was="Schachtdeckel (bisherige +X-Wand)", typ="komponente_neu", quelle={"teil": "schachtdeckel.yaml"})
for e in ("rechts", "oben", "vorne"):
    punkt(id=f"sd{e[0]}", was=f"Schachtdeckel in Maschinenkoordinaten ({e})", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": "sd", "ebene": e}, b={"komponente": PLATTE, "ebene": e}, ausrichtung="gleich")
for i in range(1, 5):
    punkt(id=f"ds{i}", was=f"Deckelschraube {i}", typ="komponente_neu", wie=S("M3x8", 3))
    # drehung_sperren: Kopie einer Bestandsschraube, die Vorgabe greift nur bei Normteilen (Lauf 11: Status 2)
    punkt(id=f"ds{i}a", was="in die Deckelbohrung", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": f"ds{i}", "referenz": "EINBAU_ACHSE"}, b={"komponente": "sd", "feature": "f3", "instanz": i, "achse": True},
          drehung_sperren=True)
    punkt(id=f"ds{i}b", was="Kopf auf dem Deckel", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": f"ds{i}", "referenz": "EINBAU_EBENE"}, b={"komponente": "sd", "feature": "f1", "flaeche": "+x"}, ausrichtung="gleich")
LASCHEN = [("fs9", 1, [-191, 42, -312.5]), ("fs9", 2, [-191, 42, -312.5]), ("fs10", 1, [-189, -81, -302]), ("fs10", 2, [-189, -81, -302])]
for k, (f, inst, nahe) in enumerate(LASCHEN, 1):
    punkt(id=f"ls{k}", was=f"Laschenschraube {k}", typ="komponente_neu", wie=S("M5x16", 1))
    punkt(id=f"ls{k}a", was="durch die Lasche in die Säule", typ="verknuepfung_neu", art="konzentrisch",
          a={"komponente": f"ls{k}", "referenz": "EINBAU_ACHSE"}, b={"komponente": C("Fallschacht"), "feature": f, "instanz": inst, "achse": True},
          drehung_sperren=True)
    punkt(id=f"ls{k}b", was="Kopf auf der Lasche", typ="verknuepfung_neu", art="deckungsgleich",
          a={"komponente": f"ls{k}", "referenz": "EINBAU_EBENE"}, b={"komponente": C("Fallschacht"), "nahe": nahe}, ausrichtung="gleich")

# ------------------------------------------------------------------ Bereiche (Modellkoordinaten der Teile: x = X, y = Z, z = −Y)
def box(pkt, datei, mn, mx):
    return "  - " + j({"punkte": pkt, "in_datei": datei, "box": {"min": mn, "max": mx}})
B = [
    # Ein Bereich je Teil, wo das Teil als Ganzes wandert oder die Differenz neue Bohrungen und Kürzung als ein Stück sieht
    # (Lauf 11: „keine Abweichung im Bereich“ der einzelnen Boxen); die Bohrungen weisen Maße und Prüfer nach.
    box(["ap1", "ag1", "ag2", "ap2", "ap3", "ap4"], AP, [-257.1, -210, -443], [-211.9, -90, -143]),
    box(["aw1", "aw2"], AW, [-317, -210, -195], [-224, -90, -135]),
    box(["kt1", "kt2", "kt3"], KT, [-245, -165, -383], [-195, -155, -283]),
    # bis an den Kanalboden (Bohrspitzen, Lauf 11)
    box(["kt4"], KT, [-178.5, -165.1, -343.2], [-173.5, -155.0, -338.2]), box(["kt4"], KT, [-166.5, -165.1, -343.2], [-161.5, -155.0, -338.2]),
    box(["kt5"], KT, [-186.5, -165.1, -343.2], [-181.5, -155.0, -338.2]), box(["kt5"], KT, [-158.5, -165.1, -343.2], [-153.5, -155.0, -338.2]),
    box(["ks1", "ks2"], KS, [-245.1, -115, -192.5], [-182, 115, -162.5]),
    box(["kh1", "kh2", "kh3"], KH, [-245, 17.9, -202.5], [-172, 77.9, -191]),
    # das alte zweite Langloch bei X −190 (das erste liegt wie das neue)
    box(["kh4", "kh5"], KH, [-193.5, 29.5, -241.1], [-186.5, 66.3, -192.4]),
    box(["ts1", "ts2", "ts3"], TS, [-245.1, -120, -327.5], [-196.9, 109, -297.5]),
    box(["za1", "za2", "za3"], ZA, [-245.1, -162.75, -417.2], [-201.4, -118.25, -389.2]),
    box(["tr1", "tr2", "tr3", "tr4"], TR, [-245, 29, -348], [-112, 122, -277]),
    box(["fs1", "fs2"], FS, [-172.5, 15, -288.5], [-167.5, 29.5, -283.5]), box(["fs1", "fs2"], FS, [-172.5, 22, -327.5], [-167.5, 29.5, -322.5]),
    box(["fs3"], FS, [-182.1, -91.1, -276.2], [-159.9, -66.5, -265.9]),
    box(["fs4"], FS, [-160.1, -139.1, -313.5], [-157.9, 23.1, -239.8]),
] + [box(["fs5", "fs6"], FS, [-168.1, min(q[1] for q in p) - 0.1, -max(q[0] for q in p) - 0.1],
          [-159.9, max(q[1] for q in p) + 0.1, -min(q[0] for q in p) + 0.1]) for p, _ in AUGEN] + [
    box(["fs7", "fs9"], FS, [-197.1, 22.9, -327.6], [-185.4, 45.1, -297.4]),
    box(["fs8", "fs10"], FS, [-197.1, -92.1, -312.1], [-180.4, -69.9, -269.9]),
    box(["ru1", "ru2", "ru3", "ru4", "ru5", "ru6", "ru7", "ru8"], RU, [-256, -324, -218.6], [-157, -174.9, -177.9]),
    box(["ru9", "ru10"], RU, [-206.1, -238.8, -208.1], [-191, -212.9, -171.9]),
    box(["ru11", "ru12"], RU, [-255.4, -342.1, -227.6], [-227.5, -323.2, -156.4]),
    box(["wk1"], WK, [-196, -202, -236.1], [-182.4, -171.3, -234.9]), box(["wk2"], WK, [-160.5, -202, -236.1], [-143.9, -171.3, -234.9]),
    box(["wk3"], WK, [-187, -201.1, -244.6], [-182.4, -173.9, -233.9]), box(["wk4"], WK, [-160.5, -201.1, -244.6], [-155.9, -173.9, -233.9]),
    box(["pk1"], PK, [-159, -146.6, -286.1], [-150.9, -142.4, -281.9]), box(["pk1"], PK, [-159, -146.6, -296.1], [-150.9, -142.4, -291.9]),
    box(["dl1", "dl2", "dl3", "dl4", "dl5", "dl6", "dl7"], DL, [-209.1, -149.1, -300.1], [-130.9, -139.9, -207.4]),
]
KOLL = [
    ([S("M5x20", 10), C("Kanaltraeger")], "neue Gewinde M5 (Punkt kt2): Gewinde kosmetisch, die Schraube überlappt das Kernloch Ø 4,2"),
    ([S("M5x20", 11), C("Kanaltraeger")], "wie oben"),
    (["wb1", C("Kanaltraeger")], "neue Gewinde M4 (Punkt kt4), Kernloch Ø 3,3"),
    (["wb2", C("Kanaltraeger")], "wie oben"),
    (["ls1", C("Trichtersaeule")], "neue Gewinde M5 (Punkt ts3)"), (["ls2", C("Trichtersaeule")], "wie oben"),
    (["ls3", C("Trichtersaeule")], "wie oben"), (["ls4", C("Trichtersaeule")], "wie oben"),
    ([S("M4x20", 1), C("Pruefkanal")], "neue Gewinde M4 (Punkt pk1)"), ([S("M4x20", 2), C("Pruefkanal")], "wie oben"),
    ([S("M4x20", 3), "Festo_ADNGF-16-25-P-A-1"], "RT-Gewinde M4 des Kaufteils (Herstellergeometrie)"),
    ([S("M4x20", 4), "Festo_ADNGF-16-25-P-A-1"], "wie oben"),
    ([S("M5x16", 9), PLATTE], "Gewinde M5 der Platte (Rutschenwinkel), Eingriff jetzt über die ganze Plattendicke"),
    ([S("M5x16", 10), PLATTE], "wie oben"),
]
kopf = f"""# Änderungs-Spec Runde 1 der Prüfstation AP 6.8 an lauf-30 (Bestand bestand-2), Auftrag laut eingabe/aufgabe.md.
# Erzeugt von erzeuge_rev1.py (Übergabe: UEBERGABE.md in diesem Ordner); Entscheidungen des Nutzers vom 06.11.2026:
# Trichter innen 40, Halterung über 3 Laschen an der Trichtersäule (keine Klemmleisten), Durchlicht gedreht und Platte näher,
# Rutsche mit Einschmelzmuttern an einem Alu-Winkel. Teile in Maschinenkoordinaten (x = X, y = Z, z = −Y).
art: aenderung
name: Pruefstation_Rev1
bestand:
  datei: AP68-Pruefstation_Pruefstation.SLDASM
  sha256: e80b74bf2685fe1e0aa09eb89ede139a29fbaa212f1856049652d5444a5e2ab7
  aufnahme: 2
parameter:
  NAEHER: 33        # Platte näher an den Kanal (Grenze: GRLA-Drosseln am ADNGF, 25 frei nach −X)
  TRICHTER_X: 40    # Trichteröffnung innen in X (Nutzer)
  NIO_WEG: 9        # n.i.O.-Kanal hinten kürzer: Rückwand innen an der Abgabekante Y 207,5 (Nutzer: etwa 1/4 zu groß)
  KH_TIEFE: 1.5     # Vertiefung Kamerahalter (Nutzer: 1–2)
  EM3_D: 4.0        # Einschmelzmutter M3: Bohrung (Annahme, Herstellerwert vor dem Druck prüfen)
  EM3_T: 6
  EM5_D: 6.4        # Einschmelzmutter M5 (Annahme)
  EM5_T: 10
punkte:
"""
text = kopf + "\n".join(zeilen) + "\nbereiche:\n" + "\n".join(B) + "\nkollision_erlaubt:\n" + "\n".join(
    "  - " + j({"paar": p, "grund": g}) for p, g in KOLL) + "\n"
text += """pruefung:
  masse_pruefen:
    - {was: "Plattenvorderseite", in_datei: AP68-Pruefstation_Anschlussplatte.SLDPRT, von: {punkt: [0, 0, 0]},
       zu: {flaeche: {nahe: [-212, -150, -250], normale: [1, 0, 0]}}, soll: 212, tol: 0.01}
    - {was: "Kanalträger Länge", in_datei: AP68-Pruefstation_Kanaltraeger.SLDPRT, von: {flaeche: {nahe: [-212, -160, -330], normale: [-1, 0, 0]}},
       zu: {flaeche: {nahe: [-151, -160, -330], normale: [1, 0, 0]}}, soll: 61, tol: 0.01}
    - {was: "n.i.O. innen", in_datei: AP68-Pruefstation_Rutsche.SLDPRT, von: {flaeche: {nahe: [-170, -210, -181.5], normale: [0, 0, -1]}},
       zu: {flaeche: {nahe: [-170, -210, -207.5], normale: [0, 0, 1]}}, soll: 26, tol: 0.01}
"""
ZIEL.write_text(text, encoding="utf-8")
print(ZIEL, len(zeilen), "Punkte/Kommentare")
