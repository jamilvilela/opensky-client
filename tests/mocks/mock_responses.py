"""
Mock responses for OpenSky API endpoints.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass


@dataclass
class MockResponse:
    """Mock HTTP response."""
    
    json_data: Optional[Union[Dict, List]] = None
    text: Optional[str] = None
    status_code: int = 200
    reason: str = "OK"
    headers: Optional[Dict[str, str]] = None
    ok: Optional[bool] = None
    
    def __post_init__(self):
        if self.ok is None:
            self.ok = 200 <= self.status_code < 300
        
        if self.text is None and self.json_data is not None:
            self.text = json.dumps(self.json_data)
        
        if self.headers is None:
            self.headers = {}
    
    def json(self):
        if self.json_data is None:
            raise ValueError("No JSON data in response")
        return self.json_data
    
    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP {self.status_code}: {self.reason}")


# Test constants
TEST_ICAO24 = "abc123"
TEST_CALLSIGN = "TEST01"
TEST_TOKEN = "test_access_token_12345"
TEST_CLIENT_ID = "test_client_id"
TEST_CLIENT_SECRET = "test_client_secret"


def mock_token_response(
    access_token: str = TEST_TOKEN,
    expires_in: int = 1800,
    token_type: str = "Bearer",
    scope: str = "read",
    refresh_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock OAuth2 token response.
    """
    response = {
        "access_token": access_token,
        "token_type": token_type,
        "expires_in": expires_in,
        "scope": scope
    }
    
    if refresh_token:
        response["refresh_token"] = refresh_token
    
    return response


def mock_states_response(
    time: Optional[int] = None,
    states_count: int = 5,
    include_none_values: bool = False
) -> Dict[str, Any]:
    """
    Mock states/all API response.
    
    Args:
        time: Unix timestamp for response time
        states_count: Number of state vectors to include
        include_none_values: Include None values to test parsing
    
    Returns:
        Mock response dictionary
    """
    if time is None:
        time = int(datetime.now().timestamp())
    
    states = []
    
    for i in range(states_count):
        icao24 = f"{TEST_ICAO24}{i}"
        callsign = f"{TEST_CALLSIGN}{i:02d}"
        
        if include_none_values and i % 2 == 0:
            # Alternate with None values for testing
            state = [
                icao24,
                callsign,
                "United States",
                time,
                time,
                None,  # longitude
                None,  # latitude
                None,  # altitude
                None,  # on_ground
                None,  # velocity
                None,  # heading
                None,  # vertical_rate
                None,  # sensors
                None,  # geo_altitude
                None,  # squawk
                None,  # spi
                None   # position_source
            ]
        else:
            state = [
                icao24,
                callsign,
                "United States",
                time - i * 60,  # Each aircraft has different timestamps
                time - i * 30,
                10.0 + i * 0.1,  # longitude
                20.0 + i * 0.1,  # latitude
                10000.0 + i * 1000,  # altitude
                False,  # on_ground
                250.0 + i * 10,  # velocity
                180.0 + i * 5,  # heading
                5.0,  # vertical_rate
                [1, 2, 3],  # sensors
                9500.0 + i * 1000,  # geo_altitude
                "7700",  # squawk
                False,  # spi
                i % 3  # position_source (0=ADSB, 1=ASTERIX, 2=MLAT)
            ]
        
        states.append(state)
    
    return {
        "time": time,
        "states": states
    }


def mock_empty_states_response() -> Dict[str, Any]:
    """
    Mock empty states response.
    """
    return {
        "time": int(datetime.now().timestamp()),
        "states": []
    }


def mock_flights_response(
    count: int = 3,
    include_missing_fields: bool = False
) -> List[Dict[str, Any]]:
    """
    Mock flights/all API response.
    
    Args:
        count: Number of flights to include
        include_missing_fields: Include flights with missing optional fields
    
    Returns:
        List of flight dictionaries
    """
    now = datetime.now()
    flights = []
    
    for i in range(count):
        flight = {
            "icao24": f"{TEST_ICAO24}{i}",
            "firstSeen": int((now - timedelta(hours=2)).timestamp()),
            "lastSeen": int((now - timedelta(hours=1)).timestamp()),
        }
        
        if not include_missing_fields or i % 3 != 0:
            flight["callsign"] = f"{TEST_CALLSIGN}{i:02d}"
        
        if not include_missing_fields or i % 3 != 1:
            flight["estDepartureAirport"] = f"EDD{i%3}"
        
        if not include_missing_fields or i % 3 != 2:
            flight["estArrivalAirport"] = f"EDM{i%3}"
        
        flights.append(flight)
    
    return flights


def mock_track_response(
    icao24: str = TEST_ICAO24,
    callsign: str = TEST_CALLSIGN,
    point_count: int = 5
) -> Dict[str, Any]:
    """
    Mock tracks/all API response.
    
    Args:
        icao24: ICAO24 address
        callsign: Aircraft callsign
        point_count: Number of track points
    
    Returns:
        Track response dictionary
    """
    now = datetime.now()
    start_time = int((now - timedelta(hours=1)).timestamp())
    end_time = int(now.timestamp())
    
    path = []
    time_step = (end_time - start_time) // max(1, point_count - 1)
    
    for i in range(point_count):
        timestamp = start_time + i * time_step
        latitude = 50.0 + i * 0.2
        longitude = 8.0 + i * 0.3
        altitude = 10000.0 + i * 500
        heading = 180.0 + i * 10
        on_ground = False
        
        path.append([timestamp, latitude, longitude, altitude, heading, on_ground])
    
    return {
        "icao24": icao24,
        "callsign": callsign,
        "startTime": start_time,
        "endTime": end_time,
        "path": path
    }


def mock_airport_response(
    icao: str = "EDDF",
    include_optional: bool = True
) -> Dict[str, Any]:
    """
    Mock single airport response.
    
    Args:
        icao: ICAO airport code
        include_optional: Include optional fields
    
    Returns:
        Airport response dictionary
    """
    airports = {
        "EDDF": {
            "icao": "EDDF",
            "iata": "FRA",
            "name": "Frankfurt am Main Airport",
            "city": "Frankfurt",
            "country": "Germany",
            "latitude": 50.0333,
            "longitude": 8.5706,
            "altitude": 111.0
        },
        "EDDM": {
            "icao": "EDDM",
            "iata": "MUC",
            "name": "Munich Airport",
            "city": "Munich",
            "country": "Germany",
            "latitude": 48.3538,
            "longitude": 11.7861,
            "altitude": 453.0
        },
        "KJFK": {
            "icao": "KJFK",
            "iata": "JFK",
            "name": "John F. Kennedy International Airport",
            "city": "New York",
            "country": "United States",
            "latitude": 40.6398,
            "longitude": -73.7789,
            "altitude": 4.0
        }
    }
    
    if icao in airports:
        return airports[icao].copy()
    
    # Default airport
    return {
        "icao": icao,
        "iata": "XXX" if include_optional else None,
        "name": f"{icao} Airport" if include_optional else None,
        "city": "Unknown" if include_optional else None,
        "country": "Unknown" if include_optional else None,
        "latitude": 0.0,
        "longitude": 0.0,
        "altitude": 0.0
    }


def mock_airports_all_response(count: int = 10) -> List[Dict[str, Any]]:
    """
    Mock airports/all API response.
    
    Args:
        count: Number of airports to include
    
    Returns:
        List of airport dictionaries
    """
    airports = []
    
    # Include some known airports
    known_airports = ["EDDF", "EDDM", "KJFK", "LFPG", "EGLL", "OMDB", "RJTT", "ZBAA"]
    
    for i in range(count):
        if i < len(known_airports):
            airport = mock_airport_response(known_airports[i])
        else:
            airport = mock_airport_response(f"TEST{i}")
        
        airports.append(airport)
    
    return airports


def mock_aircraft_response(
    icao24: str = TEST_ICAO24,
    include_all_fields: bool = True
) -> Dict[str, Any]:
    """
    Mock aircraft database response.
    
    Args:
        icao24: ICAO24 address
        include_all_fields: Include all possible fields
    
    Returns:
        Aircraft database response
    """
    base_data = {
        "icao24": icao24,
        "registration": "D-ABCD",
        "manufacturericao": "BOEING",
        "manufacturername": "Boeing",
        "model": "737-800",
        "typecode": "B738",
        "serialnumber": "12345",
        "linenumber": "456",
        "icaoaircrafttype": "L2J",
        "operator": "Test Airlines",
        "operatorcallsign": "TEST",
        "operatoricao": "TST",
        "operatoriata": "TS",
        "owner": "Test Leasing",
    }
    
    if include_all_fields:
        base_data.update({
            "reguntil": "2025-12-31",
            "engines": "CFM56-7B26",
            "firstflightdate": "2015-01-01",
            "seatconfiguration": "Y189",
            "modes": False,
            "adsb": False,
            "acars": False,
            "notes": "Test aircraft for mock responses"
        })
    
    return base_data


def mock_aircraft_by_registration_response(
    registration: str = "D-ABCD"
) -> Dict[str, Any]:
    """
    Mock aircraft database response by registration.
    """
    response = mock_aircraft_response()
    response["registration"] = registration
    return response


def mock_health_response(
    status: str = "ok",
    version: str = "1.0.0",
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock health check response.
    
    Args:
        status: Health status (ok, degraded, down)
        version: API version
        message: Optional status message
    
    Returns:
        Health response dictionary
    """
    response = {
        "status": status,
        "version": version
    }
    
    if message:
        response["message"] = message
    
    return response


def mock_error_response(
    error: str = "Bad Request",
    error_description: Optional[str] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """
    Mock error response.
    
    Args:
        error: Error type
        error_description: Detailed error description
        status_code: HTTP status code
    
    Returns:
        Error response dictionary
    """
    response = {"error": error}
    
    if error_description:
        response["error_description"] = error_description
    
    return response


def mock_rate_limit_response(
    retry_after: int = 60,
    error: str = "Too Many Requests"
) -> MockResponse:
    """
    Mock rate limit response (HTTP 429).
    
    Args:
        retry_after: Retry after seconds
        error: Error message
    
    Returns:
        MockResponse with rate limit error
    """
    return MockResponse(
        json_data={"error": error},
        status_code=429,
        reason="Too Many Requests",
        headers={"Retry-After": str(retry_after)},
        ok=False
    )


def mock_unauthorized_response(
    error: str = "Unauthorized",
    error_description: str = "Invalid or expired token"
) -> MockResponse:
    """
    Mock unauthorized response (HTTP 401).
    
    Args:
        error: Error type
        error_description: Detailed error description
    
    Returns:
        MockResponse with unauthorized error
    """
    return MockResponse(
        json_data={
            "error": error,
            "error_description": error_description
        },
        status_code=401,
        reason="Unauthorized",
        ok=False
    )


def mock_connection_error_response() -> MockResponse:
    """
    Mock connection error response.
    """
    return MockResponse(
        text="Connection failed",
        status_code=0,
        reason="Connection Error",
        ok=False
    )


def mock_parse_error_response() -> MockResponse:
    """
    Mock response with invalid JSON to test parsing errors.
    """
    return MockResponse(
        text="Invalid JSON response",
        status_code=200,
        reason="OK",
        ok=True
    )


def mock_own_states_response() -> Dict[str, Any]:
    """
    Mock states/own API response (for authenticated users).
    """
    return mock_states_response(states_count=3)