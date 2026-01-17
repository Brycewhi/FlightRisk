# ✈️ FlightRisk v4.5: High-Frequency Stochastic Travel Intelligence
### *Because "Average ETA" is a gamble. Predict your risk with 95% certainty.*

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org)
[![AsyncIO](https://img.shields.io/badge/Architecture-AsyncIO-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io)
[![C++11](https://img.shields.io/badge/C++-11-00599C.svg)](https://isocpp.org/)
[![pybind11](https://img.shields.io/badge/build-pybind11-yellow.svg)](https://github.com/pybind/pybind11)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**🔗 [Live Demo on Railway](https://flightrisk-production.up.railway.app/)**

![FlightRisk Dashboard](assets/dashboard_v3.png)
![Trip History View](assets/history_tab.png)

Standard navigation apps tell you when you'll arrive **on average**. But if a $400 flight closes its gate in 60 minutes, the average doesn't matter—the **tail-end risk** does. 

**FlightRisk v4.5** is a full-stack predictive engine that replaces static estimates with a **100,000 Monte Carlo simulation**, accounting for traffic volatility, terminal congestion, and hyper-local weather. It utilizes a **Hybrid Architecture (Async Python + Compiled C++)** to perform these simulations with <2.5s total latency.

## 🧠 The Statistical Stack (How it Works)

The system fuses four specialized engines to quantify travel uncertainty:

### 1. 🚦 Async TrafficEngine (Triangular Distribution)
Uses **`aiohttp`** to fetch three parallel data models from the **Google Directions API** simultaneously.
* **Stochastic Inputs:** Maps `min`, `mode`, and `max` values to a **Triangular Distribution**.
* **Timezone Synchronization:** Calibrated for **`America/New_York`** (EST) to ensure traffic departure epochs align with local roadway conditions, regardless of server location.

### 2. ⛈️ Async WeatherEngine (One Call 3.0 Integration)
Performs parallel spatial sampling along the route polyline using the **OpenWeather One Call 3.0 API**.
* **Gaussian Noise Factor:** Weather severity (Rain, Snow, Thunderstorms) is mapped to a **Normal Distribution**.
* **Volatility Multiplier:** Expands roadway variance during active storms, providing a realistic "spread" of possible drive times.

### 3. ✈ FlightEngine & AirportEngine (Queue Theory)
* **FlightEngine (Async):** Validates live flight status and gate closures via **AeroDataBox API**. Implements **`@st.cache_data`** to optimize limited API quotas during high-frequency testing.
* **AirportEngine (CPU-Bound):** Airport wait times follow a **Gamma Distribution** to model the "long-tail" risk of terminal bottlenecks.

### 4. 🧮 RiskEngine (Hybrid C++ Monte Carlo Core)
The system aggregates 100,000 samples to generate a **Probability Density Function (PDF)**.
* **Performance:** Core simulation loop is offloaded to a compiled **C++ Extension (`flightrisk_cpp`)** via **pybind11**.
* **Stochastic Labeling:** Maps outcomes to **Risk Status** labels (Conservative, Balanced, Aggressive) for instant user interpretability.

## 🖥️ Technical Walkthrough: The UI

* **Non-Blocking UI:** The Streamlit frontend uses an **Async Wrapper** pattern to prevent UI freezing while orchestrating 20+ API calls in parallel.
* **Persistence Layer:** Every simulation is persisted to a **SQLite** database, allowing users to track risk trends and compare departure windows in the **History Tab**.
* **KDE Risk Profile:** A Seaborn-rendered plot visually separates the "Safe Zone" (green) from the "Missed Flight Zone" (red).

## 🛠 File Architecture (Modular OOP)

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

```markdown
## 📈 Machine Learning Roadmap (v5.0)

While the current engine uses high-fidelity stochastic modeling, the next phase involves replacing static multipliers with **Learned Feature Sets**:

* **Traffic Bias Correction:** Implement a **Random Forest Regressor** to identify systematic bias in "Pessimistic" traffic estimates (e.g., quantifying how much Google under-predicts Friday rush hour in NYC).
* **Dynamic Weather Weighting:** Replace static condition penalties with a model trained on historical precipitation data (mm/hr) to predict the exact roadway speed reduction.
* **Stochastic Tuning:** Use **Bayesian Optimization** to dynamically adjust the Shape ($\alpha$) and Scale ($\beta$) parameters of the AirportEngine’s Gamma distributions based on real-time "Late Arrival" feedback loops.

```markdown
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
    ```bash
    python3 setup.py build_ext --inplace
    ```
4.  **Config:**
    Set Railway Variables or a local `.env`:
    ```env
    TZ=America/New_York
    GOOGLE_API_KEY=your_key
    OPENWEATHER_API_KEY=your_key
    RAPID_API_KEY=your_key
    ```
5.  **Run:**
    ```bash
    streamlit run src/app.py
    ```

---
**Developed by Bryce Whiteside** *Applied Mathematics & Computer Science | Stony Brook University* [![GitHub](https://img.shields.io/badge/GitHub-Brycewhi-181717?logo=github)](https://github.com/Brycewhi)