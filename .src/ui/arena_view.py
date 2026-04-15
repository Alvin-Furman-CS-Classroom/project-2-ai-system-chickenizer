"""Arena HTML/CSS renderer for Streamlit."""

from __future__ import annotations

from typing import Any, Dict

import streamlit.components.v1 as components


def render_arena(
    last_round: Dict[str, Any],
    game_over: bool,
    duration_ms: int = 700,
    hold_ms: int = 1200,
    return_ms: int = 350,
    action_nonce: int = 0,
) -> None:
    """Render a simple HTML/CSS animated arena scene."""
    p1_action = last_round.get("p1_action")
    p2_action = last_round.get("p2_action")
    outcome = (last_round.get("outcome") or "").upper()

    nonce_suffix = str(action_nonce)
    flash_class = "flash-crash" if outcome == "CRASH" else ""
    outcome_text = "No completed rounds yet" if not outcome else outcome
    if game_over:
        outcome_text = f"{outcome_text} - GAME OVER"
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

    arena_html = f"""
    <style>
      .arena {{
        position: relative;
        width: 100%;
        height: 240px;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #444;
        background:
          linear-gradient(to bottom, #111 0%, #111 48%, #333 48%, #333 52%, #111 52%, #111 100%);
      }}
      .car {{
        position: absolute;
        top: 64px;
        font-size: 64px;
      }}
      .p1 {{ left: 8%; transform: translate(0px, 0px) scaleX(-1); }}
      .p2 {{ right: 8%; transform: translate(0px, 0px); }}
      .outcome {{
        position: absolute;
        left: 50%;
        top: 8px;
        z-index: 2;
        transform: translateX(-50%);
        font-weight: 700;
        font-size: 14px;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        color: #f5f5f5;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        background: rgba(0, 0, 0, 0.75);
        border: 1px solid #888;
        border-radius: 999px;
        padding: 6px 14px;
        white-space: nowrap;
      }}
      .flash {{
        position: absolute;
        left: 50%;
        top: 68px;
        transform: translateX(-50%);
        font-size: 44px;
        opacity: 0;
      }}
      .flash-crash {{
        animation: boom {duration_ms}ms ease-in-out 1;
      }}
      @keyframes boom {{
        0% {{ opacity: 0; transform: translateX(-50%) scale(0.2); }}
        40% {{ opacity: 1; transform: translateX(-50%) scale(1.1); }}
        100% {{ opacity: 0; transform: translateX(-50%) scale(1.5); }}
      }}
    </style>

    <div class="arena arena-{action_nonce}" id="arena-{nonce_suffix}">
      <div class="outcome">{outcome_text}</div>
      <div class="car p1" id="p1-{nonce_suffix}">🚗</div>
      <div class="car p2" id="p2-{nonce_suffix}">🏎️</div>
      <div class="flash {flash_class}">💥</div>
    </div>
    <script>
      (() => {{
        const p1 = document.getElementById("p1-{nonce_suffix}");
        const p2 = document.getElementById("p2-{nonce_suffix}");
        const arena = document.getElementById("arena-{nonce_suffix}");
        if (!p1 || !p2 || !arena) return;

        const arenaW = arena.clientWidth;
        const travel = Math.min(arenaW * 0.42, 420);
        const crash = Math.min(arenaW * 0.28, 260);
        const swingY = 34;
        const p1SwerveY = -swingY;
        const p2SwerveY = Math.round(swingY * 1.45);

        const p1Action = "{p1_vec}";
        const p2Action = "{p2_vec}";
        const d1 = p1Action === "crash" ? crash : travel;
        const d2 = p2Action === "crash" ? -crash : -travel;
        const y1 = p1Action === "swerve" ? p1SwerveY : 0;
        const y2 = p2Action === "swerve" ? p2SwerveY : 0;
        const r1 = p1Action === "swerve" ? -12 : (p1Action === "crash" ? -7 : 0);
        const r2 = p2Action === "swerve" ? -12 : (p2Action === "crash" ? 7 : 0);

        const p1End = `translate(${{d1}}px, ${{y1}}px) rotate(${{r1}}deg) scaleX(-1)`;
        const p2End = `translate(${{d2}}px, ${{y2}}px) rotate(${{r2}}deg)`;
        const p1Idle = "translate(0px, 0px) scaleX(-1)";
        const p2Idle = "translate(0px, 0px)";

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
      }})();
    </script>
    """
    components.html(arena_html, height=260)

