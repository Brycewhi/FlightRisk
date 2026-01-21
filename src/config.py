import os
from dotenv import load_dotenv

# Calculate the path to the root directory to ensure file access works from any location.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from the .env file in the root directory.
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- API KEYS ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
RAPID_API_KEY = os.getenv("RAPID_API_KEY")

# --- DATABASE CONFIG ---
# Auto-detects if running on Railway (Postgres) or Local (SQLite).
DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.path.join(BASE_DIR, 'flight_data.db')

# --- SAFETY & SIMULATION FLAGS ---
# Centralized control for Cost vs. Realism.
# True = Use simulated data (Cost $0). False = Call real APIs (Cost $$).
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "True").lower() == "true"

# The "Nuclear Option": Must be explicitly set to True to spend real money.
USE_REAL_DATA_DANGEROUS = os.getenv("USE_REAL_DATA_DANGEROUS", "False").lower() == "true"

# --- VALIDATION ---
if not all([GOOGLE_API_KEY, OPENWEATHER_API_KEY, RAPID_API_KEY]):
    print("WARNING : One or more API keys are missing. App may fail in Real Mode.")