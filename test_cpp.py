import flightrisk_cpp
import time

print("\n🚀 FLIGHTRISK C++ BENCHMARK 🚀")
print("-----------------------------------")

start = time.time()

# Running 1 MILLION simulations
risk = flightrisk_cpp.calculate_risk(120.0, 60.0, 15.0, 2.0, 10.0, 10.0, 100000)

end = time.time()

print(f"✅ Risk Score: {risk * 100:.2f}%")
print(f"Time for 100k sims: {end - start:.5f} seconds")
print("-----------------------------------")