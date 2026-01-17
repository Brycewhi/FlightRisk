import sqlite3
import psycopg2 
import os
from datetime import datetime

# Railway provides this automatically. If it's missing, we are local.
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """
    Auto-switches between SQLite (Local) and PostgreSQL (Cloud).
    """
    if DATABASE_URL:
        # Cloud Mode (Postgres)
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # Local Mode (SQLite)
        return sqlite3.connect("flightrisk.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Postgres uses 'SERIAL' for auto-increment IDs
    # SQLite uses 'INTEGER PRIMARY KEY AUTOINCREMENT'
    if DATABASE_URL:
        id_type = "SERIAL PRIMARY KEY"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

    create_query = f'''
        CREATE TABLE IF NOT EXISTS trips (
            id {id_type},
            timestamp TEXT,
            flight_num TEXT,
            origin TEXT,
            destination TEXT,
            weather_mult REAL,
            suggested_time INTEGER,
            probability REAL,
            risk_status TEXT
        )
    '''
    
    cursor.execute(create_query)
    conn.commit()
    conn.close()

def log_trip(flight_num, origin, dest, multiplier, suggested_time, probability, risk_status):
    conn = get_connection()
    cursor = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Postgres uses %s for placeholders, SQLite uses ?
    # We standardize on %s and replace for SQLite if needed
    if DATABASE_URL:
        sql = "INSERT INTO trips (timestamp, flight_num, origin, destination, weather_mult, suggested_time, probability, risk_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (ts, flight_num, origin, dest, multiplier, suggested_time, probability, risk_status))
    else:
        sql = "INSERT INTO trips (timestamp, flight_num, origin, destination, weather_mult, suggested_time, probability, risk_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(sql, (ts, flight_num, origin, dest, multiplier, suggested_time, probability, risk_status))

    conn.commit()
    conn.close()

def view_history(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM trips ORDER BY id DESC LIMIT 20"
    cursor.execute(sql)
    rows = cursor.fetchall()
    
    conn.close()
    return rows