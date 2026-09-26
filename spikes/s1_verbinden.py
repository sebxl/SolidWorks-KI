"""S1: Verbindung, Revision, Early Binding (makepy)."""

from spikes._gemeinsam import lauf, start
from swki.verbindung import jahr_aus_revision, wert


def pruefen() -> dict:
    r, app = start()
    rev = wert(app.RevisionNumber)
    daten = {"revision": rev, "jahr": jahr_aus_revision(rev), "sichtbar": bool(wert(app.Visible))}
    try:
        import win32com.client

        early = win32com.client.gencache.EnsureDispatch(app._oleobj_)
        daten["early_binding"] = "ok"
        daten["early_revision"] = early.RevisionNumber()
    except Exception as e:
        daten["early_binding"] = repr(e)
    return daten


if __name__ == "__main__":
    lauf("s1_verbinden", pruefen)
