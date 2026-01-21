"""
Configuration Module for FlightRisk.

Handles environment variables, API key management, and application flags.
Supports local development (SQLite) and cloud deployment (PostgreSQL).
"""

import os
import logging
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

# Calculate the path to the root directory to ensure file access works from any location.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from the .env file in the root directory.
dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    logger.warning(f".env file not found at {dotenv_path}. Using system environment variables.")

# --- API KEYS ---
GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
RAPID_API_KEY: Optional[str] = os.getenv("RAPID_API_KEY")

# --- DATABASE CONFIG ---
# Auto-detects if running on Railway (PostgreSQL) or Local (SQLite).
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
DB_PATH: str = os.path.join(BASE_DIR, 'flight_data.db')

# --- SAFETY & SIMULATION FLAGS ---
# True = Use simulated data (Cost $0). False = Call real APIs (Cost $$).
USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

# The "Nuclear Option": Must be explicitly set to True to spend real money on APIs.
USE_REAL_DATA_DANGEROUS: bool = os.getenv("USE_REAL_DATA_DANGEROUS", "false").lower() in ("true", "1", "yes")

# --- LOGGING LEVEL ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- VALIDATION ---
def validate_config() -> None:
    """
    Validates critical configuration at startup.
    Raises ValueError if required keys are missing and USE_MOCK_DATA is False.
    """
    if not USE_MOCK_DATA and not USE_REAL_DATA_DANGEROUS:
        logger.warning("Mock data is enabled. Set USE_MOCK_DATA=false to use real APIs.")
        return

    missing_keys = []
    if not GOOGLE_API_KEY:
        missing_keys.append("GOOGLE_API_KEY")
    if not OPENWEATHER_API_KEY:
        missing_keys.append("OPENWEATHER_API_KEY")
    if not RAPID_API_KEY:
        missing_keys.append("RAPID_API_KEY")

    if missing_keys:
        if USE_REAL_DATA_DANGEROUS:
            raise ValueError(
                f"CRITICAL: Real API mode enabled, but missing keys: {', '.join(missing_keys)}. "
                f"Set these in .env or as environment variables."
            )
        else:
            logger.warning(f"Missing API keys: {', '.join(missing_keys)}. Running in mock mode.")

# Call validation on import
validate_config()

logger.info(f"FlightRisk Config Loaded | Mock Mode: {USE_MOCK_DATA} | DB: {'PostgreSQL' if DATABASE_URL else 'SQLite'}")