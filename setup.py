from setuptools import setup, Extension
import sys
import pybind11

# Define compiler flags
extra_compile_args = ["-std=c++11"]
extra_link_args = []

# If we are on a Mac (Darwin), add the Apple-specific flags
if sys.platform == "darwin":
    extra_compile_args.extend(["-stdlib=libc++", "-mmacosx-version-min=10.7"])
    extra_link_args.extend(["-stdlib=libc++", "-mmacosx-version-min=10.7"])

# Define the Extension
ext_modules = [
    Extension(
        "flightrisk_cpp",
        ["cpp_core/simulation.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

setup(
    name="flightrisk_cpp",
    version="1.0",
    description="C++ Monte Carlo Engine for FlightRisk",
    ext_modules=ext_modules,
)