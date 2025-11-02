import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import sys

logger = logging.getLogger(__name__)

DB_FILE = LOG_FILE = os.getenv("DB_FILE", "/home/rrocha/data/weather_data.db")

class WeatherDatabase:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
    
    def get_recent_readings(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent weather readings from the last N hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                '''.format(hours))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting recent readings: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count records in each table
                cursor.execute('SELECT COUNT(*) FROM weather_readings')
                weather_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM weather_api_data')
                api_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM air_quality')
                air_quality_count = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM weather_readings')
                date_range = cursor.fetchone()
                
                return {
                    'weather_readings': weather_count,
                    'api_data_records': api_count,
                    'air_quality_records': air_quality_count,
                    'earliest_reading': date_range[0],
                    'latest_reading': date_range[1],
                    'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
                }
        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
