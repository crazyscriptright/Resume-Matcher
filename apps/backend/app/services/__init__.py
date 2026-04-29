"""Business logic services package.

Submodules are intentionally *not* imported at package import time to avoid
circular import issues (some submodules depend on `app.llm`). Import the
submodules directly where needed, for example::

    from app.services import parser
    from app.services import auth

This keeps imports lightweight and prevents import-time cycles in tests.
"""

__all__ = [
    "auth",
    "parser",
    "improver",
    "refiner",
]

