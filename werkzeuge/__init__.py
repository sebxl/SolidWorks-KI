"""Werkzeuge für Diagnose und Live-Läufe (kein Produktionscode, nicht Teil des Pakets swki).

Aufruf immer aus dem Repo-Wurzelordner: .venv\\Scripts\\python.exe -m werkzeuge.<name> --help

- sw_neustart          SolidWorks beenden und frisch starten (nur ohne offene Dokumente), Einstellungen melden
- live_frisch          Live-Tests einzeln, vor jedem Test (oder ab einer Speichergrenze) frisches SolidWorks
- bau_wiederholen      Zyklen „Neustart + N × swki bauen“ bis zum ersten Fehlbau (sporadische Fehler)
- cpu_last             CPU-Last erzeugen (zu bau_wiederholen)
- inspiziere           gespeichertes Teil öffnen: Gleichungen, Feature-Baum, Skizzen (Punkte, Beziehungen, Maße),
                       Zylinderflächen, Bohrungsassistent, What's Wrong
- stl_huellquader      Hüllquader aller STL eines Ordners (ohne SolidWorks/Blender)
- kaufteil_vollanalyse STEP importieren (nichts speichern), je Körper Hüllquader und Flächenübersicht
- kaufteil_vorpruefung Aufnahmeprüfung eines noch nicht freigegebenen Kaufteil-Eintrags, Ablage im Arbeitsordner
"""
