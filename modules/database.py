import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import sys
from .gust_detector import GustDetector

logger = logging.getLogger(__name__)

DB_FILE = LOG_FILE = os.getenv("DB_FILE", "/home/rrocha/data/weather_data.db")

class WeatherDatabase:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.gust_detector = GustDetector(db_path)
    
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
    
    def get_last_reading(self) -> Optional[Dict[str, Any]]:
        """Get the most recent weather reading."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM weather_readings 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting last reading: {e}")
            return None

    def get_period_statistics(self, hours: int) -> Dict[str, Any]:
        """Get statistics (max, min, avg) for sensor data over the specified period."""
        try:
            with sqlite3.connect(self.db_path, timeout=60.0) as conn:  # Increased timeout to 60 seconds
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as record_count,
                        MIN(sensor_temperature) as temp_min,
                        MAX(sensor_temperature) as temp_max,
                        AVG(sensor_temperature) as temp_avg,
                        MIN(sensor_humidity) as humidity_min,
                        MAX(sensor_humidity) as humidity_max,
                        AVG(sensor_humidity) as humidity_avg,
                        MIN(sensor_pressure) as pressure_min,
                        MAX(sensor_pressure) as pressure_max,
                        AVG(sensor_pressure) as pressure_avg,
                        MIN(sensor_altitude) as altitude_min,
                        MAX(sensor_altitude) as altitude_max,
                        AVG(sensor_altitude) as altitude_avg,
                        MIN(sensor_wind_speed) as wind_speed_min,
                        MAX(sensor_wind_speed) as wind_speed_max,
                        AVG(sensor_wind_speed) as wind_speed_avg,
                        MIN(timestamp) as period_start,
                        MAX(timestamp) as period_end
                    FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                '''.format(hours))
                
                result = cursor.fetchone()
                
                # Get most frequent wind direction name
                cursor.execute('''
                    SELECT sensor_wind_direction_name, COUNT(*) as frequency
                    FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                    AND sensor_wind_direction_name IS NOT NULL
                    AND sensor_wind_direction_name != ''
                    GROUP BY sensor_wind_direction_name
                    ORDER BY frequency DESC
                    LIMIT 1
                '''.format(hours))
                
                wind_direction_result = cursor.fetchone()
                prevailing_wind = wind_direction_result[0] if wind_direction_result else None
                
                if result and result[0] > 0:  # Check if we have records
                    return {
                        'period_hours': hours,
                        'record_count': result[0],
                        'period_start': result[16],
                        'period_end': result[17],
                        'sensor_temperature': {
                            'min': round(result[1], 2) if result[1] is not None else None,
                            'max': round(result[2], 2) if result[2] is not None else None,
                            'avg': round(result[3], 2) if result[3] is not None else None
                        },
                        'sensor_humidity': {
                            'min': round(result[4], 2) if result[4] is not None else None,
                            'max': round(result[5], 2) if result[5] is not None else None,
                            'avg': round(result[6], 2) if result[6] is not None else None
                        },
                        'sensor_pressure': {
                            'min': round(result[7], 2) if result[7] is not None else None,
                            'max': round(result[8], 2) if result[8] is not None else None,
                            'avg': round(result[9], 2) if result[9] is not None else None
                        },
                        'sensor_altitude': {
                            'min': round(result[10], 2) if result[10] is not None else None,
                            'max': round(result[11], 2) if result[11] is not None else None,
                            'avg': round(result[12], 2) if result[12] is not None else None
                        },
                        'wind_speed': {
                            'min': round(result[13], 2) if result[13] is not None else None,
                            'max': round(result[14], 2) if result[14] is not None else None,
                            'avg': round(result[15], 2) if result[15] is not None else None
                        },
                        'prevailing_wind_direction': prevailing_wind
                    }
                else:
                    return {
                        'period_hours': hours,
                        'record_count': 0,
                        'message': f'No records found for the last {hours} hours'
                    }
                    
        except sqlite3.Error as e:
            logger.error(f"Error getting {hours}h statistics: {e}")
            return {'error': str(e)}

    def last1h(self) -> Dict[str, Any]:
        """Get statistics for the last 1 hour."""
        return self.get_period_statistics(1)

    def last15min(self) -> Dict[str, Any]:
        """Get statistics for the last 15 minutes."""
        return self.get_period_statistics(0.25)

    def last30min(self) -> Dict[str, Any]:
        """Get statistics for the last 30 minutes."""
        return self.get_period_statistics(0.5)

    def last2h(self) -> Dict[str, Any]:
        """Get statistics for the last 2 hours."""
        return self.get_period_statistics(2)

    def last6h(self) -> Dict[str, Any]:
        """Get statistics for the last 6 hours."""
        return self.get_period_statistics(6)

    def last12h(self) -> Dict[str, Any]:
        """Get statistics for the last 12 hours."""
        return self.get_period_statistics(12)

    def last24h(self) -> Dict[str, Any]:
        """Get statistics for the last 24 hours."""
        return self.get_period_statistics(24)

    def last48h(self) -> Dict[str, Any]:
        """Get statistics for the last 48 hours."""
        return self.get_period_statistics(48)

    def last(self) -> Optional[Dict[str, Any]]:
        """Alias for get_last_reading() - Get the most recent weather reading."""
        return self.get_last_reading()

    def get_gust_statistics(self, hours: float = 24.0) -> Dict[str, Any]:
        """Get wind gust statistics for the specified period."""
        return self.gust_detector.get_gust_statistics(hours)
    
    def detect_recent_gusts(self, hours: float = 1.0) -> List[Dict[str, Any]]:
        """Detect recent wind gusts."""
        return self.gust_detector.detect_recent_gusts(hours)
    
    def get_peak_gust(self, hours: float = 24.0) -> Optional[Dict[str, Any]]:
        """Get peak gust in the specified period."""
        return self.gust_detector.get_peak_gust(hours)
