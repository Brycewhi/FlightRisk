import numpy as np
import pandas as pd

def simulate_monte_carlo(opt, best, pess, weather_impact, weather_type="Clear"):
    # Set random seed to any arbitrary integer to ensure same 'random' results every time. 
    np.random.seed(16)
    iterations = 1000
    
    print(f"--- RUNNING {iterations} SIMULATIONS ---")
    
    # Simulate Traffic: Using a Triangular Distribution.
    # This assumes 'best_guess' is the peak, but it can vary between 'optimistic' and 'pessimistic'.
    traffic_samples = np.random.triangular(opt, best, pess, iterations)
    
    # Volatility increases depending on weather severity.
    volatility_map = {
        "Clear": 0.02,
        "Clouds": 0.03,
        "Drizzle": 0.05,
        "Mist": 0.08,
        "Fog": 0.10,
        "Haze": 0.10,
        "Rain": 0.12,
        "Thunderstorm": 0.20,
        "Snow": 0.25,
        "Squall": 0.40
    }
    current_vol = volatility_map.get(weather_type, 0.05)

    # Simulate Weather: Adding some randomness to the weather impact.
    # Even if weather is 'Rain', the severity varies trip-to-trip.
    weather_samples = np.random.normal(weather_impact, current_vol, iterations)
    
    # Combine: The Stochastic Trip Time (Hadamard Product).
    results = traffic_samples * weather_samples
    
    # Analyze with Pandas.
    df = pd.Series(results)
    
    # Calculate key risk metrics.
    avg = df['travel_time'].mean()
    p95 = df['travel_time'].quantile(0.95)
    std_dev = df['travel_time'].std()

    
    print(f"Input: Opt={opt}m, Best={best}m, Pess={pess}m, Weather_type={weather_type}")
    print(f"Weather Impact: {weather_impact}x (±{current_vol} variance)")
    print("-" * 50)
    print(f"RESULT: On average, you'll arrive in {avg:.1f} minutes.")
    print(f"RISK: To be 95% safe, you need {p95:.1f} minutes.")
    print(f"Standard Deviation: {std_dev:.2f} minutes.")
    
    # Check a specific deadline.
    deadline = 80
    success_rate = (df['travel_time'] < deadline).mean() * 100
    print("-" * 50)
    print(f"CHANCE OF SUCCESS: {success_rate:.1f}% chance of arriving before {deadline} mins.")
    if success_rate < 85:
        print("ADVICE: High Risk. Leave earlier than planned.")
    else:
        print("ADVICE: Within safe parameters.")

if __name__ == "__main__":
    # Test a variable route (Large gap between Best and Pessimistic).
    simulate_monte_carlo(40, 50, 90, 1.25, "Rain")