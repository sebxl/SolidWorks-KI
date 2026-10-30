"""Schnellbau (Stufe C1, docs/superpowers/specs/2026-10-25-schnellbau-c1-design.md): zweites Backend der Spec ohne
SolidWorks – Teil-Spec → exakte B-Rep (OpenCascade über build123d/OCP), Baugruppe → Lage und Gelenke, konvexe Zerlegung
und MuJoCo-Modell (MJCF). SolidWorks bleibt der verbindliche Bau; die Referenz-Suite hält beide Backends gleich
(werkzeuge/schnellbau_abgleich.py).

Braucht das Extra `schnellbau` (pyproject.toml); ohne es ist nur `fehler` importierbar.
"""
