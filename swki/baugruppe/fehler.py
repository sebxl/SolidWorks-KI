"""Fehlercodes der Baugruppen (Spec 3b §11). Geworfen werden sie als swki.compiler.fehler.BauFehler, damit sie wie
Teilfehler ins Protokoll gehen."""

TEIL_BAU = "TEIL_BAU"
KOMPONENTE_FEHLER = "KOMPONENTE_FEHLER"
VERKNUEPFUNG_FEHLER = "VERKNUEPFUNG_FEHLER"
SCHLIESSEN_FEHLER = "SCHLIESSEN_FEHLER"  # ein selbst geöffnetes Dokument ließ sich nach dem Bau nicht schließen
GRUNDSTELLUNG_FEHLER = "GRUNDSTELLUNG_FEHLER"  # Spec 4a §7.2/§10: eine Stellung ließ sich nicht herstellen
ZAHNPHASE_FEHLER = "ZAHNPHASE_FEHLER"  # Spec 4b §5.4.2/§8: Zahn-in-Lücke nach dem Drehen nicht erreicht
