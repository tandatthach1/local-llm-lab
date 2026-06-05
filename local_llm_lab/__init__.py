"""Source-tree shim so `python -m local_llm_lab` works before installation."""

from pathlib import Path

_src_pkg = Path(__file__).resolve().parents[1] / "src" / "local_llm_lab"
if _src_pkg.exists():
    __path__.append(str(_src_pkg))  # type: ignore[name-defined]

