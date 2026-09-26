"""S7: Toolbox – Bestandsaufnahme (Daten, Add-in, API-Doku)."""

import winreg
from pathlib import Path

from spikes._gemeinsam import lauf, start
from swki.api.bauen import api_db
from swki.api.index import suche


def _toolbox_daten_ordner(jahr: int) -> tuple[Path, str]:
    """Ermittelt den Toolbox-Datenordner zuerst über die Registry (Controller-Ruling R3: kein
    fest verdrahtetes 'C:\\SOLIDWORKS Data'). Schlüssel gefunden per Live-Suche:
    HKCU\\Software\\SolidWorks\\SOLIDWORKS <jahr>\\General, Wert 'Toolbox Data Location'
    (nur lesend geöffnet). Rückfall auf 'C:\\SOLIDWORKS Data', falls Wert/Schlüssel fehlt."""
    pfad_key = rf"Software\SolidWorks\SOLIDWORKS {jahr}\General"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, pfad_key, 0, winreg.KEY_READ) as key:
                wert, _ = winreg.QueryValueEx(key, "Toolbox Data Location")
                return Path(str(wert).rstrip("\\")), "registry"
        except OSError:
            continue
    return Path(r"C:\SOLIDWORKS Data"), "rueckfall"


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    daten_ordner, quelle = _toolbox_daten_ordner(r.sw_jahr)
    return {
        "toolbox_daten_quelle": quelle,
        "toolbox_daten": daten_ordner.exists(),
        "toolbox_daten_ordner": str(daten_ordner),
        "normen": (
            sorted(p.name for p in (daten_ordner / "browser").iterdir() if p.is_dir())
            if daten_ordner.exists() else []
        ),
        "interop_configure_addin": (r.installationsordner / "api" / "redist" /
                                    "SolidWorks.Interop.sldtoolboxconfigureaddin.dll").exists(),
        # Nur Titel behalten (keine Hilfetext-Auszüge/Pfade in Git, Spec §7: der Index bleibt lokal).
        "doku_toolbox": [treffer["titel"] for treffer in suche(db, "Toolbox component create", 15)],
        "doku_toolbox_konfig": [treffer["titel"] for treffer in suche(db, "Toolbox configure size", 15)],
        "toolbox_member_im_index": [
            "IAssemblyDoc.UpdateToolboxComponent(AssemblyLevelToUpdate) – aktualisiert bereits "
            "eingefügte Toolbox-Komponenten anhand der aktuellen Toolbox-Einstellungen; erzeugt "
            "keine neue Komponente.",
            "IModelDocExtension.ToolboxPartType – get/set-Flag, ob ein bereits offenes Dokument "
            "als Toolbox-Teil markiert ist; keine Erzeugung.",
            "IPackAndGo.IncludeToolboxComponents – get/set-Flag, ob Toolbox-Komponenten in ein "
            "Pack&Go aufgenommen werden; keine Erzeugung.",
            "ISldWorks.ImportToolboxItem(StdToImport, DestinationFilePath) / ExportToolboxItem – "
            "importieren/exportieren die Größentabellen (*.xlsx) einer Norm, keine Bauteilgeometrie.",
        ],
        "entscheidung": "Rückfallweg",
        "begruendung": (
            "Der lokale API-Index deckt für strukturierte 'methode'/'enum'-Einträge nur "
            "sldworks.tlb/swconst.tlb ab (siehe swki/api/bauen.py:TYPBIBLIOTHEKEN). Alle fünf "
            "Member mit 'Toolbox' im Namen dieser Typbibliotheken (s. 'toolbox_member_im_index') "
            "wurden per 'swki api methode' geprüft: keiner davon erzeugt ein Toolbox-Teil aus "
            "Norm+Größe in einem Dokument/einer Baugruppe. Suche nach 'Toolbox component create' "
            "liefert nur Beispielcode zu AddComponent/AddMate und die swconst-Namespace-Übersicht "
            "(Export/Import-Enums); Suche nach 'Toolbox configure size' liefert nur "
            "Hole-Wizard-Beispiele, nicht Toolbox-Teile. Die eigentliche "
            "Toolbox-Erzeugungs-Funktionalität (Drag&Drop aus dem Task-Pane, Norm/Größe wählen) "
            "liegt in einem eigenen Add-in mit eigener Typbibliothek "
            "(SolidWorks.Interop.sldtoolboxconfigureaddin.dll, vorhanden, s.o.), die nicht in "
            "TYPBIBLIOTHEKEN steht und daher keine strukturierten 'methode'/'enum'-Einträge "
            "liefert. Das ist NICHT gleichbedeutend mit 'nicht indiziert': 'toolboxapi.chm' ist "
            "als Hilfetext im Index durchsuchbar ('swki api suche') und zeigt die Interfaces "
            "IToolboxConfiguratorAddin, IToolBoxConfiguratorApplication, IPDMDocManager – deren "
            "Member sind aber nur Konfigurator-/PDM-Hooks (u. a. Connect/Disconnect, "
            "SetDocumentStatus, SetManagedDocument, SetCancelOperation, GetHWnd), keine Methode "
            "zum Erzeugen eines Teils. Kein 'versuch_erzeugen()' ergänzt (Brief: nur bei "
            "gefundener Methode). Größe manuell erzeugen, per 'swki normteil aufnehmen' "
            "übernehmen (Stufe 3)."
        ),
    }


if __name__ == "__main__":
    lauf("s7_toolbox", pruefen)
