import asyncio
import time
from typing import Dict, Union

# Architectural Proof-of-Concept
# Demonstrates the latency reduction achieved by the AsyncIO Event Loop.

async def fetch_weather_api() -> Dict[str, Union[int, str]]:
    """Simulates a medium-latency API call (1.5s)."""
    print("Fetching Weather Data...")
    await asyncio.sleep(1.5) 
    return {"temp": 72, "condition": "Clear"}

async def fetch_traffic_api() -> Dict[str, Union[int, str]]:
    """Simulates a high-latency API call (2.0s)."""
    print("Fetching Traffic Data...")
    await asyncio.sleep(2.0) 
    return {"traffic_time": 45, "status": "Heavy"}

async def fetch_flight_api() -> Dict[str, Union[int, str]]:
    """Simulates a low-latency API call (1.2s)."""
    print("Fetching Flight Status...")
    await asyncio.sleep(1.2) 
    return {"gate": "B12", "status": "On Time"}

async def main():
    print("🚀 Starting FlightRisk Async Benchmark...")
    start_time = time.time()

    # Trigger all 3 requests at the exact same time.
    # The total time will be determined by the SLOWEST task (2.0s),
    # rather than the sum of all tasks (4.7s).
    weather, traffic, flight = await asyncio.gather(
        fetch_weather_api(),
        fetch_traffic_api(),
        fetch_flight_api()
    )

    total_time = time.time() - start_time
    
    print("\n--- BENCHMARK RESULTS ---")
    print(f"✅ Weather: {weather}")
    print(f"✅ Traffic: {traffic}")
    print(f"✅ Flight:  {flight}")
    print(f"⏱️  Total Execution Time: {total_time:.2f} seconds")
    print("-------------------------------")
    print("Note: Synchronous execution would have taken ~4.7 seconds.")
    print("Efficiency Gain: ~57%")

if __name__ == "__main__":
    asyncio.run(main())