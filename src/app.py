import streamlit as st
import pandas as pd 
import asyncio
import time
import os  
import aiohttp 
from datetime import datetime, timedelta

# Internal Module Imports
import solver 
import database 
from visualizer import Visualizer
from flight_engine import FlightEngine 

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FlightRisk v4.5",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema
database.init_db()

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stExpander"] details summary { background-color: #262730; border-radius: 5px; }
    figure { background: transparent !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; font-size: 18px; }
    div.row-widget.stButton > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

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
    if not bd: 
        bd = {"drive": int(avg_eta*0.6), "tsa": int(avg_eta*0.3), "walk": int(avg_eta*0.1)}
        
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

# --- ASYNC WRAPPERS ---

async def get_flight_async(flight_num):
    """Fetches flight data using a temporary session."""
    async with aiohttp.ClientSession() as session:
        fe = FlightEngine()
        return await fe.get_flight_details(session, flight_num)

async def run_simulation_async(
    mode, origin, destination, 
    depart_epoch, flight_epoch, 
    check_bags, tsa_pre, 
    threshold, buffer
):
    """
    Orchestrates the Solver Class. 
    Instantiates Solver and manages the aiohttp Session.
    """
    s = solver.Solver() # Instantiate Class
    final_depart_epoch = depart_epoch
    dead_epoch_val = None
    
    # Open ONE session for all operations
    async with aiohttp.ClientSession() as session:
        
        if mode == "Suggest Best Departure":
            opt_epoch, dead_epoch_val = await s.find_optimal_departure(
                origin, destination, flight_epoch, 
                check_bags, tsa_pre, 
                risk_threshold=threshold, 
                buffer_minutes=buffer
            )
            if not opt_epoch:
                return None, None, None
            final_depart_epoch = opt_epoch

        # Run final analysis
        report = await s.run_full_analysis(
            session, # Pass session
            origin, destination, final_depart_epoch, flight_epoch, 
            check_bags, tsa_pre, buffer_minutes=buffer
        )
    
    return report, final_depart_epoch, dead_epoch_val

# --- MAIN APP UI ---

tab_sim, tab_hist = st.tabs(["🚀 Risk Simulation", "📜 Trip History"])

with st.sidebar:
    st.header("✈️ Trip Parameters")

    if os.getenv("USE_REAL_DATA_DANGEROUS") != "True":
        st.warning("SAFE MODE ACTIVE: Using Simulated Data")
    
    col_input, col_btn = st.columns([2, 1])
    with col_input:
        flight_num = st.text_input("Flight Number", value="B62223")
    with col_btn:
        st.write(""); st.write("") 
        load_flight = st.button("🔍 Load")

    # Initialize Sidebar State
    if 'dest_val' not in st.session_state: st.session_state.dest_val = "JFK Airport"
    if 'time_str' not in st.session_state: 
        st.session_state.time_str = (datetime.now() + timedelta(hours=4)).strftime("%I:%M %p")
    if 'date_val' not in st.session_state: st.session_state.date_val = datetime.now()
    
    if load_flight:
        with st.spinner("Fetching Live Flight Data..."):
            flight_data = asyncio.run(get_flight_async(flight_num))
            
        if flight_data:
            st.session_state.dest_val = flight_data['origin_airport'] 
            dt_obj = datetime.fromtimestamp(flight_data['dep_ts'])
            st.session_state.time_str = dt_obj.strftime("%I:%M %p")
            st.session_state.date_val = dt_obj.date()
            st.success("Flight Loaded!")
            st.rerun()
        else:
            st.error("Flight not found.")

    origin = st.text_input("Starting Address", value="Empire State Building, NY")
    destination = st.text_input("Airport", value=st.session_state.dest_val)
    
    col_date, col_time = st.columns(2)
    with col_date:
        flight_date = st.date_input("Flight Date", value=st.session_state.date_val)
    with col_time:
        flight_time_input = st.text_input("Flight Time", value=st.session_state.time_str)
    
    flight_t = parse_flexible_time(flight_time_input)
    if not flight_t: st.stop()
    
    flight_dt = datetime.combine(flight_date, flight_t)
    flight_epoch = int(flight_dt.timestamp())
    
    check_bags = st.checkbox("Checking Bags?", value=True)
    tsa_pre = st.checkbox("TSA PreCheck?", value=False)
    time_to_kill_input = st.slider("Desired 'Time to Kill' (min)", 0, 120, 30)
    
    risk_mode = st.select_slider("Risk Tolerance", options=["Conservative", "Balanced", "Aggressive"], value="Balanced")
    user_threshold = {"Conservative": 95.0, "Balanced": 85.0, "Aggressive": 75.0}[risk_mode]
    
    st.markdown("---")
    
    mode = st.radio("Simulation Mode:", ["Suggest Best Departure", "Leave Now", "Test Specific Time"], index=0)
    
    if mode == "Test Specific Time":
        dep_input = st.text_input("Manual Departure Time:", value=(datetime.now() + timedelta(minutes=30)).strftime("%I:%M %p"))
        depart_t = parse_flexible_time(dep_input)
        if not depart_t: st.stop()
        depart_dt = datetime.combine(flight_date, depart_t)
        depart_epoch = int(depart_dt.timestamp())
    elif mode == "Leave Now":
        depart_dt = datetime.now()
        depart_epoch = int(depart_dt.timestamp())
    else:
        depart_epoch = int((flight_dt - timedelta(hours=3)).timestamp())
        depart_dt = datetime.fromtimestamp(depart_epoch)

    run_btn = st.button("Run Simulation", type="primary", width='stretch')

# --- DASHBOARD LOGIC ---
with tab_sim:
    # 1. RUN SIMULATION LOGIC
    if run_btn:
        st.session_state['has_run'] = True
        with st.spinner("🚀 Simulating 100,000 travel scenarios..."):
            
            start_t = time.time()
            
            raw_report, final_epoch, dead_epoch = asyncio.run(run_simulation_async(
                mode, origin, destination, 
                depart_epoch, flight_epoch, 
                check_bags, tsa_pre, 
                user_threshold, time_to_kill_input
            ))
            
            duration = time.time() - start_t

            if final_epoch is None:
                st.error("❌ No viable departure found.")
                st.stop()
            if not raw_report:
                st.error("⚠️ Backend Failure.")
                st.stop()
            
            final_dt = datetime.fromtimestamp(final_epoch)
            data = normalize_output(raw_report, final_dt, flight_dt)

            # STORE RESULTS IN SESSION STATE (Persistence for Feedback)
            st.session_state['current_result'] = data
            st.session_state['current_duration'] = duration
            st.session_state['final_dt'] = final_dt
            st.session_state['dead_epoch'] = dead_epoch
            st.session_state['flight_num_log'] = flight_num
            st.session_state['origin_log'] = origin
            
            # LOG TRIP TO DB & SAVE RUN ID
            run_id = database.log_trip(
                flight_num=flight_num,
                origin=origin,
                dest=destination,
                multiplier=data['weather_mult'],
                suggested_time=final_epoch,
                probability=data['raw_prob'],
                risk_status=data['risk_label']
            )
            st.session_state['current_run_id'] = run_id

    # 2. DISPLAY RESULTS (From Session State)
    if st.session_state.get('has_run'):
        data = st.session_state['current_result']
        final_dt = st.session_state['final_dt']
        dead_epoch = st.session_state['dead_epoch']
        duration = st.session_state['current_duration']

        # RISK HEADER
        if data['is_late']:
            st.error(f"🚨 **HIGH RISK** — {data['late_minutes']}m late")
            with st.expander("💡 Rescue Plan", expanded=True):
                safe_time = final_dt - timedelta(minutes=data['late_minutes'] + 20)
                st.markdown(f"👉 **You need to leave by:** `{safe_time.strftime('%I:%M %p')}` to survive.")
        else:
            if mode == "Suggest Best Departure":
                st.success(f"💡 **Optimal Departure:** {final_dt.strftime('%I:%M %p')}")
            else:
                st.success(f"✅ **SAFE** — {int(data['raw_prob'])}% Success Probability")

        st.markdown("---")
        
        # METRICS GRID
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Suggested Departure", final_dt.strftime("%I:%M %p"))
        c2.metric("🛡️ Certainty Arrival", data['worst_case_arrival'].strftime("%I:%M %p"))
        c3.metric("Gate Closes", data['gate_close_dt'].strftime("%I:%M %p"))
        
        if dead_epoch:
            c4.metric("💀 Drop Dead", datetime.fromtimestamp(dead_epoch).strftime("%I:%M %p"))
        else:
            c4.metric("Drop Dead", "N/A")
            
        c5.metric("Time to Kill", f"{data['time_to_kill']}m")
        st.caption(f"⚡ Monte Carlo Simulation processed in {duration:.2f} seconds.")

        # VISUALIZATION
        col_chart, col_breakdown = st.columns([2, 1])
        with col_chart:
            viz = Visualizer()
            fig = viz.plot_risk_profile(data['dist_data'], data['mins_available'], data['p95_eta'])
            st.pyplot(fig)
            
        with col_breakdown:
            st.subheader("⏱️ Time Breakdown")
            bd = data['breakdown']
            st.info(f"**🚗 Drive:** ~{bd['drive']}m")
            
            tsa_color = "#ff4b4b" if bd['tsa'] > 30 else "#09ab3b"
            tsa_label = "PreCheck Active" if tsa_pre else "Standard Lane"
            st.markdown(f"""
            <div style="background-color: rgba(60,60,60,0.3); border-left: 5px solid {tsa_color}; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>👮 TSA Wait:</strong> ~{bd['tsa']}m<br>
                <span style="font-size:0.8em; opacity:0.7">{tsa_label}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.success(f"**🏃 Walk:** ~{bd['walk']}m")
            
            if data['weather_mult'] > 1.0:
                st.warning(f"⛈️ Weather Penalty: {int((data['weather_mult']-1)*100)}% slower")

        # 3. FEEDBACK LOOP
        st.markdown("---")
        st.write("### 🤖 Model Feedback")
        st.write("Help us improve accuracy. Does this assessment feel correct?")
        
        if 'current_run_id' in st.session_state:
            run_id = st.session_state['current_run_id']
            col_good, col_bad = st.columns(2)
            
            with col_good:
                if st.button("👍 Good Prediction", key="btn_good"):
                    database.log_feedback(run_id, 1)
                    st.toast("Feedback Saved: Positive", icon="✅")
                    
            with col_bad:
                if st.button("👎 Inaccurate", key="btn_bad"):
                    database.log_feedback(run_id, 0)
                    st.toast("Feedback Saved: Negative", icon="📉")

    else:
        st.info("👈 Enter flight details in the sidebar and click 'Run Simulation'")

# --- HISTORY TAB ---
with tab_hist:
    st.header("📜 Recent Trip History")
    st.write("Review your previously logged simulations below.")
    
    history_rows = database.view_history(limit=20)
    
    if history_rows:
        # Note: Added Feedback Column to View
        df = pd.DataFrame(history_rows, columns=[
            "ID", "Run Timestamp", "Flight #", "Origin", "Destination", 
            "Weather Mult", "Rec Departure", "Probability", "Risk Status", "User Feedback"
        ])
        
        st.dataframe(df.drop(columns=["ID"]), width='stretch', hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download History as CSV",
            data=csv,
            file_name="flight_risk_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No trip history found. Run your first simulation to see data here!")