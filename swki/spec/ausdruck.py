"""Sichere Auswertung von Ausdrücken wie "=L/2-20" in Spezifikationen.

Erlaubt sind Zahlen, Parameternamen, + - * / ** und Klammern. Alles andere wird abgewiesen.
"""

import ast
import operator

from swki.cli import SwkiFehler

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_SW_OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}
_ERLAUBT = (ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.USub, ast.UAdd, *_OPS)


class AusdruckFehler(SwkiFehler):
    pass


def ist_ausdruck(wert) -> bool:
    return isinstance(wert, str) and wert.startswith("=")


def _baum(ausdruck: str) -> ast.expr:
    text = ausdruck[1:] if ausdruck.startswith("=") else ausdruck
    try:
        baum = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as e:
        raise AusdruckFehler(f"Ausdruck {ausdruck!r} ist ungültig: {e.msg}") from None
    for teil in ast.walk(baum):
        if isinstance(teil, _ERLAUBT):
            continue
        if isinstance(teil, ast.Constant) and type(teil.value) in (int, float):
            continue
        raise AusdruckFehler(f"Ausdruck {ausdruck!r}: {type(teil).__name__} ist nicht erlaubt")
    return baum


def namen(ausdruck: str) -> set[str]:
    return {k.id for k in ast.walk(_baum(ausdruck)) if isinstance(k, ast.Name)}


def _rechne(k: ast.expr, parameter: dict, ausdruck: str) -> float:
    if isinstance(k, ast.Constant):
        return float(k.value)
    if isinstance(k, ast.Name):
        if k.id not in parameter:
            raise AusdruckFehler(f"Ausdruck {ausdruck!r}: unbekannter Parameter {k.id!r}")
        return float(parameter[k.id])
    if isinstance(k, ast.UnaryOp):
        wert = _rechne(k.operand, parameter, ausdruck)
        return -wert if isinstance(k.op, ast.USub) else wert
    links = _rechne(k.left, parameter, ausdruck)
    rechts = _rechne(k.right, parameter, ausdruck)
    if isinstance(k.op, ast.Div) and rechts == 0:
        raise AusdruckFehler(f"Ausdruck {ausdruck!r}: Division durch 0")
    return float(_OPS[type(k.op)](links, rechts))


def auswerten(wert, parameter: dict | None = None) -> float:
    """Zahl oder "=Ausdruck" → float (mm bzw. Grad)."""
    if isinstance(wert, bool):
        raise AusdruckFehler(f"{wert!r} ist keine Zahl")
    if isinstance(wert, (int, float)):
        return float(wert)
    if not ist_ausdruck(wert):
        raise AusdruckFehler(f"{wert!r} ist weder Zahl noch Ausdruck (beginnt mit '=')")
    return _rechne(_baum(wert), parameter or {}, wert)


def _sw(k: ast.expr, oben: bool) -> str:
    if isinstance(k, ast.Constant):
        return repr(k.value)
    if isinstance(k, ast.Name):
        return f'"{k.id}"'
    if isinstance(k, ast.UnaryOp):
        innen = _sw(k.operand, False)
        return f"-{innen}" if isinstance(k.op, ast.USub) else innen
    text = f"{_sw(k.left, False)} {_SW_OPS[type(k.op)]} {_sw(k.right, False)}"
    return text if oben else f"({text})"


def sw_ausdruck(ausdruck: str) -> str:
    """Ausdruck in SolidWorks-Gleichungssyntax, z. B. '=L/2-20' → '("L" / 2) - 20'."""
    return _sw(_baum(ausdruck), True)
