# PowerTrack Quick Start

## 1. Install & Launch

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run powertrack_app.py
```

Visit `http://localhost:8501` if the browser does not open automatically.

## 2. Pick a Data Source

Use the **Data Source** selector in the sidebar:

- **Sample Dataset** – instantly loads the bundled Avancus Houston Primetime meet.
- **LiftingCast Live** – paste a public meet ID or URL from liftingcast.com for real-time data.
- **Upload CSV** – drop in any meet export (columns for Name, Gender, attempts, totals, referee lights).

PowerTrack caches the most recent dataset so you can navigate without reloads. A download button in the sidebar lets you export the active data as CSV for media or archive use.

## 3. Explore the Views

- **Meet Overview** – headline stats, participation mix, and federation context.
- **Live Scoreboard** – expandable attempt cards with success/fail cues and performance points.
- **Standings** – podium call-outs plus sortable tables for every division.
- **Lifter Analysis** – personalised dashboards, record proximity indicators, and lift breakdown charts.
- **Warm-Up Room** – attempt countdown with alerts, rack sharing planner, and calibrated plate loader with IPF color coding and collar presets (0 kg / 0.25 kg / 2.5 kg).
- **Coach Tools** – competitor scouting, attempt strategy helpers, and division analytics.
- **Rules & Guide** – quick education on commands, infractions, and scoring systems.

## 4. Tips for Meet Day

- Filter the scoreboard by gender and sort by totals or points to surface storylines.
- Use the coaching tools to monitor rival attempts and adjust strategy between flights.
- Keep the Warm-Up Room tab open on deck to track attempts-out, coordinate racks, and visualize calibrated plates before the loaders touch the bar.
- Capture screenshots of the analysis charts for social media updates.
- Update record dictionaries in `powertrack_app.py` to reflect the latest federation standards.

## Troubleshooting

- **Install issues** – confirm the virtual environment is active and re-run `pip install -r requirements.txt`.
- **CSV errors** – verify numeric columns use `.` decimal separators and include headers for lifts and totals.
- **LiftingCast failures** – ensure the meet is public and the ID/URL is correct.
- **Blank screen** – refresh the browser; Streamlit hot-reloads when files change.

Need more detail? Dive into `README.md` for deployment ideas, branding tweaks, and roadmap notes.
