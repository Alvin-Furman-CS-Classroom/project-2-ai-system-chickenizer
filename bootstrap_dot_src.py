"""Bootstrap helper to make the repo's `.src` importable.

Use this from tests or scripts that run from the repo root so you don't have to
copy/paste `sys.path.insert(...)` blocks everywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

# This file lives at the repo root; do not rely on ``cwd`` (pytest / IDEs may differ).
_REPO_ROOT = Path(__file__).resolve().parent


def add_dot_src_to_path(*, root: Path | None = None) -> Path:
    """Ensure `<repo>/.src` is on `sys.path`, returning that path."""
    repo_root = _REPO_ROOT if root is None else Path(root)
    dot_src = (repo_root / ".src").resolve()
    if str(dot_src) not in sys.path:
        sys.path.insert(0, str(dot_src))
    return dot_src

