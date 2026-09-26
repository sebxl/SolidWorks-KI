"""Liest Interfaces, Member, Parameter und Enums aus einer COM-Typbibliothek (.tlb)."""

from dataclasses import dataclass, field
from pathlib import Path

# Stabile COM-Konstanten (oaidl.h)
TKIND_ENUM, TKIND_INTERFACE, TKIND_DISPATCH = 0, 3, 4
INVOKE_ART = {1: "methode", 2: "property_get", 4: "property_put", 8: "property_putref"}
PARAMFLAG_FOUT, PARAMFLAG_FRETVAL, PARAMFLAG_FOPT = 0x2, 0x8, 0x10
_BASIS_METHODEN = {"QueryInterface", "AddRef", "Release", "GetTypeInfoCount", "GetTypeInfo", "GetIDsOfNames", "Invoke"}


@dataclass
class Parameter:
    name: str
    aus: bool
    optional: bool


@dataclass
class Member:
    interface: str
    name: str
    art: str
    parameter: list[Parameter] = field(default_factory=list)


@dataclass
class EnumWert:
    enum: str
    name: str
    wert: int


def _parameter(ti, fd) -> list[Parameter]:
    namen = list(ti.GetNames(fd.memid))[1:]
    ergebnis = []
    for i, arg in enumerate(fd.args):
        flags = arg[1]
        if flags & PARAMFLAG_FRETVAL:
            continue
        name = namen[i] if i < len(namen) else ("Wert" if i == len(fd.args) - 1 else f"p{i + 1}")
        ergebnis.append(Parameter(name, bool(flags & PARAMFLAG_FOUT), bool(flags & PARAMFLAG_FOPT)))
    return ergebnis


def lese_typbibliothek(pfad: Path) -> tuple[list[Member], list[EnumWert]]:
    import pythoncom

    tlb = pythoncom.LoadTypeLib(str(pfad))
    members: list[Member] = []
    enums: list[EnumWert] = []
    for i in range(tlb.GetTypeInfoCount()):
        ti = tlb.GetTypeInfo(i)
        attr = ti.GetTypeAttr()
        typname = tlb.GetDocumentation(i)[0]
        if attr.typekind == TKIND_ENUM:
            for k in range(attr.cVars):
                vd = ti.GetVarDesc(k)
                enums.append(EnumWert(typname, ti.GetNames(vd.memid)[0], int(vd.value)))
        elif attr.typekind in (TKIND_INTERFACE, TKIND_DISPATCH):
            for j in range(attr.cFuncs):
                fd = ti.GetFuncDesc(j)
                name = ti.GetNames(fd.memid)[0]
                if name in _BASIS_METHODEN:
                    continue
                members.append(Member(typname, name, INVOKE_ART.get(fd.invkind, "methode"), _parameter(ti, fd)))
            if attr.typekind == TKIND_DISPATCH:
                for k in range(attr.cVars):
                    vd = ti.GetVarDesc(k)
                    members.append(Member(typname, ti.GetNames(vd.memid)[0], "property"))
    return members, enums
