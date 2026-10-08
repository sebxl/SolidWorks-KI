"""Messstand ohne SolidWorks: Transkript-Auswertung, Protokolle, Score."""

import json

import pytest

from werkzeuge.messstand import protokolle, score, transkript


def _e(typ, ts, inhalt, mid=None, usage=None):
    m = {"role": typ, "content": inhalt}
    if mid:
        m["id"] = mid
    if usage:
        m["usage"] = usage
    return {"type": typ, "timestamp": ts, "message": m}


def _bash(tid, cmd):
    return {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}


def _res(tid, text="", fehler=False):
    return {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": fehler}


U = {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 50}

WURZEL = [
    _e("user", "2026-10-09T10:00:00.000Z", "Start"),
    _e("assistant", "2026-10-09T10:00:05.000Z", [{"type": "text", "text": "x"}], "m1", {**U, "output_tokens": 5}),
    _e("assistant", "2026-10-09T10:00:06.000Z", [_bash("t1", 'cd "C:/wt" && .venv\\Scripts\\python.exe -m swki bauen a.yaml')], "m1", U),
    _e("user", "2026-10-09T10:00:36.000Z", [_res("t1", '{"status": "ok", "lauf": 1}')]),
    _e("assistant", "2026-10-09T10:00:40.000Z", [_bash("t2", "python -m swki freigeben a.yaml")], "m2", U),
    _e("user", "2026-10-09T10:00:42.000Z", [_res("t2", '{"freigegeben": "a.yaml"}')]),
    _e("assistant", "2026-10-09T10:00:43.000Z", [{"type": "tool_use", "id": "t3", "name": "Agent",
                                                   "input": {"subagent_type": "pruefer", "prompt": "p"}}], "m3", U),
    _e("user", "2026-10-09T10:01:43.000Z", [_res("t3", "{}")]),
    _e("assistant", "2026-10-09T10:01:50.000Z", [{"type": "tool_use", "id": "t4", "name": "Read",
                                                   "input": {"file_path": "C:\\Users\\User\\Documents\\Projekte\\SolidWorks-KI\\auftraege\\AP68\\x.yaml"}}], "m4", U),
    _e("user", "2026-10-09T10:01:51.000Z", [_res("t4", "...")]),
    _e("assistant", "2026-10-09T10:02:00.000Z", [{"type": "text", "text": "fertig"}], "m5", U),
]
PRUEFER = [
    _e("assistant", "2026-10-09T10:00:50.000Z", [{"type": "tool_use", "id": "p1", "name": "Read", "input": {"file_path": "b"}}], "q1", U),
    _e("user", "2026-10-09T10:00:51.000Z", [_res("p1", "")]),
]


def test_kategorien():
    assert transkript.kategorie("Bash", {"command": "x -m swki pruefen a"}) == "pruefen"
    assert transkript.kategorie("Bash", {"command": "x -m swki status a"}) == "swki_sonst"
    assert transkript.kategorie("Bash", {"command": "x -m werkzeuge.sw_neustart"}) == "werkzeuge"
    assert transkript.kategorie("Agent", {"subagent_type": "pruefer"}) == "pruefer"
    assert transkript.kategorie("Grep", {}) == "lesen"


def test_auswerten_zeit_aufrufe_tokens_lecks():
    k = transkript.auswerten(WURZEL, {"q": PRUEFER},
                             ["C:/Users/User/Documents/Projekte/SolidWorks-KI/auftraege"])
    assert k["zeit_s"] == 120.0
    assert k["zeit_anteile_s"]["bauen"] == 30.0
    assert k["zeit_anteile_s"]["pruefer"] == 60.0
    assert k["zeit_anteile_s"]["modell"] == pytest.approx(120 - 30 - 2 - 60 - 1)
    assert k["tool_aufrufe"] == 5
    assert k["tool_aufrufe_je_werkzeug"]["Read"] == 2
    assert k["freigaben"] == 1
    assert k["swki_aufrufe"] == {"bauen": 1, "freigeben": 1}
    # m1 zählt einmal (letzte usage), dazu m2..m5 und q1 → 6 Nachrichten
    assert k["tokens"]["nachrichten"] == 6
    assert k["tokens"]["output_tokens"] == 6 * 50
    assert k["tokens"]["gewichtet"] == round(6 * (10 + 125 + 100 + 250))
    assert len(k["lecks"]) == 1 and "Read" in k["lecks"][0]


def test_freigabe_mit_fehler_zaehlt_nicht():
    w = [_e("assistant", "2026-10-09T10:00:00.000Z", [_bash("t", "-m swki freigeben a")], "m", U),
         _e("user", "2026-10-09T10:00:01.000Z", [_res("t", "Exit code 1\n{\"fehler\": \"X\"}", True)])]
    assert transkript.auswerten(w)["freigaben"] == 0


def test_subagenten_rekursiv(tmp_path):
    for kid, vater in [("b", "a"), ("c", "b"), ("x", "y")]:
        (tmp_path / f"agent-{kid}.meta.json").write_text(json.dumps({"parentAgentId": vater}))
    assert set(transkript.subagenten(tmp_path, "a")) == {"b", "c"}


def _schreibe(ordner, name, d):
    (ordner / "protokolle").mkdir(parents=True, exist_ok=True)
    (ordner / "protokolle" / name).write_text(json.dumps(d), encoding="utf-8")


def test_protokolle(tmp_path):
    _schreibe(tmp_path, "a.lauf-1.protokoll.json", {"status": "fehler"})
    _schreibe(tmp_path, "a.lauf-2.protokoll.json", {"status": "ok"})
    _schreibe(tmp_path, "a.lauf-2.pruefbericht.json", {"pruefungen": [{"ok": True}, {"ok": False}, {"ok": None}]})
    _schreibe(tmp_path, "a.lauf-2.pruefer.json", {"bestanden": False, "maengel": [1, 2]})
    _schreibe(tmp_path, "a.lauf-3.protokoll.json", {"status": "ok"})
    _schreibe(tmp_path, "a.lauf-3.pruefbericht.json", {"pruefungen": [{"ok": True}]})
    _schreibe(tmp_path, "a.lauf-3.pruefer.json", {"bestanden": True, "maengel": []})
    k = protokolle.auswerten(tmp_path)
    assert k == {"laeufe": 3, "bauabbrueche": 1, "pruefmaengel": 1, "pruefer_urteile": 2, "pruefer_maengel": 2,
                 "letzter_lauf": 3, "pruefer_bestanden": True}


def test_ergebnisdatei(tmp_path):
    (tmp_path / "a.SLDPRT").write_text("")
    assert protokolle.ergebnisdatei(tmp_path).name == "a.SLDPRT"
    (tmp_path / "b.SLDPRT").write_text("")
    assert protokolle.ergebnisdatei(tmp_path) is None
    (tmp_path / "g.SLDASM").write_text("")
    assert protokolle.ergebnisdatei(tmp_path).name == "g.SLDASM"


@pytest.mark.parametrize("r, s", [(1, 2), (0.25, 7), (0.125, 10), (0.05, 10), (2, 0), (1.5, 1), (0.625, 4.5)])
def test_teilscore(r, s):
    assert score.teilscore(r, 0.25, 0.125) == pytest.approx(s)


def _kpi(aufgabe, zeit, aufrufe=100, tok=1000, mb=5000, fehler=2, richtig=True, bestanden=True, lauf="l"):
    return {"lauf": lauf, "aufgabe": aufgabe, "zeit_s": zeit, "tool_aufrufe": aufrufe, "tokens": {"gewichtet": tok},
            "speicher_spitze_mb": mb, "sw_neustarts": 0, "bauabbrueche": fehler, "pruefmaengel": 0,
            "pruefer_maengel": 0, "freigaben": 1, "bestanden": bestanden, "richtig": richtig, "lecks": []}


def test_score_baseline_ist_2_und_ziel_7():
    base = [_kpi("a", 1000), _kpi("b", 2000)]
    b = score.bezug(base)
    assert score.bewerte(base, b)["score"] == 2.0
    ziel = [_kpi("a", 250, 50, 500, 3500, 1), _kpi("b", 500, 50, 500, 3500, 1)]
    assert score.bewerte(ziel, b)["score"] == 7.0


def test_score_deckel_und_strafe():
    base = [_kpi("a", 1000)]
    b = score.bezug(base)
    falsch = score.bewerte([_kpi("a", 100, 10, 100, 2000, 0, richtig=False)], b)
    assert falsch["score"] <= 4.0 and falsch["nicht_richtig"] == ["a"]
    # nicht fertig → mindestens 1,5 × Baseline-Zeit → Zeit-Teilscore 1
    assert falsch["teilscores"]["zeit"] == pytest.approx(1.0)


def test_deutlich_besser():
    alt = {"score": 2.0, "teilscores": {"zeit": 2, "aufwand": 2, "fehler": 2, "speicher": 2}, "nicht_richtig": []}
    neu = {"score": 3.5, "teilscores": {"zeit": 4, "aufwand": 2, "fehler": 2, "speicher": 0.5}, "nicht_richtig": []}
    assert score.deutlich_besser(neu, alt)[0] is False   # Speicher > 1 Punkt schlechter
    neu["teilscores"]["speicher"] = 1.5
    assert score.deutlich_besser(neu, alt)[0] is True
