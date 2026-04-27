"""Pytest: keep repo root on ``sys.path`` so ``bootstrap_dot_src`` imports during collection."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
