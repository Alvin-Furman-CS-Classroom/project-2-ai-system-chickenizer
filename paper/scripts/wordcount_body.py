#!/usr/bin/env python3
"""Approximate main-body word count (excludes abstract, refs, captions).

Course rules exclude abstract, references, figure/table captions, appendices.
This script is a rough check when `texcount` is not installed. Prefer `texcount`
or Overleaf for the final submission count.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "sections"


def strip_latex_commands(s: str) -> str:
    s = re.sub(r"%.*", "", s)
    s = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", "", s, flags=re.DOTALL)
    s = re.sub(r"\\caption\{([^}]*)\}", "", s)  # drop caption words from count
    s = re.sub(r"\\[a-zA-Z@]+(\[[^\]]*\])?(\{[^\}]*\})*", " ", s)
    s = re.sub(r"[{}\\$]", " ", s)
    return s


def word_count(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def main() -> int:
    total = 0
    for path in sorted(SECTIONS.glob("*.tex")):
        if path.name == "abstract.tex":
            continue
        n = word_count(strip_latex_commands(path.read_text()))
        print(f"{path.name:24} {n:5}")
        total += n
    print(f"{'TOTAL (body sections)':24} {total:5}")
    print("\nTarget (course): 2200–2500 words excluding abstract, refs, captions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
