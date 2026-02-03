"""Utility functions for the OpenSky client."""

import time
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_timestamp(timestamp: Optional[Union[int, float, str]]) -> Optional[datetime]:
    """Parse OpenSky timestamp to datetime object.
    
    Args:
        timestamp: Unix timestamp or string
        
    Returns:
        datetime object or None
    """
    if timestamp is None:
        return None
    
    try:
        if isinstance(timestamp, (int, float)):
            # Handle milliseconds or seconds
            if timestamp > 1e10:  # Likely milliseconds
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # Try various formats
            for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', 
                       '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse timestamp: {timestamp}")
    except Exception as e:
        logger.warning(f"Failed to parse timestamp {timestamp}: {e}")
        return None


def to_unix_timestamp(dt: Optional[datetime]) -> Optional[int]:
    """Convert datetime to Unix timestamp (seconds).
    
    Args:
        dt: datetime object
        
    Returns:
        Unix timestamp in seconds or None
    """
    if dt is None:
        return None
    return int(dt.timestamp())


def validate_icao24(icao24: str) -> bool:
    """Validate ICAO24 address format.
    
    Args:
        icao24: ICAO24 address
        
    Returns:
        True if valid, False otherwise
    """
    if not icao24 or not isinstance(icao24, str):
        return False
    icao24 = icao24.lower().strip()
    return len(icao24) == 6 and all(c in '0123456789abcdef' for c in icao24)


def validate_callsign(callsign: str) -> bool:
    """Validate callsign format.
    
    Args:
        callsign: Aircraft callsign
        
    Returns:
        True if valid format
    """
    if not callsign:
        return False
    # Callsign format validation
    return len(callsign) <= 8


def calculate_bounding_box(
    lat: float,
    lon: float,
    radius_km: float = 100
) -> tuple:
    """Calculate bounding box around a point.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        radius_km: Radius in kilometers
        
    Returns:
        Tuple of (lamin, lomin, lamax, lomax)
    """
    # Earth's radius in km
    earth_radius = 6371.0
    
    # Convert radius to degrees (approximate)
    lat_delta = (radius_km / earth_radius) * (180 / 3.141592653589793)
    lon_delta = lat_delta / abs(3.141592653589793 / 180 * lat)
    
    return (
        lat - lat_delta,
        lon - lon_delta,
        lat + lat_delta,
        lon + lon_delta
    )


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 10):
        """
        Args:
            calls_per_second: Maximum calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        
    def wait_if_needed(self) -> None:
        """Wait if needed to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()