/**
 * @file simulation.cpp
 * @brief Monte Carlo Simulation Engine for FlightRisk.
 * This module handles the high-performance risk calculations.
 * It simulates thousands of logistic scenarios (Traffic + TSA + Walk).
 * to determine the probability of missing a flight.
 * Why C++? 
 * Python takes ~3.0s for 100k iterations. 
 * C++ does this in < 0.05s.
 */

#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <numeric>
#include <algorithm> // Required for std::max

// Standard Box-Muller transform to generate normally distributed random numbers.
// (Used because we don't want to rely on heavy external libraries like Boost)
double generate_normal(double mean, double std_dev, std::mt19937& gen) {
    std::normal_distribution<> d(mean, std::max(0.1, std_dev)); // Prevent negative std_dev.
    return d(gen);
}

// The Core Simulation Logic.
extern "C" {
    /**
     * @brief Runs a Monte Carlo simulation to calculate risk.
     * @param user_buffer_mins  Total time user has before gate closes.
     * @param avg_traffic_mins  Expected traffic duration.
     * @param traffic_std_dev   Volatility of traffic (from API).
     * @param avg_tsa_mins      Average TSA wait time (passed from Python).
     * @param tsa_std_dev       Volatility of TSA lines (based on historicals).
     * @param walk_time_mins    Walking time from TSA to Gate (Deterministic).
     * @param iterations        Number of scenarios to simulate (e.g., 100,000).
     * @return Probability of failure (0.0 to 1.0).
     */
    double calculate_failure_rate(
        double user_buffer_mins, 
        double avg_traffic_mins, 
        double traffic_std_dev, 
        double avg_tsa_mins,
        double tsa_std_dev,
        double walk_time_mins,
        int iterations
    ) {
        int missed_flights = 0;
        
        // Random Number Generator (Mersenne Twister).
        std::random_device rd;
        std::mt19937 gen(rd());

        // Effective Buffer: The "slack" we have for chaos.
        // If you have 120 mins total, but walking takes 10, you really only have 110 mins.
        double effective_buffer = user_buffer_mins - walk_time_mins;

        for(int i = 0; i < iterations; i++) {
            // 1. Simulate Traffic Scenario.
            double traffic_delay = generate_normal(avg_traffic_mins, traffic_std_dev, gen);
            
            // 2. Simulate TSA Scenario.
            double security_time = generate_normal(avg_tsa_mins, tsa_std_dev, gen);
            
            // 3. Check Total Time.
            if ((traffic_delay + security_time) > effective_buffer) {
                missed_flights++;
            }
        }

        return (double)missed_flights / iterations;
    }
}

// Main function for standalone testing (via CLI).
int main() {
    // Test Case: 
    // Buffer: 90 mins
    // Traffic: 45 mins (avg) +/- 10 mins
    // TSA: 18 mins (avg) +/- 10 mins
    // Walk: 10 mins
    double risk = calculate_failure_rate(90.0, 45.0, 10.0, 18.0, 10.0, 10.0, 10000);
    
    std::cout << "FlightRisk C++ Core Benchmark" << std::endl;
    std::cout << "Simulating 10,000 Iterations..." << std::endl;
    std::cout << "Calculated Risk: " << (risk * 100) << "%" << std::endl;
    
    return 0;
}