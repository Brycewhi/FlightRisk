/**
 * @file simulation.cpp
 * @brief High-Performance Monte Carlo Engine for FlightRisk.
 * * This module replaces the Python-based simulation loops with compiled C++.
 * It handles the stochastic generation of Traffic and TSA delays using
 * Normal and Gamma distributions, respectively.
 * * Performance:
 * Python (SciPy): ~3.0s for 100k iterations.
 * C++ (PyBind11): ~0.05s for 100k iterations.
 */

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <random>
#include <cmath>
#include <algorithm>
#include <vector>

namespace py = pybind11;

// ------------------------------------------------------------------
// CORE SIMULATION LOGIC
// ------------------------------------------------------------------

/**
 * @brief Generates an array of random Gamma-distributed variables.
 * Used by the AirportEngine to simulate TSA lines with high variance.
 * * @param shape Shape parameter (k) of the Gamma distribution.
 * @param scale Scale parameter (theta) of the Gamma distribution.
 * @param iterations Total number of samples to generate.
 * @return NumPy array of simulated wait times.
 */
py::array_t<double> simulate_gamma(double shape, double scale, int iterations) {
    auto result = py::array_t<double>(iterations);
    py::buffer_info buf = result.request();
    double *ptr = static_cast<double *>(buf.ptr);

    // Initialize High-performance Mersenne Twister Engine.
    std::random_device rd;
    std::mt19937 gen(rd());
    std::gamma_distribution<> d(shape, scale);

    // Fast generation loop (No Python overhead).
    for (int i = 0; i < iterations; i++) {
        ptr[i] = d(gen);
    }

    return result;
}

/**
 * @brief Calculates the probability of missing a flight.
 * Simulates the full "Traffic + TSA + Walk" journey 100,000+ times.
 * * @param buffer_mins Total time user has before gate closes.
 * @param traffic_avg Mean traffic duration (Normal Dist).
 * @param traffic_std Volatility of traffic (Normal Dist).
 * @param tsa_shape Gamma Shape parameter for TSA lines.
 * @param tsa_scale Gamma Scale parameter for TSA lines.
 * @param walk_time Deterministic walking time from security to gate.
 * @param iterations Number of scenarios to simulate.
 * @return Probability of failure (0.0 to 1.0).
 */
double calculate_risk(
    double buffer_mins,
    double traffic_avg,
    double traffic_std,
    double tsa_shape,
    double tsa_scale,
    double walk_time,
    int iterations
) {
    int missed_flights = 0;
    double effective_buffer = buffer_mins - walk_time;

    std::random_device rd;
    std::mt19937 gen(rd());

    // Distributions:
    // Traffic ~ Normal (Approximation of weather volatility)
    // TSA ~ Gamma (Queue Theory standard for service lines)
    std::normal_distribution<> traffic_dist(traffic_avg, std::max(0.1, traffic_std));
    std::gamma_distribution<> tsa_dist(tsa_shape, tsa_scale);

    for (int i = 0; i < iterations; i++) {
        double t_traffic = traffic_dist(gen);
        double t_tsa = tsa_dist(gen);

        if ((t_traffic + t_tsa) > effective_buffer) {
            missed_flights++;
        }
    }

    return static_cast<double>(missed_flights) / iterations;
}

// ------------------------------------------------------------------
// PYTHON BINDINGS
// ------------------------------------------------------------------
PYBIND11_MODULE(flightrisk_cpp, m) {
    m.doc() = "FlightRisk C++ Accelerated Core";

    m.def("simulate_gamma", &simulate_gamma, 
          "Generate Gamma distribution array for AirportEngine",
          py::arg("shape"), py::arg("scale"), py::arg("iterations"));

    m.def("calculate_risk", &calculate_risk, 
          "Run full Monte Carlo simulation to return failure probability",
          py::arg("buffer_mins"), 
          py::arg("traffic_avg"), py::arg("traffic_std"),
          py::arg("tsa_shape"), py::arg("tsa_scale"),
          py::arg("walk_time"), 
          py::arg("iterations") = 100000);
}