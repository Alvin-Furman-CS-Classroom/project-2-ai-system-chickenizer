"""Arena HTML/CSS renderer for Streamlit."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st
import streamlit.components.v1 as components

# Iframe width for ``components.html`` (Streamlit defaults are narrow); wide layout uses most of the main pane.
_ARENA_IFRAME_WIDTH_PX = 1600
_ARENA_IFRAME_HEIGHT_PX = 320


def build_arena_html(
    last_round: Dict[str, Any],
    game_over: bool,
    duration_ms: int = 700,
    hold_ms: int = 1200,
    return_ms: int = 350,
    action_nonce: int = 0,
    *,
    frame_id: int = 0,
) -> str:
    """Build HTML/CSS/JS for the animated arena (no Streamlit I/O).

    ``frame_id`` increments on each **New game** so iframe DOM / keyframes never
    collide with a previous match (``action_nonce`` resets to 0 each match).
    """
    p1_action = last_round.get("p1_action")
    p2_action = last_round.get("p2_action")
    raw_outcome = (last_round.get("outcome") or "").strip()
    outcome = raw_outcome.upper()
    # Initial match / new game: show arena but do not run car motion until a round exists.
    has_completed_round = bool(outcome)

    uid = f"{int(frame_id)}_{int(action_nonce)}"
    nonce_suffix = uid
    flash_class = "flash-crash" if outcome == "CRASH" else ""
    if not outcome:
        outcome_text = "No completed rounds yet"
        outcome_class = "outcome-neutral"
    elif outcome == "P1":
        outcome_text = "P1 wins"
        outcome_class = "outcome-p1"
    elif outcome == "P2":
        outcome_text = "P2 wins"
        outcome_class = "outcome-p2"
    elif outcome == "TIE":
        outcome_text = "Tie"
        outcome_class = "outcome-tie"
    elif outcome == "CRASH":
        outcome_text = "Crash"
        outcome_class = "outcome-crash"
    else:
        outcome_text = raw_outcome
        outcome_class = "outcome-neutral"
    if game_over:
        outcome_text = f"{outcome_text} — game over"
        outcome_class = f"{outcome_class} outcome-game-over"
    delay_ms = duration_ms + hold_ms
    p1_vec = "stay"
    p2_vec = "stay"
    if p1_action == "swerve":
        p1_vec = "swerve"
    if p2_action == "swerve":
        p2_vec = "swerve"
    if outcome == "CRASH":
        p1_vec = "crash"
        p2_vec = "crash"

    boom_name = f"boom_{uid.replace('-', '_')}"
    return f"""
    <style>
      html, body {{
        margin: 0;
        background: #0a0a0a;
        min-height: 100%;
        color-scheme: dark;
      }}
      .arena-wrap {{
        box-sizing: border-box;
        width: 100%;
        max-width: 1600px;
        margin: 0 auto;
        background: #0a0a0a;
        overflow-x: hidden;
        isolation: isolate;
      }}
      .arena {{
        position: relative;
        width: 100%;
        height: 280px;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #444;
        background:
          linear-gradient(to bottom, #111 0%, #111 48%, #333 48%, #333 52%, #111 52%, #111 100%);
      }}
      .car {{
        position: absolute;
        top: 82px;
        font-size: clamp(64px, 6.2vw, 100px);
        will-change: transform;
        backface-visibility: hidden;
      }}
      .p1 {{ left: 5%; transform: translate(0px, 0px) scaleX(-1); }}
      .p2 {{ right: 5%; transform: translate(0px, 0px); }}
      .outcome {{
        position: absolute;
        left: 50%;
        top: 6px;
        z-index: 2;
        transform: translateX(-50%);
        font-weight: 900;
        font-size: clamp(17px, 2.1vw, 26px);
        letter-spacing: 0.02em;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        color: #f8f8f8;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.95);
        background: rgba(0, 0, 0, 0.82);
        border: 2px solid #aaa;
        border-radius: 999px;
        padding: 8px 18px;
        white-space: nowrap;
      }}
      .outcome-p1 {{ color: #b8f2ff; border-color: #5ec8e8; }}
      .outcome-p2 {{ color: #ffd9a6; border-color: #e8a45e; }}
      .outcome-tie {{ color: #f5f5a8; border-color: #d6d65a; }}
      .outcome-crash {{ color: #ffb3b3; border-color: #e85e5e; }}
      .outcome-neutral {{ color: #f0f0f0; }}
      .outcome-game-over {{
        font-size: clamp(15px, 1.85vw, 22px);
        opacity: 0.95;
      }}
      .flash {{
        position: absolute;
        left: 50%;
        top: 96px;
        transform: translateX(-50%);
        font-size: 44px;
        opacity: 0;
      }}
      .flash-crash {{
        animation: {boom_name} {duration_ms}ms ease-in-out 1;
      }}
      @keyframes {boom_name} {{
        0% {{ opacity: 0; transform: translateX(-50%) scale(0.2); }}
        40% {{ opacity: 1; transform: translateX(-50%) scale(1.1); }}
        100% {{ opacity: 0; transform: translateX(-50%) scale(1.5); }}
      }}
    </style>

    <div class="arena-wrap">
    <div class="arena arena-{nonce_suffix}" id="arena-{nonce_suffix}">
      <div class="outcome {outcome_class}">{outcome_text}</div>
      <div class="car p1" id="p1-{nonce_suffix}">🚗</div>
      <div class="car p2" id="p2-{nonce_suffix}">🏎️</div>
      <div class="flash {flash_class}">💥</div>
    </div>
    </div>
    <script>
      (() => {{
        const runMotion = {str(has_completed_round).lower()};
        const p1 = document.getElementById("p1-{nonce_suffix}");
        const p2 = document.getElementById("p2-{nonce_suffix}");
        const arena = document.getElementById("arena-{nonce_suffix}");
        if (!p1 || !p2 || !arena) return;
        if (!runMotion) return;

        const p1Action = "{p1_vec}";
        const p2Action = "{p2_vec}";
        const p1Idle = "translate(0px, 0px) scaleX(-1)";
        const p2Idle = "translate(0px, 0px)";

        let started = false;
        let ro = null;
        let fallbackTimer = null;

        function runAnim(arenaW) {{
          const travel = Math.min(arenaW * 0.44, 980);
          const crash = Math.min(arenaW * 0.30, 620);
          const swingY = Math.round(28 + arenaW * 0.012);
          const p1SwerveY = -swingY;
          const p2SwerveY = Math.round(swingY * 1.45);

          const d1 = p1Action === "crash" ? crash : travel;
          const d2 = p2Action === "crash" ? -crash : -travel;
          const y1 = p1Action === "swerve" ? p1SwerveY : 0;
          const y2 = p2Action === "swerve" ? p2SwerveY : 0;
          const r1 = p1Action === "swerve" ? -12 : (p1Action === "crash" ? -7 : 0);
          const r2 = p2Action === "swerve" ? -12 : (p2Action === "crash" ? 7 : 0);

          const p1End = `translate(${{d1}}px, ${{y1}}px) rotate(${{r1}}deg) scaleX(-1)`;
          const p2End = `translate(${{d2}}px, ${{y2}}px) rotate(${{r2}}deg)`;

          p1.animate([{{ transform: p1Idle }}, {{ transform: p1End }}], {{
            duration: {duration_ms},
            easing: "ease-in-out",
            fill: "forwards"
          }});
          p2.animate([{{ transform: p2Idle }}, {{ transform: p2End }}], {{
            duration: {duration_ms},
            easing: "ease-in-out",
            fill: "forwards"
          }});
          setTimeout(() => {{
            p1.animate([{{ transform: p1End }}, {{ transform: p1Idle }}], {{
              duration: {return_ms},
              easing: "ease-in-out",
              fill: "forwards"
            }});
            p2.animate([{{ transform: p2End }}, {{ transform: p2Idle }}], {{
              duration: {return_ms},
              easing: "ease-in-out",
              fill: "forwards"
            }});
          }}, {delay_ms});
        }}

        function tryStart(w) {{
          if (started) return;
          const ww = w || arena.clientWidth || arena.getBoundingClientRect().width;
          if (ww < 80) return;
          started = true;
          if (ro) ro.disconnect();
          if (fallbackTimer) clearTimeout(fallbackTimer);
          runAnim(ww);
        }}

        if (typeof ResizeObserver !== "undefined") {{
          ro = new ResizeObserver((entries) => {{
            const w = entries[0].contentRect.width;
            if (w >= 80) tryStart(w);
          }});
          ro.observe(arena);
        }}
        fallbackTimer = setTimeout(() => {{
          if (!started) tryStart(arena.clientWidth >= 80 ? arena.clientWidth : 720);
        }}, 450);
      }})();
    </script>
    """


def render_arena(
    last_round: Dict[str, Any],
    game_over: bool,
    duration_ms: int = 700,
    hold_ms: int = 1200,
    return_ms: int = 350,
    action_nonce: int = 0,
    *,
    frame_id: int = 0,
) -> None:
    """Draw the animated arena in the current Streamlit layout block.

    Embeds ``build_arena_html`` via ``components.html``. The iframe is wrapped in
    ``st.empty()`` so rapid full-app reruns (e.g. auto-run to end) replace one slot
    instead of leaving a stale iframe under the active one.

    Call from inside the intended parent (e.g. ``with tab_arena:``) so Streamlit’s
    delta path matches the visible tab.

    Args:
        last_round: Last completed round actions/outcome for motion and labels.
        game_over: Whether to show game-over styling on the outcome banner.
        duration_ms, hold_ms, return_ms: Animation timing passed through to HTML/JS.
        action_nonce: Bumps when a new round completes (same match).
        frame_id: Increments on each new match; keeps DOM ids and keyframes unique.
    """
    arena_html = build_arena_html(
        last_round,
        game_over,
        duration_ms=duration_ms,
        hold_ms=hold_ms,
        return_ms=return_ms,
        action_nonce=action_nonce,
        frame_id=frame_id,
    )
    arena_slot = st.empty()
    with arena_slot:
        components.html(
            arena_html,
            width=_ARENA_IFRAME_WIDTH_PX,
            height=_ARENA_IFRAME_HEIGHT_PX,
            scrolling=False,
        )
