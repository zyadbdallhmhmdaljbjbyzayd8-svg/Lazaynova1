"""LZ-Core: Lazaynova's from-scratch decoder-only transformer, tokenizer and training library."""
import os as _os

# On phones (Termux) multi-threaded BLAS was measured to return inconsistent results
# for identical inputs, so default to 1 thread. Must run before torch is imported.
if "com.termux" in _os.environ.get("PREFIX", "") or "TERMUX_VERSION" in _os.environ:
    for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        _os.environ.setdefault(_v, _os.environ.get("LZ_THREADS", "1"))

from .config import LZConfig, PRESETS, from_preset, from_legacy_json, check_hardware_policy, is_termux
from .tokenizer import LZTokenizer

__all__ = [
    "LZConfig", "PRESETS", "from_preset", "from_legacy_json",
    "check_hardware_policy", "is_termux", "LZTokenizer",
]
__version__ = "0.1.0"
