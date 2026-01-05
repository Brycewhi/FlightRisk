import sqlite3
from datetime import datetime
from typing import Optional, List, Any

# The name of the file where data lives.
DB_NAME: str = "flight_risk.db"

def init_db() -> None:
    """
    Initializes the SQLite schema. Creates the 'trip_history' table if it doesn't exist.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Using AUTOINCREMENT for primary keys ensures unique record IDs.
        cursor.execute('''CREATE TABLE IF NOT EXISTS trip_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_timestamp TEXT,
                        flight_number TEXT,
                        origin TEXT,
                        destination TEXT,
                        weather_multiplier REAL,
                        suggested_departure TEXT,
                        success_probability REAL,
                        risk_status TEXT
                    )''')
        conn.commit()

def log_trip(
    flight_num: str, 
    origin: str, 
    dest: str, 
    multiplier: float, 
    suggested_time: Optional[int], 
    probability: float, 
    risk_status: str
) -> None:
    """
    Saves the results of a single stochastic simulation run to the history log.
    """
    # Transform Unix epoch to human-readable string for storage.
    if suggested_time is None:
        rec_time_str = "UNREACHABLE"
    else:
        rec_time_str = datetime.fromtimestamp(suggested_time).strftime('%Y-%m-%d %H:%M:%S')

    # Implementation: Secure parameterized insertion.
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        query = '''INSERT INTO trip_history 
                 (run_timestamp, flight_number, origin, destination, 
                  weather_multiplier, suggested_departure, success_probability, risk_status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        
        values = (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            flight_num.upper(), origin, dest, 
            multiplier, rec_time_str, probability, risk_status
        )
        
        cursor.execute(query, values)
        conn.commit()
    
    print(f"\n\033[92m[✓] Record committed to {DB_NAME}\033[0m")

def view_history(limit: int = 5) -> List[Any]:
    """
    Retrieves the most recent trip logs for dashboard rendering.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Sort by ID descending to get the most recent entries first.
        cursor.execute("SELECT * FROM trip_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
    
    return rows

# Local Unit Test Block.
if __name__ == "__main__":
    init_db()
    # Diagnostic Print.
    history = view_history()
    print("\nRECENT HISTORY PREVIEW")
    for entry in history:
        print(f"ID: {entry[0]} | Flight: {entry[2]} | Success: {entry[7]}%")