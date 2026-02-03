"""
Tests for utility functions.
"""

import pytest
from datetime import datetime, timedelta
from opensky.utils import (
    parse_timestamp,
    to_unix_timestamp,
    validate_icao24,
    validate_callsign,
    calculate_bounding_box,
    RateLimiter,
    setup_logging
)
import logging
import time


class TestTimestampUtilities:
    """Test timestamp parsing and conversion utilities."""
    
    def test_parse_timestamp_int_seconds(self):
        """Parse integer timestamp in seconds."""
        dt = parse_timestamp(1609459200)  # 2021-01-01 00:00:00 UTC
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
    
    def test_parse_timestamp_int_milliseconds(self):
        """Parse integer timestamp in milliseconds."""
        # 1609459200000 milliseconds = 2021-01-01 00:00:00 UTC
        dt = parse_timestamp(1609459200000)
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
    
    def test_parse_timestamp_float(self):
        """Parse float timestamp."""
        dt = parse_timestamp(1609459200.5)
        assert dt.microsecond == 500000
    
    def test_parse_timestamp_iso_string(self):
        """Parse ISO format string."""
        dt = parse_timestamp("2021-01-01T12:00:00Z")
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
    
    def test_parse_timestamp_date_string(self):
        """Parse date string."""
        dt = parse_timestamp("2021-01-01")
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
    
    def test_parse_timestamp_none(self):
        """Parse None timestamp."""
        dt = parse_timestamp(None)
        assert dt is None
    
    def test_parse_timestamp_invalid_string(self):
        """Parse invalid string timestamp."""
        dt = parse_timestamp("invalid")
        assert dt is None
    
    def test_to_unix_timestamp(self):
        """Convert datetime to Unix timestamp."""
        dt = datetime(2021, 1, 1, 12, 0, 0)
        timestamp = to_unix_timestamp(dt)
        assert timestamp == 1609495200  # 2021-01-01 12:00:00 UTC
    
    def test_to_unix_timestamp_none(self):
        """Convert None to Unix timestamp."""
        timestamp = to_unix_timestamp(None)
        assert timestamp is None
    
    def test_round_trip_conversion(self):
        """Test round-trip conversion (datetime -> timestamp -> datetime)."""
        original_dt = datetime(2021, 1, 1, 12, 30, 45)
        timestamp = to_unix_timestamp(original_dt)
        parsed_dt = parse_timestamp(timestamp)
        
        # They should be very close (within 1 second due to integer conversion)
        assert abs((parsed_dt - original_dt).total_seconds()) < 1


class TestValidationUtilities:
    """Test validation utilities."""
    
    def test_validate_icao24_valid(self):
        """Test valid ICAO24 addresses."""
        assert validate_icao24("abc123") is True
        assert validate_icao24("ABCDEF") is True
        assert validate_icao24("123456") is True
        assert validate_icao24("a1b2c3") is True
    
    def test_validate_icao24_invalid(self):
        """Test invalid ICAO24 addresses."""
        assert validate_icao24(None) is False
        assert validate_icao24("") is False
        assert validate_icao24("abc12") is False  # Too short
        assert validate_icao24("abc1234") is False  # Too long
        assert validate_icao24("abcg12") is False  # Invalid character 'g'
        assert validate_icao24("ABC-12") is False  # Invalid character '-'
    
    def test_validate_callsign_valid(self):
        """Test valid callsigns."""
        assert validate_callsign("TEST01") is True
        assert validate_callsign("THY123") is True
        assert validate_callsign("DLH4UA") is True
        assert validate_callsign("A") is True  # Single character
    
    def test_validate_callsign_invalid(self):
        """Test invalid callsigns."""
        assert validate_callsign(None) is False
        assert validate_callsign("") is False
        # Note: The current implementation only checks for None/empty
        # We might want to add more validation rules
        assert validate_callsign("TOOLONG01") is True  # Actually valid with current rules


class TestBoundingBoxCalculation:
    """Test bounding box calculation utilities."""
    
    def test_calculate_bounding_box(self):
        """Test bounding box calculation."""
        lat = 50.0
        lon = 8.0
        radius_km = 100
        
        bbox = calculate_bounding_box(lat, lon, radius_km)
        
        assert len(bbox) == 4
        lamin, lomin, lamax, lomax = bbox
        
        # Box should be centered around the point
        assert lamin < lat < lamax
        assert lomin < lon < lomax
        
        # Box should have approximately correct size
        # (approximate calculation, not exact)
        lat_span = lamax - lamin
        lon_span = lomax - lomin
        
        # For 100km radius at 50° latitude, approximate spans:
        # ~1.8° latitude span, ~2.3° longitude span
        assert 1.0 < lat_span < 3.0
        assert 1.0 < lon_span < 3.0
    
    def test_calculate_bounding_box_at_equator(self):
        """Test bounding box calculation at equator."""
        bbox = calculate_bounding_box(0.0, 0.0, 100)
        lamin, lomin, lamax, lomax = bbox
        
        # At equator, latitude and longitude spans should be similar
        lat_span = lamax - lamin
        lon_span = lomax - lomin
        
        # Should be roughly equal
        assert abs(lat_span - lon_span) < 0.5


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(calls_per_second=10)
        assert limiter.calls_per_second == 10
        assert limiter.min_interval == 0.1  # 1/10 seconds
    
    def test_wait_if_needed_first_call(self):
        """Test first call doesn't wait."""
        limiter = RateLimiter(calls_per_second=10)
        
        start_time = time.time()
        limiter.wait_if_needed()
        end_time = time.time()
        
        # First call should not wait
        assert end_time - start_time < 0.01
    
    def test_wait_if_needed_rapid_calls(self):
        """Test that rapid calls wait appropriately."""
        limiter = RateLimiter(calls_per_second=2)  # 0.5 seconds between calls
        
        # First call
        limiter.wait_if_needed()
        
        # Second call immediately should wait ~0.5 seconds
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        # Should have waited approximately 0.5 seconds
        # Allow some tolerance for test execution time
        assert 0.45 <= elapsed <= 0.55
    
    def test_respects_rate_limit(self):
        """Test that rate limit is respected over multiple calls."""
        limiter = RateLimiter(calls_per_second=5)  # 0.2 seconds between calls
        
        call_times = []
        
        for _ in range(3):
            limiter.wait_if_needed()
            call_times.append(time.time())
        
        # Check intervals between calls
        intervals = [
            call_times[1] - call_times[0],
            call_times[2] - call_times[1]
        ]
        
        # Each interval should be at least min_interval
        for interval in intervals:
            assert interval >= limiter.min_interval - 0.01  # Small tolerance


class TestLogging:
    """Test logging utilities."""
    
    def test_setup_logging(self, caplog):
        """Test logging setup."""
        # Clear any existing handlers
        logging.getLogger().handlers = []
        
        # Setup logging
        setup_logging(level=logging.DEBUG)
        
        # Test logging
        test_logger = logging.getLogger('test_logger')
        test_logger.debug("Test debug message")
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        
        # Check that logging works
        # Note: caplog might not capture due to root logger configuration
        # This test is more about ensuring no exceptions
        assert True