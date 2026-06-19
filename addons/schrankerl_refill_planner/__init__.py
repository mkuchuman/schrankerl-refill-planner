from importlib.util import find_spec

if find_spec("odoo") is not None:
    from . import models as _models
