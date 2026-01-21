"""
Setup script for FlightRisk C++ Extension.

Compiles the high-performance Monte Carlo kernel (simulation.cpp) into a Python module
using pybind11. This enables 60x speedup over pure Python (50ms vs 3s for 100k iterations).

Usage:
    python setup.py build_ext --inplace
"""

import os
import sys
from setuptools import setup, Extension

try:
    import pybind11
except ImportError:
    print("ERROR: pybind11 is required. Install with: pip install pybind11")
    sys.exit(1)

# --- VALIDATE C++ SOURCE EXISTS ---
CPP_SOURCE = os.path.join(os.path.dirname(__file__), "cpp_core", "simulation.cpp")
if not os.path.exists(CPP_SOURCE):
    raise FileNotFoundError(
        f"C++ source file not found: {CPP_SOURCE}\n"
        f"Make sure cpp_core/simulation.cpp exists in the project root."
    )

# --- COMPILER FLAGS ---
extra_compile_args = ["-std=c++11", "-O3"]  # O3 = Maximum optimization
extra_link_args = []

# --- PLATFORM-SPECIFIC FLAGS ---
if sys.platform == "darwin":
    # macOS (Apple Silicon & Intel)
    extra_compile_args.extend(["-stdlib=libc++", "-mmacosx-version-min=10.9"])
    extra_link_args.extend(["-stdlib=libc++", "-mmacosx-version-min=10.9"])
    print("✓ macOS build configuration detected")
elif sys.platform.startswith("linux"):
    # Linux
    extra_compile_args.append("-fPIC")  # Position Independent Code for shared libraries
    print("✓ Linux build configuration detected")
elif sys.platform == "win32":
    # Windows
    print("✓ Windows build configuration detected")

# --- DEFINE THE C++ EXTENSION ---
ext_modules = [
    Extension(
        name="flightrisk_cpp",
        sources=[CPP_SOURCE],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

# --- SETUP CONFIGURATION ---
setup(
    name="flightrisk",
    version="4.5.0",
    description="High-Performance Monte Carlo Engine for Flight Reliability Prediction",
    long_description="FlightRisk predicts flight reliability using 100,000 Monte Carlo simulations. "
                     "Combines stochastic modeling, queue theory, and real-time APIs.",
    author="Bryce Whiteside",
    url="https://github.com/Brycewhi/FlightRisk",
    ext_modules=ext_modules,
    cmdclass={"build_ext": __import__("pybind11.setup_helpers", fromlist=["build_ext"]).build_ext},
    zip_safe=False,
)

print("\n✓ FlightRisk C++ extension compiled successfully!")
print("  To use: from flightrisk_cpp import calculate_risk, simulate_gamma")