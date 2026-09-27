"""Handler-Registry: je Feature-Typ eine Funktion (ctx, feature_spec) -> FeatureErgebnis."""

from collections.abc import Callable

HANDLER: dict[str, Callable] = {}


def handler(*typen: str):
    def dekorator(funktion):
        for typ in typen:
            HANDLER[typ] = funktion
        return funktion

    return dekorator


def alle_handler() -> dict[str, Callable]:
    import swki.compiler.handler  # noqa: F401  (registriert alle Handler beim Import)

    return HANDLER
