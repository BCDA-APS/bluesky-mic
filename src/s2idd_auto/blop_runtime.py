"""Runtime objects shared by the active S2IDD RunEngine and Blop evaluator."""

_catalog = None


def set_catalog(catalog):
    """Bind the catalog subscribed to the active RunEngine."""
    global _catalog
    _catalog = catalog


def get_catalog():
    """Return the active RunEngine catalog without importing startup again."""
    if _catalog is None:
        raise RuntimeError(
            "No S2IDD Blop catalog is bound; initialize s2idd_auto.startup first"
        )
    return _catalog
