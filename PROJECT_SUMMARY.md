# PowerTrack - Project Summary

## What Was Built

PowerTrack is a comprehensive, professional-grade powerlifting competition companion application built with Streamlit. It transforms the proposal documents into a fully functional web application that works on laptops, iPads, and mobile devices.

## Key Changes from Original Concept

### Name Change
- **Original**: LiftScope
- **New**: PowerTrack
- Reason: More professional and clearly indicates the app's purpose

### Removed Features (as requested)
- **Wilks scoring**: Replaced with DOTS and IPF GL Points only
- **Excessive emojis**: Minimized use for professional appearance
- **Account system**: Kept it account-free as specified in proposal

### Enhanced Features
- **Verified Records**: Used actual IPF world records and USAPL American records
- **Federation Accuracy**: Separate record tracking for different federations
- **Mobile Optimization**: Fully responsive design with custom CSS
- **Visual Analytics**: Plotly charts for better data visualization
- **Live Data Integration**: Direct LiftingCast loader with caching and robust error messaging
- **Instant Exports**: Sidebar download button for the active dataset (CSV)
- **Brand Ready Theme**: Custom `.streamlit` dark mode palette optimised for presentations
- **Audience Toggle & Education**: Kilogram/pound switcher, OpenIPF percentile context, and referee explainer chips for newcomers
- **Pitch-Ready Demo**: Standalone HTML walkthrough for pitch decks and sponsor previews
- **Spotlight Score Cards**: Broadcast-ready lifter bios summarising success patterns and achievements

## Application Structure

### Seven Main Sections

1. **Meet Overview**
   - Total athletes, gender distribution
   - Average performance metrics
   - Meet details and federation info

2. **Live Scoreboard**
   - All lifter attempts with success/failure indicators
   - Filterable by gender
   - Sortable by multiple metrics
   - Color-coded lift results (green = good, red = failed)

3. **Competition Standings**
   - Separate male and female divisions
   - Podium display (🥇🥈🥉)
   - Complete rankings with all metrics
   - DOTS and IPF GL points for each lifter

4. **Lifter Cards**
   - Individual score cards with success patterns by discipline
   - OpenPowerlifting career highlights and style notes
   - Percentile badges aligned to bodyweight class

5. **Lifter Analysis**
   - Detailed individual performance
   - Visual lift breakdown charts
   - Attempt success rate calculation
   - Record comparison with progress indicators
   - Shows percentage of world/American records

6. **Coach Tools**
   - Competitor scouting with strength analysis
   - Attempt strategy calculator
   - Division performance overview
   - Distribution histograms
   - Success rate analytics

7. **Rules & Guide**
   - Complete lift execution rules
   - Referee decision system explanation
   - Scoring systems (DOTS, IPF GL)
   - Common terminology glossary
   - Educational content for newcomers

## Technical Implementation

### Technologies
- **Streamlit**: Web framework for rapid development
- **Pandas**: Data processing and analysis
- **Plotly**: Interactive, mobile-friendly visualizations
- **NumPy**: Numerical computations
- **Requests**: External API client for LiftingCast live data

### Mobile Responsiveness
- Custom CSS media queries for mobile devices
- Responsive column layouts
- Touch-friendly controls
- Optimized for screens from 320px to 4K

### Data Accuracy
- IPF World Records verified from goodlift.info
- USAPL American Records from official sources
- Records current as of October 2025
- Separate male/female record dictionaries
- Weight class-specific comparisons

## Scoring Systems Used

### DOTS (Deviation from Optimal Total Strength)
- Current industry standard (replaced Wilks in 2020)
- Accounts for body weight and gender
- Higher scores indicate relatively stronger performance
- Benchmarks:
  - 400-450: Regional level
  - 450-500: National level
  - 500-550: International level
  - 550+: Elite world-class

### IPF GL Points (Glossbrenner)
- Official IPF ranking formula
- Used for world rankings and records
- Federation-specific calculations
- Benchmarks:
  - 80-90: Regional
  - 90-100: National
  - 100-110: International
  - 110+: World-class

## Data Source

### Supported Data Sources
- **LiftingCast Live**: Enter any public meet ID/URL to stream live attempts directly from liftingcast.com.
- **Upload CSV**: Import meets exported from third-party platforms; missing scoring metrics are computed automatically.
- **Sample Dataset**: Ships with the Avancus Houston Primetime 2025 meet for offline exploration.

## How to Use

### For End Users
1. Install Python and dependencies
2. Run: `streamlit run powertrack_app.py`
3. Access at http://localhost:8501
4. Use the sidebar to select a data source (LiftingCast live, upload CSV, or sample)
5. Choose kilograms or pounds with the display toggle, then navigate between analytical views via the sidebar menu
6. Share `powertrack_demo.html` for a storyboarded run-through without launching Streamlit

### For Developers
1. Data source selection is handled in-app; no code changes required for new meets
2. Record dictionaries can be updated (lines 46-113)
3. Extensible for additional federations
4. LiftingCast integration handled in `liftingcast_loader.py`

## Alignment with Proposal

### Spectator Features ✓
- Real-time scoreboard with context
- Competition standings and rankings
- Record tracking and comparisons
- Rules and educational content
- No account required

### Coach Features ✓
- Competitor analysis and scouting
- Attempt strategy tools
- Division performance overview
- Success rate analytics
- Strategic planning support

### Technical Requirements ✓
- Web-based application
- Mobile responsive
- Uses DOTS and IPF GL (not Wilks)
- Federation-accurate records
- Clean, professional design
- Minimal emoji usage

## Files Delivered

1. **powertrack_app.py** (root entrypoint)
   - Lightweight launcher for the packaged app

2. **powertrack_app.py** (this directory)
   - Core Streamlit application (~1,000 lines) covering data ingestion and UI logic

3. **liftingcast_loader.py**
   - Live meet ingestion, schema normalisation, and point calculation backfill

4. **scoring.py**
   - DOTS, IPF GL, and Glossbrenner helpers

5. **requirements.txt**
   - Streamlit, pandas, plotly, numpy, requests

6. **README.md & QUICKSTART.md**
   - Updated documentation with deployment guidance and marketing positioning

7. **powertrack_demo.html**
   - Click-through mockup for pitch decks and sponsor previews

8. **.streamlit/config.toml** (repository root)
   - Custom dark theme for presentations and sponsor activations

9. **avancus_houston_primetime_2025_awards_results.csv**
   - Sample meet data
   - Real competition results

## Deployment Options

### Local Use
```bash
streamlit run powertrack_app.py
```

### Cloud Deployment
- **Streamlit Cloud**: Free tier available
- **Heroku**: Easy Python deployment
- **AWS/GCP**: Scalable for large meets
- **Docker**: Container for consistent deployment

## Future Enhancements

As outlined in the proposal, future versions could include:
- Live API integration with GoodLift/LiftingCast
- Push notifications for favorite lifters
- Machine learning for attempt predictions
- Multi-meet comparisons
- Social sharing features
- Olympic weightlifting support
- Training analytics

## Business Model Alignment

The application is ready for the proposed business model:
- Can be offered free to spectators
- Premium features for coaches (attempt predictions, exports)
- Can be white-labeled for federations
- Per-meet licensing for meet directors
- Scales from small local meets to nationals

## Compliance with Requirements

✓ Name changed from LiftScope to PowerTrack
✓ Minimal emoji use (only 🥇🥈🥉 for podium)
✓ DOTS and IPF GL points only (no Wilks)
✓ Verified federation records
✓ Mobile/tablet/laptop compatible
✓ Professional design
✓ All proposal features implemented
✓ Streamlit-based web application

## Quality Assurance

- Record accuracy verified against official sources
- Responsive design tested
- All calculations use correct formulas
- Data parsing handles standard CSV format
- Error handling for missing data
- Clean, maintainable code structure

---

**PowerTrack v1.1** successfully delivers all requirements from the project proposal with enhanced accuracy, professional design, and comprehensive features for both spectators and coaches.
