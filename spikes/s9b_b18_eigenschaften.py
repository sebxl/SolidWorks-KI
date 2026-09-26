"""S9b Baustein 18: Benutzerdefinierte Eigenschaften (Dokumentebene).

Extension.CustomPropertyManager("") -> Add3 (Text, swCustomPropertyReplaceValue=2) -> Get6 zurücklesen,
ersetzen, Nicht-Vorhandenes lesen, verknüpfter Wert ("SW-Masse", Dokumenteinheit g), GetNames, Delete2.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import kasten_oben, start, teil
from spikes.s9b_gemeinsam import byref_bool, byref_str

SW_CUSTOM_INFO_TEXT = 30
SW_CUSTOM_PROPERTY_REPLACE_VALUE = 2
SW_CUSTOM_PROPERTY_ONLY_IF_NEW = 0


def get6(cpm, name: str, cached: bool = False) -> dict:
    val, res, was, link = byref_str(), byref_str(), byref_bool(), byref_bool()
    ret = cpm.Get6(name, cached, val, res, was, link)
    return {"rueckgabe": ret, "wert": val.value, "aufgeloest": res.value, "was_resolved": was.value,
            "link_to_property": link.value}


def pruefen() -> dict:
    r, app = start()
    d: dict = {}
    with teil(app, r) as model:
        kasten_oben(model, 100, 60, 20)
        cpm = model.Extension.CustomPropertyManager("")          # Property mit Argument -> (…) nötig
        d["cpm_typ"] = str(type(cpm))
        d["namen_anfang"] = list(cpm.GetNames or ())
        d["add3_neu"] = cpm.Add3("Benennung", SW_CUSTOM_INFO_TEXT, "Formplatte AS", SW_CUSTOM_PROPERTY_REPLACE_VALUE)
        d["get6_neu"] = get6(cpm, "Benennung")
        d["add3_ersetzen"] = cpm.Add3("Benennung", SW_CUSTOM_INFO_TEXT, "Formplatte DS", SW_CUSTOM_PROPERTY_REPLACE_VALUE)
        d["get6_ersetzt"] = get6(cpm, "Benennung")
        d["add3_onlyifnew_vorhanden"] = cpm.Add3("Benennung", SW_CUSTOM_INFO_TEXT, "X", SW_CUSTOM_PROPERTY_ONLY_IF_NEW)
        d["get6_nach_onlyifnew"] = get6(cpm, "Benennung")
        d["add3_umlaut"] = cpm.Add3("Werkstoff", SW_CUSTOM_INFO_TEXT, "1.2312 – vergütet (ä ö ü ß)", 2)
        d["get6_umlaut"] = get6(cpm, "Werkstoff")
        model.SetMaterialPropertyName2("", "SolidWorks DIN Materials", "1.2312 (40CrMnMoS8-6)")  # 942 g
        titel = model.GetTitle
        d["add3_link"] = cpm.Add3("Gewicht", SW_CUSTOM_INFO_TEXT, f'"SW-Masse@{titel}.SLDPRT"', 2)
        d["get6_link"] = get6(cpm, "Gewicht")
        d["add3_link_kurz"] = cpm.Add3("Gewicht2", SW_CUSTOM_INFO_TEXT, '"SW-Masse"', 2)
        d["get6_link_kurz"] = get6(cpm, "Gewicht2")
        d["add3_link_falsch"] = cpm.Add3("Gewicht3", SW_CUSTOM_INFO_TEXT, f'"SW-Masse@@@{titel}.SLDPRT"', 2)
        d["get6_link_falsch"] = get6(cpm, "Gewicht3")
        d["get6_fehlt"] = get6(cpm, "gibtsnicht")
        d["set2"] = cpm.Set2("Benennung", "Formplatte neu")
        d["get6_nach_set2"] = get6(cpm, "Benennung")
        d["gettype2"] = cpm.GetType2("Benennung")
        d["count"] = cpm.Count
        d["namen"] = list(cpm.GetNames or ())
        d["delete2"] = cpm.Delete2("Werkstoff")
        d["namen_nach_delete"] = list(cpm.GetNames or ())
        # dieselbe Eigenschaft über einen neu geholten Manager lesen
        d["get6_neuer_manager"] = get6(model.Extension.CustomPropertyManager(""), "Benennung")
    return d


if __name__ == "__main__":
    lauf("s9b_b18_eigenschaften", pruefen)
