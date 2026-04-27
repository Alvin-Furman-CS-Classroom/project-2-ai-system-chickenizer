"""Reusable loading UI for Streamlit (avoids default spinner glyph)."""

from __future__ import annotations

import html
from contextlib import contextmanager
from typing import Iterator

import streamlit as st

_SPIN_STYLE = """
<style>
@keyframes _cklz_loader_spin { to { transform: rotate(360deg); } }
</style>
"""


@contextmanager
def loading_row(message: str) -> Iterator[None]:
    """Show a circular CSS spinner and message while work runs; clears when done."""
    slot = st.empty()
    m = html.escape(message)
    slot.markdown(
        _SPIN_STYLE
        + f"""
<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;margin:8px 0;
  background:linear-gradient(90deg, rgba(25,118,210,0.1), rgba(13,71,161,0.07));
  border-radius:12px;border:1px solid rgba(25,118,210,0.3);">
  <div style="width:22px;height:22px;flex-shrink:0;border-radius:50%;
    border:3px solid rgba(25,118,210,0.25);border-top-color:#1976d2;
    animation:_cklz_loader_spin 0.72s linear infinite;" aria-hidden="true"></div>
  <span style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    font-size:0.95rem;font-weight:500;color:#0d47a1;">{m}</span>
</div>
        """,
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        slot.empty()
