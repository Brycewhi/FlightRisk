import config
import requests

def test_api():
    print("Environment configured successfully.")
    print(f"API Key Loaded: {config.GOOGLE_API_KEY[:5]}...(Hidden for security)")
    # Dummy Request
    print("Pinging Google...")
    try:
        response = requests.get("https://www.google.com")
        print(f"Connection Status: {response.status_code}")
    except Exception as e:
        print(f"Connection failed: {e}")
if __name__ == "__main__":
        test_api()