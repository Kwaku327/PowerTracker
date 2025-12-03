# PowerTrack – Modern Powerlifting Meet Companion

This folder contains the Streamlit app that powers PowerTrack, a professional-grade experience for live and offline powerlifting meets.

## Feature Highlights

- **Live LiftingCast Integration** – ingest any public meet by ID or URL and convert it into the PowerTrack analytics stack.
- **Recent Meet Picker** – scrape the public LiftingCast feed and load a current meet without searching for IDs.
- **Live Refresh** – optional auto-refresh and manual refresh controls for liftingcast.com meets with last-updated timestamps.
- **Role Modes & Access Codes** – Spectator/Coach/Director modes with optional access codes or basic auth for restricted tools.
- **CSV Friendly** – upload exports from federation software; missing fields are filled with safe defaults.
- **Spectator Dashboard** – live scoreboard with expandable attempt cards, podium views, and polished theming.
- **Coach Toolkit** – competitor scouting, attempt calculators, and division analytics to inform game-day calls.
- **Warm-Up Room MVP** – intelligent countdown, rack scheduling, and color-coded plate math (IPF red/blue/yellow/green/white/black/silver palettes plus collar options).
- **Record Awareness** – IPF world and USAPL American record dictionaries highlight milestone lifts.
- **Instant Export** – download the currently active dataset from the sidebar for press releases or archives.
- **Print-Ready Exports** – one-click podium sheets and attempt cards as PDFs.
- **Webhooks** – send record/lead/bomb-out alerts to Slack/Discord-compatible webhooks from the sidebar.
- **Unit Toggle & Learning Aids** – one-click kilograms/pounds switching plus OpenIPF percentile context and referee explainer chips for new viewers.

## Installation

```bash
pip install -r requirements.txt
```

The repository root already includes a top-level `powertrack_app.py` that imports this module, so `streamlit run powertrack_app.py` works from either directory.

## Running Locally

```bash
streamlit run powertrack_app.py
```

Streamlit opens the app at `http://localhost:8501`.

## Data Sources

Use the sidebar selector to switch between:

1. **Sample Dataset** – Avancus Houston Primetime 2025 meet (bundled CSV).
2. **LiftingCast Live** – type a meet ID/URL such as `https://liftingcast.com/meets/mclafu3vkkgr`.
3. **Upload CSV** – drag-and-drop your own meet export (Name, Gender, attempts, totals, referee columns).

The most recent dataset is cached for quick navigation. A download button lets you export the active data.
Prefer a pitch-deck walkthrough? Open `powertrack_demo.html` for a ready-made, Figma-style flow you can drop into investor presentations.

## Warm-Up Room MVP

- **Attempt Countdown** – pick any lifter to see live attempts-out, buffered ETA, alert chips (15/10/5/3 attempts), and a personalized warm-up timeline tied to their opener.
- **Rack Planner** – assign lifters sharing a rack, align them by flight/platform, and get wave-by-wave order suggestions that minimize plate changes while tracking each ETA.
- **Calibrated Plate Loader** – plug in any attempt weight to auto-generate per-side plates using standard colors (red 25 kg, blue 20 kg, yellow 15 kg, green 10 kg, white 5 kg, black 2.5 kg, silver 1.25 kg, fractional 0.5 kg/0.25 kg) plus collar toggles (0 kg, 0.25 kg/side, 2.5 kg/side). A bar-sleeve visualization shows the stack exactly how it should look on the platform.

## Customising

- Update record dictionaries near the top of `powertrack_app.py`.
- Adjust the Streamlit theme via `.streamlit/config.toml` at the repository root.
- Extend `liftingcast_loader.py` if you want to support additional live data sources.
- Tailor the `OPENIPF_PERCENTILES` and `REFEREE_HINTS` structures inside `powertrack_app.py` to match your federation’s data snapshot and coaching language.
- Optional access controls: set `POWERTRACK_BASIC_AUTH=user:pass` to gate the app, or `POWERTRACK_COACH_CODE` / `POWERTRACK_DIRECTOR_CODE` to lock those role views. Pre-set `POWERTRACK_WEBHOOK_URL` to avoid pasting your Slack/Discord hook each session.

## Deployment Ideas

- **Streamlit Cloud** – set the entry point to `powertrack_app.py`.
- **Heroku / Render** – add a `Procfile` with `streamlit run powertrack_app.py`.
- **Containers/Cloud VMs** – install dependencies and expose port 8501.

## Need Help?

- Quick orientation: `QUICKSTART.md`
- Detailed roadmap and positioning: repository root `README.md`
- Formulae and calculations: `scoring.py`
- LiftingCast ingestion details: `liftingcast_loader.py`

Enjoy delivering a polished, data-rich powerlifting experience with PowerTrack!
