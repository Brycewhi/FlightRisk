"""
Database Module for FlightRisk.

Handles both local SQLite (development) and cloud PostgreSQL (production).
Persists trip history and user feedback for model calibration.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Any, List, Tuple, Optional, Union

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

import config

logger = logging.getLogger(__name__)

DbConnection = Union[sqlite3.Connection, Any]

# --- CONNECTION MANAGEMENT ---

def get_connection() -> DbConnection:
    """
    Returns appropriate database connection based on environment.
    
    Production (Cloud): PostgreSQL via Railway
    Development (Local): SQLite file-based
    
    Returns:
        Database connection object
        
    Raises:
        RuntimeError: If PostgreSQL is required but psycopg2 not installed
    """
    if config.DATABASE_URL:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "PostgreSQL connection requested but psycopg2 not installed. "
                "Install with: pip install psycopg2-binary"
            )
        try:
            conn = psycopg2.connect(
                config.DATABASE_URL,
                sslmode='require',
                connect_timeout=5,  # Fail fast on connection issues
                keepalives=1,
                keepalives_idle=30
            )
            logger.debug("Connected to PostgreSQL")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise
    else:
        try:
            conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=5.0)
            logger.debug(f"Connected to SQLite: {config.DB_PATH}")
            return conn
        except sqlite3.OperationalError as e:
            logger.error(f"SQLite connection failed: {e}")
            raise

# --- SCHEMA INITIALIZATION ---

def init_db() -> None:
    """
    Creates the trips table if it doesn't exist.
    Works with both SQLite and PostgreSQL.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Use SERIAL for PostgreSQL, AUTOINCREMENT for SQLite
    if config.DATABASE_URL:
        id_type = "SERIAL PRIMARY KEY"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

    create_query = f'''
        CREATE TABLE IF NOT EXISTS trips (
            id {id_type},
            timestamp TEXT NOT NULL,
            flight_num TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            weather_mult REAL NOT NULL,
            suggested_time INTEGER NOT NULL,
            probability REAL NOT NULL,
            risk_status TEXT NOT NULL,
            user_feedback INTEGER,
            CONSTRAINT feedback_valid CHECK (user_feedback IS NULL OR user_feedback IN (0, 1))
        )
    '''
    
    try:
        cursor.execute(create_query)
        conn.commit()
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

# --- TRIP LOGGING ---

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
    Persists a simulation result to the database.
    
    Args:
        flight_num: Flight identifier (e.g., 'DL482')
        origin: Starting address
        dest: Destination airport
        multiplier: Weather impact multiplier
        suggested_time: Unix timestamp of recommended departure
        probability: Success probability (0-100)
        risk_status: Risk label ('VERY LOW', 'LOW', 'MODERATE', 'CRITICAL')
        
    Returns:
        Row ID of inserted record, or -1 if insertion failed
    """
    conn = get_connection()
    cursor = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if config.DATABASE_URL:
            # PostgreSQL: Use RETURNING clause
            query = """
                INSERT INTO trips 
                (timestamp, flight_num, origin, destination, weather_mult, suggested_time, probability, risk_status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (ts, flight_num, origin, dest, multiplier, suggested_time, probability, risk_status))
            row_id = cursor.fetchone()[0]
        else:
            # SQLite: Use lastrowid
            query = """
                INSERT INTO trips 
                (timestamp, flight_num, origin, destination, weather_mult, suggested_time, probability, risk_status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (ts, flight_num, origin, dest, multiplier, suggested_time, probability, risk_status))
            row_id = cursor.lastrowid

        conn.commit()
        logger.info(f"Trip logged: {flight_num} (ID: {row_id})")
        return row_id if row_id else -1
        
    except Exception as e:
        logger.error(f"Failed to log trip: {e}")
        return -1
    finally:
        conn.close()

# --- FEEDBACK LOGGING ---

def log_feedback(run_id: int, feedback_score: int) -> bool:
    """
    Updates a simulation record with user feedback.
    
    Args:
        run_id: ID of the trip record to update
        feedback_score: 1 for accurate, 0 for inaccurate
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ValueError: If feedback_score is not 0 or 1
    """
    if feedback_score not in (0, 1):
        raise ValueError("feedback_score must be 0 (inaccurate) or 1 (accurate)")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if config.DATABASE_URL:
            query = "UPDATE trips SET user_feedback = %s WHERE id = %s"
            cursor.execute(query, (feedback_score, run_id))
        else:
            query = "UPDATE trips SET user_feedback = ? WHERE id = ?"
            cursor.execute(query, (feedback_score, run_id))
        
        conn.commit()
        logger.info(f"Feedback logged for run {run_id}: {'Accurate' if feedback_score == 1 else 'Inaccurate'}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")
        return False
    finally:
        conn.close()

# --- HISTORY RETRIEVAL ---

def view_history(limit: int = 20) -> List[Tuple[Any, ...]]:
    """
    Retrieves the most recent trips from the database.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of tuples containing trip data
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if limit > 1000:
        logger.warning(f"Limiting to 1000 records (requested {limit})")
        limit = 1000
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = f"SELECT * FROM trips ORDER BY id DESC LIMIT {limit}"
        cursor.execute(query)
        rows = cursor.fetchall()
        logger.debug(f"Retrieved {len(rows)} trip records")
        return rows
        
    except Exception as e:
        logger.error(f"Failed to retrieve history: {e}")
        return []
    finally:
        conn.close()

# --- UTILITY FUNCTIONS ---

def get_feedback_stats() -> dict:
    """
    Returns aggregate feedback statistics for model calibration.
    
    Returns:
        Dict with counts of accurate/inaccurate predictions
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if config.DATABASE_URL:
            query = """
                SELECT 
                    SUM(CASE WHEN user_feedback = 1 THEN 1 ELSE 0 END) as accurate,
                    SUM(CASE WHEN user_feedback = 0 THEN 1 ELSE 0 END) as inaccurate,
                    COUNT(*) as total
                FROM trips WHERE user_feedback IS NOT NULL
            """
        else:
            query = """
                SELECT 
                    SUM(CASE WHEN user_feedback = 1 THEN 1 ELSE 0 END) as accurate,
                    SUM(CASE WHEN user_feedback = 0 THEN 1 ELSE 0 END) as inaccurate,
                    COUNT(*) as total
                FROM trips WHERE user_feedback IS NOT NULL
            """
        
        cursor.execute(query)
        result = cursor.fetchone()
        
        return {
            "accurate": result[0] or 0,
            "inaccurate": result[1] or 0,
            "total": result[2] or 0,
            "accuracy": (result[0] or 0) / (result[2] or 1) if result[2] else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve feedback stats: {e}")
        return {"accurate": 0, "inaccurate": 0, "total": 0, "accuracy": 0.0}
    finally:
        conn.close()