import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Fetch the key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validation: Stop the app if the key is missing
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found.")