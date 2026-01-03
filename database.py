import sqlite3
from datetime import datetime

# The name of the file where data lives.
DB_NAME = "flight_risk.db"

def init_db():
    """
    Creates the 'trip_history' table if it doesn't exist yet.
    Think of this as setting up the columns in an Excel sheet.
    """
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    # Create a table with specific columns.
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
    
    connection.commit() # Save changes.
    connection.close()  # Close connection.

def log_trip(flight_num, origin, dest, multiplier, suggested_time, probability, risk_status):
    # Saves the results of a single simulation run.
    
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    # Handle the "UNREACHABLE" case (None).
    if suggested_time is None:
        rec_time_str = "UNREACHABLE"
    else:
        # Convert the timestamp into a string (ex: "1735923000 --> 2026-01-03 16:30:00").
        rec_time_str = datetime.fromtimestamp(suggested_time).strftime('%Y-%m-%d %H:%M:%S')

    # Insert a new row of data.
    cursor.execute('''INSERT INTO trip_history 
                 (run_timestamp, flight_number, origin, destination, 
                  weather_multiplier, suggested_departure, success_probability, risk_status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
               flight_num, origin, dest, 
               multiplier, rec_time_str, probability, risk_status))
    
    connection.commit()
    connection.close()
    print(f"\n\033[92m Trip saved to History Log (flight_risk.db).\033[0m")

def view_history():
    """
    A helper tool to print the last 5 trips to the screen.
    Useful for checking if it worked without opening a database viewer.
    """
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM trip_history ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    connection.close()
    
    print("\n--- RECENT TRIP HISTORY ---")
    if not rows:
        print("No history found.")
    for row in rows:
        # row[2] is Flight Number, row[6] is Suggested Time, row[7] is Probability.
        print(f"ID: {row[0]} | Flt: {row[2]} | Rec: {row[6]} | Prob: {row[7]}%")
    print("---------------------------\n")

# If you run 'python database.py', it creates the DB and shows history.
if __name__ == "__main__":
    init_db()
    view_history()