import streamlit as st
import pandas as pd 
from datetime import datetime, timedelta, time
import solver
import database 
from visualizer import Visualizer
from flight_engine import FlightEngine 

# Page configuration.
st.set_page_config(
    page_title="FlightRisk v3.0",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on app start.
database.init_db()

# Custom CSS.
st.markdown("""
<style>
    .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stExpander"] details summary { background-color: #262730; border-radius: 5px; }
    .suggestion-box { padding: 15px; border-radius: 8px; background-color: #262730; border-left: 5px solid #F39C12; }
    figure { background: transparent !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# Helper Functions.
def parse_flexible_time(time_str):
    time_str = time_str.strip().upper()
    formats = ["%I:%M %p", "%I:%M%p", "%H:%M"] 
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError: continue
    return None

def normalize_output(report, departure_dt, flight_dt):
    p95_eta = report.get('p95_eta', 0)
    avg_eta = report.get('avg_eta', 0)
    gate_close_dt = flight_dt - timedelta(minutes=15)
    worst_case_arrival = departure_dt + timedelta(minutes=p95_eta)
    median_arrival = departure_dt + timedelta(minutes=avg_eta)
    is_late = worst_case_arrival > gate_close_dt
    late_minutes = int((worst_case_arrival - gate_close_dt).total_seconds() / 60)
    time_to_kill = int((gate_close_dt - median_arrival).total_seconds() / 60)
    mins_available = (gate_close_dt - departure_dt).total_seconds() / 60
    bd = report.get('breakdown', {})
    if not bd: bd = {"drive": int(avg_eta*0.6), "tsa": int(avg_eta*0.3), "walk": int(avg_eta*0.1)}
    return {
        "raw_prob": report.get('success_probability', 0),
        "gate_close_dt": gate_close_dt,
        "worst_case_arrival": worst_case_arrival,
        "median_arrival": median_arrival,
        "is_late": is_late,
        "late_minutes": late_minutes,
        "time_to_kill": time_to_kill,
        "weather_mult": report.get('multiplier', 1.0),
        "breakdown": bd,
        "dist_data": report.get('raw_data', []),
        "mins_available": mins_available,
        "p95_eta": p95_eta,
        "risk_label": report.get('risk', 'UNKNOWN')
    }

# Main Application Tabs
tab_sim, tab_hist = st.tabs(["🚀 Risk Simulation", "📜 Trip History"])

# Sidebar: inputs.
with st.sidebar:
    st.header("✈️ Trip Parameters")
    
    col_input, col_btn = st.columns([2, 1])
    with col_input:
        flight_num = st.text_input("Flight Number", value="B62223")
    with col_btn:
        st.write(""); st.write("") 
        load_flight = st.button("🔍 Load")

    if 'dest_val' not in st.session_state: st.session_state.dest_val = "JFK Airport"
    if 'time_str' not in st.session_state: 
        st.session_state.time_str = (datetime.now() + timedelta(hours=4)).strftime("%I:%M %p")
    
    if load_flight:
        fe = FlightEngine()
        flight_data = fe.get_flight_details(flight_num)
        if flight_data:
            st.session_state.dest_val = flight_data['origin_airport'] 
            st.session_state.time_str = datetime.fromtimestamp(flight_data['dep_ts']).strftime("%I:%M %p")
            st.rerun()

    origin = st.text_area("Starting Address", value="Empire State Building, NY")
    destination = st.text_input("Airport", value=st.session_state.dest_val)
    flight_time_input = st.text_input("Flight Departure Time", value=st.session_state.time_str)
    
    flight_t = parse_flexible_time(flight_time_input)
    if not flight_t: st.stop()
    
    now = datetime.now()
    flight_dt = datetime.combine(now.date(), flight_t)
    if flight_dt < now: flight_dt += timedelta(days=1)
    flight_epoch = int(flight_dt.timestamp())
    
    check_bags = st.checkbox("Checking Bags?", value=True)
    tsa_pre = st.checkbox("TSA PreCheck?", value=False)
    risk_mode = st.select_slider("Risk Tolerance", options=["Conservative", "Balanced", "Aggressive"], value="Balanced")
    user_threshold = {"Conservative": 95.0, "Balanced": 85.0, "Aggressive": 75.0}[risk_mode]
    
    st.markdown("---")
    
    mode = st.radio("Simulation Mode:", ["Suggest Best Departure", "Leave Now", "Test Specific Time"], index=0)
    
    if mode == "Test Specific Time":
        dep_input = st.text_input("Manual Departure Time:", value=(now + timedelta(minutes=30)).strftime("%I:%M %p"))
        depart_t = parse_flexible_time(dep_input)
        if not depart_t: st.stop()
        depart_dt = datetime.combine(flight_dt.date(), depart_t)
        depart_epoch = int(depart_dt.timestamp())
    elif mode == "Leave Now":
        depart_dt = datetime.now()
        depart_epoch = int(depart_dt.timestamp())
    else:
        depart_epoch = int((flight_dt - timedelta(hours=3)).timestamp())
        depart_dt = datetime.fromtimestamp(depart_epoch)

    run_btn = st.button("Run Simulation", type="primary", width=True)

# Main Dashboard Logic
with tab_sim:
    if run_btn:
        with st.spinner("Analyzing Risks..."):
            if mode == "Suggest Best Departure":
                opt_epoch, dead_epoch = solver.find_optimal_departure(origin, destination, flight_epoch, check_bags, tsa_pre, risk_threshold=user_threshold)
                if opt_epoch:
                    depart_epoch, depart_dt = opt_epoch, datetime.fromtimestamp(opt_epoch)
                    st.info(f"💡 Optimal Departure: **{depart_dt.strftime('%I:%M %p')}**")
                else: st.error("❌ No viable departure found."); st.stop()
            
            raw_report = solver.run_full_analysis(origin, destination, depart_epoch, flight_epoch, check_bags, tsa_pre)
            if not raw_report: st.error("⚠️ Traffic API Failure."); st.stop()
                
            data = normalize_output(raw_report, depart_dt, flight_dt)

            # Database logging.
            database.log_trip(
                flight_num=flight_num,
                origin=origin,
                dest=destination,
                multiplier=data['weather_mult'],
                suggested_time=depart_epoch,
                probability=data['raw_prob'],
                risk_status=data['risk_label']
            )

        # UI Rendering.
        if data['is_late']:
            st.error(f"🚨 **HIGH RISK** — {data['late_minutes']}m late")
            with st.expander("💡 Suggestion", expanded=True):
                safe_time = depart_dt - timedelta(minutes=data['late_minutes'] + 15)
                st.markdown(f"👉 **Leave by:** `{safe_time.strftime('%I:%M %p')}`")
        else:
            st.success(f"✅ **SAFE** — {int(data['raw_prob'])}% Chance")

        st.markdown("---")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Gate Closes", data['gate_close_dt'].strftime("%I:%M %p"))
        c2.metric("Departure", depart_dt.strftime("%I:%M %p"))
        c3.metric("Est. Arrival", data['median_arrival'].strftime("%I:%M %p"))
        c4.metric("Time to Kill", f"{data['time_to_kill']}m")
        c5.metric("Worst Case", data['worst_case_arrival'].strftime("%I:%M %p"))

        col_chart, col_breakdown = st.columns([2, 1])
        with col_chart:
            viz = Visualizer()
            st.pyplot(viz.plot_risk_profile(data['dist_data'], data['mins_available'], data['p95_eta']))
        with col_breakdown:
            st.subheader("⏱️ Breakdown")
            bd = data['breakdown']
            st.info(f"**🚗 Drive:** ~{bd['drive']}m")
            tsa_color = "#ff4b4b" if bd['tsa'] > 30 else "#09ab3b"
            st.markdown(f"""
            <div style="background-color: rgba(60,60,60,0.3); border-left: 5px solid {tsa_color}; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>👮 TSA Wait:</strong> ~{bd['tsa']}m<br>
                <span style="font-size:0.8em; opacity:0.7">PreCheck: {'Active' if tsa_pre else 'Off'}</span>
            </div>
            """, unsafe_allow_html=True)
            st.success(f"**🏃 Walk:** ~{bd['walk']}m")
            st.caption(f"Weather Impact: {data['weather_mult']}x multiplier")

    else:
        st.info("👈 Enter flight details in the sidebar and click 'Run Simulation'")

# History Tab Logic.
with tab_hist:
    st.header("📜 Recent Trip History")
    st.write("Review your previously logged simulations below.")
    
    # Retrieve data from database.
    history_rows = database.view_history(limit=20)
    
    if history_rows:
        # Create a DataFrame for a clean, interactive table.
        df = pd.DataFrame(history_rows, columns=[
            "ID", "Run Timestamp", "Flight #", "Origin", "Destination", 
            "Weather Mult", "Rec Departure", "Probability", "Risk Status"
        ])
        
        # Display the table (hiding ID column).
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
        
        # Add an export option.
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download History as CSV",
            data=csv,
            file_name="flight_risk_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No trip history found. Run your first simulation to see data here!")