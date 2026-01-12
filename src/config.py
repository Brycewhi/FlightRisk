import os
from dotenv import load_dotenv

# Calculate the path to the root directory to ensure file access works from any location.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from the .env file in the root directory.
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Keep API keys centralized for easier maintnence.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
RAPID_API_KEY = os.getenv("RAPID_API_KEY")

# Define the database path centrally so all modules use the same file.
DB_PATH = os.path.join(BASE_DIR, 'flight_data.db')

# Check that the keys exist before execution.
if not GOOGLE_API_KEY or not OPENWEATHER_API_KEY or not RAPID_API_KEY:
    print("Configuration Error: One or more API keys are missing in the .env file.")