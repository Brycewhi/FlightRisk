# ✈️ FlightRisk (v2.0)
### *Stochastic Travel Intelligence for the High-Stakes Traveler.*

![Risk Profile Visualization](risk_profile_v2.png)
*> Figure 1: Real-time Monte Carlo simulation (N=1,000) showing the Probability Density Function (PDF) of arrival times against a strict flight departure deadline.*

I built this because "Average ETA" is a lie. When you have a $300 flight on the line, you don't care about the *average* time; you care about the *worst-case* scenario. **FlightRisk** replaces static navigation estimates with a probabilistic distribution of risks.

## 🧠 How it works (The Math)

The "brain" of this project is a **Monte Carlo Simulation Engine** that models uncertainty using distinct statistical distributions:

### 1. Stochastic Traffic Modeling (Triangular Distribution)
Traffic isn't random; it's bounded. I use the **Google Directions API** to fetch three distinct data points: *Optimistic*, *Best Guess*, and *Pessimistic* duration.
* The engine treats these as `left`, `mode`, and `right` parameters for a **Triangular Distribution**.
* It generates **1,000 unique trip scenarios** to model the realistic variance of road conditions.

### 2. Weather Volatility (Normal Distribution)
Weather impact is non-linear. The system performs **Spatial Sampling** along the decoded polyline (Origin → Midpoint → Airport) using the **OpenWeather API**.
* Route segments are weighted (Destination weather carries 65% risk weight).
* Weather severity introduces a **Gaussian noise factor** (Normal Distribution) to the traffic simulation, expanding the variance during storms.

### 3. The Result: 95% Confidence (P95)
Instead of a single time, the app calculates the **95th Percentile (P95)** arrival time.
* *Translation:* "In 950 out of 1,000 simulated universes, you arrive by this time."
* This effectively quantifies the "Tail Risk" of missing your flight.

---

## 🛠 Tech Stack

**Engineering & APIs:**
* **Python 3.10** (Modular OOP Architecture)
* **Google Directions API** (Traffic modeling & Polyline decoding)
* **OpenWeather API** (Spatial environmental sampling)

**Data Science & Visualization:**
* **NumPy** (Vectorized simulation generation)
* **Pandas** (Statistical aggregation)
* **Seaborn & Matplotlib** (Kernel Density Estimation & plotting)

---

## 🚦 Getting Started

1. **Clone it:** `git clone https://github.com/Brycewhi/FlightRisk.git`
2. **Setup venv:** `source venv/bin/activate`
3. **Install:** `pip install -r requirements.txt`
4. **Config:** Throw your API keys into `config.py` (or use a `.env`).
5. **Run:** `python main.py`

---

## 🚧 Status & Whats's Next

### Phase 1: The Foundation [COMPLETED ✅]
- [x] Environment setup and Google Maps API integration.
- [x] OpenWeather API integration and Polyline decoding.
- [x] Static Dashboard for base risk calculations.

### Phase 2: Stochastic Intelligence [COMPLETED ✅]
- [x] **Statistical Engine:** Implemented Monte Carlo simulations (1,000 iterations).
- [x] **Math:** Fused Triangular (Traffic) and Normal (Weather) distributions.
- [x] **Visualizer:** Added Matplotlib/Seaborn KDE plots to visualize the "Bell Curve" of risk.
- [x] **Confidence Intervals:** Implemented P95 arrival time analysis.

### Phase 3: Real-World Data Fusion [UPCOMING 🔄]
- [ ] **TSA Logistics:** Model Curb-to-Gate time as a third random variable.
- [ ] **Flight Tracking:** Integrate live flight status to dynamically adjust deadlines.
- [ ] **Gamma Distributions:** Use Gamma math for flight delays (modeling "long-tail" events).
- [ ] **Streamlit UI:** Move from the Terminal to a browser-based interactive dashboard.
