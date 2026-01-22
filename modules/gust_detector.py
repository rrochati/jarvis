import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

logger = logging.getLogger(__name__)

DB_FILE = os.getenv("DB_FILE", "/home/rrocha/data/weather_data.db")

class GustDetector:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.gust_threshold_knots = 5.0  # Minimum difference for gust detection (knots)
        self.sustained_wind_period_minutes = 10  # Period for sustained wind calculation
        
    def calculate_sustained_wind(self, hours: float = 1.0) -> Optional[float]:
        """Calculate sustained wind speed (10-minute average) over the specified period."""
        try:
            logger.info(f"Calculating sustained wind for {hours} hours")
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT AVG(sensor_wind_speed) as sustained_wind
                    FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                    AND sensor_wind_speed IS NOT NULL
                '''.format(hours))
                
                result = cursor.fetchone()
                sustained_wind = result[0] if result and result[0] is not None else None
                logger.info(f"Sustained wind calculated: {sustained_wind} knots")
                return sustained_wind
                
        except sqlite3.Error as e:
            logger.error(f"Error calculating sustained wind: {e}")
            return None
    
    def detect_recent_gusts(self, hours: float = 1.0) -> List[Dict[str, Any]]:
        """Detect wind gusts in recent readings using statistical analysis."""
        try:
            logger.info(f"Starting gust detection for {hours} hours")
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # Get wind speed readings for the specified period
                cursor.execute('''
                    SELECT timestamp, sensor_wind_speed
                    FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                    AND sensor_wind_speed IS NOT NULL
                    ORDER BY timestamp ASC
                '''.format(hours))
                
                readings = cursor.fetchall()
                logger.info(f"Found {len(readings)} wind readings for gust analysis")
                
                if len(readings) < 3:  # Need at least 3 readings for analysis
                    logger.warning(f"Insufficient readings for gust detection: {len(readings)}")
                    return []
                
                gusts = []
                sustained_wind = self.calculate_sustained_wind(hours)
                
                if sustained_wind is None:
                    logger.warning("Could not calculate sustained wind, skipping gust detection")
                    return []
                
                logger.info(f"Using sustained wind of {sustained_wind:.1f} knots for gust detection")
                
                # Analyze each reading for potential gusts
                for i, (timestamp, wind_speed) in enumerate(readings):
                    # Calculate local average (3-reading window for smoothing)
                    start_idx = max(0, i - 1)
                    end_idx = min(len(readings), i + 2)
                    local_readings = readings[start_idx:end_idx]
                    local_avg = sum(r[1] for r in local_readings) / len(local_readings)
                    
                    # Check if this reading qualifies as a gust
                    if self._is_gust(wind_speed, sustained_wind, local_avg):
                        gust = {
                            'timestamp': timestamp,
                            'gust_speed_knots': round(wind_speed, 1),
                            'gust_speed_kmh': round(wind_speed * 1.852, 1),
                            'sustained_wind_knots': round(sustained_wind, 1),
                            'sustained_wind_kmh': round(sustained_wind * 1.852, 1),
                            'gust_factor': round(wind_speed / sustained_wind, 2) if sustained_wind > 0 else None
                        }
                        gusts.append(gust)
                        logger.debug(f"Gust detected: {wind_speed:.1f} kn at {timestamp}")
                
                logger.info(f"Detected {len(gusts)} gusts in {hours} hours")
                return gusts
                
        except sqlite3.Error as e:
            logger.error(f"Error detecting gusts: {e}")
            return []
    
    def _is_gust(self, wind_speed: float, sustained_wind: float, local_avg: float) -> bool:
        """Determine if a wind speed reading qualifies as a gust."""
        # Gust criteria:
        # 1. Must exceed sustained wind by threshold
        # 2. Must be significantly higher than local average
        # 3. Sustained wind must be meaningful (> 2 knots)
        
        if sustained_wind < 2.0:  # Very light winds, gusts not meaningful
            logger.debug(f"Sustained wind too low for gust detection: {sustained_wind:.1f} kn")
            return False
            
        exceeds_sustained = wind_speed > (sustained_wind + self.gust_threshold_knots)
        exceeds_local = wind_speed > (local_avg + 2.0)  # Local spike
        
        is_gust = exceeds_sustained and exceeds_local
        
        if is_gust:
            logger.debug(f"Gust criteria met: speed={wind_speed:.1f}, sustained={sustained_wind:.1f}, local_avg={local_avg:.1f}")
        
        return is_gust
    
    def get_peak_gust(self, hours: float = 24.0) -> Optional[Dict[str, Any]]:
        """Get the peak gust in the specified time period."""
        try:
            logger.info(f"Getting peak gust for {hours} hours")
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, MAX(sensor_wind_speed) as peak_gust
                    FROM weather_readings 
                    WHERE datetime(timestamp) >= datetime('now', '-{} hours')
                    AND sensor_wind_speed IS NOT NULL
                '''.format(hours))
                
                result = cursor.fetchone()
                
                if result and result[1] is not None:
                    sustained_wind = self.calculate_sustained_wind(hours)
                    peak_gust = result[1]
                    
                    peak_data = {
                        'timestamp': result[0],
                        'peak_gust_knots': round(peak_gust, 1),
                        'peak_gust_kmh': round(peak_gust * 1.852, 1),
                        'sustained_wind_knots': round(sustained_wind, 1) if sustained_wind else None,
                        'sustained_wind_kmh': round(sustained_wind * 1.852, 1) if sustained_wind else None,
                        'gust_factor': round(peak_gust / sustained_wind, 2) if sustained_wind and sustained_wind > 0 else None
                    }
                    
                    logger.info(f"Peak gust found: {peak_gust:.1f} kn at {result[0]}")
                    return peak_data
                
                logger.info("No peak gust data found")
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting peak gust: {e}")
            return None
    
    def get_gust_statistics(self, hours: float = 24.0) -> Dict[str, Any]:
        """Get comprehensive gust statistics for the specified period."""
        logger.info(f"Getting comprehensive gust statistics for {hours} hours")
        
        gusts = self.detect_recent_gusts(hours)
        peak_gust = self.get_peak_gust(hours)
        sustained_wind = self.calculate_sustained_wind(hours)
        
        if not gusts:
            logger.info(f"No gusts found in {hours} hours")
            return {
                'period_hours': hours,
                'gust_count': 0,
                'peak_gust': peak_gust,
                'sustained_wind_knots': round(sustained_wind, 1) if sustained_wind else None,
                'sustained_wind_kmh': round(sustained_wind * 1.852, 1) if sustained_wind else None,
                'message': f'No significant gusts detected in the last {hours} hours'
            }
        
        # Calculate gust statistics
        gust_speeds = [g['gust_speed_knots'] for g in gusts]
        gust_factors = [g['gust_factor'] for g in gusts if g['gust_factor']]
        
        stats = {
            'period_hours': hours,
            'gust_count': len(gusts),
            'recent_gusts': gusts[-5:] if len(gusts) > 5 else gusts,  # Last 5 gusts
            'peak_gust': peak_gust,
            'average_gust_speed_knots': round(sum(gust_speeds) / len(gust_speeds), 1),
            'average_gust_speed_kmh': round((sum(gust_speeds) / len(gust_speeds)) * 1.852, 1),
            'average_gust_factor': round(sum(gust_factors) / len(gust_factors), 2) if gust_factors else None,
            'sustained_wind_knots': round(sustained_wind, 1) if sustained_wind else None,
            'sustained_wind_kmh': round(sustained_wind * 1.852, 1) if sustained_wind else None
        }
        
        logger.info(f"Gust statistics calculated: {len(gusts)} gusts, avg speed {stats['average_gust_speed_knots']} kn")
        return stats
    
    def set_gust_threshold(self, threshold_knots: float):
        """Set the minimum wind speed difference for gust detection."""
        self.gust_threshold_knots = threshold_knots
        logger.info(f"Gust detection threshold set to {threshold_knots} knots")