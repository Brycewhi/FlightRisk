import asyncio
import time
import random

# Mock API functions (Simulating network calls).
async def fetch_weather_api():
    print("Fetching Weather Data...")
    await asyncio.sleep(1.5) # Simulates network latency.
    return {"temp": 72, "condition": "Clear"}

async def fetch_traffic_api():
    print("Fetching Traffic Data...")
    await asyncio.sleep(2.0) # Simulates a slow API.
    return {"traffic_time": 45, "status": "Heavy"}

async def fetch_flight_api():
    print("Fetching Flight Status...")
    await asyncio.sleep(1.2) # Simulates a fast API.
    return {"gate": "B12", "status": "On Time"}

async def main():
    print("Starting FlightRisk Async Benchmark")
    start_time = time.time()

    # Trigger all 3 requests at the exact same time.
    # This waits for the SLOWEST one (2.0s), not the sum of them (4.7s).
    weather, traffic, flight = await asyncio.gather(
        fetch_weather_api(),
        fetch_traffic_api(),
        fetch_flight_api()
    )

    total_time = time.time() - start_time
    
    print("\nResults")
    print(f"Weather: {weather}")
    print(f"Traffic: {traffic}")
    print(f"Flight:  {flight}")
    print(f"Total Time: {total_time:.2f} seconds")
    print("-------------------------------")
    print("Note: Synchronous execution would have taken ~4.7 seconds.")

if __name__ == "__main__":
    asyncio.run(main())