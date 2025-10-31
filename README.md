# PowerTrack - Powerlifting Competition Companion

A comprehensive Streamlit-based application for powerlifting meet management, analysis, and coaching.

## Features

### For Spectators
- **Live Scoreboard**: Real-time display of all lifter attempts and results
- **Competition Standings**: Podium display and full rankings by division
- **Lifter Analysis**: Detailed performance metrics with visualizations
- **Record Tracking**: Compare lifts against IPF World Records and American Records
- **Rules & Guide**: Comprehensive explanation of powerlifting rules and terminology

### For Coaches
- **Competitor Analysis**: Scout other lifters with strength breakdowns
- **Attempt Strategy Calculator**: Analyze optimal attempt weights
- **Division Overview**: Performance distributions and statistics
- **Real-time Standings**: Track competition positions

### Scoring Systems
- **DOTS Points**: Modern standard for relative strength comparison
- **IPF GL Points**: Official IPF ranking system
- Uses accurate, federation-specific records (IPF, USAPL)
- Does NOT use deprecated Wilks formula

## Installation

### Requirements
- Python 3.8 or higher
- pip package manager

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the application:**
```bash
streamlit run powertrack_app.py
```

The app will open in your default web browser at `http://localhost:8501`

## Usage

### Navigation
Use the sidebar menu to switch between different views:
- **Meet Overview**: Competition statistics and details
- **Live Scoreboard**: Detailed attempt-by-attempt results
- **Standings**: Current rankings and podium positions
- **Lifter Analysis**: Individual performance breakdowns
- **Coach Tools**: Strategic analysis and planning
- **Rules & Guide**: Educational content about powerlifting

### Mobile/Tablet Compatibility
PowerTrack is fully responsive and optimized for:
- Desktop computers
- iPads and tablets
- Mobile phones

The interface automatically adapts to your screen size.

### Data Source
The app loads meet data from the CSV file. To use with different meets:
1. Replace the CSV file path in `powertrack_app.py` (line 381)
2. Ensure the CSV follows the standard powerlifting meet format

## Features in Detail

### Meet Overview
- Total athlete count
- Gender distribution
- Average performance metrics
- Meet details and federation info

### Live Scoreboard
- Filter by gender
- Sort by place, total, DOTS, or IPF points
- Expandable athlete cards with:
  - Personal information
  - All 9 attempts (squat, bench, deadlift)
  - Success/failure indicators
  - Performance points

### Competition Standings
- Separate tabs for male and female divisions
- Podium display (gold, silver, bronze)
- Complete rankings table
- DOTS and IPF GL points for each lifter

### Lifter Analysis
- Personal profile and stats
- Visual lift breakdown chart
- Attempt success rate calculation
- Record comparison with progress bars
- Shows proximity to world and American records

### Coach Tools

#### Competitor Analysis
- Top 5 lifters in each division
- Strength analysis (best lifts)
- Lift distribution pie charts
- Success rate calculations

#### Attempt Strategy
- Calculate optimal attempt weights
- Position analysis
- Success probability estimates
- Strategic recommendations

#### Division Overview
- Total distribution histograms
- DOTS distribution histograms
- Average lift statistics

### Rules & Guide

#### Comprehensive coverage of:
- Squat execution rules
- Bench press rules
- Deadlift rules
- Referee decision system
- Scoring formulas (DOTS, IPF GL)
- Common powerlifting terminology

## Technical Details

### Technologies Used
- **Streamlit**: Web application framework
- **Pandas**: Data processing and analysis
- **Plotly**: Interactive visualizations
- **NumPy**: Numerical computations

### Record Data Sources
- IPF World Records from goodlift.info
- USAPL American Records from official sources
- Records updated as of October 2025

### Performance Points
- **DOTS (Deviation from Optimal Total Strength)**: Current standard
- **IPF GL Points**: IPF-specific ranking formula
- **Glossbrenner**: Alternative relative strength metric

## Customization

### Adding New Meets
To use PowerTrack with different meet data:

1. Ensure your CSV has these columns:
   - Name, Gender, Body Weight (kg)
   - Squat 1-3, Best Squat
   - Bench 1-3, Best Bench
   - Deadlift 1-3, Best Deadlift
   - Total, Dots Points, IPF Points
   - Referee decision columns (S1HRef, B1HRef, D1HRef, etc.)

2. Update the CSV path in the script

### Updating Records
To update world or American records:
1. Locate the record dictionaries (lines 46-113)
2. Update values with current records
3. Add new weight classes if needed

## Troubleshooting

### App won't start
- Verify all dependencies are installed
- Check Python version (3.8+)
- Ensure CSV file path is correct

### Data not displaying
- Verify CSV format matches expected structure
- Check for missing required columns
- Ensure numeric data is properly formatted

### Mobile display issues
- Clear browser cache
- Ensure responsive design CSS is loading
- Try landscape orientation for tablets

## Project Background

PowerTrack was developed based on comprehensive research of existing powerlifting software:
- **GoodLift**: Official IPF competition management
- **LiftingCast**: USAPL meet management platform
- **OpenPowerlifting**: Historical data archive

The app combines real-time meet data with historical context to enhance the experience for spectators, athletes, and coaches.

## Future Enhancements

Potential features for future versions:
- Live data integration with meet software APIs
- Push notifications for favorite lifters
- Predictive modeling for attempt success
- Social sharing of results
- Multi-meet comparison
- Training analytics
- Olympic weightlifting support

## Support

For issues, questions, or feature requests, please refer to the project documentation or contact the development team.

## License

This application is designed for use at powerlifting competitions and meets. Ensure compliance with federation rules and data privacy regulations when using with live meet data.

---

**PowerTrack v1.0** - Professional Powerlifting Meet Companion
Built with Streamlit | Optimized for all devices | Federation-accurate records
