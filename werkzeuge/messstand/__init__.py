"""Messstand: KPI-Messung der KI-Konstruktion (Spec docs/superpowers/specs/2026-10-09-messstand-design.md).

Ein Lauf = ein frischer Konstruktions-Agent bearbeitet eine Aufgabe aus tests/messstand/aufgaben/ in einem eigenen
git-Worktree. Messdaten liegen unter <arbeitsordner>/MESSSTAND/ (nicht im Git).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.messstand <befehl> …   (Übersicht: --help)
"""
