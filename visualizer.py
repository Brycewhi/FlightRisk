import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

class Visualizer:
    def __init__(self, theme="darkgrid"):
        sns.set_theme(style=theme)
    
    def plot_risk_profile(self, simulated_times, deadline, p95_time):
        plt.figure(figsize=(10,6))

        # Plot the distribution of simulated times as a smooth bell curve.
        # kde=True ensures curve is smooth.
        ax = sns.histplot(simulated_times, kde=True, color="skyblue", element="step")

        # Add the deadline line (Vertical Asymptote).
        plt.axvline(deadline, color='red', linestyle='--', label=f'Flight Deadline ({deadline}m)')

        # Add the P95 line (Vertical Asymptote).
        plt.axvline(p95_time, color='orange', linestyle=':', label=f'95% Confidence ({p95_time}m)')
        
        # Shade the failure zone after the deadline.
        kdeline = ax.lines[0]
        xs = kdeline.get_xdata()
        ys = kdeline.get_ydata()
        ax.fill_between(xs, ys, where=(xs > deadline), color='red', alpha=0.3)

        # Formatting.
        plt.title("Travel Time Probability Distribution (Monte Carlo)", fontsize=15)
        plt.xlabel("Minutes from Departure", fontsize=12)
        plt.ylabel("Frequency of Outcomes", fontsize=12)
        plt.legend()

        # Save visulization for GitHub.
        plt.savefig("risk_profile_v2.png", dpi=300)
        print("[*] Dashboard saved as risk_profile_v2.png")
        plt.show()

# Unit test block.
if __name__ == "__main__":
    viz = Visualizer()
    dummy_data = np.random.normal(75, 15, 1000) # Mean 75, StdDev 15
    viz.plot_risk_profile(dummy_data, deadline=90, p95_time=105)