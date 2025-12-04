import io
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, Literal, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests
from fpdf import FPDF
try:
    from openai import OpenAI
except ImportError:  # OpenAI client is optional for the chatbot
    OpenAI = None  # type: ignore

try:  # When executed as a package (recommended path)
    from .liftingcast_loader import (
        LiftingCastError,
        fetch_recent_liftingcast_meets,
        load_liftingcast_meet,
    )
    from .scoring import calculate_dots, calculate_glossbrenner, calculate_ipf_gl
except ImportError:  # Fallback when run directly within the directory
    from liftingcast_loader import (  # type: ignore
        LiftingCastError,
        fetch_recent_liftingcast_meets,
        load_liftingcast_meet,
    )
    from scoring import calculate_dots, calculate_glossbrenner, calculate_ipf_gl  # type: ignore

# Page configuration for mobile responsiveness
st.set_page_config(
    page_title="PowerTrack - Powerlifting Meet Companion",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness and vibrant design
st.markdown(
    """
<style>
    :root {
        --powertrack-primary: #7c3aed;
        --powertrack-secondary: #2563eb;
        --powertrack-accent: #a5b4fc;
        --powertrack-ink: #050814;
        --powertrack-surface: rgba(10, 14, 32, 0.92);
        --powertrack-surface-2: rgba(16, 21, 45, 0.82);
        --powertrack-border: rgba(255, 255, 255, 0.08);
        --powertrack-glow: rgba(124, 58, 237, 0.25);
        --powertrack-text: #e5e7eb;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 20%, rgba(124, 58, 237, 0.18), transparent 32%),
            radial-gradient(circle at 82% 16%, rgba(37, 99, 235, 0.25), transparent 35%),
            linear-gradient(160deg, #050814, #0a0f1f 55%, #0b1430);
        color: var(--powertrack-text);
    }

    .block-container {
        padding: 2.4rem 2rem 3rem;
        background: var(--powertrack-surface);
        border-radius: 28px;
        box-shadow: 0 32px 80px rgba(5, 8, 20, 0.72);
        border: 1px solid var(--powertrack-border);
        backdrop-filter: blur(28px);
    }

    .hero-banner {
        background: linear-gradient(120deg, #7c3aed, #2563eb 70%);
        border-radius: 24px;
        padding: 1.9rem 2.1rem;
        color: #ffffff;
        box-shadow: 0 28px 70px rgba(37, 99, 235, 0.45);
        margin-bottom: 1.7rem;
        border: 1px solid rgba(255, 255, 255, 0.14);
    }

    .hero-banner h1 {
        font-size: 2.25rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        letter-spacing: 0.01em;
    }

    .hero-banner p {
        font-size: 1.08rem;
        opacity: 0.94;
        margin: 0;
    }

    .metric-card, .stMetric {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.24), rgba(37, 99, 235, 0.28));
        padding: 1.05rem;
        border-radius: 18px;
        border: 1px solid var(--powertrack-border);
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04), 0 14px 32px rgba(4, 6, 20, 0.65);
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--powertrack-border);
        border-radius: 18px;
        background: var(--powertrack-surface-2);
        margin-bottom: 0.9rem;
        box-shadow: 0 20px 40px rgba(5, 8, 22, 0.55);
    }

    div[data-testid="stExpander"] > div:first-child {
        background: linear-gradient(120deg, rgba(124, 58, 237, 0.22), rgba(37, 99, 235, 0.18));
        border-radius: 16px 16px 0 0;
    }

    .stTabs [role="tablist"] {
        gap: 0.35rem;
        border-bottom: none;
        flex-wrap: wrap;
    }

    .stTabs [role="tablist"] button {
        border-radius: 999px;
        padding: 0.45rem 1.15rem;
        color: #f8fafc;
        border: 1px solid var(--powertrack-border);
        background: var(--tab-gradient, linear-gradient(120deg, rgba(124, 58, 237, 0.85), rgba(37, 99, 235, 0.85)));
        transition: all 0.25s ease;
        font-weight: 600;
        letter-spacing: 0.02em;
        box-shadow: 0 10px 22px rgba(5, 8, 22, 0.4);
    }

    .stTabs [role="tablist"] button:hover {
        filter: brightness(1.05);
        transform: translateY(-1px);
    }

    .stTabs [role="tablist"] button[aria-selected="true"] {
        border-color: var(--tab-accent, rgba(165, 180, 252, 0.8));
        box-shadow: var(--tab-shadow, 0 16px 36px rgba(5, 8, 22, 0.5));
        transform: translateY(-2px);
    }

    .stTabs [role="tabpanel"] {
        border: 1px solid var(--powertrack-border);
        border-radius: 22px;
        padding: 1rem 1.2rem;
        margin-top: 1.1rem;
        background: rgba(6, 10, 22, 0.72);
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
    }

    .good-lift {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: #0f172a;
        font-weight: 600;
        background: rgba(52, 211, 153, 0.9);
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.04em;
    }

    .bad-lift {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: #0f172a;
        font-weight: 600;
        background: rgba(248, 113, 113, 0.92);
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.04em;
    }

    .pending-lift {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: #f8fafc;
        font-weight: 600;
        background: rgba(148, 163, 184, 0.4);
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.04em;
    }

    .record-indicator {
        background: linear-gradient(120deg, #a5b4fc, #60a5fa);
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-weight: 700;
        color: #111827;
        display: inline-block;
        margin-top: 0.35rem;
    }

    .percentile-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(96, 165, 250, 0.18);
        border: 1px solid rgba(124, 58, 237, 0.45);
        color: #e0e7ff;
        padding: 0.4rem 0.75rem;
        border-radius: 999px;
        font-size: 0.85rem;
        margin: 0.35rem 0;
    }

    .referee-tip {
        background: rgba(76, 29, 149, 0.2);
        border-left: 4px solid #7c3aed;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        color: #e0e7ff;
    }

    .attempt-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.35rem 0;
        border-bottom: 1px dashed rgba(148, 163, 184, 0.18);
        font-size: 0.95rem;
    }

    .attempt-row:last-child {
        border-bottom: none;
    }

    .attempt-weight {
        font-weight: 600;
        color: #f8fafc;
    }

    .info-pill {
        background: rgba(96, 165, 250, 0.15);
        border: 1px solid rgba(96, 165, 250, 0.35);
        padding: 0.65rem 0.9rem;
        border-radius: 12px;
        color: #dbeafe;
        margin-bottom: 0.8rem;
    }

    .signature-highlight {
        background: linear-gradient(140deg, rgba(124, 58, 237, 0.78), rgba(37, 99, 235, 0.78));
        border-radius: 22px;
        padding: 1.05rem 1.3rem;
        margin-bottom: 1.2rem;
        color: #ffffff;
        box-shadow: 0 24px 52px rgba(3, 7, 18, 0.55);
    }

    .countdown-card {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.26), rgba(37, 99, 235, 0.28));
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 1.15rem 1.35rem;
        box-shadow: 0 24px 50px rgba(5, 8, 22, 0.65);
        margin-bottom: 1rem;
    }

    .alert-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.45rem 0.85rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .alert-chip.critical {
        background: rgba(248, 113, 113, 0.2);
        border: 1px solid rgba(248, 113, 113, 0.55);
        color: #fecaca;
    }

    .alert-chip.warning {
        background: rgba(251, 191, 36, 0.2);
        border: 1px solid rgba(251, 191, 36, 0.55);
        color: #fef3c7;
    }

    .alert-chip.ready {
        background: rgba(74, 222, 128, 0.18);
        border: 1px solid rgba(74, 222, 128, 0.5);
        color: #bbf7d0;
    }

    .plate-stack {
        display: flex;
        align-items: center;
        gap: 0.3rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
    }

    .plate-piece {
        width: 30px;
        height: 66px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 600;
        color: #0f172a;
        box-shadow: inset 0 0 0 2px rgba(15, 23, 42, 0.15);
    }

    .plate-piece.small {
        height: 46px;
    }

    .bar-sleeve {
        width: 22px;
        height: 70px;
        border-radius: 8px;
        background: linear-gradient(180deg, #cbd5f5, #94a3b8);
        box-shadow: inset 0 0 0 2px rgba(15, 23, 42, 0.25);
    }

    .collar-piece {
        width: 16px;
        height: 70px;
        border-radius: 6px;
        background: linear-gradient(180deg, #404040, #111827);
        box-shadow: inset 0 0 0 2px rgba(15, 23, 42, 0.45);
    }

    .warmup-phase-card {
        border: 1px solid var(--powertrack-border);
        border-radius: 14px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.65rem;
        background: var(--powertrack-surface-2);
    }

    .warmup-phase-card h4 {
        margin: 0 0 0.35rem;
        font-size: 1rem;
        color: #c7d2fe;
    }

    .rack-order {
        border: 1px dashed rgba(148, 163, 184, 0.45);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        background: rgba(30, 41, 59, 0.75);
    }

    .chat-shell {
        border: 1px solid var(--powertrack-border);
        background: var(--powertrack-surface-2);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 18px 40px rgba(5, 8, 22, 0.45);
    }

    .chat-suggestions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 0.6rem;
    }

    .chat-suggestions button {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.24), rgba(37, 99, 235, 0.3));
        color: #e5e7eb;
        border: 1px solid var(--powertrack-border);
        border-radius: 999px;
        padding: 0.35rem 0.85rem;
        font-weight: 600;
        font-size: 0.9rem;
    }

    .chat-suggestions button:hover {
        filter: brightness(1.06);
    }

    [data-testid="stChatMessage"] {
        background: var(--powertrack-surface-2);
        border: 1px solid var(--powertrack-border);
        border-radius: 16px;
        padding: 0.85rem 0.9rem;
        box-shadow: 0 12px 28px rgba(5, 8, 22, 0.45);
    }

    [data-testid="stChatMessage"] + [data-testid="stChatMessage"] {
        margin-top: 0.6rem;
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 1.2rem 1rem 2rem;
        }
        .hero-banner h1 {
            font-size: 1.65rem;
        }
        .hero-banner p {
            font-size: 0.98rem;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# IPF World Records (Classic/Raw) - Based on latest available data
IPF_WORLD_RECORDS_MEN = {
    "59": {"squat": 250.0, "bench": 165.0, "deadlift": 300.0, "total": 695.0},
    "66": {"squat": 272.5, "bench": 185.0, "deadlift": 310.0, "total": 745.0},
    "74": {"squat": 310.0, "bench": 217.5, "deadlift": 357.5, "total": 860.0},
    "83": {"squat": 327.5, "bench": 235.0, "deadlift": 370.0, "total": 900.0},
    "93": {"squat": 350.0, "bench": 246.0, "deadlift": 400.0, "total": 950.0},
    "105": {"squat": 380.0, "bench": 260.0, "deadlift": 410.0, "total": 1015.0},
    "120": {"squat": 415.0, "bench": 280.0, "deadlift": 415.5, "total": 1050.0},
    "120+": {"squat": 450.0, "bench": 300.0, "deadlift": 430.0, "total": 1105.0}
}

IPF_WORLD_RECORDS_WOMEN = {
    "47": {"squat": 175.0, "bench": 102.0, "deadlift": 215.0, "total": 461.5},
    "52": {"squat": 182.5, "bench": 107.5, "deadlift": 227.5, "total": 500.0},
    "57": {"squat": 200.0, "bench": 120.0, "deadlift": 242.5, "total": 540.0},
    "63": {"squat": 220.0, "bench": 135.0, "deadlift": 260.0, "total": 590.0},
    "69": {"squat": 235.0, "bench": 145.0, "deadlift": 275.0, "total": 630.0},
    "76": {"squat": 250.0, "bench": 155.0, "deadlift": 290.0, "total": 670.0},
    "84": {"squat": 270.0, "bench": 165.0, "deadlift": 313.0, "total": 715.0},
    "84+": {"squat": 290.0, "bench": 175.0, "deadlift": 330.0, "total": 755.0}
}

# USAPL American Records (approximate based on recent data)
USAPL_AMERICAN_RECORDS_MEN = {
    "59": {"squat": 242.5, "bench": 160.0, "deadlift": 287.5, "total": 667.5},
    "66": {"squat": 265.0, "bench": 180.0, "deadlift": 305.0, "total": 730.0},
    "74": {"squat": 300.0, "bench": 210.0, "deadlift": 345.0, "total": 835.0},
    "83": {"squat": 320.0, "bench": 230.0, "deadlift": 365.0, "total": 890.0},
    "93": {"squat": 342.5, "bench": 240.0, "deadlift": 390.0, "total": 935.0},
    "105": {"squat": 370.0, "bench": 255.0, "deadlift": 405.0, "total": 995.0},
    "120": {"squat": 405.0, "bench": 275.0, "deadlift": 410.0, "total": 1035.0},
    "120+": {"squat": 440.0, "bench": 295.0, "deadlift": 420.0, "total": 1080.0}
}

USAPL_AMERICAN_RECORDS_WOMEN = {
    "47": {"squat": 167.5, "bench": 95.0, "deadlift": 205.0, "total": 445.0},
    "52": {"squat": 177.5, "bench": 102.5, "deadlift": 220.0, "total": 485.0},
    "57": {"squat": 192.5, "bench": 115.0, "deadlift": 235.0, "total": 525.0},
    "63": {"squat": 212.5, "bench": 130.0, "deadlift": 252.5, "total": 575.0},
    "69": {"squat": 227.5, "bench": 140.0, "deadlift": 267.5, "total": 615.0},
    "76": {"squat": 242.5, "bench": 150.0, "deadlift": 282.5, "total": 652.5},
    "84": {"squat": 262.5, "bench": 160.0, "deadlift": 305.0, "total": 695.0},
    "84+": {"squat": 280.0, "bench": 170.0, "deadlift": 320.0, "total": 735.0}
}

ATTEMPT_WEIGHT_COLUMNS = [
    f"{lift} {idx}" for lift in ("Squat", "Bench", "Deadlift") for idx in range(1, 4)
]
ATTEMPT_RESULT_COLUMNS = [
    f"{prefix}{idx}HRef" for prefix in ("S", "B", "D") for idx in range(1, 4)
]
NUMERIC_ZERO_COLUMNS = [
    "Best Squat",
    "Best Bench",
    "Best Deadlift",
    "Total",
    "Dots Points",
    "IPF Points",
    "Glossbrenner Points",
]
OPTIONAL_STRING_COLUMNS = [
    "Weight Class",
    "State/Province",
    "Country",
    "Team",
]
OPTIONAL_NUMERIC_COLUMNS = [
    "Exact Age",
]

POINT_COMPUTERS = {
    "Dots Points": calculate_dots,
    "IPF Points": calculate_ipf_gl,
    "Glossbrenner Points": calculate_glossbrenner,
}

UnitSystem = Literal["kg", "lb"]
KG_TO_LB = 2.2046226218
UNIT_LABELS = {"kg": "Kilograms", "lb": "Pounds"}
BASIC_AUTH_ENV = "POWERTRACK_BASIC_AUTH"
ROLE_CODES = {
    "Coach": "POWERTRACK_COACH_CODE",
    "Director": "POWERTRACK_DIRECTOR_CODE",
}
DEFAULT_ROLE = "Spectator"
ROLE_PAGE_MAP = {
    "Spectator": [
        "Meet Overview",
        "Lifter Attempts Breakdown",
        "Scoreboard",
        "Lifter Cards",
        "Lifter Analysis",
        "Live Simulation",
        "Spectator Chat",
        "Rules & Guide",
    ],
    "Coach": [
        "Meet Overview",
        "Lifter Attempts Breakdown",
        "Scoreboard",
        "Lifter Cards",
        "Lifter Analysis",
        "Warm-Up Room",
        "Coach Tools",
        "Live Simulation",
        "Spectator Chat",
        "Rules & Guide",
    ],
    "Director": [
        "Meet Overview",
        "Lifter Attempts Breakdown",
        "Scoreboard",
        "Lifter Cards",
        "Lifter Analysis",
        "Warm-Up Room",
        "Coach Tools",
        "LiftingCast Explorer",
        "Live Simulation",
        "Spectator Chat",
        "Rules & Guide",
    ],
}
WEBHOOK_URL_ENV = "POWERTRACK_WEBHOOK_URL"
DEFAULT_AUTO_REFRESH_SECONDS = 45

PAGE_COLOR_MAP = {
    "Meet Overview": {
        "gradient": "linear-gradient(120deg, #7c3aed, #2563eb)",
        "shadow": "0 24px 60px rgba(37, 99, 235, 0.35)",
        "accent": "#a5b4fc",
    },
    "Lifter Attempts Breakdown": {
        "gradient": "linear-gradient(120deg, #4338ca, #1d4ed8)",
        "shadow": "0 24px 60px rgba(29, 78, 216, 0.4)",
        "accent": "#60a5fa",
    },
    "Scoreboard": {
        "gradient": "linear-gradient(120deg, #312e81, #7c3aed)",
        "shadow": "0 24px 60px rgba(124, 58, 237, 0.32)",
        "accent": "#c4b5fd",
    },
    "Lifter Cards": {
        "gradient": "linear-gradient(120deg, #1e3a8a, #4c1d95)",
        "shadow": "0 24px 60px rgba(67, 56, 202, 0.34)",
        "accent": "#93c5fd",
    },
    "Lifter Analysis": {
        "gradient": "linear-gradient(120deg, #1d4ed8, #6366f1)",
        "shadow": "0 24px 60px rgba(79, 70, 229, 0.36)",
        "accent": "#a5b4fc",
    },
    "Warm-Up Room": {
        "gradient": "linear-gradient(120deg, #312e81, #2563eb)",
        "shadow": "0 24px 60px rgba(49, 46, 129, 0.35)",
        "accent": "#93c5fd",
    },
    "Coach Tools": {
        "gradient": "linear-gradient(120deg, #4338ca, #2563eb)",
        "shadow": "0 24px 60px rgba(37, 99, 235, 0.32)",
        "accent": "#bfdbfe",
    },
    "LiftingCast Explorer": {
        "gradient": "linear-gradient(120deg, #0ea5e9, #4338ca)",
        "shadow": "0 24px 60px rgba(14, 165, 233, 0.32)",
        "accent": "#7dd3fc",
    },
    "Live Simulation": {
        "gradient": "linear-gradient(120deg, #7c3aed, #0ea5e9)",
        "shadow": "0 24px 60px rgba(124, 58, 237, 0.32)",
        "accent": "#c4b5fd",
    },
    "Rules & Guide": {
        "gradient": "linear-gradient(120deg, #4c1d95, #1e3a8a)",
        "shadow": "0 24px 60px rgba(76, 29, 149, 0.34)",
        "accent": "#c4b5fd",
    },
    "Spectator Chat": {
        "gradient": "linear-gradient(120deg, #7c3aed, #1d4ed8)",
        "shadow": "0 24px 60px rgba(76, 29, 149, 0.35)",
        "accent": "#a5b4fc",
    },
}

CHAT_STARTER_QUESTIONS = [
    "What do the red and white lights mean?",
    "How do the squat, bench, and deadlift commands work?",
    "What makes a smart opener attempt?",
    "How are lifters ranked when totals tie?",
]

COMMON_CHAT_QA = [
    {
        "keywords": ["white light", "red light", "lights", "judges"],
        "answer": (
            "Three white lights mean the lift counts. Two or more red lights mean no lift. "
            "Judges watch depth on squat, the pause on bench, and the lockout plus control on deadlift."
        ),
    },
    {
        "keywords": ["command", "commands", "ref"],
        "answer": (
            "Squat: wait for 'squat' to start and 'rack' to finish. "
            "Bench: wait for 'start', pause until 'press', then rack on 'rack'. "
            "Deadlift: lift when ready, hold still, and wait for the 'down' call."
        ),
    },
    {
        "keywords": ["dot", "dots", "relative strength", "score"],
        "answer": (
            "DOTS compares lifters of different bodyweights using their total and weight. "
            "Higher is better; ~380+ is strong for women, ~450+ is national level for men, and 500+ is world class."
        ),
    },
    {
        "keywords": ["opener", "first attempt", "start weight"],
        "answer": (
            "A good opener is something you can triple on a training day—around 88-92% of your best single. "
            "It should move fast, calm nerves, and set up jumps to a second attempt you’re confident in."
        ),
    },
    {
        "keywords": ["tie", "tiebreak", "same total"],
        "answer": (
            "If totals tie, the lighter lifter wins. If bodyweight is also the same, the lifter who weighed in earlier wins."
        ),
    },
]

LIFTINGCAST_SAMPLE_MEETS = [
    {"label": "LiftingCast Demo Meet", "id": "mclafu3vkkgr"},
]

SIMULATION_SCENARIOS = [
    {
        "label": "Squat Openers",
        "description": "Everyone is finding depth and getting nerves under control. Expect fast white lights.",
        "now": "Flight A opener rotation is underway. Platform clock is moving quickly.",
        "alerts": [
            "Next on deck: Lila Zhang (150 kg).",
            "Spotter change after this lifter.",
        ],
        "attempts": [
            {"name": "Alicia Torres", "lift": "Squat", "attempt": "1", "weight": 172.5, "result": "good", "clock": "00:45"},
            {"name": "Lila Zhang", "lift": "Squat", "attempt": "1", "weight": 150.0, "result": "pending", "clock": "01:00"},
            {"name": "Mariana Ruiz", "lift": "Squat", "attempt": "1", "weight": 165.0, "result": "good", "clock": "00:52"},
            {"name": "Chase Grantham", "lift": "Squat", "attempt": "1", "weight": 190.0, "result": "good", "clock": "00:48"},
            {"name": "Evan Brooks", "lift": "Squat", "attempt": "1", "weight": 210.0, "result": "no lift", "clock": "00:40"},
        ],
        "leaderboard": [
            {"name": "Chase Grantham", "subtotal": 190.0, "place": 1, "note": "+10 kg over seed"},
            {"name": "Evan Brooks", "subtotal": 0.0, "place": 5, "note": "Needs 2nd attempt to stay alive"},
            {"name": "Alicia Torres", "subtotal": 172.5, "place": 2, "note": "Depth confirmed, clean start"},
        ],
    },
    {
        "label": "Bench Second Attempts",
        "description": "Jumps get smaller. Coaches are protecting totals and chasing chips.",
        "now": "Bench bar is at 17 cm rack height. Final lifter is chalked.",
        "alerts": [
            "Potential American record chip coming from Evan Brooks.",
            "Bar change after 3 more attempts.",
        ],
        "attempts": [
            {"name": "Alicia Torres", "lift": "Bench", "attempt": "2", "weight": 97.5, "result": "good", "clock": "00:42"},
            {"name": "Lila Zhang", "lift": "Bench", "attempt": "2", "weight": 85.0, "result": "good", "clock": "00:39"},
            {"name": "Mariana Ruiz", "lift": "Bench", "attempt": "2", "weight": 92.5, "result": "no lift", "clock": "00:35"},
            {"name": "Chase Grantham", "lift": "Bench", "attempt": "2", "weight": 107.5, "result": "good", "clock": "00:37"},
            {"name": "Evan Brooks", "lift": "Bench", "attempt": "2", "weight": 137.5, "result": "pending", "clock": "01:00"},
        ],
        "leaderboard": [
            {"name": "Chase Grantham", "subtotal": 297.5, "place": 1, "note": "+7.5 kg lead"},
            {"name": "Evan Brooks", "subtotal": 210.0, "place": 4, "note": "Needs bench make to stay in podium race"},
            {"name": "Alicia Torres", "subtotal": 270.0, "place": 2, "note": "Consistent across attempts"},
        ],
    },
    {
        "label": "Final Deadlift Showdown",
        "description": "Totals are set. Lifters are reaching for medals and records.",
        "now": "Clock reset to 60 seconds. Third attempts only.",
        "alerts": [
            "Records in play: Alicia Torres (total), Evan Brooks (deadlift).",
            "Coach change requests closed.",
        ],
        "attempts": [
            {"name": "Alicia Torres", "lift": "Deadlift", "attempt": "3", "weight": 207.5, "result": "pending", "clock": "00:55"},
            {"name": "Lila Zhang", "lift": "Deadlift", "attempt": "3", "weight": 192.5, "result": "good", "clock": "00:44"},
            {"name": "Mariana Ruiz", "lift": "Deadlift", "attempt": "3", "weight": 215.0, "result": "no lift", "clock": "00:33"},
            {"name": "Chase Grantham", "lift": "Deadlift", "attempt": "3", "weight": 240.0, "result": "pending", "clock": "00:58"},
            {"name": "Evan Brooks", "lift": "Deadlift", "attempt": "3", "weight": 265.0, "result": "good", "clock": "00:47"},
        ],
        "leaderboard": [
            {"name": "Chase Grantham", "subtotal": 537.5, "place": 1, "note": "Lead vulnerable if Alicia hits 207.5"},
            {"name": "Alicia Torres", "subtotal": 480.0, "place": 2, "note": "Total record attempt on deck"},
            {"name": "Evan Brooks", "subtotal": 475.0, "place": 3, "note": "Pulled into podium with last deadlift"},
        ],
    },
]


DEFAULT_OPENIPF_CSV = (
    Path(__file__).resolve().parents[1]
    / "openipf-2025-11-08"
    / "openipf-2025-11-08-c1c550e2.csv"
)
OPENIPF_MIN_SAMPLE_SIZE = 40


@st.cache_resource(show_spinner=False)
def _get_openai_client(api_key: Optional[str]):
    """Instantiate an OpenAI client if the package and API key are available."""
    if not OpenAI or not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def _get_meet_snapshot(df: pd.DataFrame, metadata: Dict[str, Any], unit_system: UnitSystem) -> str:
    """Lightweight context string for AI prompts and fallbacks."""
    if df is None or df.empty:
        return ""

    pieces: List[str] = []
    meet_name = metadata.get("name") or "this meet"
    pieces.append(f"{len(df)} athletes are on the roster for {meet_name}.")

    totals = pd.to_numeric(df.get("Total"), errors="coerce") if "Total" in df else pd.Series(dtype=float)
    if not totals.empty and totals.notna().any():
        leader_idx = totals.idxmax()
        leader_row = df.loc[leader_idx]
        leader_name = leader_row.get("Name", "Top lifter")
        leader_total = format_weight_display(leader_row.get("Total"), unit_system)
        weight_class = leader_row.get("Weight Class")
        class_text = f" in the {weight_class} class" if pd.notna(weight_class) else ""
        pieces.append(f"{leader_name} leads at {leader_total}{class_text}.")

    meet_date = metadata.get("date")
    if meet_date:
        pieces.append(f"Schedule: {meet_date}.")

    return " ".join(pieces)


def _match_common_question(question: str) -> Optional[str]:
    query = (question or "").lower()
    for entry in COMMON_CHAT_QA:
        if any(keyword in query for keyword in entry["keywords"]):
            return entry["answer"]
    return None


def _fallback_chat_answer(question: str, df: pd.DataFrame, metadata: Dict[str, Any], unit_system: UnitSystem) -> str:
    matched = _match_common_question(question)
    snapshot = _get_meet_snapshot(df, metadata, unit_system)
    if matched:
        return f"{matched} {'Here is the current picture: ' + snapshot if snapshot else ''}".strip()

    if snapshot:
        return (
            f"{snapshot} Ask me about commands, how scoring works, or what the referee lights mean—"
            "I'll keep it beginner-friendly."
        )

    return (
        "Ask me anything about the lifts, judging lights, or how lifters move up the rankings. "
        "I’ll keep answers short and easy to follow."
    )


def _build_chat_messages(
    question: str,
    df: pd.DataFrame,
    metadata: Dict[str, Any],
    unit_system: UnitSystem,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    history = history or []
    snapshot = _get_meet_snapshot(df, metadata, unit_system)
    system_prompt = (
        "You are PowerTrack's concierge chatbot for spectators. "
        "Answer in 2-3 sentences, use plain language, and explain any jargon briefly. "
        "Be concise, friendly, and safety-minded."
    )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if snapshot:
        messages.append({"role": "system", "content": f"Meet snapshot: {snapshot}"})

    for message in history[-4:]:
        role = message.get("role", "user")
        content = message.get("content", "")
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question})
    return messages


def get_chat_completion(
    question: str,
    df: pd.DataFrame,
    metadata: Dict[str, Any],
    unit_system: UnitSystem,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, bool, Optional[str]]:
    """Return answer, whether live AI was used, and any error text."""
    fallback = _fallback_chat_answer(question, df, metadata, unit_system)
    api_key = os.getenv("OPENAI_API_KEY")
    client = _get_openai_client(api_key)
    if not client:
        return fallback, False, None

    messages = _build_chat_messages(question, df, metadata, unit_system, history)
    model = os.getenv("POWERTRACK_CHAT_MODEL", "gpt-4o")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.35,
            max_tokens=260,
        )
        content = response.choices[0].message.content if response.choices else None
        if content:
            return content.strip(), True, None
    except Exception as exc:  # pragma: no cover - defensive logging for manual runs
        return fallback, False, str(exc)

    return fallback, False, "No content returned from OpenAI."


@dataclass(frozen=True)
class LiftPercentileStats:
    count: int
    mean: float
    median: float
    top25: float
    top10: float
    top5: float
    top1: float
    distribution: np.ndarray

    def percentile_of(self, lift_value: float) -> Tuple[float, int]:
        if self.count == 0:
            return 0.0, 0
        values = self.distribution
        idx_le = int(np.searchsorted(values, lift_value, side="right"))
        percentile = (idx_le / self.count) * 100.0
        idx_ge = int(np.searchsorted(values, lift_value, side="left"))
        count_at_or_above = max(self.count - idx_ge, 0)
        return percentile, count_at_or_above


@dataclass(frozen=True)
class OpenIPFReferenceData:
    metadata: Dict[str, Any]
    stats: Dict[str, Dict[str, Dict[str, LiftPercentileStats]]]

    def get_stats(self, gender: str, weight_class: str, lift_name: str) -> Optional[LiftPercentileStats]:
        gender_key = (gender or "").upper()
        class_key = weight_class or ""
        lift_key = lift_name.title()
        return self.stats.get(gender_key, {}).get(class_key, {}).get(lift_key)


def _infer_weight_class_value(bodyweight: Optional[float], weight_class_text: Optional[str]) -> Optional[float]:
    """
    Derive a numeric proxy for weight class using actual body weight.
    We intentionally ignore provided class text to normalize into current IPF classes.
    """
    if bodyweight is not None and not pd.isna(bodyweight):
        return float(bodyweight)
    return None


def _resolve_openipf_csv_path(csv_override: Optional[str] = None) -> Optional[Path]:
    env_path = os.getenv("POWERTRACK_OPENIPF_CSV")
    candidate = Path(csv_override or env_path or DEFAULT_OPENIPF_CSV)
    if candidate.exists():
        return candidate
    return None


def _build_openipf_reference(df: pd.DataFrame, csv_path: Path) -> Optional[OpenIPFReferenceData]:
    if df.empty:
        return None

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"].notna()]
    if df.empty:
        return None

    # Use all available years in the CSV (no recency cutoff).
    cutoff_date = df["Date"].min()

    df["Gender"] = np.where(df["Sex"] == "M", "MALE", "FEMALE")
    resolved_weight = df.apply(
        lambda row: _infer_weight_class_value(row["BodyweightKg"], row["WeightClassKg"]),
        axis=1,
    )
    df["ResolvedWeight"] = resolved_weight
    df["WeightClassCategory"] = [
        get_weight_class_category(weight, gender)
        for weight, gender in zip(df["ResolvedWeight"], df["Gender"])
    ]
    df = df[df["WeightClassCategory"] != "Unknown"].copy()
    if df.empty:
        return None

    for column in ["Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg", "TotalKg"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    stats_map: Dict[str, Dict[str, Dict[str, Dict[str, LiftPercentileStats]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    lift_columns = {
        "Squat": "Best3SquatKg",
        "Bench": "Best3BenchKg",
        "Deadlift": "Best3DeadliftKg",
        "Total": "TotalKg",
    }

    for lift_name, column in lift_columns.items():
        valid = df[["Gender", "WeightClassCategory", "EquipType", column]].dropna()
        if valid.empty:
            continue
        grouped = valid.groupby(["Gender", "WeightClassCategory", "EquipType"])[column]
        for (gender, weight_class, equip), series in grouped:
            values = series.to_numpy(dtype=np.float32)
            count = len(values)
            if count < OPENIPF_MIN_SAMPLE_SIZE:
                continue
            sorted_values = np.sort(values)
            stats_map[gender][weight_class][equip][lift_name] = LiftPercentileStats(
                count=count,
                mean=float(np.mean(sorted_values)),
                median=float(np.median(sorted_values)),
                top25=float(np.percentile(sorted_values, 75)),
                top10=float(np.percentile(sorted_values, 90)),
                top5=float(np.percentile(sorted_values, 95)),
                top1=float(np.percentile(sorted_values, 99)),
                distribution=sorted_values,
            )

    if not stats_map:
        return None

    stats_dict = {
        gender: {
            weight_class: {equip: dict(lifts) for equip, lifts in equip_map.items()}
            for weight_class, equip_map in weight_map.items()
        }
        for gender, weight_map in stats_map.items()
    }

    metadata = {
        "csv_path": str(csv_path),
        "start_date": df["Date"].min().strftime("%Y-%m-%d"),
        "end_date": df["Date"].max().strftime("%Y-%m-%d"),
        "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
        "period_label": f"{df['Date'].min().year}-{df['Date'].max().year}",
        "filtered_row_count": int(len(df)),
    }
    return OpenIPFReferenceData(metadata=metadata, stats=stats_dict)


@st.cache_resource(show_spinner=True)
def load_openipf_reference_data(csv_override: Optional[str] = None) -> Optional[OpenIPFReferenceData]:
    csv_path = _resolve_openipf_csv_path(csv_override)
    if csv_path is None:
        return None

    usecols = [
        "Sex",
        "Event",
        "Equipment",
        "BodyweightKg",
        "WeightClassKg",
        "Best3SquatKg",
        "Best3BenchKg",
        "Best3DeadliftKg",
        "TotalKg",
        "Date",
    ]

    try:
        df = pd.read_csv(csv_path, usecols=usecols, parse_dates=["Date"])
    except FileNotFoundError:
        return None
    except Exception as exc:  # pragma: no cover - defensive logging for manual runs
        st.warning(f"Unable to load OpenIPF reference data: {exc}")
        return None

    df = df[df["Event"] == "SBD"]
    df = df[df["Sex"].isin(["M", "F"])]

    # Split classic vs equipped; build stats for both so the app can distinguish.
    df["EquipType"] = np.where(df["Equipment"].str.lower().eq("raw"), "RAW", "EQUIPPED")
    if df.empty:
        return None

    return _build_openipf_reference(df, csv_path)


def get_openipf_reference_summary() -> Optional[str]:
    reference = load_openipf_reference_data()
    if not reference:
        return None
    meta = reference.metadata
    sample_size = meta.get("filtered_row_count")
    period_label = meta.get("period_label")
    if sample_size:
        sample_text = f"{sample_size:,}"
    else:
        sample_text = "thousands of"
    period_text = period_label or "the last decade"
    return f"Percentiles benchmark {sample_text} Raw SBD entries from OpenIPF.org ({period_text})."


def convert_weight_value(value: Optional[float], unit_system: UnitSystem) -> float:
    """Convert a single numeric value for display without mutating source data."""
    if value is None or pd.isna(value):
        return np.nan
    if unit_system == "lb":
        return value * KG_TO_LB
    return float(value)


def format_weight_display(
    value: Optional[float],
    unit_system: UnitSystem,
    *,
    decimals: int = 1,
    show_units: bool = True,
) -> str:
    converted = convert_weight_value(value, unit_system)
    if pd.isna(converted):
        return "—"
    suffix = "lb" if unit_system == "lb" else "kg"
    formatted = f"{converted:.{decimals}f}"
    return f"{formatted} {suffix}" if show_units else formatted


def convert_series_for_display(series: pd.Series, unit_system: UnitSystem) -> pd.Series:
    """Return a converted copy of a numeric series for charting in the selected units."""
    numeric = pd.to_numeric(series, errors="coerce")
    if unit_system == "kg":
        return numeric
    return numeric.apply(lambda v: convert_weight_value(v, unit_system))


FALLBACK_OPENIPF_PERCENTILES: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {
    "FEMALE": {
        "47": {
            "Squat": {"median": 115, "top25": 130, "elite10": 145},
            "Bench": {"median": 70, "top25": 80, "elite10": 90},
            "Deadlift": {"median": 135, "top25": 150, "elite10": 165},
            "Total": {"median": 320, "top25": 355, "elite10": 390},
        },
        "52": {
            "Squat": {"median": 130, "top25": 145, "elite10": 162},
            "Bench": {"median": 75, "top25": 85, "elite10": 95},
            "Deadlift": {"median": 150, "top25": 170, "elite10": 185},
            "Total": {"median": 360, "top25": 395, "elite10": 430},
        },
        "57": {
            "Squat": {"median": 140, "top25": 160, "elite10": 180},
            "Bench": {"median": 80, "top25": 90, "elite10": 102},
            "Deadlift": {"median": 165, "top25": 185, "elite10": 205},
            "Total": {"median": 385, "top25": 425, "elite10": 465},
        },
        "63": {
            "Squat": {"median": 155, "top25": 175, "elite10": 195},
            "Bench": {"median": 90, "top25": 100, "elite10": 110},
            "Deadlift": {"median": 180, "top25": 205, "elite10": 225},
            "Total": {"median": 420, "top25": 470, "elite10": 515},
        },
        "69": {
            "Squat": {"median": 165, "top25": 185, "elite10": 205},
            "Bench": {"median": 95, "top25": 107, "elite10": 118},
            "Deadlift": {"median": 200, "top25": 225, "elite10": 245},
            "Total": {"median": 455, "top25": 505, "elite10": 550},
        },
        "76": {
            "Squat": {"median": 177, "top25": 197, "elite10": 215},
            "Bench": {"median": 102, "top25": 115, "elite10": 127},
            "Deadlift": {"median": 210, "top25": 240, "elite10": 260},
            "Total": {"median": 480, "top25": 540, "elite10": 585},
        },
        "84": {
            "Squat": {"median": 185, "top25": 205, "elite10": 225},
            "Bench": {"median": 105, "top25": 118, "elite10": 130},
            "Deadlift": {"median": 220, "top25": 250, "elite10": 275},
            "Total": {"median": 505, "top25": 560, "elite10": 610},
        },
        "84+": {
            "Squat": {"median": 190, "top25": 215, "elite10": 240},
            "Bench": {"median": 110, "top25": 125, "elite10": 140},
            "Deadlift": {"median": 225, "top25": 260, "elite10": 290},
            "Total": {"median": 520, "top25": 585, "elite10": 640},
        },
    },
    "MALE": {
        "59": {
            "Squat": {"median": 185, "top25": 205, "elite10": 225},
            "Bench": {"median": 120, "top25": 132, "elite10": 145},
            "Deadlift": {"median": 210, "top25": 235, "elite10": 255},
            "Total": {"median": 500, "top25": 550, "elite10": 595},
        },
        "66": {
            "Squat": {"median": 205, "top25": 225, "elite10": 245},
            "Bench": {"median": 130, "top25": 142, "elite10": 155},
            "Deadlift": {"median": 230, "top25": 255, "elite10": 280},
            "Total": {"median": 535, "top25": 585, "elite10": 635},
        },
        "74": {
            "Squat": {"median": 225, "top25": 247, "elite10": 270},
            "Bench": {"median": 145, "top25": 160, "elite10": 175},
            "Deadlift": {"median": 250, "top25": 280, "elite10": 305},
            "Total": {"median": 575, "top25": 635, "elite10": 685},
        },
        "83": {
            "Squat": {"median": 240, "top25": 265, "elite10": 290},
            "Bench": {"median": 160, "top25": 175, "elite10": 190},
            "Deadlift": {"median": 275, "top25": 305, "elite10": 330},
            "Total": {"median": 620, "top25": 690, "elite10": 745},
        },
        "93": {
            "Squat": {"median": 255, "top25": 282, "elite10": 308},
            "Bench": {"median": 167, "top25": 182, "elite10": 198},
            "Deadlift": {"median": 285, "top25": 320, "elite10": 345},
            "Total": {"median": 655, "top25": 725, "elite10": 785},
        },
        "105": {
            "Squat": {"median": 270, "top25": 300, "elite10": 325},
            "Bench": {"median": 175, "top25": 192, "elite10": 208},
            "Deadlift": {"median": 300, "top25": 335, "elite10": 360},
            "Total": {"median": 690, "top25": 765, "elite10": 825},
        },
        "120": {
            "Squat": {"median": 290, "top25": 320, "elite10": 345},
            "Bench": {"median": 185, "top25": 205, "elite10": 220},
            "Deadlift": {"median": 315, "top25": 350, "elite10": 380},
            "Total": {"median": 720, "top25": 800, "elite10": 865},
        },
        "120+": {
            "Squat": {"median": 305, "top25": 340, "elite10": 370},
            "Bench": {"median": 195, "top25": 215, "elite10": 235},
            "Deadlift": {"median": 330, "top25": 365, "elite10": 400},
            "Total": {"median": 750, "top25": 835, "elite10": 900},
        },
    },
}


RARITY_COUNTS = {
    "top1": 15,
    "top5": 60,
    "top10": 180,
    "top25": 600,
}


def get_world_record_value(weight_class: str, lift_name: str, gender: str) -> Optional[float]:
    """Fetch the IPF world record for the given lift."""
    record_book = IPF_WORLD_RECORDS_MEN if (gender or "").upper() == "MALE" else IPF_WORLD_RECORDS_WOMEN
    entry = record_book.get(weight_class or "", {})
    return entry.get(lift_name.lower())


def evaluate_percentile(
    gender: str,
    weight_class: str,
    lift_name: str,
    lift_value: Optional[float],
    unit_system: UnitSystem = "kg",
) -> Dict[str, Optional[float]]:
    """Return structured percentile and peer-count data for a lift."""
    lift_display = format_weight_display(lift_value, unit_system) if lift_value is not None else "—"
    if lift_value is None or pd.isna(lift_value):
        return {
            "discipline": lift_name.title(),
            "rank": 999,
            "label": "Unranked",
            "detail": "Awaiting OpenIPF percentile reference.",
            "full_text": None,
            "performance_ratio": 0.0,
            "threshold_value": None,
            "record_note": None,
            "lift_display": lift_display,
        }

    record_note = None
    record_comp = compare_to_records(lift_name.lower(), lift_value, gender, weight_class)
    if record_comp:
        ipf_delta = record_comp.get("ipf_delta")
        if ipf_delta:
            delta_display = format_weight_display(abs(ipf_delta), unit_system)
            record_note = (
                f"{delta_display} above the IPF world record for this class."
                if ipf_delta > 0
                else f"{delta_display} shy of the IPF world record."
            )

    profile = _evaluate_with_openipf_reference(
        gender, weight_class, lift_name, lift_value, unit_system, lift_display
    )
    if profile:
        profile["record_note"] = profile.get("record_note") or record_note
        return profile

    profile = _evaluate_from_percentile_table(
        gender, weight_class, lift_name, lift_value, unit_system, lift_display
    )
    if record_note:
        profile["record_note"] = record_note
    return profile


def _evaluate_with_openipf_reference(
    gender: str,
    weight_class: str,
    lift_name: str,
    lift_value: float,
    unit_system: UnitSystem,
    lift_display: str,
) -> Optional[Dict[str, Optional[float]]]:
    reference = load_openipf_reference_data()
    if not reference:
        return None
    stats = reference.get_stats(gender, weight_class, lift_name)
    if not stats:
        return None

    percentile, count_at_or_above = stats.percentile_of(lift_value)
    percentile = float(np.clip(percentile, 0.0, 100.0))
    total_count = stats.count

    label, rank, threshold_value = _select_reference_band(stats, lift_value)
    threshold_value = threshold_value or stats.median

    period_label = reference.metadata.get("period_label", "the last decade")
    avg_display = format_weight_display(stats.mean, unit_system)
    median_display = format_weight_display(stats.median, unit_system)
    percentile_label = f"{percentile:.1f}th percentile"

    peer_scope = f"{gender.title()} lifters in the {weight_class} class"
    if count_at_or_above <= 0:
        peer_sentence = f"No recorded Raw SBD {peer_scope} in this dataset has matched this lift yet."
    elif percentile >= 50:
        peer_sentence = (
            f"Only {count_at_or_above:,} of {total_count:,} tracked {peer_scope} "
            f"from {period_label} have lifted this much weight or more."
        )
    else:
        peer_sentence = (
            f"About {count_at_or_above:,} of {total_count:,} {peer_scope} "
            f"from {period_label} are already at or above this mark."
        )

    detail = (
        f"{percentile_label} within OpenIPF Raw SBD peers ({period_label}). "
        f"Average {lift_name.lower()} is {avg_display}; median is {median_display}. "
        f"{peer_sentence}"
    )
    return {
        "discipline": lift_name.title(),
        "rank": rank,
        "label": label,
        "detail": detail,
        "full_text": f"{label}: {lift_display}. {detail}",
        "performance_ratio": (lift_value / threshold_value) if threshold_value else 0.0,
        "threshold_value": threshold_value,
        "record_note": None,
        "lift_display": lift_display,
        "percentile": percentile,
        "median_value": stats.median,
    }


def _select_reference_band(stats: LiftPercentileStats, lift_value: float) -> Tuple[str, int, Optional[float]]:
    bands = [
        ("World-class (top 1%)", 1, stats.top1),
        ("Elite (top 5%)", 5, stats.top5),
        ("International (top 10%)", 10, stats.top10),
        ("National calibre (top 25%)", 25, stats.top25),
    ]
    for label, rank, threshold in bands:
        if threshold and not pd.isna(threshold) and lift_value >= threshold:
            return label, rank, threshold
    if lift_value >= stats.median:
        return "Above average", 50, stats.median
    return "Developing", 90, stats.median


def _evaluate_from_percentile_table(
    gender: str,
    weight_class: str,
    lift_name: str,
    lift_value: float,
    unit_system: UnitSystem,
    lift_display: str,
) -> Dict[str, Optional[float]]:
    gender_key = (gender or "").upper()
    class_key = weight_class or ""
    lift_key = lift_name.title()
    percentile_data = FALLBACK_OPENIPF_PERCENTILES.get(gender_key, {}).get(class_key, {}).get(lift_key)

    result = {
        "discipline": lift_name.title(),
        "rank": 999,
        "label": "Unranked",
        "detail": "Awaiting OpenIPF percentile reference.",
        "full_text": f"Unranked — lifted {lift_display}. Awaiting OpenIPF percentile reference.",
        "performance_ratio": 0.0,
        "threshold_value": None,
        "record_note": None,
        "lift_display": lift_display,
        "percentile": None,
        "median_value": None,
    }

    if not percentile_data:
        return result

    median = percentile_data.get("median")
    top25 = percentile_data.get("top25")
    top10 = percentile_data.get("elite10") or percentile_data.get("top10")
    world_record = get_world_record_value(class_key, lift_name.lower(), gender_key)

    thresholds = []
    if top10:
        if world_record:
            top1_threshold = max(top10, world_record * 0.97)
            delta = max(world_record - top10, 0)
            top5_threshold = top10 + 0.4 * delta if delta > 0 else top10 * 1.05
        else:
            top1_threshold = top10 * 1.05
            top5_threshold = top10 * 1.02

        thresholds.append(
            {
                "rank": 1,
                "label": "World-class (top 1%)",
                "threshold": top1_threshold,
                "detail": f"Only about {RARITY_COUNTS['top1']} lifters have cleared ≥ {format_weight_display(top1_threshold, unit_system)} (legacy OpenIPF snapshot).",
            }
        )
        thresholds.append(
            {
                "rank": 5,
                "label": "Elite (top 5%)",
                "threshold": top5_threshold,
                "detail": f"Approximately {RARITY_COUNTS['top5']} lifters have matched ≥ {format_weight_display(top5_threshold, unit_system)} (legacy OpenIPF snapshot).",
            }
        )
        thresholds.append(
            {
                "rank": 10,
                "label": "International (top 10%)",
                "threshold": top10,
                "detail": f"Roughly {RARITY_COUNTS['top10']} lifters sit above {format_weight_display(top10, unit_system)} (legacy OpenIPF snapshot).",
            }
        )
    if top25:
        thresholds.append(
            {
                "rank": 25,
                "label": "National calibre (top 25%)",
                "threshold": top25,
                "detail": f"About {RARITY_COUNTS['top25']} lifters have achieved ≥ {format_weight_display(top25, unit_system)} (legacy OpenIPF snapshot).",
            }
        )
    if median:
        thresholds.append(
            {
                "rank": 50,
                "label": "Above average",
                "threshold": median,
                "detail": f"Ahead of the historical OpenIPF median of {format_weight_display(median, unit_system)}.",
            }
        )

    for entry in thresholds:
        threshold_value = entry["threshold"]
        if threshold_value and lift_value >= threshold_value - 1e-6:
            detail = entry["detail"]
            return {
                "discipline": lift_name.title(),
                "rank": entry["rank"],
                "label": entry["label"],
                "detail": detail,
                "full_text": f"{entry['label']}: lifted {lift_display}. {detail}",
                "performance_ratio": (lift_value / threshold_value) if threshold_value else 0.0,
                "threshold_value": threshold_value,
                "record_note": None,
                "lift_display": lift_display,
                "percentile": None,
                "median_value": median,
            }

    if median:
        deficit_display = format_weight_display(median - lift_value, unit_system)
        median_display = format_weight_display(median, unit_system)
        detail = f"Needs about {deficit_display} to reach the legacy OpenIPF median of {median_display}."
        return {
            "discipline": lift_name.title(),
            "rank": 90,
            "label": "Developing",
            "detail": detail,
            "full_text": f"Developing — lifted {lift_display}. {detail}",
            "performance_ratio": lift_value / median if median else 0.0,
            "threshold_value": median,
            "record_note": None,
            "lift_display": lift_display,
            "percentile": None,
            "median_value": median,
        }

    return result


def get_percentile_blurb(
    gender: str,
    weight_class: str,
    lift_name: str,
    lift_value: Optional[float],
    unit_system: UnitSystem = "kg",
) -> Optional[str]:
    profile = evaluate_percentile(gender, weight_class, lift_name, lift_value, unit_system)
    return profile.get("full_text")


REFEREE_HINTS: Dict[str, str] = {
    "squat": (
        "Finished the rep but still red lights? Two common causes are cutting depth "
        "above parallel or reracking before the head referee's 'rack' command."
    ),
    "bench": (
        "A smooth press can still fail if the bar isn’t paused on the chest, if the "
        "glutes leave the bench, or if the lifter racks before the 'rack' command."
    ),
    "deadlift": (
        "Deadlifts are often turned down for hitching the bar up the thighs, lowering "
        "before the 'down' call, or failing to lock the knees and shoulders."
    ),
}

LIFTER_ACCOMPLISHMENTS: Dict[str, list[str]] = {
    "Meghan Scanlon": [
        "2023 IPF Classic World Champion (63 kg)",
        "Multi-time PrimeTime invitee with 570+ kg total",
    ],
    "Leanne Le": [
        "2024 USAPL Raw Nationals podium (47 kg)",
        "Multiple Texas state records across squat and total",
    ],
    "Janee Kovac": [
        "2024 USAPL Junior National Champion (69 kg)",
        "Top-10 global ranking in class on OpenPowerlifting",
    ],
    "Emily Reynolds": [
        "USAPL Raw Nationals silver medalist (75 kg)",
        "Three consecutive national podium totals above 540 kg",
    ],
    "Angelina Martinez": [
        "2024 USAPL Raw Nationals champion (60 kg)",
        "Ranked top five globally at 60 kg on OpenPowerlifting",
    ],
    "Megan Hurlburt": [
        "2023 USAPL Raw Nationals podium finisher (82.5 kg)",
        "Multiple New York state titles across lifts",
    ],
    "Ellie Weinstein": [
        "USAPL Collegiate National Champion (63 kg)",
        "Collegiate American record holder in bench press",
    ],
    "Austin Perkins": [
        "2023 USAPL 75 kg National Champion",
        "All-time world record DOTS at 75 kg",
    ],
    "Angelo Fortino": [
        "2024 USAPL Pro Series Champion (82.5 kg)",
        "Consistent PrimeTime podium finisher since 2021",
    ],
    "Nonso Chinye": [
        "2024 USAPL Raw Nationals Superheavyweight Champion",
        "Sheffield 2024 invitee with 1100+ kg potential",
    ],
    "Ade Omisakin": [
        "2023 USAPL Raw Nationals podium (90 kg)",
        "Nigerian national records in squat and total",
    ],
    "Joseph Borenstein": [
        "2024 USAPL Collegiate National Champion (82.5 kg)",
        "Top junior DOTS ranking on the Pro Series circuit",
    ],
    "Demetrius Smith": [
        "USAPL Pro Series finalist (110 kg)",
        "Masters standout with totals above 900 kg",
    ],
    "JamaRR Royster": [
        "2024 USAPL Arnold Pro Series qualifier",
        "Multiple 360+ kg deadlifts in the 110 kg class",
    ],
    "Chase Gravitt": [
        "USAPL Junior Nationals gold medalist (82.5 kg)",
        "Top junior DOTS score for 2024 season",
    ],
    "Wascar Carpio": [
        "Dominican Republic national champion",
        "Regular 300 kg deadlifter on the Pro Series tour",
    ],
    "Sean Mills": [
        "2022 USAPL Raw Nationals medalist (100 kg)",
        "Former collegiate national champion",
    ],
}

DISCIPLINE_MAP = {
    "Squat": ("S", "Best Squat"),
    "Bench": ("B", "Best Bench"),
    "Deadlift": ("D", "Best Deadlift"),
}

ATTEMPT_ALERT_WINDOWS = [
    {"threshold": 3, "label": "Final Call", "severity": "critical"},
    {"threshold": 5, "label": "Critical Window", "severity": "critical"},
    {"threshold": 10, "label": "Begin Warm-Ups", "severity": "warning"},
    {"threshold": 15, "label": "Prep Phase", "severity": "warning"},
]

WARMUP_PHASES = [
    {
        "label": "Mobility & Empty Bar",
        "percent": 0.3,
        "minutes_before": 20,
        "rep_scheme": "8-10 reps · groove the movement",
    },
    {
        "label": "Speed Sets",
        "percent": 0.5,
        "minutes_before": 15,
        "rep_scheme": "2 x 3 fast reps",
    },
    {
        "label": "Builder Set",
        "percent": 0.7,
        "minutes_before": 10,
        "rep_scheme": "2 x 2 controlled reps",
    },
    {
        "label": "Last Warm-Up",
        "percent": 0.85,
        "minutes_before": 6,
        "rep_scheme": "1-2 singles",
    },
    {
        "label": "Platform Readiness",
        "percent": 1.0,
        "minutes_before": 0,
        "rep_scheme": "Opener visualization",
    },
]

PLATE_LIBRARY = {
    "kg": [
        {"weight": 25.0, "color": "#E31B23", "label": "25 kg · Red", "abbr": "25"},
        {"weight": 20.0, "color": "#2459C9", "label": "20 kg · Blue", "abbr": "20"},
        {"weight": 15.0, "color": "#F4C430", "label": "15 kg · Yellow", "abbr": "15"},
        {"weight": 10.0, "color": "#2EBF4F", "label": "10 kg · Green", "abbr": "10"},
        {"weight": 5.0, "color": "#F8FAFC", "label": "5 kg · White", "abbr": "5"},
        {"weight": 2.5, "color": "#111827", "label": "2.5 kg · Black", "abbr": "2.5"},
        {"weight": 1.25, "color": "#C0C0C0", "label": "1.25 kg · Silver", "abbr": "1.25"},
        {"weight": 0.5, "color": "#94A3B8", "label": "0.5 kg · Change", "abbr": "0.5"},
        {"weight": 0.25, "color": "#CBD5F5", "label": "0.25 kg · Micro", "abbr": "0.25"},
    ],
    "lb": [
        {"weight": 55.0, "color": "#E31B23", "label": "55 lb · Red", "abbr": "55"},
        {"weight": 45.0, "color": "#2459C9", "label": "45 lb · Blue", "abbr": "45"},
        {"weight": 35.0, "color": "#F4C430", "label": "35 lb · Yellow", "abbr": "35"},
        {"weight": 25.0, "color": "#2EBF4F", "label": "25 lb · Green", "abbr": "25"},
        {"weight": 15.0, "color": "#F8FAFC", "label": "15 lb · White", "abbr": "15"},
        {"weight": 10.0, "color": "#111827", "label": "10 lb · Black", "abbr": "10"},
        {"weight": 5.0, "color": "#C0C0C0", "label": "5 lb · Silver", "abbr": "5"},
        {"weight": 2.5, "color": "#94A3B8", "label": "2.5 lb · Change", "abbr": "2.5"},
        {"weight": 1.25, "color": "#CBD5F5", "label": "1.25 lb · Micro", "abbr": "1.25"},
    ],
}

BAR_LIBRARY = {
    "kg": [
        {"label": "20 kg Power Bar", "weight": 20.0},
        {"label": "15 kg Women's Bar", "weight": 15.0},
        {"label": "25 kg Squat Bar", "weight": 25.0},
    ],
    "lb": [
        {"label": "45 lb Power Bar", "weight": 45.0},
        {"label": "55 lb Squat Bar", "weight": 55.0},
    ],
}

COLLAR_OPTIONS_KG = {
    "0 kg collar (no lock)": 0.0,
    "0.25 kg collar per side": 0.25,
    "2.5 kg competition collar per side": 2.5,
}

LIFT_RECOMMENDATION_STEPS = {
    "Squat": (2.5, 5.0, 7.5),
    "Bench": (2.5, 5.0, 7.5),
    "Deadlift": (5.0, 7.5, 10.0),
}


def interpret_attempt_status(value: Optional[str]) -> str:
    """Normalize attempt status strings into display-friendly states."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "pending"
    normalized = str(value).strip().lower()
    if not normalized:
        return "pending"
    if "good" in normalized:
        return "good"
    if "bad" in normalized or "miss" in normalized:
        return "miss"
    return "pending"


def build_attempt_schedule(
    df: pd.DataFrame,
    lift_name: str,
    flight_filter: Optional[str] = None,
    platform_filter: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Create an ordered list of attempts for a given lift/flight."""
    prefix, _ = DISCIPLINE_MAP[lift_name]
    working = df.copy()

    def _normalize_filter(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        lowered = str(value).strip().lower()
        if lowered in {"all", "all flights", "any"}:
            return None
        return lowered

    flight_target = _normalize_filter(flight_filter)
    platform_target = _normalize_filter(platform_filter)

    if flight_target and "Flight" in working.columns:
        working = working[
            working["Flight"].astype(str).str.strip().str.lower() == flight_target
        ]

    if platform_target and "Platform" in working.columns:
        working = working[
            working["Platform"].astype(str).str.strip().str.lower() == platform_target
        ]

    if working.empty:
        working = df.copy()

    if "Lot" in working.columns:
        working = working.sort_values(
            by="Lot",
            key=lambda series: pd.to_numeric(series, errors="coerce"),
        )
    else:
        working = working.sort_values(by="Name")

    schedule: List[Dict[str, object]] = []
    for attempt in range(1, 4):
        for _, row in working.iterrows():
            weight_col = f"{lift_name} {attempt}"
            status_col = f"{prefix}{attempt}HRef"
            entry = {
                "sequence": len(schedule) + 1,
                "name": row.get("Name", "Unknown"),
                "attempt": attempt,
                "weight": row.get(weight_col),
                "status": interpret_attempt_status(row.get(status_col)),
                "raw_status": row.get(status_col),
                "lot": row.get("Lot"),
                "flight": row.get("Flight"),
                "platform": row.get("Platform"),
            }
            schedule.append(entry)
    return schedule


def find_attempt_index(schedule: List[Dict[str, object]], lifter_name: str, attempt_number: int) -> int:
    """Return the zero-based index for a lifter's attempt within a schedule."""
    for idx, entry in enumerate(schedule):
        if entry["name"] == lifter_name and entry["attempt"] == attempt_number:
            return idx
    return 0


def get_neighbor_names(schedule: List[Dict[str, object]], index: int) -> Tuple[Optional[str], Optional[str]]:
    """Return the lifter directly before and after the index."""
    previous_name = schedule[index - 1]["name"] if index - 1 >= 0 else None
    next_name = schedule[index + 1]["name"] if index + 1 < len(schedule) else None
    return previous_name, next_name


def format_minutes(value: float) -> str:
    """Format minute counts for UI copy."""
    if value <= 0.5:
        return "now"
    return f"{value:.1f} min"


def derive_alert_payload(
    attempts_out: int,
    eta_minutes: float,
    previous_name: Optional[str],
    next_name: Optional[str],
) -> Dict[str, str]:
    """Return alert metadata for the countdown card."""
    eta_text = format_minutes(max(eta_minutes, 0))
    if attempts_out <= 0:
        return {
            "title": "ON PLATFORM",
            "body": "Bars loaded — move now!",
            "eta": eta_text,
            "severity": "critical",
            "emoji": "🚨",
        }
    if attempts_out <= 3:
        neighbor_text = ""
        if previous_name or next_name:
            neighbor_text = f"Next: {previous_name or '—'} → **You** → {next_name or 'platform'}"
        return {
            "title": "FINAL CALL",
            "body": f"3 or fewer lifters remain. {neighbor_text}",
            "eta": eta_text,
            "severity": "critical",
            "emoji": "🔴",
        }
    if attempts_out <= 5:
        return {
            "title": "CRITICAL WINDOW",
            "body": "Finish last warm-up, stay near the platform.",
            "eta": eta_text,
            "severity": "critical",
            "emoji": "🧨",
        }
    if attempts_out <= 10:
        return {
            "title": "BEGIN BAR WORK",
            "body": "Start opener build-up now.",
            "eta": eta_text,
            "severity": "warning",
            "emoji": "🟠",
        }
    if attempts_out <= 15:
        return {
            "title": "PREP WINDOW",
            "body": "Finish mobility, transition to barbell soon.",
            "eta": eta_text,
            "severity": "warning",
            "emoji": "🟡",
        }
    return {
        "title": "CRUISE MODE",
        "body": "You have time — monitor pace and stay loose.",
        "eta": eta_text,
        "severity": "ready",
        "emoji": "🟢",
    }


def round_to_increment(value: float, increment: float = 0.5) -> float:
    """Round to the nearest allowable plate increment."""
    if increment <= 0:
        return value
    return round(round(value / increment) * increment, 3)


def build_warmup_sets(opener: Optional[float], unit_system: UnitSystem) -> List[Dict[str, float]]:
    """Return warm-up stage targets based on opener weight."""
    if opener is None or pd.isna(opener) or opener == 0:
        return []
    increment = 0.5 if unit_system == "kg" else 1.0
    plan = []
    for phase in WARMUP_PHASES:
        weight = round_to_increment(opener * phase["percent"], increment)
        plan.append(
            {
                "label": phase["label"],
                "percent": phase["percent"],
                "minutes_before": phase["minutes_before"],
                "rep_scheme": phase["rep_scheme"],
                "weight": weight,
            }
        )
    return plan


def get_collar_options(unit_system: UnitSystem) -> Dict[str, float]:
    """Return collar weight choices expressed in the active unit system."""
    if unit_system == "kg":
        return COLLAR_OPTIONS_KG
    options: Dict[str, float] = {}
    for label, value in COLLAR_OPTIONS_KG.items():
        converted = value * KG_TO_LB
        options[f"{label} (~{converted:.1f} lb/side)"] = converted
    return options


def calculate_plate_breakdown(
    target_weight: float,
    bar_weight: float,
    collar_weight_per_side: float,
    plates: List[Dict[str, object]],
) -> Dict[str, object]:
    """Compute plate counts per side for a desired total weight."""
    working_weight = target_weight - bar_weight - (collar_weight_per_side * 2)
    if working_weight < -1e-6:
        raise ValueError("Bar + collars exceed target weight.")
    per_side = working_weight / 2
    breakdown: List[Dict[str, object]] = []
    remaining = per_side

    for plate in plates:
        plate_weight = plate["weight"]
        if plate_weight <= 0:
            continue
        count = math.floor((remaining + 1e-6) / plate_weight)
        if count <= 0:
            continue
        remaining -= count * plate_weight
        breakdown.append(
            {
                "label": plate["label"],
                "abbr": plate["abbr"],
                "weight": plate_weight,
                "count": count,
                "color": plate["color"],
            }
        )
        if remaining <= 0.001:
            remaining = 0.0
            break

    loaded_from_plates = sum(item["weight"] * item["count"] * 2 for item in breakdown)
    resolved_total = bar_weight + (collar_weight_per_side * 2) + loaded_from_plates
    return {
        "breakdown": breakdown,
        "unresolved": max(remaining, 0.0),
        "working_weight": max(working_weight, 0.0),
        "resolved_total": resolved_total,
    }


def plate_stack_markup(breakdown: List[Dict[str, object]], collar_weight: float) -> str:
    """Return HTML markup for the plate visualization."""
    pieces = ['<div class="bar-sleeve"></div>']
    if collar_weight > 0:
        pieces.append('<div class="collar-piece"></div>')
    for plate in breakdown:
        is_small = plate["weight"] <= 2.5
        classes = "plate-piece small" if is_small else "plate-piece"
        pieces.append(
            f'<div class="{classes}" style="background:{plate["color"]};">'
            f'{plate["abbr"]}'
            "</div>"
        )
    return f'<div class="plate-stack">{"".join(pieces)}</div>'


def build_attempt_history_dataframe(lifter_row: pd.Series, unit_system: UnitSystem) -> pd.DataFrame:
    """Return a tidy attempt history for CRM exports."""
    records = []
    for lift_name, (prefix, _) in DISCIPLINE_MAP.items():
        for attempt in range(1, 4):
            weight = lifter_row.get(f"{lift_name} {attempt}")
            status = interpret_attempt_status(lifter_row.get(f"{prefix}{attempt}HRef"))
            records.append(
                {
                    "Lift": lift_name,
                    "Attempt": attempt,
                    "Weight": format_weight_display(weight, unit_system),
                    "Status": status.title(),
                }
            )
    return pd.DataFrame(records)


def project_total_with_attempt(lifter_row: pd.Series, lift_name: str, proposed_weight: float) -> float:
    """Calculate the lifter's total if the proposed attempt becomes the best lift."""
    _, best_column = DISCIPLINE_MAP[lift_name]
    best_value = lifter_row.get(best_column) or 0.0
    current_total = lifter_row.get("Total") or 0.0
    if proposed_weight <= best_value:
        return float(current_total)
    return float(current_total - best_value + proposed_weight)


def get_division_slice(df: pd.DataFrame, lifter_row: pd.Series) -> pd.DataFrame:
    """Return lifters competing in the same gender/division context."""
    division = df[df["Gender"] == lifter_row.get("Gender")].copy()
    if "Awards Division" in df.columns and lifter_row.get("Awards Division"):
        narrowed = division[division["Awards Division"] == lifter_row.get("Awards Division")].copy()
        if not narrowed.empty:
            division = narrowed
    if division.empty:
        division = df.copy()
    return division


def estimate_projected_place(df: pd.DataFrame, lifter_row: pd.Series, projected_total: float) -> Optional[int]:
    """Return the lifter's projected placing after updating their total."""
    division = get_division_slice(df, lifter_row)
    if division.empty:
        return None
    division = division.copy()
    mask = division["Name"] == lifter_row.get("Name")
    if not mask.any():
        division = pd.concat([division, lifter_row.to_frame().T], ignore_index=True)
        mask = division["Name"] == lifter_row.get("Name")
    division.loc[mask, "Total"] = projected_total
    division = division.sort_values("Total", ascending=False, kind="mergesort").reset_index(drop=True)
    row = division[division["Name"] == lifter_row.get("Name")]
    if row.empty:
        return None
    return int(row.index[0] + 1)


def estimate_success_probability(lifter_row: pd.Series, delta: float, attempt_number: int, profile: str) -> float:
    """Estimate a success probability using attempt history and aggressiveness."""
    base_rate = calculate_success_rate(lifter_row)
    attempt_penalty = max(attempt_number - 1, 0) * 4
    profile_penalty = {"Conservative": 0, "Moderate": 4, "Aggressive": 9}.get(profile, 5)
    delta_penalty = max(delta - 2.5, 0) * 1.5
    probability = base_rate - attempt_penalty - profile_penalty - delta_penalty + 5
    return round(float(min(max(probability, 20.0), 99.0)), 1)


def generate_attempt_recommendations(
    lifter_row: pd.Series,
    df: pd.DataFrame,
    lift_name: str,
    attempt_number: int,
    unit_system: UnitSystem,
) -> List[Dict[str, object]]:
    """Produce conservative/moderate/aggressive attempt options."""
    steps = LIFT_RECOMMENDATION_STEPS.get(lift_name, (2.5, 5.0, 7.5))
    prefix, best_column = DISCIPLINE_MAP[lift_name]
    best_value = lifter_row.get(best_column) or 0.0

    last_reference = None
    for idx in range(attempt_number - 1, 0, -1):
        status = interpret_attempt_status(lifter_row.get(f"{prefix}{idx}HRef"))
        attempt_weight = lifter_row.get(f"{lift_name} {idx}")
        if status == "good" and attempt_weight:
            last_reference = attempt_weight
            break

    if last_reference is None:
        planned = lifter_row.get(f"{lift_name} {attempt_number}") or 0.0
        if attempt_number == 1 and best_value:
            last_reference = max(best_value * 0.9, planned)
        else:
            last_reference = planned or best_value

    base_reference = last_reference or best_value or 0.0
    current_place = lifter_row.get("Place")

    profiles = [
        ("Conservative", steps[0], "Protects your subtotal and confidence"),
        ("Moderate", steps[1], "Balanced jump toward a meet PR"),
        ("Aggressive", steps[2], "All-in move to chase the next placing"),
    ]

    recommendations: List[Dict[str, object]] = []
    for label, step, note in profiles:
        proposed_weight = max(base_reference + step, step)
        projected_total = project_total_with_attempt(lifter_row, lift_name, proposed_weight)
        projected_place = estimate_projected_place(df, lifter_row, projected_total)
        probability = estimate_success_probability(lifter_row, step, attempt_number, label)

        if projected_place and current_place:
            if projected_place < current_place:
                place_text = f"Potential jump to #{projected_place}"
            elif projected_place == current_place:
                place_text = "Maintains current standing"
            else:
                place_text = f"Holds #{current_place}"
        else:
            place_text = "Improves subtotal for later lifts"

        recommendations.append(
            {
                "label": label,
                "weight": proposed_weight,
                "note": note,
                "probability": probability,
                "projected_total": projected_total,
                "place_text": place_text,
                "display_weight": format_weight_display(proposed_weight, unit_system),
                "display_total": format_weight_display(projected_total, unit_system),
            }
        )
    return recommendations


def display_warmup_room(df, unit_system: UnitSystem):
    """Warm-up room MVP surface: countdown, rack planning, and plate math."""
    st.header("Warm-Up Room Command Center")
    st.info(
        "Track pacing, coordinate racks, and eliminate plate math errors with a single dashboard. "
        "Data refreshes automatically with the meet feed — adjust sliders when meet pace changes."
    )

    if df.empty:
        st.warning("No meet data loaded. Select a data source to unlock the warm-up suite.")
        return

    unit_suffix = "lb" if unit_system == "lb" else "kg"
    tab_countdown, tab_racks, tab_plates = st.tabs(
        ["Attempt Countdown", "Rack Planner", "Plate Loader"]
    )

    with tab_countdown:
        st.subheader("Attempt Countdown & Alerts")
        name_options = sorted(df["Name"].dropna().unique())
        selected_name = st.selectbox("Focus lifter", name_options, key="warmup_focus_lifter")
        lifter_row = df[df["Name"] == selected_name].iloc[0]

        flight_values = (
            sorted(df["Flight"].dropna().astype(str).unique())
            if "Flight" in df.columns
            else []
        )
        platform_values = (
            sorted(df["Platform"].dropna().astype(str).unique())
            if "Platform" in df.columns
            else []
        )

        flight_options = ["All Flights"] + flight_values
        platform_options = ["All Platforms"] + platform_values

        def _default_index(options: List[str], value) -> int:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return 0
            value_str = str(value)
            if value_str in options:
                return options.index(value_str)
            return 0

        flight_index = _default_index(flight_options, lifter_row.get("Flight"))
        platform_index = _default_index(platform_options, lifter_row.get("Platform"))

        flight_choice = st.selectbox(
            "Flight filter", flight_options, index=flight_index, key="warmup_flight"
        )
        platform_choice = st.selectbox(
            "Platform filter",
            platform_options,
            index=platform_index,
            key="warmup_platform",
        )

        lift_choice = st.radio(
            "Lift focus", list(DISCIPLINE_MAP.keys()), horizontal=True, key="warmup_lift"
        )
        attempt_choice = st.selectbox(
            "Upcoming attempt", [1, 2, 3], index=0, key="warmup_attempt"
        )

        flight_filter = None if "All" in flight_choice else flight_choice
        platform_filter = None if "All" in platform_choice else platform_choice
        schedule = build_attempt_schedule(df, lift_choice, flight_filter, platform_filter)

        if not schedule:
            st.warning("No attempt order available for that combination yet.")
        else:
            target_index = find_attempt_index(schedule, selected_name, attempt_choice)
            target_sequence = schedule[target_index]["sequence"]

            default_pointer = st.session_state.get("warmup_sequence_pointer", max(target_sequence - 4, 1))
            default_pointer = min(max(default_pointer, 1), len(schedule))
            current_sequence = st.slider(
                "Current attempt number on the platform",
                min_value=1,
                max_value=len(schedule),
                value=default_pointer,
                key="warmup_sequence_slider",
            )
            st.session_state["warmup_sequence_pointer"] = current_sequence

            pace_value = st.slider(
                "Observed pace (minutes per attempt)",
                min_value=0.5,
                max_value=3.0,
                value=1.8,
                step=0.1,
                key="warmup_pace",
            )
            buffer_percent = st.slider(
                "Conservative buffer",
                min_value=0,
                max_value=40,
                value=20,
                format="%d%%",
                key="warmup_buffer",
            )

            attempts_out = max(target_sequence - current_sequence, 0)
            eta_minutes = attempts_out * pace_value
            buffered_eta = eta_minutes * (1 + buffer_percent / 100)
            prev_name, next_name = get_neighbor_names(schedule, target_index)
            alert_payload = derive_alert_payload(
                attempts_out, buffered_eta, prev_name, next_name
            )
            attempt_weight_display = format_weight_display(
                schedule[target_index]["weight"], unit_system
            )

            st.markdown(
                f"""
                <div class="countdown-card">
                    <div class="alert-chip {alert_payload['severity']}">
                        {alert_payload['emoji']} {alert_payload['title']}
                    </div>
                    <h3>{attempts_out} attempts out · Target weight {attempt_weight_display}</h3>
                    <p>{alert_payload['body']}</p>
                    <p><strong>Conservative ETA:</strong> {alert_payload['eta']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Attempts Ahead", attempts_out)
            col2.metric("ETA (buffered)", alert_payload["eta"])
            col3.metric("Live Pace", f"{pace_value:.1f} min/attempt")

            progress_ratio = min(current_sequence / max(target_sequence, 1), 1.0)
            st.progress(progress_ratio)

            chips = []
            for window in ATTEMPT_ALERT_WINDOWS:
                active = attempts_out <= window["threshold"]
                css_class = (
                    f"alert-chip {window['severity'] if active else 'ready'}"
                )
                style = "" if active else "style='opacity:0.45;'"
                chips.append(
                    f"<span class=\"{css_class}\" {style}>≤{window['threshold']} attempts · {window['label']}</span>"
                )
            st.markdown(" ".join(chips), unsafe_allow_html=True)

            current_index = max(current_sequence - 1, 0)
            queue_slice = schedule[current_index : min(current_index + 12, len(schedule))]
            status_icons = {"good": "✅ Good", "miss": "❌ Miss", "pending": "⏳ Pending"}
            queue_rows = []
            for entry in queue_slice:
                label = entry["name"]
                if label == selected_name:
                    label = f"{label} (you)"
                queue_rows.append(
                    {
                        "Seq": entry["sequence"],
                        "Attempt": entry["attempt"],
                        "Lifter": label,
                        "Weight": format_weight_display(entry["weight"], unit_system),
                        "Status": status_icons.get(entry["status"], entry["status"]),
                    }
                )
            st.write("**Next up**")
            st.dataframe(pd.DataFrame(queue_rows), hide_index=True, use_container_width=True)

            opener_value = lifter_row.get(f"{lift_choice} 1")
            warmup_sets = build_warmup_sets(opener_value, unit_system)
            if warmup_sets:
                st.write("**Personal Warm-Up Timeline**")
                for stage in warmup_sets:
                    start_in = max(buffered_eta - stage["minutes_before"], 0)
                    start_text = "Now" if start_in <= 0.5 else f"In {format_minutes(start_in)}"
                    weight_display = format_weight_display(stage["weight"], unit_system)
                    st.markdown(
                        f"""
                        <div class="warmup-phase-card">
                            <h4>{stage['label']} · {weight_display}</h4>
                            <p>{stage['rep_scheme']}</p>
                            <p>Start: {start_text}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Add opener attempts to this lifter to unlock warm-up set targets.")

    with tab_racks:
        st.subheader("Rack Planner & Rotation")
        flight_values = (
            sorted(df["Flight"].dropna().astype(str).unique())
            if "Flight" in df.columns
            else []
        )
        platform_values = (
            sorted(df["Platform"].dropna().astype(str).unique())
            if "Platform" in df.columns
            else []
        )
        flight_options = ["All Flights"] + flight_values
        platform_options = ["All Platforms"] + platform_values

        rack_flight = st.selectbox("Rack flight", flight_options, key="rack_flight")
        rack_platform = st.selectbox(
            "Rack platform", platform_options, key="rack_platform"
        )

        rack_df = df.copy()
        if "All" not in rack_flight and "Flight" in rack_df.columns:
            rack_df = rack_df[
                rack_df["Flight"].astype(str).str.strip() == rack_flight
            ]
        if "All" not in rack_platform and "Platform" in rack_df.columns:
            rack_df = rack_df[
                rack_df["Platform"].astype(str).str.strip() == rack_platform
            ]

        if rack_df.empty:
            st.warning("No lifters match the current rack filters.")
        else:
            lifter_choices = rack_df["Name"].tolist()
            default_selection = lifter_choices[: min(4, len(lifter_choices))]
            selected_lifters = st.multiselect(
                "Assign lifters to this warm-up rack",
                lifter_choices,
                default=default_selection,
                key="rack_lifter_selection",
            )

            if not selected_lifters:
                st.info("Choose at least one lifter to build a rack rotation.")
            else:
                lift_focus = st.radio(
                    "Lift focus",
                    list(DISCIPLINE_MAP.keys()),
                    horizontal=True,
                    key="rack_lift_focus",
                )
                attempt_focus = st.selectbox(
                    "Attempt wave",
                    [1, 2, 3],
                    index=0,
                    key="rack_attempt_focus",
                )
                rack_schedule = build_attempt_schedule(
                    df,
                    lift_focus,
                    None if "All" in rack_flight else rack_flight,
                    None if "All" in rack_platform else rack_platform,
                )
                if not rack_schedule:
                    st.warning("Unable to build attempt order for this rack yet.")
                else:
                    pointer_default = st.session_state.get("rack_sequence_pointer", 1)
                    pointer_default = min(max(pointer_default, 1), len(rack_schedule))
                    rack_current_sequence = st.slider(
                        "Current attempt number on the competition platform",
                        min_value=1,
                        max_value=len(rack_schedule),
                        value=pointer_default,
                        key="rack_sequence_slider",
                    )
                    st.session_state["rack_sequence_pointer"] = rack_current_sequence

                    rack_pace = st.slider(
                        "Observed pace for this flight (min/attempt)",
                        min_value=0.5,
                        max_value=3.0,
                        value=1.7,
                        step=0.1,
                        key="rack_pace",
                    )

                    focus_df = rack_df[rack_df["Name"].isin(selected_lifters)]
                    rack_plans = []
                    for _, lifter in focus_df.iterrows():
                        target_idx = find_attempt_index(
                            rack_schedule, lifter["Name"], attempt_focus
                        )
                        target_sequence = rack_schedule[target_idx]["sequence"]
                        attempts_out = max(target_sequence - rack_current_sequence, 0)
                        eta_minutes = attempts_out * rack_pace
                        opener_value = lifter.get(f"{lift_focus} 1")
                        warmup_sets = build_warmup_sets(opener_value, unit_system)
                        set_rows = []
                        for stage in warmup_sets:
                            start_in = max(eta_minutes - stage["minutes_before"], 0)
                            set_rows.append(
                                {
                                    "Phase": stage["label"],
                                    "Weight": stage["weight"],
                                    "Start In": "Now"
                                    if start_in <= 0.5
                                    else f"In {format_minutes(start_in)}",
                                    "Notes": stage["rep_scheme"],
                                }
                            )
                        rack_plans.append(
                            {
                                "name": lifter["Name"],
                                "attempts_out": attempts_out,
                                "eta": eta_minutes,
                                "opener": opener_value,
                                "sets": warmup_sets,
                                "table": set_rows,
                            }
                        )

                    for plan in rack_plans:
                        opener_display = format_weight_display(plan["opener"], unit_system)
                        st.markdown(
                            f"**{plan['name']}** — {plan['attempts_out']} attempts out "
                            f"(ETA {format_minutes(plan['eta'])}) · Opener {opener_display}"
                        )
                        if plan["table"]:
                            table_df = pd.DataFrame(plan["table"])
                            table_df["Weight"] = table_df["Weight"].apply(
                                lambda w: format_weight_display(w, unit_system)
                            )
                            st.dataframe(
                                table_df, hide_index=True, use_container_width=True
                            )
                        else:
                            st.caption("Add opener data for this lifter to map warm-ups.")

                    rotation_rows = []
                    max_sets = max(len(plan["sets"]) for plan in rack_plans) if rack_plans else 0
                    for idx in range(max_sets):
                        wave_entries = []
                        stage_label = None
                        for plan in rack_plans:
                            if idx >= len(plan["sets"]):
                                continue
                            stage = plan["sets"][idx]
                            stage_label = stage["label"]
                            wave_entries.append(
                                {
                                    "name": plan["name"],
                                    "weight": stage["weight"],
                                    "display": format_weight_display(
                                        stage["weight"], unit_system
                                    ),
                                }
                            )
                        if not wave_entries:
                            continue
                        wave_entries.sort(key=lambda item: item["weight"])
                        order = " → ".join(
                            f"{entry['name']} ({entry['display']})"
                            for entry in wave_entries
                        )
                        rotation_rows.append(
                            {
                                "Warm-Up Wave": stage_label or f"Stage {idx + 1}",
                                "Suggested Order": order,
                                "Plate Spread": f"{wave_entries[0]['display']} – {wave_entries[-1]['display']}",
                            }
                        )
                    if rotation_rows:
                        st.markdown("**Rack Rotation Preview**")
                        st.dataframe(
                            pd.DataFrame(rotation_rows),
                            hide_index=True,
                            use_container_width=True,
                        )

    with tab_plates:
        st.subheader("Calibrated Plate Loader")
        plate_set = PLATE_LIBRARY["lb" if unit_system == "lb" else "kg"]
        bar_options = BAR_LIBRARY["lb" if unit_system == "lb" else "kg"]
        bar_labels = [option["label"] for option in bar_options]

        def _bar_weight(label: str) -> float:
            for option in bar_options:
                if option["label"] == label:
                    return option["weight"]
            return bar_options[0]["weight"]

        col1, col2 = st.columns(2)
        default_target = 200.0 if unit_system == "kg" else 440.0
        step_value = 2.5 if unit_system == "kg" else 5.0
        with col1:
            total_weight = st.number_input(
                f"Attempt weight ({unit_suffix})",
                min_value=0.0,
                max_value=2000.0,
                value=default_target,
                step=step_value,
                key="plate_target_weight",
            )
            bar_choice = st.selectbox(
                "Competition bar",
                bar_labels,
                key="plate_bar_choice",
            )
            bar_weight = _bar_weight(bar_choice)
        with col2:
            collar_options = get_collar_options(unit_system)
            collar_labels = list(collar_options.keys())
            collar_choice = st.selectbox(
                "Collar selection (per side)", collar_labels, key="plate_collar_choice"
            )
            collar_weight = collar_options[collar_choice]

        if total_weight <= 0:
            st.info("Enter a target weight to generate plate math.")
        else:
            try:
                payload = calculate_plate_breakdown(
                    total_weight, bar_weight, collar_weight, plate_set
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                breakdown = payload["breakdown"]
                unresolved = payload["unresolved"]
                resolved_total = payload["resolved_total"]
                working = payload["working_weight"]

                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric("Plates on the bar", f"{working:.1f} {unit_suffix}")
                metric_col2.metric("Resolved total", f"{resolved_total:.1f} {unit_suffix}")
                st.caption("Plates metric excludes bar + collars; resolved total includes both.")
                st.markdown(plate_stack_markup(breakdown, collar_weight), unsafe_allow_html=True)

                table_rows = []
                for plate in breakdown:
                    total_plate_weight = plate["weight"] * plate["count"] * 2
                    table_rows.append(
                        {
                            "Plate": plate["label"],
                            "Count/Side": plate["count"],
                            "Total Weight": f"{total_plate_weight:.1f} {unit_suffix}",
                        }
                    )
                if table_rows:
                    st.dataframe(
                        pd.DataFrame(table_rows),
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.caption("No plates needed — bar and collars exceed target weight.")

                tolerance = 0.05 if unit_system == "kg" else 0.1
                if unresolved > tolerance:
                    st.warning(
                        f"{unresolved * 2:.2f} {unit_suffix} remaining per side. "
                        "Add fractional plates (.25 kg / .5 kg) to finish the load."
                    )
def summarise_attempts(row, discipline: str) -> Dict[str, str]:
    prefix, best_column = DISCIPLINE_MAP[discipline]
    good = 0
    bad = 0
    no_lift = 0
    for idx in range(1, 4):
        result = row.get(f"{prefix}{idx}HRef") if hasattr(row, "get") else row[f"{prefix}{idx}HRef"]
        if result == "good":
            good += 1
        elif result == "bad":
            bad += 1
        else:
            no_lift += 1
    if good == 3:
        descriptor = "Perfect 3-for-3"
    elif good == 2:
        descriptor = "Dialed in – 2/3 conversions"
    elif good == 1:
        descriptor = "Needs adjustments – 1/3 conversions"
    else:
        descriptor = "Still chasing a first make"
    best_value = row.get(best_column) if hasattr(row, "get") else row[best_column]
    return {
        "success": f"{good}/3 good lifts",
        "descriptor": descriptor,
        "best": best_value,
    }


def achievements_for_lifter(name: str) -> list[str]:
    return LIFTER_ACCOMPLISHMENTS.get(
        name,
        [
            "PrimeTime invitee demonstrating rapid year-over-year progression",
        ],
    )


def _normalize_gender(gender_value: str) -> str:
    if not gender_value or gender_value is pd.NA:
        return "UNSPECIFIED"
    value = str(gender_value).strip().upper()
    if value in {"F", "FEM", "FEMALE"}:
        return "FEMALE"
    if value in {"M", "MALE"}:
        return "MALE"
    return value


def ensure_meet_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure that the dataframe has the expected schema and numeric types."""
    data = df.copy()

    # Gender normalization.
    if "Gender" in data.columns:
        data["Gender"] = data["Gender"].apply(_normalize_gender)
    else:
        data["Gender"] = "UNSPECIFIED"

    # Ensure attempt columns exist.
    for column in ATTEMPT_WEIGHT_COLUMNS:
        if column not in data.columns:
            data[column] = np.nan
    for column in ATTEMPT_RESULT_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA

    for column in OPTIONAL_STRING_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column not in data.columns:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce")

    # Numeric conversions and defaults.
    if "Body Weight (kg)" not in data.columns:
        data["Body Weight (kg)"] = np.nan
    data["Body Weight (kg)"] = pd.to_numeric(
        data["Body Weight (kg)"], errors="coerce"
    )

    for column in NUMERIC_ZERO_COLUMNS:
        if column not in data.columns:
            data[column] = 0.0
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

    # Recompute missing totals from best lifts for any lifter that needs it.
    needs_total = data["Total"].isna() | (data["Total"] == 0)
    if needs_total.any():
        data.loc[needs_total, "Total"] = (
            data.loc[needs_total, "Best Squat"].fillna(0.0)
            + data.loc[needs_total, "Best Bench"].fillna(0.0)
            + data.loc[needs_total, "Best Deadlift"].fillna(0.0)
        )

    # Calculate missing point values.
    for column, func in POINT_COMPUTERS.items():
        if column not in data.columns:
            data[column] = 0.0
        needs_update = data[column].isna() | (data[column] == 0)
        if needs_update.any():
            data.loc[needs_update, column] = data.loc[needs_update].apply(
                lambda row: func(
                    row.get("Total", 0.0),
                    row.get("Body Weight (kg)") or 0.0,
                    row.get("Gender", ""),
                ),
                axis=1,
            )

    if "Awards Division" not in data.columns:
        data["Awards Division"] = pd.NA

    # Recompute placing if missing or not numeric.
    if "Place" not in data.columns:
        data["Place"] = np.nan
    data["Place"] = pd.to_numeric(data["Place"], errors="coerce")
    if data["Place"].isna().any():
        data.sort_values(
            ["Gender", "Total", "Body Weight (kg)"],
            ascending=[True, False, True],
            inplace=True,
        )
        data["Place"] = data.groupby("Gender").cumcount().add(1)
    data["Place"] = data["Place"].astype(int, errors="ignore")

    data.reset_index(drop=True, inplace=True)
    return data


@st.cache_data(show_spinner=False)
def load_sample_dataset() -> Tuple[pd.DataFrame, Dict[str, str]]:
    sample_path = Path(__file__).resolve().parent / "avancus_houston_primetime_2025_awards_results.csv"
    df = pd.read_csv(sample_path)
    df = ensure_meet_dataframe(df)
    metadata = {
        "meet_id": "avancus_houston_primetime_2025",
        "name": "Avancus Houston Primetime 2025",
        "date": "October 11, 2025",
        "federation": "Powerlifting America",
        "equipment": "Raw",
        "units": "KG",
        "source": "sample_csv",
    }
    return df, metadata


@st.cache_data(show_spinner=True)
def load_liftingcast_cached(meet_reference: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    df, metadata = load_liftingcast_meet(meet_reference)
    df = ensure_meet_dataframe(df)
    return df, asdict(metadata)


@st.cache_data(show_spinner=False, ttl=900)
def fetch_recent_meets_cached(limit: int = 12) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        return fetch_recent_liftingcast_meets(limit=limit), None
    except LiftingCastError as exc:
        return [], str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return [], f"Unexpected error: {exc}"


@st.cache_data(show_spinner=False)
def load_uploaded_csv(data: bytes, filename: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    buffer = io.BytesIO(data)
    df = pd.read_csv(buffer)
    df = ensure_meet_dataframe(df)
    metadata = {
        "meet_id": filename,
        "name": filename,
        "date": None,
        "federation": None,
        "equipment": None,
        "units": "KG",
        "source": "uploaded_csv",
    }
    return df, metadata


def enforce_basic_auth() -> None:
    """Optional basic auth gate controlled by POWERTRACK_BASIC_AUTH (user:pass)."""
    credentials = os.getenv(BASIC_AUTH_ENV)
    if not credentials:
        return
    expected_user = None
    expected_pass = None
    if ":" in credentials:
        expected_user, expected_pass = credentials.split(":", 1)
    else:
        expected_pass = credentials

    if st.session_state.get("basic_auth_ok"):
        return

    st.sidebar.subheader("Authentication")
    user = st.sidebar.text_input("Username", value="", key="basic_auth_user")
    password = st.sidebar.text_input("Password", value="", type="password", key="basic_auth_pass")
    if st.sidebar.button("Unlock", key="basic_auth_unlock"):
        if (
            (expected_user is None or user == expected_user)
            and password == expected_pass
        ):
            st.session_state["basic_auth_ok"] = True
            st.sidebar.success("Access granted.")
        else:
            st.sidebar.error("Invalid credentials.")

    if not st.session_state.get("basic_auth_ok"):
        st.stop()


def ensure_role_access(role: str) -> bool:
    """Check if the selected role requires an access code."""
    env_key = ROLE_CODES.get(role)
    if not env_key:
        return True
    expected = os.getenv(env_key)
    if not expected:
        return True
    session_flag = f"role_code_ok_{role}"
    if st.session_state.get(session_flag):
        return True

    code = st.sidebar.text_input(
        f"{role} access code",
        type="password",
        key=f"{role}_code_input",
        help=f"Set {env_key} in your environment to require this code.",
    )
    if code and code == expected:
        st.session_state[session_flag] = True
        st.sidebar.success(f"{role} mode unlocked.")
        return True
    if code and code != expected:
        st.sidebar.error("Incorrect code.")
    return False


def format_timestamp(ts: Optional[pd.Timestamp]) -> str:
    """Format a timestamp safely, localizing to the current timezone."""
    if ts is None:
        return "—"
    if not isinstance(ts, (pd.Timestamp, datetime)):
        ts = pd.to_datetime(ts, errors="coerce")
    if ts is None or (isinstance(ts, pd.Timestamp) and pd.isna(ts)):
        return "—"

    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        ts = ts.to_pydatetime()

    # datetime path
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    local_tz = datetime.now().astimezone().tzinfo or timezone.utc
    return ts.astimezone(local_tz).strftime("%b %d, %H:%M:%S")


def refresh_active_liftingcast_dataset() -> Optional[Tuple[pd.DataFrame, Dict[str, Any]]]:
    """Force-refresh the active LiftingCast dataset."""
    meet_id = st.session_state.get("last_meet_id")
    if not meet_id:
        return None
    load_liftingcast_cached.clear()
    df, meta = load_liftingcast_cached(meet_id)
    st.session_state["active_dataset"] = (df, meta)
    st.session_state["last_refresh_at"] = pd.Timestamp.utcnow()
    return df, meta


def maybe_auto_refresh_live_data(metadata: Dict[str, Any]) -> None:
    """Auto-refresh live data if enabled and the source is LiftingCast."""
    if metadata.get("source") != "liftingcast":
        return
    if not st.session_state.get("auto_refresh_live"):
        return
    interval = st.session_state.get("auto_refresh_interval", DEFAULT_AUTO_REFRESH_SECONDS)
    last_refresh = st.session_state.get("last_refresh_at")
    now = pd.Timestamp.utcnow()
    if last_refresh is not None and (now - last_refresh).total_seconds() < interval:
        return
    try:
        refreshed = refresh_active_liftingcast_dataset()
        if refreshed:
            st.session_state["last_auto_refresh"] = now
            st.experimental_rerun()
    except LiftingCastError as exc:
        st.sidebar.warning(f"Auto-refresh failed: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        st.sidebar.warning(f"Auto-refresh error: {exc}")


def get_weight_class_category(weight_kg, gender):
    """Determine weight class category for record comparison"""
    if weight_kg is None or pd.isna(weight_kg):
        return "Unknown"
    gender = (gender or "").upper()
    if gender == "MALE":
        if weight_kg <= 59:
            return "59"
        elif weight_kg <= 66:
            return "66"
        elif weight_kg <= 74:
            return "74"
        elif weight_kg <= 83:
            return "83"
        elif weight_kg <= 93:
            return "93"
        elif weight_kg <= 105:
            return "105"
        elif weight_kg <= 120:
            return "120"
        else:
            return "120+"
    else:  # FEMALE and other cases default to female classes
        if weight_kg <= 47:
            return "47"
        elif weight_kg <= 52:
            return "52"
        elif weight_kg <= 57:
            return "57"
        elif weight_kg <= 63:
            return "63"
        elif weight_kg <= 69:
            return "69"
        elif weight_kg <= 76:
            return "76"
        elif weight_kg <= 84:
            return "84"
        else:
            return "84+"

def compare_to_records(lift_type, weight, gender, weight_class_cat):
    """Compare a lift to world and American records"""
    valid_weight = weight is not None and not pd.isna(weight)
    if gender == "MALE":
        ipf_records = IPF_WORLD_RECORDS_MEN.get(weight_class_cat, {})
        usapl_records = USAPL_AMERICAN_RECORDS_MEN.get(weight_class_cat, {})
    else:
        ipf_records = IPF_WORLD_RECORDS_WOMEN.get(weight_class_cat, {})
        usapl_records = USAPL_AMERICAN_RECORDS_WOMEN.get(weight_class_cat, {})
    
    results = {}
    
    if lift_type in ipf_records:
        ipf_record = ipf_records[lift_type]
        results['ipf_record'] = ipf_record
        results['ipf_percent'] = (weight / ipf_record * 100) if valid_weight and ipf_record > 0 else 0
        results['is_ipf_record'] = bool(valid_weight and weight >= ipf_record)
        results['ipf_delta'] = (weight - ipf_record) if valid_weight else None

    if lift_type in usapl_records:
        usapl_record = usapl_records[lift_type]
        results['usapl_record'] = usapl_record
        results['usapl_percent'] = (weight / usapl_record * 100) if valid_weight and usapl_record > 0 else 0
        results['is_usapl_record'] = bool(valid_weight and weight >= usapl_record)
        results['usapl_delta'] = (weight - usapl_record) if valid_weight else None

    return results


def build_podium_sheet_pdf(df: pd.DataFrame, metadata: Dict[str, Any], unit_system: UnitSystem) -> bytes:
    """Generate a podium PDF for quick sharing."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, metadata.get("name", "Powerlifting Meet"), ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Date: {metadata.get('date') or 'TBD'}", ln=1)
    pdf.cell(0, 8, f"Generated: {format_timestamp(pd.Timestamp.utcnow())}", ln=1)
    pdf.ln(4)

    totals = pd.to_numeric(df.get("Total"), errors="coerce")
    df = df.copy()
    df["TotalNumeric"] = totals
    gender_sections = [("Women", "FEMALE"), ("Men", "MALE")]
    for section_title, gender_key in gender_sections:
        subset = df[df["Gender"] == gender_key].sort_values("TotalNumeric", ascending=False).head(3)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, f"{section_title} Podium", ln=1)
        pdf.set_font("Helvetica", "", 11)
        if subset.empty:
            pdf.cell(0, 8, "No competitors", ln=1)
        else:
            for idx, (_, row) in enumerate(subset.iterrows(), start=1):
                total_display = format_weight_display(row.get("Total"), unit_system)
                pdf.cell(
                    0,
                    8,
                    f"{idx}. {row.get('Name', 'Unknown')} — {total_display} ({row.get('Weight Class', 'N/A')})",
                    ln=1,
                )
        pdf.ln(3)
    return pdf.output(dest="S").encode("latin-1")


def build_attempt_cards_pdf(df: pd.DataFrame, metadata: Dict[str, Any], unit_system: UnitSystem) -> bytes:
    """Generate attempt cards PDF for all lifters in running order."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    sorted_df = df.copy()
    if "Place" in sorted_df:
        sorted_df = sorted_df.sort_values("Place")

    for _, row in sorted_df.iterrows():
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, row.get("Name", "Unknown lifter"), ln=1)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(
            0,
            8,
            f"{row.get('Gender', 'N/A')} · {row.get('Weight Class', 'N/A')} · "
            f"Bodyweight {format_weight_display(row.get('Body Weight (kg)'), unit_system)}",
            ln=1,
        )
        pdf.cell(
            0,
            8,
            f"Total: {format_weight_display(row.get('Total'), unit_system)} · DOTS {row.get('Dots Points', 0):.1f}",
            ln=1,
        )
        pdf.ln(2)
        for lift_label, prefix, best_key in [
            ("Squat", "S", "Best Squat"),
            ("Bench", "B", "Best Bench"),
            ("Deadlift", "D", "Best Deadlift"),
        ]:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, lift_label, ln=1)
            pdf.set_font("Helvetica", "", 11)
            best_display = format_weight_display(row.get(best_key), unit_system)
            attempts_text = []
            for attempt_no in range(1, 4):
                weight_value = row.get(f"{lift_label} {attempt_no}")
                result = row.get(f"{prefix}{attempt_no}HRef")
                result_marker = "✓" if result == "good" else "✗" if result == "bad" else "•"
                attempts_text.append(
                    f"{attempt_no}: {format_weight_display(weight_value, unit_system)} {result_marker}"
                )
            pdf.multi_cell(0, 8, f"Best: {best_display} | " + "  ".join(attempts_text))
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())

    return pdf.output(dest="S").encode("latin-1")


def _bomb_out_flags(row: pd.Series) -> List[str]:
    flags: List[str] = []
    for lift_label, prefix in [("Squat", "S"), ("Bench", "B"), ("Deadlift", "D")]:
        best_value = row.get(f"Best {lift_label}")
        attempts = [row.get(f"{prefix}{idx}HRef") for idx in range(1, 4)]
        if (pd.isna(best_value) or best_value in (None, 0)) and any(
            result == "bad" for result in attempts
        ):
            flags.append(lift_label)
    return flags


def collect_alerts(
    df: pd.DataFrame,
    metadata: Dict[str, Any],
    include_records: bool = True,
    include_lead: bool = True,
    include_bomb: bool = True,
) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []

    if include_records:
        for _, row in df.iterrows():
            weight_class_cat = get_weight_class_category(row.get("Body Weight (kg)"), row.get("Gender"))
            for lift_name, best_key in [
                ("squat", "Best Squat"),
                ("bench", "Best Bench"),
                ("deadlift", "Best Deadlift"),
                ("total", "Total"),
            ]:
                best_value = row.get(best_key)
                if pd.isna(best_value) or best_value in (None, 0):
                    continue
                record_info = compare_to_records(lift_name, best_value, row.get("Gender", ""), weight_class_cat)
                ipf_percent = record_info.get("ipf_percent", 0)
                usapl_percent = record_info.get("usapl_percent", 0)
                if record_info.get("is_ipf_record") or record_info.get("is_usapl_record") or max(ipf_percent, usapl_percent) >= 98:
                    alerts.append(
                        {
                            "type": "record",
                            "lifter": row.get("Name"),
                            "lift": lift_name,
                            "value": best_value,
                            "weight_class": weight_class_cat,
                            "ipf_percent": round(ipf_percent, 1),
                            "usapl_percent": round(usapl_percent, 1),
                        }
                    )

    if include_lead:
        df_sorted = df.copy()
        df_sorted["TotalNumeric"] = pd.to_numeric(df_sorted.get("Total"), errors="coerce")
        df_sorted = df_sorted.sort_values("TotalNumeric", ascending=False)
        if len(df_sorted) >= 2:
            leader = df_sorted.iloc[0]
            chaser = df_sorted.iloc[1]
            gap = (leader.get("TotalNumeric") or 0) - (chaser.get("TotalNumeric") or 0)
            if gap <= 5:
                alerts.append(
                    {
                        "type": "lead_change",
                        "leader": leader.get("Name"),
                        "chaser": chaser.get("Name"),
                        "gap": gap,
                    }
                )

    if include_bomb:
        for _, row in df.iterrows():
            flags = _bomb_out_flags(row)
            if flags:
                alerts.append(
                    {
                        "type": "bomb_out",
                        "lifter": row.get("Name"),
                        "lifts": flags,
                    }
                )

    if metadata:
        for alert in alerts:
            alert["meet"] = metadata.get("name") or metadata.get("meet_id")
    return alerts


def send_webhook_alerts(url: str, alerts: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not url:
        return False, "Webhook URL missing."
    if not alerts:
        return False, "No alerts to send."
    payload = {
        "meet": metadata.get("name") or metadata.get("meet_id"),
        "count": len(alerts),
        "alerts": alerts,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Webhook failed: {exc}"
    return True, None

def display_meet_overview(df, metadata, unit_system: UnitSystem):
    """Display meet overview statistics"""
    st.header("Meet Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Athletes", len(df))
    
    with col2:
        male_count = int((df['Gender'] == 'MALE').sum())
        female_count = int((df['Gender'] == 'FEMALE').sum())
        st.metric("Male Athletes", male_count)
    
    with col3:
        st.metric("Female Athletes", female_count)
    
    with col4:
        avg_dots = df['Dots Points'].mean()
        st.metric("Average DOTS", f"{avg_dots:.1f}")

    col5, col6, _ = st.columns(3)
    with col5:
        avg_gl = df['IPF Points'].mean()
        st.metric("Average IPF GL", f"{avg_gl:.1f}")
    
    # Competition details
    st.subheader("Competition Details")
    meet_name = metadata.get("name") or "Meet"
    meet_date = metadata.get("date") or "To be announced"
    federation = metadata.get("federation") or "Unknown"
    equipment = metadata.get("equipment") or "Not specified"
    source = metadata.get("source")

    st.write(f"**Meet:** {meet_name}")
    st.write(f"**Date:** {meet_date}")
    st.write(f"**Federation:** {federation}")
    st.write(f"**Equipment:** {equipment}")
    if source:
        st.write(f"**Data Source:** {source.replace('_', ' ').title()}")
    st.markdown(
        "<div class='info-pill'>Totals show the sum of a lifter's best squat, bench, "
        "and deadlift in the units you choose. Toggle between kilograms and pounds in the sidebar "
        "to match the audience you are presenting to.</div>",
        unsafe_allow_html=True,
    )

def display_live_scoreboard(df, unit_system: UnitSystem):
    """Display lifter attempts with a quick leaderboard on top."""
    st.header("Lifter Attempts Breakdown")

    st.markdown(
        "<div class='info-pill'>Tap any lifter to see their full attempt history. "
        "Green badges indicate a successful lift with majority white lights; red badges "
        "flag attempts that were turned down by the referees — often for depth or missed commands.</div>",
        unsafe_allow_html=True,
    )
    unit_suffix = "lb" if unit_system == "lb" else "kg"

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        gender_filter = st.selectbox("Filter by Gender", ["All", "MALE", "FEMALE"])
    with col2:
        sort_by = st.selectbox("Sort by", ["Place", "Total", "DOTS Points", "IPF Points"])
    
    # Apply filters
    filtered_df = df.copy()
    if gender_filter != "All":
        filtered_df = filtered_df[filtered_df['Gender'] == gender_filter]
    
    # Sort
    if sort_by == "Place":
        filtered_df = filtered_df.sort_values('Place')
    elif sort_by == "Total":
        filtered_df = filtered_df.sort_values('Total', ascending=False)
    elif sort_by == "DOTS Points":
        filtered_df = filtered_df.sort_values('Dots Points', ascending=False)
    else:  # IPF Points
        filtered_df = filtered_df.sort_values('IPF Points', ascending=False)

    # Hero leaderboard cards (top 8) before detailed expanders.
    top_df = filtered_df.head(8).copy()
    top_df["TotalDisplay"] = convert_series_for_display(top_df.get("Total", pd.Series(dtype=float)), unit_system)
    top_df["DotsDisplay"] = top_df.get("Dots Points", pd.Series(dtype=float)).round(1)
    leaderboard_rows = []
    for _, row in top_df.iterrows():
        leaderboard_rows.append(
            {
                "place": int(row.get("Place", 0)),
                "name": row.get("Name", "Unknown"),
                "class": row.get("Weight Class", "N/A"),
                "total": row.get("TotalDisplay", "—"),
                "dots": row.get("DotsDisplay", "—"),
            }
        )

    if leaderboard_rows:
        st.markdown("### Podium Leaderboard")
        card_html = ["<div style='display:flex;flex-direction:column;gap:10px;'>"]
        bg_colors = ["linear-gradient(120deg,#fbbf24,#f59e0b)", "linear-gradient(120deg,#cbd5f5,#a5b4fc)", "linear-gradient(120deg,#c4b5fd,#818cf8)"]
        for idx, entry in enumerate(leaderboard_rows):
            color = bg_colors[entry["place"]-1] if entry["place"] in {1,2,3} and entry["place"]-1 < len(bg_colors) else "linear-gradient(120deg,#0ea5e9,#2563eb)"
            card_html.append(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    padding:12px 14px;
                    border-radius:14px;
                    background:{color};
                    color:#0f172a;
                    box-shadow:0 12px 28px rgba(0,0,0,0.25);
                    border:1px solid rgba(255,255,255,0.25);
                ">
                    <div style="font-weight:800;font-size:1rem;">#{entry['place']}</div>
                    <div style="flex:1;margin-left:10px;">
                        <div style="font-weight:700;font-size:1.05rem;">{entry['name']}</div>
                        <div style="font-size:0.9rem;opacity:0.9;">Class {entry['class']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700;font-size:1.05rem;">{entry['total']}</div>
                        <div style="font-size:0.9rem;opacity:0.9;">DOTS {entry['dots']}</div>
                    </div>
                </div>
                """
            )
        card_html.append("</div>")
        st.markdown("".join(card_html), unsafe_allow_html=True)

    def render_attempt_row(
        result: Optional[str],
        label: str,
        weight_value: Optional[float],
        lift_type: str,
    ) -> None:
        if result == "good":
            css_class = "good-lift"
            status_label = "✓ White lights"
        elif result == "bad":
            css_class = "bad-lift"
            status_label = "✗ Red lights"
        else:
            css_class = "pending-lift"
            status_label = "• Next attempt"

        weight_text = format_weight_display(weight_value, unit_system)
        st.markdown(
            f"<div class='attempt-row'><span class='{css_class}'>{status_label}</span>"
            f"<span class='attempt-weight'>{label}: {weight_text}</span></div>",
            unsafe_allow_html=True,
        )
        if result == "bad":
            hint = REFEREE_HINTS.get(lift_type.lower())
            if hint:
                st.caption(f"Why red? {hint}")

    st.info("Tap a lifter to expand their attempts. White = good, Red = no lift, Gray = pending.")

    for _, row in filtered_df.iterrows():
        bw_display = format_weight_display(row.get('Body Weight (kg)'), unit_system)
        total_display = format_weight_display(row.get('Total'), unit_system)
        expander_label = (
            f"#{int(row['Place'])} · {row['Name']} · Bodyweight: {bw_display} · Total: {total_display}"
        )
        with st.expander(expander_label):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Athlete Snapshot**")
                st.write(f"Gender: {row.get('Gender', 'Unlisted')}")
                weight_class = row.get("Weight Class")
                st.write(f"Weight Class: {weight_class if pd.notna(weight_class) else 'Not specified'}")
                st.write(f"Body Weight: {bw_display}")
                state = row.get("State/Province")
                country = row.get("Country")
                location_parts = [
                    str(value) for value in (state, country) if value is not None and not pd.isna(value)
                ]
                if location_parts:
                    st.write(f"Location: {', '.join(location_parts)}")
                age = row.get("Exact Age")
                if age is not None and not pd.isna(age):
                    st.write(f"Age: {int(age)}")
            
            with col2:
                st.write("**Performance Summary**")
                st.write(f"DOTS Points: {row['Dots Points']:.2f}")
                st.write(f"IPF GL Points: {row['IPF Points']:.2f}")
                st.write(f"Competition Total: {total_display}")
            
            st.write("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Squat Attempts ({unit_suffix})**")
                for i in range(1, 4):
                    render_attempt_row(
                        row.get(f"S{i}HRef"),
                        f"Attempt {i}",
                        row.get(f"Squat {i}"),
                        "squat",
                    )
                st.write(f"**Best:** {format_weight_display(row['Best Squat'], unit_system)}")
            
            with col2:
                st.write(f"**Bench Attempts ({unit_suffix})**")
                for i in range(1, 4):
                    render_attempt_row(
                        row.get(f"B{i}HRef"),
                        f"Attempt {i}",
                        row.get(f"Bench {i}"),
                        "bench",
                    )
                st.write(f"**Best:** {format_weight_display(row['Best Bench'], unit_system)}")
            
            with col3:
                st.write(f"**Deadlift Attempts ({unit_suffix})**")
                for i in range(1, 4):
                    render_attempt_row(
                        row.get(f"D{i}HRef"),
                        f"Attempt {i}",
                        row.get(f"Deadlift {i}"),
                        "deadlift",
                    )
                st.write(f"**Best:** {format_weight_display(row['Best Deadlift'], unit_system)}")

def display_standings(df, unit_system: UnitSystem):
    """Display competition scoreboard by division"""
    st.header("Scoreboard")
    
    # Separate by gender
    tab1, tab2 = st.tabs(["Female Division", "Male Division"])
    
    with tab1:
        female_df = df[df['Gender'] == 'FEMALE'].sort_values('Place')
        if len(female_df) > 0:
            display_division_standings(female_df, "Female", unit_system)
        else:
            st.info("No female competitors in this division")
    
    with tab2:
        male_df = df[df['Gender'] == 'MALE'].sort_values('Place')
        if len(male_df) > 0:
            display_division_standings(male_df, "Male", unit_system)
        else:
            st.info("No male competitors in this division")

def display_division_standings(div_df, division_name, unit_system: UnitSystem):
    """Display standings for a specific division"""
    st.subheader(f"{division_name} Division Results")
    unit_suffix = "lb" if unit_system == "lb" else "kg"
    st.caption(f"Podium totals shown in {unit_suffix}.")
    
    # Podium display
    if len(div_df) >= 3:
        col1, col2, col3 = st.columns(3)
        
        with col2:  # Gold in center
            gold = div_df.iloc[0]
            st.markdown("### 🥇 GOLD")
            st.write(f"**{gold['Name']}**")
            st.write(f"Total: {format_weight_display(gold['Total'], unit_system)}")
            st.write(f"DOTS: {gold['Dots Points']:.2f}")
        
        with col1:  # Silver on left
            silver = div_df.iloc[1]
            st.markdown("### 🥈 SILVER")
            st.write(f"**{silver['Name']}**")
            st.write(f"Total: {format_weight_display(silver['Total'], unit_system)}")
            st.write(f"DOTS: {silver['Dots Points']:.2f}")
        
        with col3:  # Bronze on right
            bronze = div_df.iloc[2]
            st.markdown("### 🥉 BRONZE")
            st.write(f"**{bronze['Name']}**")
            st.write(f"Total: {format_weight_display(bronze['Total'], unit_system)}")
            st.write(f"DOTS: {bronze['Dots Points']:.2f}")
    
    # Full standings table
    st.write("---")
    st.write("**Complete Standings**")
    
    standings_data = []
    for idx, row in div_df.iterrows():
        bw = row.get('Body Weight (kg)')
        squat = row.get('Best Squat')
        bench = row.get('Best Bench')
        dead = row.get('Best Deadlift')
        total = row.get('Total')
        standings_data.append({
            "Place": int(row['Place']),
            "Name": row['Name'],
            "Body Weight": format_weight_display(bw, unit_system) if pd.notna(bw) else "—",
            "Squat": format_weight_display(squat, unit_system) if pd.notna(squat) else "—",
            "Bench": format_weight_display(bench, unit_system) if pd.notna(bench) else "—",
            "Deadlift": format_weight_display(dead, unit_system) if pd.notna(dead) else "—",
            "Total": format_weight_display(total, unit_system) if pd.notna(total) else "—",
            "DOTS": f"{row['Dots Points']:.2f}",
            "IPF GL": f"{row['IPF Points']:.2f}"
        })
    
    standings_df = pd.DataFrame(standings_data)
    st.dataframe(standings_df, use_container_width=True, hide_index=True)


def display_lifter_cards(df: pd.DataFrame, unit_system: UnitSystem):
    st.header("Lifter Spotlight Score Cards")
    st.markdown(
        "<div class='info-pill'>Lifter profiles. Pick a lifter and walk through their story in bite-sized sections.</div>",
        unsafe_allow_html=True,
    )
    reference_summary = get_openipf_reference_summary()
    if reference_summary:
        st.markdown(
            f"<div class='info-pill'>{reference_summary} Percentile chips now call out the median, average, and how many lifters have hit the same number.</div>",
            unsafe_allow_html=True,
        )

    gender_choice = st.selectbox("Division", ["All", "FEMALE", "MALE"], index=0)
    lifter_options = df[df['Gender'] == gender_choice] if gender_choice != "All" else df

    if lifter_options.empty:
        st.info("No lifters available for this selection.")
        return

    lifter_name = st.selectbox(
        "Select lifter",
        lifter_options.sort_values("Dots Points", ascending=False)['Name'].tolist(),
    )

    lifter = lifter_options[lifter_options['Name'] == lifter_name].iloc[0]
    total_display = format_weight_display(lifter.get('Total'), unit_system)

    st.markdown(f"## {lifter.get('Name', 'Unknown Lifter')}")
    st.caption(
        f"{lifter.get('Gender', 'Unlisted')} · {lifter.get('Weight Class', 'N/A')} class · "
        f"Total {total_display} · DOTS {lifter.get('Dots Points', 0):.1f}"
    )

    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Competition Total", total_display or "—")
        st.metric("DOTS", f"{lifter.get('Dots Points', 0):.1f}")
    with metrics_col2:
        st.metric("IPF GL Points", f"{lifter.get('IPF Points', 0):.1f}")
        st.metric("Success Rate", f"{calculate_success_rate(lifter)}%")

    # Quick visual for competition PRs.
    lift_bars = []
    for label, key in [("Squat", "Best Squat"), ("Bench", "Best Bench"), ("Deadlift", "Best Deadlift")]:
        value = lifter.get(key)
        if value is None or pd.isna(value):
            continue
        lift_bars.append(
            {
                "Lift": label,
                "Weight": convert_weight_value(value, unit_system),
            }
        )
    if lift_bars:
        fig = px.bar(
            lift_bars,
            x="Lift",
            y="Weight",
            text="Weight",
            color="Lift",
            color_discrete_sequence=["#7c3aed", "#2563eb", "#22c55e"],
        )
        fig.update_traces(texttemplate="%{text:.1f}")
        fig.update_layout(
            title=f"Competition PRs ({UNIT_LABELS[unit_system]})",
            yaxis_title=f"Weight ({unit_system})",
            xaxis_title="",
            showlegend=False,
            height=320,
            margin=dict(t=50, b=30, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    accomplishments = achievements_for_lifter(lifter.get('Name', ''))

    body_weight = lifter.get('Body Weight (kg)')
    weight_class_cat = get_weight_class_category(body_weight, lifter.get('Gender'))
    if weight_class_cat == "Unknown":
        wc_label = str(lifter.get('Weight Class') or "")
        match = re.search(r"\d+\+?", wc_label)
        if match:
            weight_class_cat = match.group()

    primary_disciplines = ["Squat", "Bench", "Deadlift"]
    percentile_profiles: Dict[str, Dict[str, Optional[float]]] = {}
    for discipline in primary_disciplines:
        best_value = lifter.get(DISCIPLINE_MAP[discipline][1])
        profile = evaluate_percentile(
            lifter.get('Gender'),
            weight_class_cat,
            discipline,
            best_value,
            unit_system,
        )
        percentile_profiles[discipline] = profile

    # Visualize PRs side-by-side with class median plus percentile labels.
    bar_rows: List[Dict[str, object]] = []
    for discipline in primary_disciplines:
        best_value = lifter.get(DISCIPLINE_MAP[discipline][1])
        if best_value is None or pd.isna(best_value):
            continue
        profile = percentile_profiles.get(discipline, {})
        percentile = profile.get("percentile")
        percentile_text = f"{percentile:.1f}th pct" if percentile is not None else "—"
        athlete_weight = convert_weight_value(best_value, unit_system)
        bar_rows.append(
            {
                "Lift": discipline,
                "Series": "Athlete",
                "Weight": athlete_weight,
                "Text": f"{athlete_weight:.1f} {unit_system} • {percentile_text}",
            }
        )
        median_value = profile.get("median_value")
        if median_value is not None and not pd.isna(median_value):
            median_weight = convert_weight_value(median_value, unit_system)
            bar_rows.append(
                {
                    "Lift": discipline,
                    "Series": "Class Median",
                    "Weight": median_weight,
                    "Text": f"{median_weight:.1f} {unit_system} • median",
                }
            )

    if bar_rows:
        fig = px.bar(
            bar_rows,
            x="Lift",
            y="Weight",
            color="Series",
            text="Text",
            barmode="group",
            color_discrete_map={"Athlete": "#7c3aed", "Class Median": "#94a3b8"},
        )
        fig.update_traces(texttemplate="%{text}", textfont_size=16)
        fig.update_layout(
            title=f"Competition PRs vs. {weight_class_cat} median ({UNIT_LABELS[unit_system]})",
            yaxis_title=f"Weight ({unit_system})",
            xaxis_title="",
            showlegend=True,
            height=360,
            margin=dict(t=60, b=30, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    signature_profile = min(
        percentile_profiles.values(),
        key=lambda p: (p["rank"], -(p.get("performance_ratio") or 0)),
        default=None,
    )

    if signature_profile and signature_profile.get("full_text"):
        st.markdown(
            f"<div class='signature-highlight'>Signature Lift: <strong>{signature_profile['discipline']}</strong><br>{signature_profile['full_text']}</div>",
            unsafe_allow_html=True,
        )
        if signature_profile.get("record_note"):
            st.caption(signature_profile["record_note"])

    tabs = st.tabs(["Highlights", "Attempt Patterns", "Fast Facts"])

    with tabs[0]:
        if accomplishments:
            st.write("**Career highlights**")
            for item in accomplishments:
                st.markdown(f"- 🏆 {item}")
        else:
            st.info("Add forthcoming accolades here to personalise this profile.")

    with tabs[1]:
        for discipline in primary_disciplines:
            summary = summarise_attempts(lifter, discipline)
            best_value = summary.get("best")
            profile = percentile_profiles[discipline]
            with st.expander(f"{discipline} • {summary['success']}"):
                st.write(summary["descriptor"])
                st.write(f"**Best:** {format_weight_display(best_value, unit_system)}")
                if profile.get("full_text"):
                    st.markdown(
                        f"<span class='percentile-chip'>{profile['full_text']}</span>",
                        unsafe_allow_html=True,
                    )
                if profile.get("record_note"):
                    st.caption(profile["record_note"])

    with tabs[2]:
        st.write("**Quick reference**")
        st.markdown(
            f"- Body weight: {format_weight_display(body_weight, unit_system)}\n"
            f"- Place: #{int(lifter.get('Place')) if pd.notna(lifter.get('Place')) else '—'}\n"
            f"- Hometown: {', '.join(str(v) for v in [lifter.get('State/Province'), lifter.get('Country')] if pd.notna(v)) or '—'}\n"
        )
        total_profile = evaluate_percentile(
            lifter.get('Gender'),
            weight_class_cat,
            "Total",
            lifter.get('Total'),
            unit_system,
        )
        if total_profile.get("full_text"):
            st.markdown(
                f"<span class='percentile-chip'>{total_profile['full_text']}</span>",
                unsafe_allow_html=True,
            )
        if total_profile.get("record_note"):
            st.caption(total_profile["record_note"])


def display_lifter_analysis(df, unit_system: UnitSystem):
    """Display detailed analysis for individual lifters"""
    st.header("Lifter Analysis")
    
    # Lifter selection
    lifter_name = st.selectbox("Select Lifter", df['Name'].tolist())
    
    if lifter_name:
        lifter = df[df['Name'] == lifter_name].iloc[0]
        unit_suffix = "lb" if unit_system == "lb" else "kg"
        weight_class_cat = get_weight_class_category(lifter['Body Weight (kg)'], lifter['Gender'])
        
        col1, col2 = st.columns(2)
        percentile_context = get_openipf_reference_summary()
        
        with col1:
            st.subheader("Lifter Profile")
            st.write(f"**Name:** {lifter.get('Name', 'Unknown')}")
            st.write(f"**Gender:** {lifter.get('Gender', 'Unlisted')}")
            body_weight = lifter.get('Body Weight (kg)')
            body_weight_display = format_weight_display(body_weight, unit_system)
            st.write(f"**Body Weight:** {body_weight_display}")
            weight_class = lifter.get('Weight Class')
            st.write(f"**Weight Class:** {weight_class if pd.notna(weight_class) else 'Not specified'}")
            age = lifter.get('Exact Age')
            if age is not None and not pd.isna(age):
                st.write(f"**Age:** {int(age)}")
            state = lifter.get('State/Province')
            country = lifter.get('Country')
            location_parts = [
                str(value) for value in (state, country) if value is not None and not pd.isna(value)
            ]
            if location_parts:
                st.write(f"**Location:** {', '.join(location_parts)}")
            place = lifter.get('Place')
            if place is not None and not pd.isna(place):
                st.write(f"**Place:** #{int(place)}")
            info_text = (
                f"{percentile_context} Percentile chips explain exactly where this lift lands versus the class average."
                if percentile_context
                else "Percentile benchmarks use OpenIPF.org meet data for the lifter’s weight class so newcomers can understand how impressive each lift is."
            )
            st.markdown(f"<div class='info-pill'>{info_text}</div>", unsafe_allow_html=True)
        
        with col2:
            st.subheader("Performance Metrics")
            total_val = lifter.get('Total')
            dots_val = lifter.get('Dots Points')
            ipf_val = lifter.get('IPF Points')
            gloss_val = lifter.get('Glossbrenner Points')
            st.write(
                f"**Total:** {format_weight_display(total_val, unit_system)}"
                if total_val is not None and not pd.isna(total_val)
                else "**Total:** —"
            )
            st.write(f"**DOTS Points:** {dots_val:.2f}" if dots_val is not None and not pd.isna(dots_val) else "**DOTS Points:** —")
            st.write(f"**IPF GL Points:** {ipf_val:.2f}" if ipf_val is not None and not pd.isna(ipf_val) else "**IPF GL Points:** —")
            st.write(f"**Glossbrenner:** {gloss_val:.2f}" if gloss_val is not None and not pd.isna(gloss_val) else "**Glossbrenner:** —")
        
        percentile_cols = st.columns(2)
        for idx, (label, value) in enumerate(
            [
                ("Squat", lifter['Best Squat']),
                ("Bench", lifter['Best Bench']),
                ("Deadlift", lifter['Best Deadlift']),
                ("Total", lifter['Total']),
            ]
        ):
            blurb = get_percentile_blurb(lifter.get('Gender'), weight_class_cat, label, value, unit_system)
            if blurb:
                with percentile_cols[idx % 2]:
                    st.markdown(
                        f"<span class='percentile-chip'>{blurb}</span>",
                        unsafe_allow_html=True,
                    )
        
        # Lift breakdown visualization
        st.subheader("Lift Breakdown")
        
        lift_values = [
            convert_weight_value(lifter['Best Squat'], unit_system),
            convert_weight_value(lifter['Best Bench'], unit_system),
            convert_weight_value(lifter['Best Deadlift'], unit_system),
        ]
        fig = go.Figure(
            data=[
                go.Bar(
                    name='Lifts',
                    x=['Squat', 'Bench', 'Deadlift'],
                    y=lift_values,
                    marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'],
                    hovertemplate=f"%{{x}}: %{{y:.1f}} {unit_suffix}<extra></extra>",
                )
            ]
        )
        fig.update_layout(
            title="Best Lifts by Movement",
            yaxis_title=f"Weight ({unit_suffix})",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Attempt success rate
        st.subheader("Attempt Success Rate")
        
        total_attempts = 9
        successful_attempts = 0
        for lift in ['Squat', 'Bench', 'Deadlift']:
            for i in range(1, 4):
                ref_col = f'{lift[0]}{i}HRef'
                if lifter[ref_col] == 'good':
                    successful_attempts += 1
        
        success_rate = (successful_attempts / total_attempts) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Successful Attempts", f"{successful_attempts}/9")
        with col2:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Record comparison
        st.subheader("Record Comparison")
        
        for lift_name, best_lift in [('squat', lifter['Best Squat']), 
                                     ('bench', lifter['Best Bench']), 
                                     ('deadlift', lifter['Best Deadlift']),
                                     ('total', lifter['Total'])]:
            record_comp = compare_to_records(lift_name, best_lift, lifter['Gender'], weight_class_cat)
            
            if record_comp:
                st.write(f"**{lift_name.title()}:** {format_weight_display(best_lift, unit_system)}")
                
                if 'ipf_record' in record_comp:
                    ipf_pct = record_comp['ipf_percent']
                    ipf_record = record_comp['ipf_record']
                    if record_comp.get('is_ipf_record'):
                        st.markdown(f"<span class='record-indicator'>IPF WORLD RECORD!</span>", 
                                  unsafe_allow_html=True)
                    else:
                        st.progress(min(ipf_pct / 100, 1.0))
                        st.caption(
                            f"IPF World Record: {format_weight_display(ipf_record, unit_system)} "
                            f"({ipf_pct:.1f}% of record)"
                        )
                    ipf_delta = record_comp.get("ipf_delta")
                    if ipf_delta:
                        delta_display = format_weight_display(abs(ipf_delta), unit_system)
                        if ipf_delta > 0:
                            st.markdown(
                                f"*This attempt is {delta_display} above the current IPF world record for this class.*"
                            )
                        else:
                            st.caption(f"{delta_display} shy of the IPF world record benchmark.")
                
                if 'usapl_record' in record_comp:
                    usapl_pct = record_comp['usapl_percent']
                    usapl_record = record_comp['usapl_record']
                    if record_comp.get('is_usapl_record'):
                        st.markdown(f"<span class='record-indicator'>AMERICAN RECORD!</span>", 
                                  unsafe_allow_html=True)
                    else:
                        st.progress(min(usapl_pct / 100, 1.0))
                        st.caption(
                            f"American Record: {format_weight_display(usapl_record, unit_system)} "
                            f"({usapl_pct:.1f}% of record)"
                        )
                    usapl_delta = record_comp.get("usapl_delta")
                    if usapl_delta:
                        delta_display = format_weight_display(abs(usapl_delta), unit_system)
                        if usapl_delta > 0:
                            st.caption(f"{delta_display} above the US national record.")
                        else:
                            st.caption(f"{delta_display} shy of the US national record.")
                
                st.write("---")

def display_coach_tools(df, unit_system: UnitSystem):
    """Display coaching and strategy tools"""
    st.header("Coach Tools")
    
    st.info(
        "These tools translate meet-day data into clear strategy calls — perfect for coaches "
        "and commentators explaining what each attempt means."
    )
    
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Competitor Analysis", "Attempt Strategy", "Division Overview", "Smart Coach CRM"]
    )
    
    unit_suffix = "lb" if unit_system == "lb" else "kg"
    to_display = lambda value: format_weight_display(value, unit_system)

    with tab1:
        st.subheader("Competitor Scouting")
        
        gender_select = st.radio("Select Division", ["FEMALE", "MALE"], horizontal=True)
        competitors = df[df['Gender'] == gender_select].sort_values('Total', ascending=False)
        
        st.write(f"**Top Competitors in {gender_select} Division:**")
        
        for idx, comp in competitors.head(5).iterrows():
            total_display = to_display(comp['Total'])
            with st.expander(f"#{comp['Place']} · {comp['Name']} · Total: {total_display}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Strengths:**")
                    lifts = {
                        'Squat': comp['Best Squat'],
                        'Bench': comp['Best Bench'],
                        'Deadlift': comp['Best Deadlift']
                    }
                    total_kg = float(comp['Total']) if pd.notna(comp['Total']) and comp['Total'] else 1.0
                    best_lift = max(lifts, key=lambda k: lifts[k] / total_kg)
                    st.write(f"- Strongest lift: {best_lift} ({to_display(lifts[best_lift])})")
                    st.write(f"- DOTS: {comp['Dots Points']:.2f}")
                    st.write(f"- Success rate: {calculate_success_rate(comp)}%")
                
                with col2:
                    st.write("**Lift Distribution:**")
                    fig = go.Figure(data=[go.Pie(
                        labels=['Squat', 'Bench', 'Deadlift'],
                        values=[
                            convert_weight_value(comp['Best Squat'], unit_system),
                            convert_weight_value(comp['Best Bench'], unit_system),
                            convert_weight_value(comp['Best Deadlift'], unit_system),
                        ],
                        hole=0.3
                    )])
                    fig.update_layout(height=250, showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Attempt Selection Calculator")
        
        st.write("Calculate optimal attempt weights based on competition position")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_lifter = st.selectbox("Your Lifter", df['Name'].tolist(), key="attempt_lifter")
            current_lift = st.selectbox("Current Lift", ["Squat", "Bench", "Deadlift"])
            attempt_number = st.selectbox("Attempt Number", [1, 2, 3])
        
        with col2:
            target_weight_display = st.number_input(
                f"Proposed Attempt ({unit_suffix})",
                min_value=0.0,
                max_value=1100.0 if unit_system == "lb" else 500.0,
                step=5.0 if unit_system == "lb" else 2.5,
                value=220.0 if unit_system == "lb" else 100.0,
            )
        target_weight = (
            target_weight_display if unit_system == "kg" else target_weight_display / KG_TO_LB
        )
        
        if st.button("Calculate Strategy"):
            lifter_data = df[df['Name'] == current_lifter].iloc[0]
            
            st.write("**Strategic Analysis:**")
            
            # Calculate position impact
            current_place = lifter_data['Place']
            st.write(f"- Current place: #{current_place}")
            
            # Estimate success probability (simplified)
            if attempt_number == 1:
                success_prob = 95
            elif attempt_number == 2:
                success_prob = 85
            else:
                success_prob = 70
            
            st.write(f"- Estimated success probability: {success_prob}%")
            st.write(f"- If successful: New subtotal would be calculated")
            st.write(f"- Potential place improvement: Analyze competitors")
            
            st.success(
                f"Recommendation: {format_weight_display(target_weight, unit_system)} is "
                f"{'conservative' if attempt_number == 1 else 'moderate' if attempt_number == 2 else 'aggressive'} "
                f"for attempt {attempt_number}."
            )

        lifter_data = df[df['Name'] == current_lifter].iloc[0]
        st.write("**Automated Recommendations**")
        recommendations = generate_attempt_recommendations(
            lifter_data, df, current_lift, attempt_number, unit_system
        )
        rec_cols = st.columns(len(recommendations))
        for col, rec in zip(rec_cols, recommendations):
            with col:
                st.markdown(f"**{rec['label']}**")
                st.metric("Attempt", rec["display_weight"], help=rec["note"])
                st.metric("Projected Total", rec["display_total"])
                st.progress(min(rec["probability"] / 100, 1.0))
                st.caption(f"{rec['probability']}% success · {rec['place_text']}")
    
    with tab3:
        st.subheader("Division Performance Overview")
        
        gender_overview = st.radio("Division", ["FEMALE", "MALE"], horizontal=True, key="overview_gender")
        division_data = df[df['Gender'] == gender_overview]
        totals_display = convert_series_for_display(division_data['Total'], unit_system)
        squat_display = convert_series_for_display(division_data['Best Squat'], unit_system)
        bench_display = convert_series_for_display(division_data['Best Bench'], unit_system)
        dead_display = convert_series_for_display(division_data['Best Deadlift'], unit_system)
        division_display = division_data.assign(
            TotalDisplay=totals_display,
            SquatDisplay=squat_display,
            BenchDisplay=bench_display,
            DeadliftDisplay=dead_display,
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Total Distribution**")
            fig = px.histogram(
                division_display,
                x='TotalDisplay',
                nbins=10,
                title=f"{gender_overview} Division Total Distribution",
            )
            fig.update_layout(height=300, xaxis_title=f"Total ({unit_suffix})")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("**DOTS Points Distribution**")
            fig = px.histogram(division_data, x='Dots Points', nbins=10,
                             title=f"{gender_overview} Division DOTS Distribution")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        st.write("**Lift Averages**")
        avg_data = {
            'Lift': ['Squat', 'Bench', 'Deadlift', 'Total'],
            f'Average ({unit_suffix})': [
                convert_weight_value(division_data['Best Squat'].mean(), unit_system),
                convert_weight_value(division_data['Best Bench'].mean(), unit_system),
                convert_weight_value(division_data['Best Deadlift'].mean(), unit_system),
                convert_weight_value(division_data['Total'].mean(), unit_system),
            ]
        }
        avg_df = pd.DataFrame(avg_data)
        st.dataframe(avg_df, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Smart Coach CRM")
        crm_lifter = st.selectbox("Select lifter", sorted(df['Name'].dropna().unique()), key="crm_lifter")
        lifter_row = df[df['Name'] == crm_lifter].iloc[0]
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        metrics_col1.metric("Total", format_weight_display(lifter_row.get("Total"), unit_system))
        metrics_col2.metric("DOTS", f"{lifter_row.get('Dots Points', 0):.2f}")
        metrics_col3.metric("Success Rate", f"{calculate_success_rate(lifter_row)}%")

        st.write("**Attempt History**")
        history_df = build_attempt_history_dataframe(lifter_row, unit_system)
        st.dataframe(history_df, hide_index=True, use_container_width=True)

        notes_state = st.session_state.setdefault("coach_notes", {})
        note_key = f"coach_note_input_{crm_lifter}"
        existing_note = notes_state.get(crm_lifter, "")
        note_value = st.text_area(
            "Coach notes (private)",
            value=existing_note,
            height=160,
            key=note_key,
        )
        if st.button("Save Coach Note", key=f"save_note_{crm_lifter}"):
            notes_state[crm_lifter] = note_value
            st.success("Coach note saved to this session.")

        summary_payload = {
            "name": crm_lifter,
            "division": lifter_row.get("Awards Division"),
            "gender": lifter_row.get("Gender"),
            "bodyweight": lifter_row.get("Body Weight (kg)"),
            "totals": {
                "squat": lifter_row.get("Best Squat"),
                "bench": lifter_row.get("Best Bench"),
                "deadlift": lifter_row.get("Best Deadlift"),
                "total": lifter_row.get("Total"),
            },
            "success_rate": calculate_success_rate(lifter_row),
            "notes": notes_state.get(crm_lifter, ""),
            "attempt_history": history_df.to_dict(orient="records"),
        }
        st.download_button(
            "Download Lifter Brief (JSON)",
            data=json.dumps(summary_payload, indent=2).encode("utf-8"),
            file_name=f"{crm_lifter.replace(' ', '_').lower()}_coach_brief.json",
            mime="application/json",
        )
        st.caption("Use the downloadable brief to share quick lifter updates with remote teams or premium clients.")

def calculate_success_rate(lifter):
    """Calculate attempt success rate for a lifter"""
    successful = 0
    total = 0
    for lift in ['S', 'B', 'D']:
        for i in range(1, 4):
            ref_col = f'{lift}{i}HRef'
            if pd.notna(lifter.get(ref_col)):
                total += 1
                if lifter[ref_col] == 'good':
                    successful += 1
    return round((successful / total * 100), 1) if total > 0 else 0

def display_spectator_chat(df: pd.DataFrame, metadata, unit_system: UnitSystem):
    """Spectator-facing chatbot that leans on OpenAI when available."""
    metadata = metadata or {}
    df = df if df is not None else pd.DataFrame()

    st.header("Spectator Chatbot")
    st.caption("Concise answers to common powerlifting questions. Beginner friendly, mobile ready.")

    snapshot = _get_meet_snapshot(df, metadata, unit_system)
    if snapshot:
        st.markdown(
            f"<div class='signature-highlight'>{snapshot}</div>",
            unsafe_allow_html=True,
        )

    if not os.getenv("OPENAI_API_KEY"):
        st.info(
            "Set the OPENAI_API_KEY environment variable to unlock live AI answers. "
            "You’ll still get curated quick tips without it."
        )
        st.caption("Using quick-tip mode.")
    else:
        st.caption("OPENAI_API_KEY detected. Chat should use live answers.")

    st.markdown("**Quick asks**")
    suggestion_cols = st.columns(2)
    prompt = None
    for idx, question in enumerate(CHAT_STARTER_QUESTIONS):
        col = suggestion_cols[idx % 2]
        if col.button(question, key=f"chat_starter_{idx}", use_container_width=True):
            prompt = question

    user_prompt = st.chat_input("Ask about lifts, judging lights, or who is leading")
    prompt = prompt or user_prompt

    history = st.session_state.setdefault("spectator_chat_history", [])
    prior_history = history.copy()

    if prompt:
        history.append({"role": "user", "content": prompt})
        answer, used_ai, error_text = get_chat_completion(
            prompt, df, metadata, unit_system, history=prior_history
        )
        history.append({"role": "assistant", "content": answer})
        st.session_state["spectator_chat_last_used_ai"] = used_ai
        st.session_state["spectator_chat_last_error"] = error_text

    if not history:
        st.info("Try a suggested prompt above or type your own question to start the conversation.")
    else:
        for message in history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    used_ai = st.session_state.get("spectator_chat_last_used_ai", False)
    error_text = st.session_state.get("spectator_chat_last_error")
    if used_ai:
        st.success("Live OpenAI response used.")
    else:
        st.warning("Using quick-tip fallback (no live AI response).")
        if error_text:
            st.caption(f"Details: {error_text}")

def display_liftingcast_explorer(unit_system: UnitSystem):
    """Search and preview LiftingCast meets without overwriting the main session."""
    st.header("LiftingCast Explorer")
    st.caption("Search recent meets on liftingcast.com and preview data before loading it into PowerTrack.")

    recent_meets, recent_error = fetch_recent_meets_cached()
    selected_recent_id: Optional[str] = None
    with st.expander("Recent public meets (auto-scraped from liftingcast.com)", expanded=True):
        if recent_error:
            st.warning(f"Could not fetch recent meets: {recent_error}")
        elif not recent_meets:
            st.info("No recent meets returned right now.")
        else:
            options = {
                f"{entry['name']} — {entry.get('date') or 'Date TBD'} ({entry['id']})": entry
                for entry in recent_meets
            }
            labels = ["— Select —"] + list(options.keys())
            choice = st.selectbox(
                "Pick a recent meet",
                labels,
                index=0,
                key="recent_meet_pick",
                help="Fresh list pulled from liftingcast.com; cached for 15 minutes.",
            )
            if choice != "— Select —":
                selected = options[choice]
                selected_recent_id = selected["id"]
                st.caption(f"Selected {selected['name']} · {selected.get('date') or 'Date TBD'}")
                st.session_state["liftingcast_explorer_input"] = selected_recent_id

    st.markdown("**Quick picks**")
    selected_suggestion = None
    if LIFTINGCAST_SAMPLE_MEETS:
        suggestion_cols = st.columns(len(LIFTINGCAST_SAMPLE_MEETS))
        for col, entry in zip(suggestion_cols, LIFTINGCAST_SAMPLE_MEETS):
            if col.button(entry["label"], key=f"lc_suggestion_{entry['id']}"):
                selected_suggestion = entry["id"]
                st.session_state["liftingcast_explorer_input"] = entry["id"]
    else:
        st.caption("No preset suggestions configured.")

    default_value = st.session_state.get("liftingcast_explorer_input", "")
    meet_reference = st.text_input(
        "Meet ID or LiftingCast URL",
        value=default_value,
        placeholder="e.g., mclafu3vkkgr or https://liftingcast.com/meets/mclafu3vkkgr",
    )
    st.session_state["liftingcast_explorer_input"] = meet_reference

    load_triggered = st.button("Search & Preview", type="primary", use_container_width=True)
    df_preview = None
    meta_preview: Optional[Dict[str, Any]] = None

    if load_triggered or selected_suggestion or selected_recent_id:
        target = (selected_recent_id or selected_suggestion or meet_reference or "").strip()
        if not target:
            st.warning("Enter a meet ID or URL to search.")
        else:
            with st.spinner(f"Fetching {target} from LiftingCast..."):
                try:
                    df_preview, meta_preview = load_liftingcast_cached(target)
                except LiftingCastError as exc:
                    st.error(str(exc))
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unexpected error: {exc}")

    if df_preview is None or meta_preview is None:
        st.info("Use recent meets, quick picks, or enter a meet ID/URL to preview live data. You can load it into the main app after previewing.")
        return

    st.success(f"Loaded {meta_preview.get('name', meta_preview.get('meet_id', 'meet'))} from LiftingCast.")
    st.caption(f"Federation: {meta_preview.get('federation') or 'Unknown'} · Date: {meta_preview.get('date') or 'TBD'} · Units: {meta_preview.get('units', 'KG')}")

    # Metrics
    top_total_value = pd.to_numeric(df_preview.get("Total"), errors="coerce").max()
    top_total_display = format_weight_display(top_total_value, unit_system) if top_total_value and not pd.isna(top_total_value) else "—"
    avg_dots = df_preview.get("Dots Points").mean() if "Dots Points" in df_preview else None
    col1, col2, col3 = st.columns(3)
    col1.metric("Athletes", len(df_preview))
    col2.metric("Top Total", top_total_display)
    col3.metric("Avg DOTS", f"{avg_dots:.1f}" if avg_dots else "—")

    # Leaderboard preview
    preview_df = df_preview.copy()
    preview_df["TotalDisplay"] = convert_series_for_display(preview_df.get("Total", pd.Series(dtype=float)), unit_system)
    preview_df["DotsDisplay"] = preview_df.get("Dots Points", pd.Series(dtype=float)).round(2)
    leaderboard = preview_df.sort_values("Total", ascending=False).head(12)
    leaderboard_display = leaderboard[["Name", "Weight Class", "TotalDisplay", "DotsDisplay", "Place"]] if "Place" in leaderboard else leaderboard[["Name", "Weight Class", "TotalDisplay", "DotsDisplay"]]
    st.markdown("**Quick leaderboard (top 12 by total)**")
    st.dataframe(leaderboard_display.rename(columns={"TotalDisplay": f"Total ({unit_system})", "DotsDisplay": "DOTS"}), use_container_width=True, hide_index=True)

    if st.button("Load this meet into PowerTrack", type="secondary", use_container_width=True):
        st.session_state["active_dataset"] = (df_preview, meta_preview)
        st.success("Loaded into session. Use the sidebar pages to explore this meet.")

def display_live_simulation(unit_system: UnitSystem):
    """Interactive spectator simulation to show live tracking scenarios."""
    st.header("Live Meet Simulation")
    st.caption("See what a spectator would experience at different points in a meet: openers, bench battles, and final deadlift showdowns.")

    scenario_labels = [scenario["label"] for scenario in SIMULATION_SCENARIOS]
    selection = st.select_slider("Select scenario", options=scenario_labels)
    scenario = next(s for s in SIMULATION_SCENARIOS if s["label"] == selection)

    st.subheader(scenario["label"])
    st.write(scenario["description"])
    st.info(scenario["now"])

    if scenario.get("alerts"):
        st.markdown("**Live cues**")
        for alert in scenario["alerts"]:
            st.markdown(f"- {alert}")

    attempts = scenario["attempts"]
    attempt_rows = []
    for attempt in attempts:
        weight = attempt.get("weight")
        attempt_rows.append({
            "Name": attempt["name"],
            "Lift": attempt["lift"],
            "Attempt": attempt["attempt"],
            "Weight": format_weight_display(weight, unit_system),
            "Result": attempt["result"].title(),
            "Clock": attempt.get("clock", "—"),
        })
    attempt_df = pd.DataFrame(attempt_rows)
    st.markdown("**Current attempt stream**")
    st.dataframe(attempt_df, use_container_width=True, hide_index=True)

    leaderboard_rows = []
    for row in scenario["leaderboard"]:
        leaderboard_rows.append({
            "Place": row["place"],
            "Name": row["name"],
            "Subtotal/Total": format_weight_display(row["subtotal"], unit_system),
            "Note": row["note"],
        })
    leaderboard_df = pd.DataFrame(leaderboard_rows).sort_values("Place")
    st.markdown("**Projected standings in this moment**")
    st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)

    st.markdown(
        "<div class='info-pill'>This simulation shows what a spectator sees: attempt order, timers, lights, and how each lift shifts the leaderboard.</div>",
        unsafe_allow_html=True,
    )

def display_rules_guide():
    """Display powerlifting rules and FAQ"""
    st.header("Rules & Competition Guide")

    st.info(
        "Brand-new to the sport? This guide explains what you’re seeing on the platform, "
        "why referees flash different colored cards, and how lifters are ranked."
    )

    dataset = st.session_state.get("active_dataset")
    active_df = dataset[0] if dataset else None

    tab1, tab2, tab3, tab4 = st.tabs(["Lift Rules", "Referee Signals", "Scoring", "Common Terms"])
    
    with tab1:
        st.subheader("Lift Execution Rules")
        
        with st.expander("Squat Rules"):
            st.write("""
            **Setup and Execution:**
            - Bar must be held horizontally across shoulders
            - Lifter must wait for head referee's signal to begin
            - Must descend until hip crease is below top of knee (parallel or below)
            - Must recover to standing position with knees locked
            - Must wait for rack command before returning bar
            
            **Common Reasons for Red Lights:**
            - Failure to reach proper depth
            - Double bounce at bottom
            - Uneven lockout or hip rise
            - Stepping forward or backward
            - Touching safety bars or supports
            """)
        
        with st.expander("Bench Press Rules"):
            st.write("""
            **Setup and Execution:**
            - Head, shoulders, and buttocks must remain on bench
            - Feet must be flat on floor (or raised platform if allowed)
            - Must wait for start command after bar is settled
            - Bar must touch chest or abdominal area
            - Must pause at chest until press command given
            - Must press to full arm extension
            
            **Common Reasons for Red Lights:**
            - Failure to pause at chest
            - Heaving or bouncing the bar
            - Uneven extension of arms
            - Buttocks leaving bench
            - Movement of feet during lift
            """)
        
        with st.expander("Deadlift Rules"):
            st.write("""
            **Setup and Execution:**
            - Bar must be lifted until lifter is standing erect
            - Knees must be locked
            - Shoulders must be back
            - Must wait for down command before lowering bar
            - Must maintain control of bar during descent
            
            **Common Reasons for Red Lights:**
            - Failure to stand fully erect
            - Failure to lock knees or stand with shoulders back
            - Supporting bar on thighs during performance
            - Stepping backward or forward
            - Lowering bar before receiving down command
            - Supporting the bar on the thighs
            """)
    
    with tab2:
        st.subheader("Referee Decision System")
        
        st.write("""
        Each lift is judged by three referees (left, center, right). 
        A lifter needs at least 2 white lights (2/3 majority) for a successful lift.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**White Lights (✓)**")
            st.write("- Lift satisfied all technical rules and commands.")
            st.write("- 2 of 3 (or 3 of 3) whites = good lift.")
            
            st.write("")
            st.write("**Red Lights (✗)**")
            st.write("- Failed lift; see colored cards for why.")
        
        with col2:
            st.write("**Card Colors (IPF 2025, Classic/Equipped):**")
            st.write("- **Red Card:** Commands missed (start/rack/down), bar not motionless at chest/shoulders, downward bar movement in squat/bench, supporting on thighs in deadlift, stepping/foot movement, double bounce, dumping bar.")
            st.write("- **Blue Card:** Squat depth not reached; not standing erect/locked knees; heaving or sinking in bench; soft knee/shoulder lockout in deadlift.")
            st.write("- **Yellow Card:** Contact with rack/uprights after start, uneven lockout, bar not touching chest (bench) or touching belt (deadlift), equipment/strap infractions, any other technical fault not covered above.")

        st.markdown("---")
        st.subheader("Real-World Case Studies")

        case_col1, case_col2 = st.columns(2)

        with case_col1:
            with st.expander("Squat: Depth vs. Command"):
                st.write(
                    "A lifter can stand up with the bar yet still fail if the hip crease never dips below the knee. "
                    "Another easy-to-miss mistake is reracking before the head referee says 'rack'."
                )
                st.write("**Watch for:** lifter pausing at the top while officials flash their lights.")

        with case_col2:
            with st.expander("Bench Press: Perfect Press, Red Lights"):
                st.write(
                    "Even a smooth press earns reds if the bar doesn’t pause on the chest, the glutes pop off the bench, "
                    "or the lifter racks the bar before hearing 'rack'."
                )
                st.write("**Watch for:** head referee’s hand signals (start, press, rack)." )

        st.markdown(
            "<div class='referee-tip'>New to deadlifts? The referees look for locked knees, upright shoulders, and "
            "control on the way down. Dropping the bar or soft-knee lockouts usually trigger yellow or blue cards.</div>",
            unsafe_allow_html=True,
        )
    
    with tab3:
        st.subheader("Scoring Systems")
        
        st.write("""
        Powerlifting uses several scoring formulas to compare lifters across different 
        weight classes and genders fairly.
        """)
        
        with st.expander("DOTS (Deviation from Optimal Total Strength)"):
            st.write("""
            **DOTS** is the current standard for comparing relative strength across weight classes.
            
            - Takes into account gender and body weight
            - Higher score = relatively stronger performance
            - Normalized to allow direct comparison between all lifters
            - Replaced the older Wilks formula in 2019
            - Formula accounts for natural strength advantages at different body weights
            
            **Typical DOTS Scores:**
            - 400-450: Regional level competitor
            - 450-500: National level competitor
            - 500-550: International level competitor
            - 550+: Elite, world-class lifter
            """)
        
        with st.expander("IPF GL Points (Glossbrenner Points)"):
            st.write("""
            **IPF GL Points** are used specifically in IPF (International Powerlifting Federation) 
            competitions for official rankings.
            
            - IPF-specific formula for relative strength
            - Considers body weight and gender
            - Used for IPF world rankings and records
            - Similar purpose to DOTS but with IPF-specific calculations
            
            **Typical IPF GL Scores:**
            - 80-90: Regional level
            - 90-100: National level
            - 100-110: International level
            - 110+: World-class level
            """)
        
        with st.expander("Total and Placing"):
            st.write("""
            **Total:** Sum of best successful squat, bench press, and deadlift
            
            **Placing Tiebreakers (in order):**
            1. Higher total wins
            2. If totals are equal: lighter body weight wins
            3. If both total and body weight equal: earlier weigh-in time wins
            4. If still tied: lifter with lower lot number wins
            
            **Bomb Out:** Failing all three attempts in any lift results in no total 
            and elimination from final rankings.
            """)
    
    with tab4:
        st.subheader("Common Powerlifting Terms")
        
        terms = {
            "Bomb Out": "Failing all 3 attempts in any single lift, resulting in no total",
            "Raw/Classic": "Lifting with only a belt, wrist wraps, and knee sleeves (no supportive equipment)",
            "Equipped": "Lifting with specialized supportive suits and shirts",
            "Opener": "First attempt in a lift (usually conservative)",
            "PR/Personal Record": "Lifter's best-ever performance in a lift or total",
            "Subtotal": "Running total after squat and bench, before deadlift",
            "Flight": "Group of lifters competing together in a session",
            "Platform": "The raised area where lifting takes place",
            "Lot Number": "Used for weigh-in order and tiebreakers",
            "Wilks": "Older scoring formula (replaced by DOTS in 2020)",
            "IPF": "International Powerlifting Federation (drug-tested)",
            "USAPL": "USA Powerlifting (IPF affiliate in United States)",
            "Squat Rack Height": "Height adjustment for the bar before squat",
            "Commands": "Verbal signals from head referee (Squat/Start/Press/Rack/Down)"
        }
        
        for term, definition in terms.items():
            with st.expander(term):
                st.write(definition)

        if active_df is not None and not active_df.empty:
            highlight = active_df.iloc[0]
            highlight_name = highlight.get("Name", "This lifter")
            highlight_class = highlight.get("Weight Class")
            class_text = highlight_class if pd.notna(highlight_class) else "their division"
            st.markdown(
                f"<div class='info-pill'>Curious how this applies? In the Avancus Houston Primetime meet, "
                f"{highlight_name} lifted in the {class_text} class. Toggle to the Lifter Attempts Breakdown tab "
                "and you’ll see every attempt annotated with these referee cues.</div>",
                unsafe_allow_html=True,
            )

def main():
    st.title("PowerTrack")
    st.caption("Professional Powerlifting Meet Companion")

    enforce_basic_auth()

    if "active_dataset" not in st.session_state:
        st.session_state["active_dataset"] = load_sample_dataset()
        st.session_state["last_refresh_at"] = pd.Timestamp.utcnow()

    st.sidebar.title("Role")
    role_choices = list(ROLE_PAGE_MAP.keys())
    saved_role = st.session_state.get("active_role", DEFAULT_ROLE)
    role_index = role_choices.index(saved_role) if saved_role in role_choices else 0
    selected_role = st.sidebar.radio(
        "Choose role",
        role_choices,
        index=role_index,
        help="Limits the UI to the tools that match your duties.",
    )
    if not ensure_role_access(selected_role):
        st.sidebar.info("Reverting to Spectator mode.")
        selected_role = DEFAULT_ROLE
    st.session_state["active_role"] = selected_role

    st.sidebar.title("Data Source")
    source_option = st.sidebar.selectbox(
        "Choose data source",
        ["Sample Dataset", "LiftingCast Live", "Upload CSV"],
        index=0,
    )

    if source_option == "Sample Dataset":
        st.session_state["active_dataset"] = load_sample_dataset()
        st.session_state["last_meet_id"] = None
        st.session_state["last_refresh_at"] = pd.Timestamp.utcnow()

    elif source_option == "LiftingCast Live":
        with st.sidebar.form("liftingcast_loader"):
            meet_reference = st.text_input(
                "Meet ID or LiftingCast URL",
                st.session_state.get("last_meet_id", ""),
                help="Example: mclafu3vkkgr or https://liftingcast.com/meets/mclafu3vkkgr",
            )
            submitted = st.form_submit_button("Load Live Meet")

        if submitted:
            if not meet_reference.strip():
                st.sidebar.warning("Please enter a meet ID or URL.")
            else:
                try:
                    dataset = load_liftingcast_cached(meet_reference.strip())
                    st.session_state["active_dataset"] = dataset
                    st.session_state["last_meet_id"] = meet_reference.strip()
                    st.session_state["last_refresh_at"] = pd.Timestamp.utcnow()
                    st.sidebar.success(f"Loaded {dataset[1].get('name')}")
                except LiftingCastError as exc:
                    st.sidebar.error(str(exc))
                except Exception as exc:
                    st.sidebar.error(f"Unexpected error: {exc}")

    else:  # Upload CSV
        uploaded = st.sidebar.file_uploader("Upload meet CSV", type="csv")
        if uploaded:
            try:
                dataset = load_uploaded_csv(uploaded.getvalue(), uploaded.name)
                st.session_state["active_dataset"] = dataset
                st.session_state["last_meet_id"] = None
                st.session_state["last_refresh_at"] = pd.Timestamp.utcnow()
                st.sidebar.success(f"Loaded {uploaded.name}")
            except Exception as exc:
                st.sidebar.error(f"Failed to load CSV: {exc}")

    df, metadata = st.session_state.get("active_dataset", load_sample_dataset())
    metadata = metadata or {}
    st.session_state.setdefault("last_refresh_at", pd.Timestamp.utcnow())

    is_live_source = metadata.get("source") == "liftingcast"
    if is_live_source:
        st.sidebar.markdown("---")
        st.sidebar.title("Live refresh")
        st.sidebar.caption(f"Last update: {format_timestamp(st.session_state.get('last_refresh_at'))}")
        refresh_cols = st.sidebar.columns(2)
        if refresh_cols[0].button("Refresh now", use_container_width=True):
            try:
                refresh_active_liftingcast_dataset()
                st.sidebar.success("Live data refreshed.")
            except LiftingCastError as exc:
                st.sidebar.error(str(exc))
            except Exception as exc:
                st.sidebar.error(f"Unexpected error: {exc}")
        st.session_state["auto_refresh_live"] = st.sidebar.toggle(
            "Auto-refresh live data",
            value=st.session_state.get("auto_refresh_live", False),
            help="Periodically pull the latest liftingcast.com data while this session stays open.",
        )
        st.session_state["auto_refresh_interval"] = st.sidebar.slider(
            "Refresh interval (sec)",
            15,
            180,
            st.session_state.get("auto_refresh_interval", DEFAULT_AUTO_REFRESH_SECONDS),
        )
        maybe_auto_refresh_live_data(metadata)
    else:
        st.session_state["auto_refresh_live"] = False

    unit_label_map = {"Kilograms (kg)": "kg", "Pounds (lb)": "lb"}
    default_index = 1 if st.session_state.get("unit_system") == "lb" else 0

    st.sidebar.markdown("---")
    st.sidebar.title("Display Options")
    unit_choice = st.sidebar.radio(
        "Weight Units",
        list(unit_label_map.keys()),
        index=default_index,
    )
    unit_system = unit_label_map[unit_choice]
    st.session_state["unit_system"] = unit_system

    st.sidebar.markdown("---")
    st.sidebar.metric("Athletes", len(df))
    top_total_value = pd.to_numeric(df.get("Total"), errors="coerce").max()
    top_total_display = (
        format_weight_display(top_total_value, unit_system)
        if top_total_value and not pd.isna(top_total_value)
        else "—"
    )
    st.sidebar.metric("Top Total", top_total_display)
    st.sidebar.markdown(
        f"**Meet:** {metadata.get('name', 'Unknown')}\n\n"
        f"**Federation:** {metadata.get('federation', 'Unknown')}\n\n"
        f"**Equipment:** {metadata.get('equipment', 'Not specified')}"
    )
    csv_name = metadata.get("meet_id") or metadata.get("name") or "powertrack_meet"
    st.sidebar.download_button(
        "Download results (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{csv_name}.csv",
        mime="text/csv",
    )
    st.sidebar.caption("CSV export is provided in original kilogram values.")

    st.sidebar.title("Exports")
    try:
        podium_pdf = build_podium_sheet_pdf(df, metadata, unit_system)
        st.sidebar.download_button(
            "Podium sheet (PDF)",
            data=podium_pdf,
            file_name=f"{csv_name}_podium.pdf",
            mime="application/pdf",
        )
        attempt_pdf = build_attempt_cards_pdf(df, metadata, unit_system)
        st.sidebar.download_button(
            "Attempt cards (PDF)",
            data=attempt_pdf,
            file_name=f"{csv_name}_attempt_cards.pdf",
            mime="application/pdf",
        )
    except Exception as exc:
        st.sidebar.caption(f"PDF exports unavailable: {exc}")

    st.sidebar.markdown("---")
    st.sidebar.title("Alerts & Webhooks")
    default_webhook = st.session_state.get("webhook_url") or os.getenv(WEBHOOK_URL_ENV, "")
    webhook_url = st.sidebar.text_input(
        "Webhook URL (Slack/Discord)",
        value=default_webhook,
        key="webhook_url_input",
    )
    st.session_state["webhook_url"] = webhook_url
    include_records = st.sidebar.checkbox("Record pushes", value=True, key="alerts_records")
    include_leads = st.sidebar.checkbox("Tight lead changes", value=True, key="alerts_leads")
    include_bombs = st.sidebar.checkbox("Bomb-out risk", value=True, key="alerts_bombs")
    in_app_alerts = st.sidebar.checkbox("In-app popups", value=False, key="alerts_in_app")
    alerts_preview = collect_alerts(df, metadata, include_records, include_leads, include_bombs)
    st.sidebar.caption(f"{len(alerts_preview)} alert(s) ready.")
    if st.sidebar.button("Send alerts now", use_container_width=True):
        ok, error_text = send_webhook_alerts(
            webhook_url or os.getenv(WEBHOOK_URL_ENV, ""),
            alerts_preview,
            metadata,
        )
        if ok:
            st.sidebar.success("Alerts sent.")
        else:
            st.sidebar.error(error_text or "Unable to send alerts.")
        if in_app_alerts:
            for alert in alerts_preview:
                message = alert.get("type", "alert").replace("_", " ").title()
                if alert.get("lifter"):
                    message += f" • {alert['lifter']}"
                if alert.get("value"):
                    message += f" @ {format_weight_display(alert['value'], unit_system)}"
                st.toast(message)

    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    st.sidebar.caption("Color-coded tabs/pages mirror their accent inside the main view.")
    # Update page labels for clarity.
    renamed_pages = [page.replace("Live Scoreboard", "Lifter Attempts Breakdown").replace("Standings", "Scoreboard") for page in ROLE_PAGE_MAP.get(selected_role, ROLE_PAGE_MAP[DEFAULT_ROLE])]
    available_pages = renamed_pages
    previous_page = st.session_state.get("last_page", available_pages[0])
    if previous_page not in available_pages:
        previous_page = available_pages[0]
    page = st.sidebar.radio(
        "Select View",
        available_pages,
        index=available_pages.index(previous_page),
    )
    st.session_state["last_page"] = page

    st.sidebar.markdown("---")
    st.sidebar.info(
        "**PowerTrack** delivers real-time meet data, analytics, and coaching tools. "
        "Optimized for desktop, tablets, and mobile devices."
    )

    meet_title = metadata.get("name") or "Powerlifting Meet"
    meet_date = metadata.get("date") or "Date to be announced"
    hero_total = top_total_display
    hero_palette = PAGE_COLOR_MAP.get(page, PAGE_COLOR_MAP["Meet Overview"])
    st.markdown(
        f"""
        <style>
            :root {{
                --tab-gradient: {hero_palette['gradient']};
                --tab-shadow: {hero_palette['shadow']};
                --tab-accent: {hero_palette['accent']};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="hero-banner" style="background:{hero_palette['gradient']};box-shadow:{hero_palette['shadow']};">
            <h1>{meet_title}</h1>
            <p>{len(df)} athletes · {meet_date} · Top total so far: {hero_total}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if page == "Meet Overview":
        display_meet_overview(df, metadata, unit_system)
    elif page == "Lifter Attempts Breakdown":
        display_live_scoreboard(df, unit_system)
    elif page == "Scoreboard":
        display_standings(df, unit_system)
    elif page == "Lifter Cards":
        display_lifter_cards(df, unit_system)
    elif page == "Lifter Analysis":
        display_lifter_analysis(df, unit_system)
    elif page == "Warm-Up Room":
        display_warmup_room(df, unit_system)
    elif page == "Coach Tools":
        display_coach_tools(df, unit_system)
    elif page == "LiftingCast Explorer":
        display_liftingcast_explorer(unit_system)
    elif page == "Live Simulation":
        display_live_simulation(unit_system)
    elif page == "Spectator Chat":
        display_spectator_chat(df, metadata, unit_system)
    else:
        display_rules_guide()

    st.sidebar.markdown("---")
    st.sidebar.caption("PowerTrack v1.2")

if __name__ == "__main__":
    main()
