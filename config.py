import os
from dotenv import load_dotenv

# Separates configuration from code logic.
# Load environment variables from the .env file for security.
load_dotenv()

# Keep API keys centralized for easier maintnence.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
RAPID_API_KEY = os.getenv("RAPID_API_KEY")

# Check that the keys exist before execution.
if not GOOGLE_API_KEY or not OPENWEATHER_API_KEY or not RAPID_API_KEY:
    print("Configuration Error: One or more API keys are missing in the .env file.")