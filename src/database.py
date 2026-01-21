import sqlite3
import psycopg2 
from datetime import datetime
from typing import Any, List, Union, Tuple, Optional
import config 

DbConnection = Union[sqlite3.Connection, Any] 

def get_connection() -> DbConnection:
    if config.DATABASE_URL:
        return psycopg2.connect(config.DATABASE_URL, sslmode='require')
    else:
        return sqlite3.connect(config.DB_PATH, check_same_thread=False)

def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    
    id_type = "SERIAL PRIMARY KEY" if config.DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"

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
            risk_status TEXT,
            user_feedback INTEGER DEFAULT NULL
        )
    '''
    # Note: Changed user_feedback to INTEGER (1=Good, 0=Bad) for easier ML processing later
    
    cursor.execute(create_query)
    conn.commit()
    conn.close()

def log_trip(
    flight_num: str, 
    origin: str, 
    dest: str, 
    multiplier: float, 
    suggested_time: int, 
    probability: float, 
    risk_status: str
) -> int:
    """
    Persists simulation results and RETURNS the Row ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    query = """
        INSERT INTO trips 
        (timestamp, flight_num, origin, destination, weather_mult, suggested_time, probability, risk_status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (ts, flight_num, origin, dest, multiplier, suggested_time, probability, risk_status)

    row_id = None

    if config.DATABASE_URL:
        # PostgreSQL: Use RETURNING clause
        query += " RETURNING id"
        cursor.execute(query, params)
        row_id = cursor.fetchone()[0]
    else:
        # SQLite: Use cursor.lastrowid
        query = query.replace("%s", "?")
        cursor.execute(query, params)
        row_id = cursor.lastrowid

    conn.commit()
    conn.close()
    
    return row_id if row_id is not None else -1

def log_feedback(run_id: int, feedback_score: int) -> None:
    """
    Updates a specific run ID with feedback.
    1 = Thumbs Up (Accurate)
    0 = Thumbs Down (Inaccurate)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "UPDATE trips SET user_feedback = %s WHERE id = %s"
    
    if not config.DATABASE_URL:
        query = query.replace("%s", "?")
        
    cursor.execute(query, (feedback_score, run_id))
    conn.commit()
    conn.close()

def view_history(limit: int = 20) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM trips ORDER BY id DESC LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    return rows