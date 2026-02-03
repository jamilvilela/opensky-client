"""
Configuration and fixtures for OpenSky client tests.
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List
import pytest
from .mocks import (
    create_mock_authenticated_client,
    create_mock_anonymous_client,
    MockSession,
    MockTokenManager
)

from opensky.client import OpenSkyClient
from opensky.auth import OAuth2TokenManager
from opensky.models import StateVector


# Test constants
TEST_CLIENT_ID = "test_client_id"
TEST_CLIENT_SECRET = "test_client_secret"
TEST_ACCESS_TOKEN = "test_access_token_12345"
TEST_ICAO24 = "abc123"
TEST_CALLSIGN = "TEST01"
TEST_BBOX = (47.0, 5.0, 55.0, 15.0)  # Germany


@pytest.fixture
def mock_token_response() -> Dict[str, Any]:
    """Mock OAuth2 token response."""
    return {
        "access_token": TEST_ACCESS_TOKEN,
        "token_type": "Bearer",
        "expires_in": 1800,  # 30 minutes
        "scope": "read"
    }


@pytest.fixture
def mock_states_response() -> Dict[str, Any]:
    """Mock states/all API response."""
    return {
        "time": 1609459200,
        "states": [
            [TEST_ICAO24, TEST_CALLSIGN, "United States", 1609459200, 1609459200,
             10.0, 20.0, 10000.0, False, 250.0, 180.0, 5.0, [], 9500.0,
             "7700", False, 0]
        ]
    }


@pytest.fixture
def mock_flights_response() -> List[Dict[str, Any]]:
    """Mock flights/all API response."""
    return [
        {
            "icao24": TEST_ICAO24,
            "firstSeen": 1609459200,
            "lastSeen": 1609459300,
            "callsign": TEST_CALLSIGN,
            "estDepartureAirport": "EDDF",
            "estArrivalAirport": "EDDM"
        }
    ]


@pytest.fixture
def mock_track_response() -> Dict[str, Any]:
    """Mock tracks/all API response."""
    return {
        "icao24": TEST_ICAO24,
        "callsign": TEST_CALLSIGN,
        "startTime": 1609459200,
        "endTime": 1609459300,
        "path": [
            [1609459200, 50.0, 8.0, 10000.0, 180.0, False],
            [1609459250, 51.0, 9.0, 11000.0, 185.0, False]
        ]
    }


@pytest.fixture
def mock_airport_response() -> Dict[str, Any]:
    """Mock airport API response."""
    return {
        "icao": "EDDF",
        "iata": "FRA",
        "name": "Frankfurt am Main Airport",
        "city": "Frankfurt",
        "country": "Germany",
        "latitude": 50.0333,
        "longitude": 8.5706,
        "altitude": 111.0
    }


@pytest.fixture
def mock_aircraft_response() -> Dict[str, Any]:
    """Mock aircraft database response."""
    return {
        "icao24": TEST_ICAO24,
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
        "reguntil": "2025-12-31",
        "engines": "CFM56-7B26",
        "firstflightdate": "2015-01-01",
        "seatconfiguration": "Y189",
        "modes": False,
        "adsb": False,
        "acars": False,
        "notes": "Test aircraft"
    }


@pytest.fixture
def mock_http_session():
    """Mock HTTP session for testing."""
    with patch('requests.Session') as mock_session:
        session_instance = Mock()
        mock_session.return_value = session_instance
        yield session_instance


@pytest.fixture
def anonymous_client() -> OpenSkyClient:
    """Create anonymous client for testing."""
    return OpenSkyClient(enable_logging=False)


@pytest.fixture
def authenticated_client() -> OpenSkyClient:
    """Create authenticated client for testing."""
    return OpenSkyClient(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
        enable_logging=False
    )


@pytest.fixture
def mock_oauth_token_manager():
    """Mock OAuth2 token manager."""
    with patch('opensky.client.OAuth2TokenManager') as mock_manager:
        manager_instance = Mock()
        manager_instance.get_token.return_value = TEST_ACCESS_TOKEN
        manager_instance.token_info = {
            'has_token': True,
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat(),
            'token_type': 'Bearer',
            'scope': 'read',
            'seconds_until_expiry': 1800
        }
        mock_manager.return_value = manager_instance
        yield manager_instance


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data, status_code=200, text=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text or json.dumps(json_data) if json_data else ""
        self.reason = "OK" if status_code == 200 else "Error"
        self.headers = {}
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error {self.status_code}")


# Monkey-patch para testes assíncronos (se necessário)
@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for async testing."""
    try:
        import aiohttp
        with patch('aiohttp.ClientSession') as mock_session:
            session_instance = AsyncMock()
            mock_session.return_value = session_instance
            yield session_instance
    except ImportError:
        pytest.skip("aiohttp not installed")


# Configuração de ambiente para testes
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Limpar variáveis de ambiente
    original_env = os.environ.copy()
    os.environ.clear()
    
    # Configurar ambiente de teste
    os.environ['OPENSKY_CLIENT_ID'] = TEST_CLIENT_ID
    os.environ['OPENSKY_CLIENT_SECRET'] = TEST_CLIENT_SECRET
    
    yield
    
    # Restaurar ambiente original
    os.environ.clear()
    os.environ.update(original_env)

# tests/conftest.py (adição)

@pytest.fixture
def mock_session():
    """Provide a mock HTTP session."""
    return MockSession()

@pytest.fixture
def mock_token_manager():
    """Provide a mock token manager."""
    return MockTokenManager()

@pytest.fixture
def authenticated_mock_client():
    """Provide an authenticated mock client."""
    return create_mock_authenticated_client()

@pytest.fixture
def anonymous_mock_client():
    """Provide an anonymous mock client."""
    return create_mock_anonymous_client()    