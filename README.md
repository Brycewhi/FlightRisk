# ✈️ FlightRisk v3.0: Stochastic Travel Intelligence
### *Because "Average ETA" is a gamble. Predict your risk with 95% certainty.*

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io)
[![C++11](https://img.shields.io/badge/C++-11-00599C.svg)](https://isocpp.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![FlightRisk Dashboard](assets/dashboard_v3.png)
![Trip History View](assets/history_tab.png)

Standard navigation apps tell you when you'll arrive *on average*. But if a $400 flight closes its gate in 60 minutes, the average doesn't matter—the **tail-end risk** does. **FlightRisk v3.0** is a full-stack predictive engine that replaces static estimates with a **1,000-trial Monte Carlo simulation**, accounting for traffic volatility, terminal congestion, and hyper-local weather.

---

## 🧠 The Statistical Stack (How it Works)

I built this project to apply **Queue Theory** and **Stochastic Modeling** to a real-world logistics problem. The system fuses four specialized engines:

### 1. 🚦 TrafficEngine (Triangular Distribution)
Fetches data from the **Google Directions API** (Optimistic, Best Guess, and Pessimistic durations). 
* It treats these as `min`, `mode`, and `max` values to build a **Triangular Distribution**.
* This simulates the reality that traffic delays are "right-skewed"—it is mathematically easier to be 20 minutes late than 20 minutes early.

### 2. ⛈️ WeatherEngine (Gaussian Noise Factor)
Uses the **OpenWeather API** to perform spatial sampling along the route polyline.
* Weather severity at the origin and airport is mapped to a **Normal Distribution**.
* This acts as a "Volatility Multiplier" on the traffic data, expanding the variance during active storms.

### 3. 🛡️ AirportEngine (Gamma Distribution Queue Theory)
Airport wait times (TSA, Bag Drop, Check-in) follow a **Gamma Distribution** to model the "long-tail" risk of unexpected bottlenecks.
* **Tiered Logic:** The model distinguishes between **Tier 1 Hubs** (JFK, ATL) and **Tier 2 Regional** airports to adjust wait-time variance.

### 4. 🧮 RiskEngine (Monte Carlo Integration)
The system aggregates 1,000 samples from the engines to generate a **Probability Density Function (PDF)**.
* **Hybrid Architecture:** The project includes both a NumPy-based Python engine and a high-performance **C++ simulation core** (`cpp_core/`) capable of running 100k+ iterations in <0.05s.

---

## 🖥️ Technical Walkthrough: The UI

The v3.0 Dashboard is designed for high-stakes decision-making, emphasizing **interpretability** and **actionability**:

* **Interactive Risk Sliders:** Allows users to choose between *Conservative* (95% confidence), *Balanced* (85%), or *Aggressive* (75%) strategies.
* **The "Leave Now" Mode:** Calculates the immediate probability of arrival based on current system time for travelers in transit.
* **KDE Risk Profile:** A Seaborn-rendered plot that visually separates the "Safe Zone" (green) from the "Missed Flight Zone" (red) relative to strict gate-closure deadlines.
* **Trip History:** A persistence-backed tab utilizing **Pandas** to display previous runs from the **SQLite** database, allowing for CSV export and auditability.

---

## 🔌 API & Data Integration

FlightRisk is powered by a live data-fusion pipeline:
* **Google Directions API:** Real-time traffic, distance, and route polylines.
* **OpenWeather API:** Real-time weather conditions for origin and destination coordinates.
* **AeroDataBox API:** Live flight status lookups and automated **-15m Gate Closure** deadline calculation.

---

## 🛠 File Architecture (Modular OOP)

The project follows a standard Python package structure to separate source code, assets, and compiled binaries.

```text
FlightRisk/
├── assets/                 # UI Screenshots and static images
├── cpp_core/               # C++ Simulation Engine (High-Performance)
│   └── simulation.cpp
├── src/                    # Source Code Package
│   ├── app.py              # Main Streamlit Dashboard
│   ├── main.py             # CLI Entry Point
│   ├── solver.py           # Recursive Departure Optimization Algorithm
│   ├── config.py           # Environment & Path Configuration
│   ├── database.py         # SQLite Persistence Layer
│   ├── traffic_engine.py   # Google Maps Integration
│   ├── weather_engine.py   # OpenWeather Integration
│   ├── flight_engine.py    # AeroDataBox Integration
│   ├── risk_engine.py      # Python Monte Carlo Logic
│   └── visualizer.py       # Matplotlib/Seaborn Rendering
├── .env                    # API Keys (GitIgnored)
└── requirements.txt        # Python Dependencies
```

---

## 🚦 Installation

1.  **Clone:**
    ```bash
    git clone [https://github.com/Brycewhi/FlightRisk.git](https://github.com/Brycewhi/FlightRisk.git)
    cd FlightRisk
    ```
2.  **Install:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Config:**
    Create a `.env` file in the root directory with your API keys:
    ```env
    GOOGLE_API_KEY=your_key
    OPENWEATHER_API_KEY=your_key
    RAPID_API_KEY=your_key
    ```
4.  **Run:**
    ```bash
    streamlit run src/app.py
    ```

### 🐍 Developer Setup (Virtual Environment)
If you are developing locally, it is recommended to use a virtual environment:
```bash
# Create the environment
python3 -m venv .venv

# Activate it (Mac/Linux)
source .venv/bin/activate

# Activate it (Windows)
.venv\Scripts\activate
```

### ⚡ C++ Core Compilation (Optional)
To enable the high-performance simulation engine, compile the C++ shared library:
```bash
g++ -O3 -shared -std=c++11 -fPIC cpp_core/simulation.cpp -o cpp_core/simulation.so
```

---

## 📈 Roadmap

* **v3.5:** Implement `asyncio` to parallelize multi-engine API requests (Proof of Concept in `src/async_benchmark.py`).
* **v4.0:** Full integration of the C++ Core via `ctypes` for main dashboard simulations.
* **v4.5 [ML Feedback Layer]:**
    * Implement a regression model to analyze `trip_history` data from SQLite.
    * Use actual vs. predicted arrival deltas to dynamically tune the **Shape ($\alpha$)** and **Scale ($\beta$)** parameters of the AirportEngine’s Gamma distributions.

---
**Developed by Bryce Whiteside** *Applied Mathematics & Computer Science | Stony Brook University* [![GitHub](https://img.shields.io/badge/GitHub-Brycewhi-181717?logo=github)](https://github.com/Brycewhi)