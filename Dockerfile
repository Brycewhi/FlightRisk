# 1. Base Image: Python 3.10 on Linux (Slim version to save space)
FROM python:3.10-slim

# 2. Install System Tools (Compilers for C++ & Postgres libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    cmake \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set Working Directory
WORKDIR /app

# 4. Copy Dependencies First (Better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the App Code
COPY . .

# 6. Compile the C++ Core
RUN python setup.py build_ext --inplace && mv flightrisk_cpp*.so src/

# 7. Expose the Port
EXPOSE 8501

# 8. Run Command
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]