"""Runtime optional dependency helpers.

The core package is intentionally standard-library only. Optional packages are
imported lazily and treated as enhancements, never requirements.
"""

from __future__ import annotations

import importlib
from types import ModuleType


def optional_import(name: str) -> ModuleType | None:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def has_optional(name: str) -> bool:
    return optional_import(name) is not None

