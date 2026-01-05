# ✈️ FlightRisk v3.0: Stochastic Travel Intelligence
### *Because "Average ETA" is a gamble. Predict your risk with 95% certainty.*

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)



**The Hook:** Standard navigation apps tell you when you'll arrive *on average*. But if a $400 flight closes its gate in 60 minutes, the average doesn't matter—the **tail-end risk** does. **FlightRisk v3.0** is a full-stack predictive engine that replaces static estimates with a **1,000-trial Monte Carlo simulation**, accounting for traffic volatility, terminal congestion, and hyper-local weather.

---

## 🧠 The Statistical Stack (How it Works)

I built this project to apply **Queue Theory** and **Stochastic Modeling** to a real-world logistics problem. The system fusions four specialized engines:

### 1. 🚦 TrafficEngine (Triangular Distribution)
Fetches data from the **Google Directions API** (Optimistic, Best Guess, and Pessimistic durations). 
* It treats these as `min`, `mode`, and `max` values to build a **Triangular Distribution**, simulating the reality that traffic delays are "right-skewed" (it's easier to be 20 mins late than 20 mins early).

### 2. ⛈️ WeatherEngine (Gaussian Noise Factor)
Uses the **OpenWeather API** to perform spatial sampling along the route.
* Weather severity at the origin and airport is mapped to a **Normal Distribution**, which acts as a "Volatility Multiplier" on the traffic data.

### 3. 🛡️ AirportEngine (Gamma Distribution Queue Theory)
*This is the core of terminal logistics.* Airport wait times (TSA, Bag Drop, Check-in) follow a **Gamma Distribution** to model the "long-tail" risk of unexpected security bottlenecks.
* **Tiered Logic:** The model distinguishes between **Tier 1 Hubs** (JFK, ATL) and **Tier 2 Regional** (BUR, PBI) airports to adjust wait-time variance.

### 4. 🧮 RiskEngine (Monte Carlo Integration)
The "Heart" of the system. It aggregates the 1,000 samples from the three previous engines to generate a **Probability Density Function (PDF)**. It calculates the **P95 Arrival Time**—the time by which you will arrive in 95% of simulated universes.



---

## 🔌 API & Data Integration

FlightRisk is powered by a live data-fusion pipeline:
* **Google Directions API:** Real-time traffic, distance, and route polylines.
* **OpenWeather API:** Real-time weather conditions for origin and destination coordinates.
* **AeroDataBox API:** Live flight status lookups and automated **-15m Gate Closure** deadline calculation.

---

## 🛠 File Architecture (Modular OOP)

* `app.py`: Reactive **Streamlit** dashboard with a History tab and CSV export.
* `solver.py`: The recursive search algorithm that identifies the "Latest Safe Departure."
* `flight_engine.py`: Handles live flight validation and IATA code resolution.
* `airport_engine.py`: Simulates terminal processing using Gamma-distribution queue modeling.
* `traffic_engine.py` & `weather_engine.py`: Handle external data ingestion and noise generation.
* `database.py`: **SQLite** persistence layer using the Context Manager pattern for trip logging.

---

## 🚦 Getting Started

1.  **Clone:** `git clone https://github.com/Brycewhi/FlightRisk.git`
2.  **Install:** `pip install -r requirements.txt`
3.  **Config:** Add your API keys to `.env` or `config.py`.
4.  **Run:** `streamlit run app.py`

---

## 📈 Roadmap
* **v3.5:** Implement `asyncio` to reduce API latency by 50%.
* **v4.0:** Port simulation loops to C++/PyBind11 for high-performance computation.