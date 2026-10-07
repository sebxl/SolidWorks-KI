"""Katalogeintrag Nanotec GPLE60-2S-32 (Plan-Nachtrag Task 7N) ohne SolidWorks: gültig, einziger Hinweis die unbelegte
Gewindegruppe, freigegeben und mit bestandenem Prüfer-Urteil zur aktuellen Freigabe (Spec 3c §4.5, §4.6, §5.2)."""

from swki.kaufteile.eintrag import lade_eintrag, validieren
from swki.kaufteile.katalog import finde, geprueft
from swki.spec.freigabe import pruefe_freigabe

URL = "https://www.nanotec.com/fileadmin/files/Datenblaetter/Getriebe/Planetengetriebe_GPLE60/GPLE60-2S.stp"


def test_gple60_gueltig_freigegeben_geprueft():
    pfad = finde("Nanotec GPLE60-2S-32")
    assert validieren(pfad)["hinweise"] == [{"art": "nicht_belegt", "pfad": "gewinde.flansch",
                                              "meldung": "Kennmaß ohne Beleg: wird geprüft, gilt im Bericht als "
                                                         "„nicht belegt“"}]
    spec = lade_eintrag(pfad)
    pruefe_freigabe(pfad, spec)
    assert geprueft(pfad, spec) and spec["original"]["bezug"] == {
        "art": "url", "url": URL, "datum": "2026-10-06",
        "hinweis": "Download mit Nutzerfreigabe (85716 Byte); STEP der Baureihe 2S, gilt für alle 2S-Untersetzungen"}
