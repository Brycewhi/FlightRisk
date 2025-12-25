# ✈️ FlightRisk (v1.0)
### *Because "ETA" isn't the same thing as "Actually making your flight."*

I built this because I’m tired of navigation apps giving me a "best-case scenario" time when I have a $300 flight on the line. I wanted a tool that treats travel time as a **distribution of risks** rather than a single number.

## 🧠 How it works (The Logic)

The "brain" of this project is a multi-layered risk engine that combines two main variables:

### 1. The Traffic "Sandwich"
Instead of just asking Google "How long?", I fetch the **Optimistic**, **Best Guess**, and **Pessimistic** models simultaneously. 
* If the gap between "Optimistic" and "Pessimistic" is huge, the app flags a **Low Confidence** score. 
* This captures "volatility"—if one accident on the LIE changes your trip by 40 minutes, you need to know that before you leave.

### 2. Spatial Weather Sampling
Weather doesn't just happen at your house; it happens on the road. This engine decodes the route's **G-Maps Polyline** into GPS coordinates and samples the weather at:
* **The Start** (Origin)
* **The Midpoint** (Halfway)
* **The Destination** (Airport)

**The Logic:** I’ve weighted the impact so that bad weather at the **Destination** carries a 65% risk weight. Why? Because if you hit a storm 5 minutes from JFK, you have zero "buffer time" left to recover from the delay.

---

## 🛠 Tech Stack
* **Python 3.10** (Modular engine structure)
* **Google Directions API** (Traffic modeling & polylines)
* **OpenWeather API** (Spatial sampling)
* **Polyline Library** (For coordinate decoding)

---

## 🚦 Getting Started

1. **Clone it:** `git clone https://github.com/YOUR_USERNAME/FlightRisk.git`
2. **Setup venv:** `source venv/bin/activate`
3. **Install:** `pip install -r requirements.txt`
4. **Config:** Throw your API keys into `config.py` (or use a `.env`).
5. **Run:** `python main.py`

---

## 🚧 Status & What's Next
**Phase 1 (Complete):**
- [x] Multi-model traffic integration.
- [x] Weighted weather impact logic.
- [x] Future-dated scheduling (Unix timestamps).
- [x] Terminal Dashboard UI.

**Phase 2 (Current):** Moving from deterministic "labels" to **Monte Carlo Simulations**. I'm currently working on a statistical layer using `NumPy` to run 1,000 trip iterations to provide a "Probability of Arrival" percentage based on historical variance.