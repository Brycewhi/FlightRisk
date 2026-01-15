import sys
from setuptools import setup, Extension
import pybind11

# COMPILER CONFIGURATION
# Flags optimized for macOS High Performance (clang++).
# Ensure we strictly use C++11 standard and libc++ for compatibility.
cpp_args = ['-std=c++11', '-stdlib=libc++', '-mmacosx-version-min=10.7']

ext_modules = [
    Extension(
        'flightrisk_cpp',
        ['cpp_core/simulation.cpp'],
        include_dirs=[pybind11.get_include()],
        language='c++',
        extra_compile_args=cpp_args,
    ),
]

setup(
    name='flightrisk_cpp',
    version='1.0',
    description='High-Performance Monte Carlo Engine for FlightRisk',
    ext_modules=ext_modules,
)