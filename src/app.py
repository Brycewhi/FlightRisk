import streamlit as st
import pandas as pd 
import asyncio
import time
import os  
import aiohttp 
import pydeck as pdk
import polyline
from datetime import datetime, timedelta

# Internal Module Imports
import solver 
import database 
from visualizer import Visualizer
from engines.flight_engine import FlightEngine 

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
    div.row-widget.stButton > button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def get_map_data(polyline_str):
    """Converts Google polyline to DataFrame for PyDeck mapping."""
    if not polyline_str:
        return pd.DataFrame()
    path = polyline.decode(polyline_str)
    # PyDeck expects [lon, lat]
    return pd.DataFrame([{"lon": p[1], "lat": p[0]} for p in path])

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
        "risk_label": report.get('risk', 'UNKNOWN'),
        "polyline": report.get('route_polyline', "")
    }

# --- ASYNC WRAPPERS ---

async def get_flight_async(flight_num):
    async with aiohttp.ClientSession() as session:
        fe = FlightEngine()
        return await fe.get_flight_details(session, flight_num)

async def run_simulation_async(mode, origin, destination, depart_epoch, flight_epoch, check_bags, tsa_pre, threshold, buffer):
    s = solver.Solver()
    final_depart_epoch = depart_epoch
    dead_epoch_val = None
    
    async with aiohttp.ClientSession() as session:
        if mode == "Suggest Best Departure":
            opt_epoch, dead_epoch_val = await s.find_optimal_departure(
                origin, destination, flight_epoch, check_bags, tsa_pre, 
                risk_threshold=threshold, buffer_minutes=buffer
            )
            if not opt_epoch: return None, None, None
            final_depart_epoch = opt_epoch

        report = await s.run_full_analysis(
            session, origin, destination, final_depart_epoch, flight_epoch, 
            check_bags, tsa_pre, buffer_minutes=buffer
        )
    return report, final_depart_epoch, dead_epoch_val

# --- MAIN APP UI ---

tab_sim, tab_hist = st.tabs(["🚀 Risk Simulation", "📜 Trip History"])

with st.sidebar:
    st.header("✈️ Trip Parameters")
    
    col_input, col_btn = st.columns([2, 1])
    with col_input:
        flight_num = st.text_input("Flight Number", value="B62223")
    with col_btn:
        st.write(""); st.write("") 
        load_flight = st.button("🔍 Load")

    if 'dest_val' not in st.session_state: st.session_state.dest_val = "JFK Airport"
    if 'time_str' not in st.session_state: st.session_state.time_str = (datetime.now() + timedelta(hours=4)).strftime("%I:%M %p")
    if 'date_val' not in st.session_state: st.session_state.date_val = datetime.now()
    
    if load_flight:
        with st.spinner("Fetching..."):
            flight_data = asyncio.run(get_flight_async(flight_num))
        if flight_data:
            st.session_state.dest_val = flight_data['origin_airport'] 
            dt_obj = datetime.fromtimestamp(flight_data['dep_ts'])
            st.session_state.time_str = dt_obj.strftime("%I:%M %p")
            st.session_state.date_val = dt_obj.date()
            st.rerun()

    origin = st.text_input("Starting Address", value="Empire State Building, NY")
    destination = st.text_input("Airport", value=st.session_state.dest_val)
    
    c_date, c_time = st.columns(2)
    flight_date = c_date.date_input("Date", value=st.session_state.date_val)
    flight_time_input = c_time.text_input("Time", value=st.session_state.time_str)
    
    flight_t = parse_flexible_time(flight_time_input)
    if not flight_t: st.stop()
    flight_dt = datetime.combine(flight_date, flight_t)
    flight_epoch = int(flight_dt.timestamp())
    
    check_bags = st.checkbox("Checking Bags?", value=True)
    tsa_pre = st.checkbox("TSA PreCheck?", value=False)
    time_to_kill_input = st.slider("Buffer at Gate (min)", 0, 120, 30, help="Desired time between arriving at gate and gate closure.")
    
    risk_mode = st.select_slider("Risk Tolerance", options=["Conservative", "Balanced", "Aggressive"], value="Balanced")
    user_threshold = {"Conservative": 95.0, "Balanced": 85.0, "Aggressive": 75.0}[risk_mode]
    
    st.divider()
    mode = st.radio("Simulation Mode:", ["Suggest Best Departure", "Leave Now", "Test Specific Time"])
    
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

    run_btn = st.button("🚀 Run Simulation", type="primary")

    st.divider()
    st.subheader("📖 Metric Guide")
    with st.expander("What is P95 / Certainty?"):
        st.write("This is the 'Safe Bet' arrival. In 95% of simulations, you arrived by this time, accounting for worst-case traffic and TSA delays.")
    with st.expander("Drop Dead Time"):
        st.write("The absolute latest you can leave and still have a statistical chance of making the gate before it closes.")

# --- DASHBOARD LOGIC ---
with tab_sim:
    if run_btn:
        st.session_state['has_run'] = True
        with st.spinner("Simulating 100,000 scenarios..."):
            start_t = time.time()
            raw_report, final_epoch, dead_epoch = asyncio.run(run_simulation_async(
                mode, origin, destination, depart_epoch, flight_epoch, 
                check_bags, tsa_pre, user_threshold, time_to_kill_input
            ))
            duration = time.time() - start_t

            if final_epoch is None:
                st.error("❌ No viable departure found.")
                st.stop()
            
            final_dt = datetime.fromtimestamp(final_epoch)
            data = normalize_output(raw_report, final_dt, flight_dt)

            # Persist state
            st.session_state['current_result'] = data
            st.session_state['current_duration'] = duration
            st.session_state['final_dt'] = final_dt
            st.session_state['dead_epoch'] = dead_epoch
            
            run_id = database.log_trip(flight_num, origin, destination, data['weather_mult'], final_epoch, data['raw_prob'], data['risk_label'])
            st.session_state['current_run_id'] = run_id
            st.session_state['feedback_sent'] = False

    if st.session_state.get('has_run'):
        data = st.session_state['current_result']
        final_dt = st.session_state['final_dt']
        dead_epoch = st.session_state['dead_epoch']

        if data['is_late']:
            st.error(f"🚨 **HIGH RISK** — Expected to be {data['late_minutes']}m late")
        else:
            st.success(f"✅ **SAFE** — Recommended Departure: {final_dt.strftime('%I:%M %p')}")

        # Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Start Trip", final_dt.strftime("%I:%M %p"), help="Optimal time to leave your origin.")
        m2.metric("🛡️ Certainty", data['worst_case_arrival'].strftime("%I:%M %p"), help="95% probability of arrival by this time.")
        m3.metric("Gate Closes", data['gate_close_dt'].strftime("%I:%M %p"))
        m4.metric("💀 Drop Dead", datetime.fromtimestamp(dead_epoch).strftime("%I:%M %p") if dead_epoch else "N/A", help="Latest possible departure time.")
        m5.metric("Success Rate", f"{int(data['raw_prob'])}%")

        st.divider()

        # Visuals: Chart & Map
        col_viz, col_map = st.columns([1, 1])
        with col_viz:
            st.subheader("📈 Risk Distribution")
            viz = Visualizer()
            st.pyplot(viz.plot_risk_profile(data['dist_data'], data['mins_available'], data['p95_eta']))
            st.caption(f"⚡ Monte Carlo Latency: {st.session_state['current_duration']:.3f}s")
            
        with col_map:
            st.subheader("🗺️ Live Route")
            map_points = get_map_data(data['polyline'])
            if not map_points.empty:
                st.pydeck_chart(pdk.Deck(
                    # Use 'light' or 'dark' (lowercase) for built-in styles that often work without tokens
                    map_style='light', 
                    initial_view_state=pdk.ViewState(
                        latitude=map_points['lat'].mean(),
                        longitude=map_points['lon'].mean(),
                        zoom=10, 
                        pitch=45
                    ),
                    layers=[
                        pdk.Layer(
                            'PathLayer',
                            data=[{"path": map_points[["lon", "lat"]].values.tolist()}],
                            get_path='path',
                            width_scale=20,
                            width_min_pixels=3,
                            get_color='[0, 255, 150, 200]',
                        ),
                    ],
                ))
            else:
                st.info("No map data available.")

        # Breakdown Sidebar-style section
        st.divider()
        st.subheader("⏱️ Segment Breakdown")
        b1, b2, b3, b4 = st.columns(4)
        bd = data['breakdown']
        b1.info(f"🚗 **Drive:** ~{bd['drive']}m")
        b2.info(f"👮 **TSA:** ~{bd['tsa']}m")
        b3.info(f"🏃 **Walk:** ~{bd['walk']}m")
        if data['weather_mult'] > 1.0:
            b4.warning(f"⛈️ Weather Impact: +{int((data['weather_mult']-1)*100)}%")

        # Feedback
        st.divider()
        st.write("### 🤖 Model Accuracy Feedback")
        if not st.session_state.get('feedback_sent'):
            f1, f2, _ = st.columns([1, 1, 4])
            if f1.button("👍 Looks Correct"):
                database.log_feedback(st.session_state['current_run_id'], 1)
                st.session_state['feedback_sent'] = True
                st.rerun()
            if f2.button("👎 Seems Off"):
                database.log_feedback(st.session_state['current_run_id'], 0)
                st.session_state['feedback_sent'] = True
                st.rerun()
        else:
            st.success("Feedback saved! Thanks for helping us tune the engine.")

with tab_hist:
    st.header("📜 Recent Simulations")
    history = database.view_history(limit=25)
    if history:
        df = pd.DataFrame(history, columns=["ID", "Timestamp", "Flight", "Origin", "Dest", "Weather", "Departure", "Prob", "Status", "Feedback"])
        df['Departure'] = df['Departure'].apply(lambda x: datetime.fromtimestamp(int(x)).strftime('%I:%M %p') if x else "N/A")
        df['Feedback'] = df['Feedback'].map({1: "👍", 0: "👎"}).fillna("—")
        st.dataframe(df.drop(columns=["ID"]), width='stretch', hide_index=True)
    else:
        st.info("No history found.")