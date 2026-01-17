# ✈️ FlightRisk v4.5: High-Frequency Stochastic Travel Intelligence
### *Because "Average ETA" is a gamble. Predict your risk with 95% certainty.*

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org)
[![AsyncIO](https://img.shields.io/badge/Architecture-AsyncIO-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io)
[![C++11](https://img.shields.io/badge/C++-11-00599C.svg)](https://isocpp.org/)
[![pybind11](https://img.shields.io/badge/build-pybind11-yellow.svg)](https://github.com/pybind/pybind11)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

![FlightRisk Dashboard](assets/dashboard_v3.png)
![Trip History View](assets/history_tab.png)

Standard navigation apps tell you when you'll arrive *on average*. But if a $400 flight closes its gate in 60 minutes, the average doesn't matter—the **tail-end risk** does. 

**FlightRisk v4.5** is a full-stack predictive engine that replaces static estimates with a **100,000 Monte Carlo simulation**, accounting for traffic volatility, terminal congestion, and hyper-local weather. It utilizes a **Hybrid Architecture (Async Python + Compiled C++)** to perform these simulations with <2.5s total latency.

---

## 🧠 The Statistical Stack (How it Works)

I built this project to apply **Queue Theory**, **Stochastic Modeling**, and **Async Concurrency** to a real-world logistics problem. The system fuses four specialized engines:

### 1. 🚦 Async TrafficEngine (Triangular Distribution)
Uses **`aiohttp`** to fetch three parallel data models from the **Google Directions API** (Optimistic, Best Guess, and Pessimistic) simultaneously.
* It treats these as `min`, `mode`, and `max` values to build a **Triangular Distribution**.
* **Upgrade:** By parallelizing requests, network latency was reduced by **66%**, allowing for real-time iterative searching.

### 2. ⛈️ Async WeatherEngine (Gaussian Noise Factor)
Performs parallel spatial sampling along the route polyline using the **OpenWeather API**.
* Weather severity at the origin, midpoint, and airport is mapped to a **Normal Distribution**.
* This acts as a "Volatility Multiplier" on the traffic data, expanding the variance during active storms.

### 3. ✈ FlightEngine & AirportEngine (Queue Theory)
* **FlightEngine (Async):** Validates live flight status and gate closures via **AeroDataBox API** without blocking the solver loop.
* **AirportEngine (CPU-Bound):** Airport wait times (TSA, Bag Drop, Check-in) follow a **Gamma Distribution** to model the "long-tail" risk of bottlenecks. It distinguishes between **Tier 1 Hubs** (JFK, ATL) and **Tier 2 Regional** airports.

### 4. 🧮 RiskEngine (Hybrid C++ Monte Carlo Core)
The system aggregates 100,000 samples from the engines to generate a **Probability Density Function (PDF)**.
* **Performance:** The core simulation loop is offloaded to a compiled **C++ Extension (`flightrisk_cpp`)** via **pybind11**.
* **Speedup:** Reduces simulation time from ~30.0s (Pure Python) to **<0.15s (C++)**.

---

## 🖥️ Technical Walkthrough: The UI

The v4.5 Dashboard is designed for high-stakes decision-making, emphasizing **interpretability** and **responsiveness**:

* **Non-Blocking UI:** The Streamlit frontend uses an **Async Wrapper** pattern to prevent UI freezing while the backend orchestrates 20+ API calls in parallel.
* **Interactive Risk Sliders:** Allows users to choose between *Conservative* (95% confidence), *Balanced* (85%), or *Aggressive* (75%) strategies.
* **The "Certainty Arrival" Metric:** Displays the 95th percentile worst-case arrival time, offering a statistical guarantee rather than a simple average.
* **KDE Risk Profile:** A Seaborn-rendered plot that visually separates the "Safe Zone" (green) from the "Missed Flight Zone" (red).

---

## 🔌 API & Data Integration

FlightRisk is powered by a high-concurrency data-fusion pipeline:
* **Google Directions API:** Real-time traffic, distance, and route polylines.
* **OpenWeather API:** Real-time weather conditions for origin and destination coordinates.
* **AeroDataBox API:** Live flight status lookups and automated **-15m Gate Closure** deadline calculation.

---

## 🛠 File Architecture (Modular OOP)

The project follows a standard Python package structure to separate source code, assets, and compiled binaries.

```text
FlightRisk/
├── assets/                 # UI Screenshots and static images
├── cpp_core/               # C++ Source Code
│   └── simulation.cpp      # The Monte Carlo Engine
├── src/                    # Python Application Logic
│   ├── app.py              # Async Streamlit Entry Point
│   ├── solver.py           # Async Orchestrator & Binary Search
│   ├── traffic_engine.py   # Async Google Maps Integration
│   ├── weather_engine.py   # Async OpenWeather Integration
│   ├── flight_engine.py    # Async Flight Status Lookup
│   ├── risk_engine.py      # Hybrid Engine (Python Logic + C++ Bindings)
│   ├── airport_engine.py   # TSA Queue Theory Logic (CPU Bound)
│   └── database.py         # SQLite Persistence Layer
├── setup.py                # C++ Compilation Script
└── requirements.txt        # Python Dependencies
```

---

## 🚦 Installation

1.  **Clone:**
    ```bash
    git clone [https://github.com/Brycewhi/FlightRisk.git](https://github.com/Brycewhi/FlightRisk.git)
    cd FlightRisk
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Compile C++ Core:**
    This project requires the C++ extension to be built for your system.
    ```bash
    python3 setup.py build_ext --inplace
    ```
4.  **Config:**
    Create a `.env` file in the root directory with your API keys:
    ```env
    GOOGLE_API_KEY=your_key
    OPENWEATHER_API_KEY=your_key
    RAPID_API_KEY=your_key
    ```
5.  **Run:**
    ```bash
    streamlit run src/app.py
    ```

### Troubleshooting C++ Build
If you are on macOS, ensure you have the command line tools installed:
```bash
xcode-select --install
```

---

### 📈 Roadmap

* **v5.0 [ML Feedback Layer]:**
    * **Traffic Calibration:** Train a regression model to correct systematic bias in Google's "Pessimistic" estimates (e.g., detecting if rush hour is consistently worse than predicted).
    * **Weather Impact Learning:** Replace static weather penalties with a learned model that correlates specific precipitation levels (mm/hr) to actual roadway speed reductions.
    * **Queue Theory Tuning:** Dynamically optimize the **Shape ($\alpha$)** and **Scale ($\beta$)** of the AirportEngine’s Gamma distributions based on historical "Late Arrival" rates.

---
**Developed by Bryce Whiteside** *Applied Mathematics & Computer Science | Stony Brook University* [![GitHub](https://img.shields.io/badge/GitHub-Brycewhi-181717?logo=github)](https://github.com/Brycewhi)