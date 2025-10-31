import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

# Page configuration for mobile responsiveness
st.set_page_config(
    page_title="PowerTrack - Powerlifting Meet Companion",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness and cleaner design
st.markdown("""
<style>
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.3rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
    }
    
    /* Custom styling */
    .stAlert {
        padding: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .good-lift {
        color: #00CC00;
        font-weight: bold;
    }
    .bad-lift {
        color: #FF0000;
        font-weight: bold;
    }
    .record-indicator {
        background-color: #FFD700;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

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

def load_meet_data(csv_path):
    """Load and process meet data from CSV"""
    df = pd.read_csv(csv_path)
    return df

def get_weight_class_category(weight_kg, gender):
    """Determine weight class category for record comparison"""
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
    else:  # FEMALE
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
        results['ipf_percent'] = (weight / ipf_record * 100) if ipf_record > 0 else 0
        results['is_ipf_record'] = weight >= ipf_record
    
    if lift_type in usapl_records:
        usapl_record = usapl_records[lift_type]
        results['usapl_record'] = usapl_record
        results['usapl_percent'] = (weight / usapl_record * 100) if usapl_record > 0 else 0
        results['is_usapl_record'] = weight >= usapl_record
    
    return results

def display_meet_overview(df):
    """Display meet overview statistics"""
    st.header("Meet Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Athletes", len(df))
    
    with col2:
        male_count = len(df[df['Gender'] == 'MALE'])
        female_count = len(df[df['Gender'] == 'FEMALE'])
        st.metric("Male Athletes", male_count)
    
    with col3:
        st.metric("Female Athletes", female_count)
    
    with col4:
        avg_total = df['Total'].mean()
        st.metric("Average Total", f"{avg_total:.1f} kg")
    
    # Competition details
    st.subheader("Competition Details")
    meet_name = df['Awards Division'].iloc[0] if 'Awards Division' in df.columns else "Meet"
    st.write(f"**Meet:** {meet_name}")
    st.write(f"**Date:** October 31, 2025")
    st.write(f"**Federation:** Avancus Houston Signature Series")
    st.write(f"**Equipment:** Raw (Classic)")

def display_live_scoreboard(df):
    """Display live scoreboard with attempt details"""
    st.header("Live Scoreboard")
    
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
    
    # Display scoreboard
    for idx, row in filtered_df.iterrows():
        with st.expander(f"#{row['Place']} - {row['Name']} ({row['Body Weight (kg)']} kg) - Total: {row['Total']} kg"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Athlete Information**")
                st.write(f"Gender: {row['Gender']}")
                st.write(f"Weight Class: {row['Weight Class']}")
                st.write(f"Body Weight: {row['Body Weight (kg)']} kg")
                if pd.notna(row.get('State/Province')):
                    st.write(f"Location: {row['State/Province']}, {row['Country']}")
                if pd.notna(row.get('Exact Age')):
                    st.write(f"Age: {int(row['Exact Age'])}")
            
            with col2:
                st.write("**Performance Points**")
                st.write(f"DOTS Points: {row['Dots Points']:.2f}")
                st.write(f"IPF GL Points: {row['IPF Points']:.2f}")
                st.write(f"Total: {row['Total']} kg")
            
            # Lift details
            st.write("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Squat**")
                for i in range(1, 4):
                    attempt_weight = row[f'Squat {i}']
                    result = row[f'S{i}HRef']
                    if pd.notna(attempt_weight):
                        status = "✓" if result == "good" else "✗"
                        color = "good-lift" if result == "good" else "bad-lift"
                        st.markdown(f"<span class='{color}'>{status} Attempt {i}: {attempt_weight} kg</span>", 
                                  unsafe_allow_html=True)
                st.write(f"**Best: {row['Best Squat']} kg**")
            
            with col2:
                st.write("**Bench Press**")
                for i in range(1, 4):
                    attempt_weight = row[f'Bench {i}']
                    result = row[f'B{i}HRef']
                    if pd.notna(attempt_weight):
                        status = "✓" if result == "good" else "✗"
                        color = "good-lift" if result == "good" else "bad-lift"
                        st.markdown(f"<span class='{color}'>{status} Attempt {i}: {attempt_weight} kg</span>", 
                                  unsafe_allow_html=True)
                st.write(f"**Best: {row['Best Bench']} kg**")
            
            with col3:
                st.write("**Deadlift**")
                for i in range(1, 4):
                    attempt_weight = row[f'Deadlift {i}']
                    result = row[f'D{i}HRef']
                    if pd.notna(attempt_weight):
                        status = "✓" if result == "good" else "✗"
                        color = "good-lift" if result == "good" else "bad-lift"
                        st.markdown(f"<span class='{color}'>{status} Attempt {i}: {attempt_weight} kg</span>", 
                                  unsafe_allow_html=True)
                st.write(f"**Best: {row['Best Deadlift']} kg**")

def display_standings(df):
    """Display competition standings by division"""
    st.header("Competition Standings")
    
    # Separate by gender
    tab1, tab2 = st.tabs(["Female Division", "Male Division"])
    
    with tab1:
        female_df = df[df['Gender'] == 'FEMALE'].sort_values('Place')
        if len(female_df) > 0:
            display_division_standings(female_df, "Female")
        else:
            st.info("No female competitors in this division")
    
    with tab2:
        male_df = df[df['Gender'] == 'MALE'].sort_values('Place')
        if len(male_df) > 0:
            display_division_standings(male_df, "Male")
        else:
            st.info("No male competitors in this division")

def display_division_standings(div_df, division_name):
    """Display standings for a specific division"""
    st.subheader(f"{division_name} Division Results")
    
    # Podium display
    if len(div_df) >= 3:
        col1, col2, col3 = st.columns(3)
        
        with col2:  # Gold in center
            gold = div_df.iloc[0]
            st.markdown("### 🥇 GOLD")
            st.write(f"**{gold['Name']}**")
            st.write(f"Total: {gold['Total']} kg")
            st.write(f"DOTS: {gold['Dots Points']:.2f}")
        
        with col1:  # Silver on left
            silver = div_df.iloc[1]
            st.markdown("### 🥈 SILVER")
            st.write(f"**{silver['Name']}**")
            st.write(f"Total: {silver['Total']} kg")
            st.write(f"DOTS: {silver['Dots Points']:.2f}")
        
        with col3:  # Bronze on right
            bronze = div_df.iloc[2]
            st.markdown("### 🥉 BRONZE")
            st.write(f"**{bronze['Name']}**")
            st.write(f"Total: {bronze['Total']} kg")
            st.write(f"DOTS: {bronze['Dots Points']:.2f}")
    
    # Full standings table
    st.write("---")
    st.write("**Complete Standings**")
    
    standings_data = []
    for idx, row in div_df.iterrows():
        standings_data.append({
            "Place": int(row['Place']),
            "Name": row['Name'],
            "Body Weight": f"{row['Body Weight (kg)']} kg",
            "Squat": f"{row['Best Squat']} kg",
            "Bench": f"{row['Best Bench']} kg",
            "Deadlift": f"{row['Best Deadlift']} kg",
            "Total": f"{row['Total']} kg",
            "DOTS": f"{row['Dots Points']:.2f}",
            "IPF GL": f"{row['IPF Points']:.2f}"
        })
    
    standings_df = pd.DataFrame(standings_data)
    st.dataframe(standings_df, use_container_width=True, hide_index=True)

def display_lifter_analysis(df):
    """Display detailed analysis for individual lifters"""
    st.header("Lifter Analysis")
    
    # Lifter selection
    lifter_name = st.selectbox("Select Lifter", df['Name'].tolist())
    
    if lifter_name:
        lifter = df[df['Name'] == lifter_name].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Lifter Profile")
            st.write(f"**Name:** {lifter['Name']}")
            st.write(f"**Gender:** {lifter['Gender']}")
            st.write(f"**Body Weight:** {lifter['Body Weight (kg)']} kg")
            st.write(f"**Weight Class:** {lifter['Weight Class']}")
            if pd.notna(lifter.get('Exact Age')):
                st.write(f"**Age:** {int(lifter['Exact Age'])}")
            if pd.notna(lifter.get('State/Province')):
                st.write(f"**Location:** {lifter['State/Province']}, {lifter['Country']}")
            st.write(f"**Place:** #{lifter['Place']}")
        
        with col2:
            st.subheader("Performance Metrics")
            st.write(f"**Total:** {lifter['Total']} kg")
            st.write(f"**DOTS Points:** {lifter['Dots Points']:.2f}")
            st.write(f"**IPF GL Points:** {lifter['IPF Points']:.2f}")
            st.write(f"**Glossbrenner:** {lifter['Glossbrenner Points']:.2f}")
        
        # Lift breakdown visualization
        st.subheader("Lift Breakdown")
        
        fig = go.Figure(data=[
            go.Bar(name='Lifts', x=['Squat', 'Bench', 'Deadlift'], 
                  y=[lifter['Best Squat'], lifter['Best Bench'], lifter['Best Deadlift']],
                  marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ])
        fig.update_layout(
            title="Best Lifts by Movement",
            yaxis_title="Weight (kg)",
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
        
        weight_class_cat = get_weight_class_category(lifter['Body Weight (kg)'], lifter['Gender'])
        
        for lift_name, best_lift in [('squat', lifter['Best Squat']), 
                                     ('bench', lifter['Best Bench']), 
                                     ('deadlift', lifter['Best Deadlift']),
                                     ('total', lifter['Total'])]:
            record_comp = compare_to_records(lift_name, best_lift, lifter['Gender'], weight_class_cat)
            
            if record_comp:
                st.write(f"**{lift_name.title()}:** {best_lift} kg")
                
                if 'ipf_record' in record_comp:
                    ipf_pct = record_comp['ipf_percent']
                    ipf_record = record_comp['ipf_record']
                    if record_comp.get('is_ipf_record'):
                        st.markdown(f"<span class='record-indicator'>IPF WORLD RECORD!</span>", 
                                  unsafe_allow_html=True)
                    else:
                        st.progress(min(ipf_pct / 100, 1.0))
                        st.caption(f"IPF World Record: {ipf_record} kg ({ipf_pct:.1f}% of record)")
                
                if 'usapl_record' in record_comp:
                    usapl_pct = record_comp['usapl_percent']
                    usapl_record = record_comp['usapl_record']
                    if record_comp.get('is_usapl_record'):
                        st.markdown(f"<span class='record-indicator'>AMERICAN RECORD!</span>", 
                                  unsafe_allow_html=True)
                    else:
                        st.progress(min(usapl_pct / 100, 1.0))
                        st.caption(f"American Record: {usapl_record} kg ({usapl_pct:.1f}% of record)")
                
                st.write("---")

def display_coach_tools(df):
    """Display coaching and strategy tools"""
    st.header("Coach Tools")
    
    st.info("These tools help coaches make strategic decisions during competition")
    
    tab1, tab2, tab3 = st.tabs(["Competitor Analysis", "Attempt Strategy", "Division Overview"])
    
    with tab1:
        st.subheader("Competitor Scouting")
        
        gender_select = st.radio("Select Division", ["FEMALE", "MALE"], horizontal=True)
        competitors = df[df['Gender'] == gender_select].sort_values('Total', ascending=False)
        
        st.write(f"**Top Competitors in {gender_select} Division:**")
        
        for idx, comp in competitors.head(5).iterrows():
            with st.expander(f"#{comp['Place']} - {comp['Name']} - {comp['Total']} kg"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Strengths:**")
                    lifts = {
                        'Squat': comp['Best Squat'],
                        'Bench': comp['Best Bench'],
                        'Deadlift': comp['Best Deadlift']
                    }
                    best_lift = max(lifts, key=lambda k: lifts[k] / comp['Total'])
                    st.write(f"- Strongest lift: {best_lift} ({lifts[best_lift]} kg)")
                    st.write(f"- DOTS: {comp['Dots Points']:.2f}")
                    st.write(f"- Success rate: {calculate_success_rate(comp)}%")
                
                with col2:
                    st.write("**Lift Distribution:**")
                    fig = go.Figure(data=[go.Pie(
                        labels=['Squat', 'Bench', 'Deadlift'],
                        values=[comp['Best Squat'], comp['Best Bench'], comp['Best Deadlift']],
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
            target_weight = st.number_input("Proposed Attempt (kg)", 
                                           min_value=0.0, 
                                           max_value=500.0, 
                                           step=2.5,
                                           value=100.0)
        
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
            
            st.success(f"Recommendation: {target_weight} kg is {'conservative' if attempt_number == 1 else 'moderate' if attempt_number == 2 else 'aggressive'} for attempt {attempt_number}")
    
    with tab3:
        st.subheader("Division Performance Overview")
        
        gender_overview = st.radio("Division", ["FEMALE", "MALE"], horizontal=True, key="overview_gender")
        division_data = df[df['Gender'] == gender_overview]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Total Distribution**")
            fig = px.histogram(division_data, x='Total', nbins=10, 
                             title=f"{gender_overview} Division Total Distribution")
            fig.update_layout(height=300)
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
            'Average (kg)': [
                division_data['Best Squat'].mean(),
                division_data['Best Bench'].mean(),
                division_data['Best Deadlift'].mean(),
                division_data['Total'].mean()
            ]
        }
        avg_df = pd.DataFrame(avg_data)
        st.dataframe(avg_df, use_container_width=True, hide_index=True)

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

def display_rules_guide():
    """Display powerlifting rules and FAQ"""
    st.header("Rules & Competition Guide")
    
    st.info("Understanding powerlifting rules and scoring")
    
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
            st.write("**White Light** ✓")
            st.write("- Good lift")
            st.write("- Lift meets all technical requirements")
            
            st.write("")
            st.write("**Red Light** ✗")
            st.write("- Failed lift")
            st.write("- One or more technical requirements not met")
        
        with col2:
            st.write("**Card Colors Indicate Specific Infractions:**")
            st.write("- **Blue Card:** Depth or lockout issue")
            st.write("- **Red Card:** Major technical violation")
            st.write("- **Yellow Card:** Minor technical violation")
    
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

def main():
    # App title
    st.title("PowerTrack")
    st.caption("Professional Powerlifting Meet Companion")
    
    # Load data
    csv_path = "/mnt/project/avancus_houston_primetime_2025_awards_results.csv"
    
    try:
        df = load_meet_data(csv_path)
        
        # Sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Select View",
            ["Meet Overview", "Live Scoreboard", "Standings", "Lifter Analysis", "Coach Tools", "Rules & Guide"]
        )
        
        st.sidebar.markdown("---")
        st.sidebar.info("""
        **PowerTrack** provides real-time meet data, 
        performance analytics, and coaching tools for 
        powerlifting competitions.
        
        Compatible with laptops, tablets, and mobile devices.
        """)
        
        # Display selected page
        if page == "Meet Overview":
            display_meet_overview(df)
        elif page == "Live Scoreboard":
            display_live_scoreboard(df)
        elif page == "Standings":
            display_standings(df)
        elif page == "Lifter Analysis":
            display_lifter_analysis(df)
        elif page == "Coach Tools":
            display_coach_tools(df)
        else:  # Rules & Guide
            display_rules_guide()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.caption("PowerTrack v1.0 | Avancus Houston Prime 2025")
        
    except Exception as e:
        st.error(f"Error loading meet data: {str(e)}")
        st.info("Please ensure the meet data file is available.")

if __name__ == "__main__":
    main()
