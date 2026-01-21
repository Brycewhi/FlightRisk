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

Standard navigation apps tell you when you will arrive on average. But if a $400 flight closes its gate in 60 minutes, the average does not matter; the tail-end risk does. 

**FlightRisk v4.5** is a full-stack predictive engine that replaces static estimates with a **100,000 Monte Carlo simulation**, accounting for traffic volatility, terminal congestion, and hyper-local weather. It utilizes a **Hybrid Architecture (Async Python + Compiled C++)** to perform these simulations with <2.5s total latency.

---

## 🧠 The Statistical Stack (How it Works)

I built this project to apply Queue Theory, Stochastic Modeling, and Async Concurrency to a real-world logistics problem. The system fuses four specialized engines:

### 1. 🚦 Async TrafficEngine (Triangular Distribution)
Uses **`aiohttp`** to fetch three parallel data models from the **Google Directions API** simultaneously.
* It treats these as `min`, `mode`, and `max` values to build a **Triangular Distribution**.
* **Timezone Synchronization:** The engine is calibrated with **`America/New_York`** logic via the `TZ` environment variable to ensure traffic departure epochs align with local roadway conditions.

### 2. ⛈️ Async WeatherEngine (One Call 3.0 Integration)
Performs parallel spatial sampling along the route polyline using the **OpenWeather One Call 3.0 API**.
* **Gaussian Noise Factor:** Weather severity (Rain, Snow, Thunderstorms) at the origin, midpoint, and airport is mapped to a **Normal Distribution**.
* **Volatility Multiplier:** Acts as a variance expander on traffic data, modeling the increased roadway uncertainty during active storms.

### 3. ✈ FlightEngine & AirportEngine (Queue Theory)
* **FlightEngine (Async):** Validates live flight status and gate closures via **AeroDataBox API**. Implements **`@st.cache_data`** to optimize limited API quotas during high-frequency testing.
* **AirportEngine (CPU-Bound):** Airport wait times follow a **Gamma Distribution** to model the long-tail risk of terminal bottlenecks.

### 4. 🧮 RiskEngine (Hybrid C++ Monte Carlo Core)
The system aggregates 100,000 samples from the engines to generate a **Probability Density Function (PDF)**.
* **Performance:** The core simulation loop is offloaded to a compiled **C++ Extension (`flightrisk_cpp`)** via **pybind11**.
* **Stochastic Labeling:** Automatically maps simulation outcomes to **Risk Status** labels (Conservative, Balanced, Aggressive) to provide instant user interpretability.

---

## 🖥️ Technical Walkthrough: The UI

* **Non-Blocking UI:** The Streamlit frontend uses an **Async Wrapper** pattern to prevent UI freezing while orchestrating 20+ API calls in parallel.
* **Persistence Layer:** Every simulation is persisted to a **SQLite** database, allowing users to track risk trends and compare departure windows in the **History Tab**.
* **The "Certainty Arrival" Metric:** Displays the 95th percentile worst-case arrival time, offering a statistical guarantee rather than a simple average.
* **KDE Risk Profile:** A Seaborn-rendered plot that visually separates the Safe Zone (green) from the Missed Flight Zone (red).

---

## 🛠 File Architecture (Modular OOP)

```text
FlightRisk/
├── assets/                 # UI Screenshots and static images
├── build/                  # C++ Build artifacts (Generated)
├── cpp_core/               # C++ Source Code
│   └── simulation.cpp      # The Monte Carlo Engine core logic
├── src/                    # Python Application Logic
│   ├── airport_engine.py   # TSA Queue Theory & Gamma Distribution logic
│   ├── app.py              # Async Streamlit Entry Point (Frontend)
│   ├── async_benchmark.py  # Performance testing & latency analysis
│   ├── config.py           # Centralized API & Environment configuration
│   ├── database.py         # SQLite Persistence Layer & History logic
│   ├── flight_engine.py    # Async AeroDataBox API Integration
│   ├── main.py             # Application logic orchestrator
│   ├── risk_engine.py      # Hybrid Engine (Python + C++ Bindings)
│   ├── solver.py           # Async Orchestrator & Binary Search
│   ├── traffic_engine.py   # Async Google Maps Integration
│   ├── visualizer.py       # Seaborn/Matplotlib KDE plotting logic
│   └── weather_engine.py   # Async OpenWeather One Call 3.0 Integration
├── .dockerignore           # Docker build exclusions
├── .env                    # Local environment variables (Hidden)
├── .gitignore              # Git version control exclusions
├── Dockerfile              # Containerization instructions
├── flight_data.db          # Cached flight status & quota protection DB
├── flightrisk.db           # Main simulation & risk history DB
├── LICENSE                 # Project MIT License
├── README.md               # Project documentation
├── requirements.txt        # Python Dependencies
├── setup.py                # C++ Compilation & pybind11 script
└── test_cpp.py             # Unit tests for C++ extension verification
```

---

## 🚢 Deployment

This project is containerized for consistent deployment across environments:

1. **Local Docker Build:**
   ```bash
   docker build -t flightrisk .
   docker run -p 8501:8501 --env-file .env flightrisk
2. **Cloud Deployment (Railway/Render):** The repository is configured for automatic deployment via the included Dockerfile. Ensure your TZ environment variable is set to America/New_York to maintain timezone synchronization across the stochastic engines.

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