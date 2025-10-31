# PowerTrack Quick Start Guide

## Installation (2 minutes)

1. **Open Terminal/Command Prompt**

2. **Install dependencies:**
```bash
pip install streamlit pandas plotly numpy
```

3. **Run the app:**
```bash
streamlit run powertrack_app.py
```

4. **Access the app:**
   - Opens automatically in your browser
   - Or go to: http://localhost:8501

## First Time Using PowerTrack

### For Spectators
1. Click **Meet Overview** to see competition stats
2. Go to **Live Scoreboard** to see all lifter attempts
3. Click **Standings** to see rankings and podium
4. Select **Lifter Analysis** to deep-dive into any athlete

### For Coaches
1. Navigate to **Coach Tools**
2. Use **Competitor Analysis** to scout opponents
3. Try **Attempt Strategy** to plan weights
4. Check **Division Overview** for performance context

### Learning the Sport
- Click **Rules & Guide** for comprehensive rules
- Learn about DOTS and IPF GL scoring
- Understand referee decisions
- Review common terminology

## Key Features

### Mobile Use
- Works on phones, tablets, and laptops
- Automatically adapts to screen size
- Use landscape mode for best tablet experience

### Navigation
- Sidebar menu (left) for main sections
- Expandable cards for detailed info
- Tabs for different views within sections

### Understanding the Data

**DOTS Points**: Higher = relatively stronger
- 400-450: Regional level
- 450-500: National level
- 500-550: International level
- 550+: World-class

**IPF GL Points**: IPF-specific ranking
- 80-90: Regional level
- 90-100: National level
- 100-110: International level
- 110+: World-class

**Record Indicators**:
- Gold badges = World/American records
- Progress bars = Percentage of record

## Tips

1. **Filter by gender** in Live Scoreboard for cleaner view
2. **Sort standings** by different metrics to find insights
3. **Expand lifter cards** to see all 9 attempts
4. **Check record comparisons** in Lifter Analysis
5. **Use Coach Tools** even if you're not coaching - great insights!

## Common Questions

**Q: Can I use this at a real meet?**
A: Yes! Just update the CSV file path with your meet data.

**Q: Does this work offline?**
A: Yes, once installed, no internet needed (except initial install).

**Q: Can I compare multiple meets?**
A: Current version is single-meet focused. Multi-meet coming soon.

**Q: Are the records accurate?**
A: Yes - based on IPF and USAPL official records as of October 2025.

## Troubleshooting

**App won't load:**
- Restart: `streamlit run powertrack_app.py`
- Check CSV file is in same folder

**Blank screen:**
- Clear browser cache (Ctrl+Shift+Delete)
- Try different browser

**Mobile display cut off:**
- Rotate to landscape
- Zoom out (pinch gesture)
- Refresh page

## Need Help?

Refer to the full README.md for:
- Detailed feature explanations
- Technical documentation
- Customization options
- Advanced troubleshooting

---

**Ready to go!** Start with Meet Overview and explore from there.

PowerTrack v1.0 | Streamlit-based | All devices supported
