import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.figure import Figure
from typing import List, Union

class Visualizer:
    """
    Presentation Layer for Statistical Visualization.
    
    Responsible for rendering the Probability Density Function (PDF) of travel times
    and visually encoding risk thresholds using Matplotlib/Seaborn.
    """
    def __init__(self, theme: str = "darkgrid") -> None:
        sns.set_theme(style=theme)
        
    def plot_risk_profile(self, simulated_times: Union[List[float], np.ndarray], deadline: float, p95_time: float) -> Figure:
        """
        Generates a shaded Kernel Density Estimate (KDE) plot.

        Args:
            simulated_times: Array of Monte Carlo duration samples (in minutes).
            deadline: The critical time threshold (Gate Closure).
            p95_time: The 95th percentile result from the simulation.

        Returns:
            A Matplotlib Figure object optimized for Streamlit embedding.
        """
        # Create figure and axes using the Object-Oriented API.
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the Density Curve.
        # We use a white line to contrast against the dark UI background.
        sns.kdeplot(simulated_times, color="white", linewidth=2, ax=ax)
        
        # Extract geometry for shading logic. 
        line = ax.lines[0]
        x_data = line.get_xdata()
        y_data = line.get_ydata()
        
        # Shade the 'Safe Zone' (Area under the curve BEFORE deadline).
        ax.fill_between(x_data, y_data, where=(x_data <= deadline), color='#2ECC71', alpha=0.3, label='Safe Zone')
        
        # Shade the 'Risk Zone' (Area under curve AFTER deadline).
        # This visualizes the failure probability tail.
        ax.fill_between(x_data, y_data, where=(x_data > deadline), color='#E74C3C', alpha=0.5, label='Risk Zone')

        # Add Vertical Markers for critical thresholds.
        ax.axvline(deadline, color='#E74C3C', linestyle='--', linewidth=2, label='Gate Closes')
        ax.axvline(p95_time, color='#F39C12', linestyle=':', linewidth=2, label='95% Confidence')

        # Styling for Dark Mode.
        ax.set_title("Travel Time Probability Distribution", fontsize=14, color='white')
        ax.set_xlabel("Minutes", fontsize=12, color='white')
        ax.set_ylabel("Probability", fontsize=12, color='white')
        
        # Colorize ticks and borders (spines) to match dark theme.
        ax.tick_params(colors='white')
        for spine in ax.spines.values(): 
            spine.set_edgecolor('white')
        
        # Configure Legend styling.
        legend = ax.legend(facecolor='#262730', edgecolor='white')
        plt.setp(legend.get_texts(), color='white')
        
        # Transparent background to blend with Streamlit's background.
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        return fig
    
# Local Unit Test Block.
if __name__ == "__main__":
    print("Testing Visualizer...")
    
    # Generate Mock Stochastic Data.
    # We use a normal distribution to simulate 1,000 trips with a mean of 65 mins, std of 12 mins.
    test_data = np.random.normal(loc=65, scale=12, size=1000)
    
    # Define test thresholds. 
    test_deadline = 80
    test_p95 = 85
    
    # Render plot.
    viz = Visualizer()
    test_fig = viz.plot_risk_profile(test_data, test_deadline, test_p95)
    
    # Display Window (Requires a GUI environment, works on Mac/Windows).
    plt.show()
    print("✅ Local test complete.")
