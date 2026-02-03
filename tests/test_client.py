"""
Tests for OpenSkyClient class with OAuth2 authentication.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, call
from typing import Dict, Any

from opensky.client import OpenSkyClient
from opensky.exceptions import (
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError
)
from opensky.models import StateVector, Flight, Airport


class TestOpenSkyClientInitialization:
    """Test OpenSkyClient initialization."""
    
    def test_anonymous_client_initialization(self):
        """Test initialization without OAuth2 credentials."""
        client = OpenSkyClient(enable_logging=False)
        
        assert client.token_manager is None
        assert client.base_url == "https://opensky-network.org/api"
        assert client.timeout == 30
    
    def test_authenticated_client_initialization(self):
        """Test initialization with OAuth2 credentials."""
        client = OpenSkyClient(
            client_id="test_id",
            client_secret="test_secret",
            enable_logging=False
        )
        
        assert client.token_manager is not None
        assert client.token_manager.client_id == "test_id"
        assert client.token_manager.client_secret == "test_secret"
    
    def test_custom_base_url(self):
        """Test initialization with custom base URL."""
        custom_url = "https://custom.opensky.net/api"
        client = OpenSkyClient(
            client_id="test_id",
            client_secret="test_secret",
            base_url=custom_url,
            enable_logging=False
        )
        
        assert client.base_url == custom_url
    
    def test_custom_timeout_and_rate_limit(self):
        """Test initialization with custom timeout and rate limit."""
        client = OpenSkyClient(
            client_id="test_id",
            client_secret="test_secret",
            timeout=60,
            rate_limit=5.0,
            enable_logging=False
        )
        
        assert client.timeout == 60
        assert client.rate_limiter.calls_per_second == 5.0


class TestOpenSkyClientAuthentication:
    """Test authentication methods."""
    
    def test_get_auth_header_anonymous(self):
        """Test auth header for anonymous client."""
        client = OpenSkyClient(enable_logging=False)
        headers = client._get_auth_header()
        
        assert headers == {}
    
    def test_get_auth_header_authenticated(self):
        """Test auth header for authenticated client."""
        with patch('opensky.auth.OAuth2TokenManager') as MockTokenManager:
            mock_manager = Mock()
            mock_manager.get_token.return_value = "test_token"
            MockTokenManager.return_value = mock_manager
            
            client = OpenSkyClient(
                client_id="test_id",
                client_secret="test_secret",
                enable_logging=False
            )
            
            headers = client._get_auth_header()
            
            assert headers == {'Authorization': 'Bearer test_token'}
            mock_manager.get_token.assert_called_once()
    
    def test_get_auth_header_token_error(self):
        """Test auth header when token acquisition fails."""
        with patch('opensky.auth.OAuth2TokenManager') as MockTokenManager:
            mock_manager = Mock()
            mock_manager.get_token.side_effect = AuthenticationError("Token error")
            MockTokenManager.return_value = mock_manager
            
            client = OpenSkyClient(
                client_id="test_id",
                client_secret="test_secret",
                enable_logging=False
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                client._get_auth_header()
            
            assert "Token error" in str(exc_info.value)
    
    def test_get_token_info_anonymous(self):
        """Test get_token_info for anonymous client."""
        client = OpenSkyClient(enable_logging=False)
        token_info = client.get_token_info()
        
        assert token_info is None
    
    def test_get_token_info_authenticated(self):
        """Test get_token_info for authenticated client."""
        with patch('opensky.auth.OAuth2TokenManager') as MockTokenManager:
            mock_manager = Mock()
            mock_manager.token_info = {"expires_at": "2024-01-01T00:00:00"}
            MockTokenManager.return_value = mock_manager
            
            client = OpenSkyClient(
                client_id="test_id",
                client_secret="test_secret",
                enable_logging=False
            )
            
            token_info = client.get_token_info()
            
            assert token_info == {"expires_at": "2024-01-01T00:00:00"}
    
    def test_refresh_token_anonymous(self):
        """Test refresh_token for anonymous client."""
        client = OpenSkyClient(enable_logging=False)
        
        # Should not raise an error, just do nothing
        client.refresh_token()
    
    def test_refresh_token_authenticated(self):
        """Test refresh_token for authenticated client."""
        with patch('opensky.auth.OAuth2TokenManager') as MockTokenManager:
            mock_manager = Mock()
            MockTokenManager.return_value = mock_manager
            
            client = OpenSkyClient(
                client_id="test_id",
                client_secret="test_secret",
                enable_logging=False
            )
            
            client.refresh_token()
            
            mock_manager.clear_token.assert_called_once()
            mock_manager.get_token.assert_called_once()


class TestOpenSkyClientRequestHandling:
    """Test HTTP request handling."""
    
    def test_successful_request(self, authenticated_client, mock_http_session):
        """Test successful API request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True}
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = '{"success": true}'
        mock_response.headers = {}
        
        mock_http_session.request.return_value = mock_response
        
        # Make request
        with patch.object(authenticated_client.token_manager, 'get_token', return_value="test_token"):
            response = authenticated_client._request('GET', '/test')
        
        assert response == {"success": True}
    
    def test_authentication_error_401(self, authenticated_client, mock_http_session):
        """Test handling of 401 Unauthorized error."""
        # Setup mock response with 401
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.reason = "Unauthorized"
        mock_response.text = "Invalid token"
        
        mock_http_session.request.return_value = mock_response
        
        # Setup token manager to refresh token on first 401
        with patch.object(authenticated_client.token_manager, 'get_token') as mock_get_token:
            mock_get_token.side_effect = ["expired_token", "new_token"]
            
            with patch.object(authenticated_client.token_manager, 'clear_token') as mock_clear_token:
                # First call should trigger token refresh
                mock_http_session.request.side_effect = [
                    mock_response,  # First call returns 401
                    Mock(ok=True, json=lambda: {"success": True})  # Second call succeeds
                ]
                
                response = authenticated_client._request('GET', '/test')
                
                # Verify token was cleared
                mock_clear_token.assert_called_once()
                assert response == {"success": True}
    
    def test_rate_limit_error_429(self, authenticated_client, mock_http_session):
        """Test handling of 429 Rate Limit error."""
        # Setup mock response with 429
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.reason = "Too Many Requests"
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {'Retry-After': '60'}
        
        mock_http_session.request.return_value = mock_response
        
        with pytest.raises(RateLimitError) as exc_info:
            authenticated_client._request('GET', '/test')
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.status_code == 429
    
    def test_api_error_other_codes(self, authenticated_client, mock_http_session):
        """Test handling of other API errors."""
        # Setup mock response with 500
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Server error"
        
        mock_http_session.request.return_value = mock_response
        
        with pytest.raises(APIError) as exc_info:
            authenticated_client._request('GET', '/test')
        
        assert "HTTP 500" in str(exc_info.value)
        assert exc_info.value.status_code == 500
    
    def test_connection_error_with_retry(self, authenticated_client, mock_http_session):
        """Test handling of connection errors with retry logic."""
        # Setup mock to raise connection error twice then succeed
        mock_http_session.request.side_effect = [
            Exception("Connection error"),
            Exception("Connection error"),
            Mock(ok=True, json=lambda: {"success": True})
        ]
        
        response = authenticated_client._request('GET', '/test', retries=3)
        
        assert response == {"success": True}
        assert mock_http_session.request.call_count == 3
    
    def test_connection_error_max_retries(self, authenticated_client, mock_http_session):
        """Test handling of connection errors when max retries reached."""
        # Setup mock to always raise connection error
        mock_http_session.request.side_effect = Exception("Connection error")
        
        with pytest.raises(APIError) as exc_info:
            authenticated_client._request('GET', '/test', retries=2)
        
        assert "failed after 2 retries" in str(exc_info.value)


class TestOpenSkyClientStatesEndpoint:
    """Test states/all endpoint methods."""
    
    def test_get_states_anonymous(self, anonymous_client, mock_http_session):
        """Test get_states with anonymous client."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "time": 1609459200,
            "states": [
                ["abc123", "TEST01", "United States", 1609459200, 1609459200,
                 10.0, 20.0, 10000.0, False, 250.0, 180.0, 5.0, [], 9500.0,
                 "7700", False, 0]
            ]
        }
        
        mock_http_session.request.return_value = mock_response
        
        states = anonymous_client.get_states()
        
        assert len(states) == 1
        assert isinstance(states[0], StateVector)
        assert states[0].icao24 == "abc123"
        assert states[0].callsign == "TEST01"
    
    def test_get_states_with_bbox(self, anonymous_client, mock_http_session):
        """Test get_states with bounding box."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"time": 1609459200, "states": []}
        
        mock_http_session.request.return_value = mock_response
        
        bbox = (47.0, 5.0, 55.0, 15.0)  # Germany
        anonymous_client.get_states(bbox=bbox)
        
        # Verify request was made with correct parameters
        call_args = mock_http_session.request.call_args
        assert call_args[0] == ('GET', 'https://opensky-network.org/api/states/all')
        
        params = call_args[1]['params']
        assert params['lamin'] == 47.0
        assert params['lomin'] == 5.0
        assert params['lamax'] == 55.0
        assert params['lomax'] == 15.0
    
    def test_get_states_with_icao24_filter(self, anonymous_client, mock_http_session):
        """Test get_states with ICAO24 filter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"time": 1609459200, "states": []}
        
        mock_http_session.request.return_value = mock_response
        
        anonymous_client.get_states(icao24="abc123")
        
        call_args = mock_http_session.request.call_args
        params = call_args[1]['params']
        assert params['icao24'] == "abc123"
    
    def test_get_states_historical_requires_auth(self, anonymous_client):
        """Test that historical states require authentication."""
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_states(time_secs=1609459200)
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_states_historical_with_auth(self, authenticated_client, mock_http_session):
        """Test historical states with authenticated client."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"time": 1609459200, "states": []}
        
        mock_http_session.request.return_value = mock_response
        
        authenticated_client.get_states(time_secs=1609459200)
        
        call_args = mock_http_session.request.call_args
        params = call_args[1]['params']
        assert params['time'] == 1609459200
    
    def test_get_states_bbox_validation_error(self, anonymous_client):
        """Test validation error for invalid bounding box."""
        with pytest.raises(ValidationError) as exc_info:
            anonymous_client.get_states(bbox=(1.0, 2.0, 3.0))  # Missing 4th value
        
        assert "Bounding box must have 4 values" in str(exc_info.value)
    
    def test_get_states_icao24_validation_error(self, anonymous_client):
        """Test validation error for invalid ICAO24."""
        with pytest.raises(ValidationError) as exc_info:
            anonymous_client.get_states(icao24="invalid")  # Invalid format
        
        assert "Invalid ICAO24 address" in str(exc_info.value)
    
    def test_get_states_bbox_area(self, anonymous_client, mock_http_session):
        """Test get_states_bbox method."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"time": 1609459200, "states": []}
        
        mock_http_session.request.return_value = mock_response
        
        states = anonymous_client.get_states_bbox(lat=50.0, lon=8.0, radius_km=100)
        
        # Verify bounding box was calculated
        call_args = mock_http_session.request.call_args
        params = call_args[1]['params']
        
        # Should have bounding box parameters
        assert 'lamin' in params
        assert 'lomin' in params
        assert 'lamax' in params
        assert 'lomax' in params


class TestOpenSkyClientFlightsEndpoint:
    """Test flights/all endpoint methods."""
    
    def test_get_flights_requires_auth(self, anonymous_client):
        """Test that flights endpoint requires authentication."""
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_flights(begin=begin, end=end)
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_flights_success(self, authenticated_client, mock_http_session):
        """Test successful flights retrieval."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {
                "icao24": "abc123",
                "firstSeen": 1609459200,
                "lastSeen": 1609459300,
                "callsign": "TEST01",
                "estDepartureAirport": "EDDF",
                "estArrivalAirport": "EDDM"
            }
        ]
        
        mock_http_session.request.return_value = mock_response
        
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        flights = authenticated_client.get_flights(begin=begin, end=end)
        
        assert len(flights) == 1
        assert isinstance(flights[0], Flight)
        assert flights[0].icao24 == "abc123"
        assert flights[0].callsign == "TEST01"
    
    def test_get_flights_with_icao24_filter(self, authenticated_client, mock_http_session):
        """Test flights retrieval with ICAO24 filter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = []
        
        mock_http_session.request.return_value = mock_response
        
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        authenticated_client.get_flights(begin=begin, end=end, icao24="abc123")
        
        call_args = mock_http_session.request.call_args
        params = call_args[1]['params']
        assert params['icao24'] == "abc123"


class TestOpenSkyClientAirportsEndpoint:
    """Test airports endpoint methods."""
    
    def test_get_airports_all(self, anonymous_client, mock_http_session):
        """Test getting all airports."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {
                "icao": "EDDF",
                "iata": "FRA",
                "name": "Frankfurt Airport",
                "city": "Frankfurt",
                "country": "Germany",
                "latitude": 50.0333,
                "longitude": 8.5706,
                "altitude": 111.0
            }
        ]
        
        mock_http_session.request.return_value = mock_response
        
        airports = anonymous_client.get_airports()
        
        assert len(airports) == 1
        assert isinstance(airports[0], Airport)
        assert airports[0].icao == "EDDF"
        assert airports[0].name == "Frankfurt Airport"
    
    def test_get_airports_specific(self, anonymous_client, mock_http_session):
        """Test getting specific airport by ICAO code."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "icao": "EDDF",
            "iata": "FRA",
            "name": "Frankfurt Airport",
            "city": "Frankfurt",
            "country": "Germany",
            "latitude": 50.0333,
            "longitude": 8.5706,
            "altitude": 111.0
        }
        
        mock_http_session.request.return_value = mock_response
        
        airports = anonymous_client.get_airports(icao="EDDF")
        
        assert len(airports) == 1
        assert airports[0].icao == "EDDF"
        assert airports[0].iata == "FRA"


class TestOpenSkyClientTrackEndpoint:
    """Test tracks/all endpoint methods."""
    
    def test_get_track_requires_auth_for_historical(self, anonymous_client):
        """Test that historical tracks require authentication."""
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_track(icao24="abc123", time_secs=1609459200)
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_track_success(self, authenticated_client, mock_http_session):
        """Test successful track retrieval."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "icao24": "abc123",
            "callsign": "TEST01",
            "startTime": 1609459200,
            "endTime": 1609459300,
            "path": [
                [1609459200, 50.0, 8.0, 10000.0, 180.0, False],
                [1609459250, 51.0, 9.0, 11000.0, 185.0, False]
            ]
        }
        
        mock_http_session.request.return_value = mock_response
        
        track = authenticated_client.get_track(icao24="abc123")
        
        assert track.icao24 == "abc123"
        assert track.callsign == "TEST01"
        assert len(track.path) == 2
        assert track.duration_seconds == 100.0  # 1609459300 - 1609459200
    
    def test_get_track_icao24_validation(self, authenticated_client):
        """Test ICAO24 validation for track endpoint."""
        with pytest.raises(ValidationError) as exc_info:
            authenticated_client.get_track(icao24="invalid")
        
        assert "Invalid ICAO24 address" in str(exc_info.value)


class TestOpenSkyClientAirportMovements:
    """Test airport movements endpoints (arrivals/departures)."""
    
    def test_get_arrivals_requires_auth(self, anonymous_client):
        """Test that arrivals endpoint requires authentication."""
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_arrivals(airport="EDDF", begin=begin, end=end)
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_departures_requires_auth(self, anonymous_client):
        """Test that departures endpoint requires authentication."""
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_departures(airport="EDDF", begin=begin, end=end)
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_arrivals_success(self, authenticated_client, mock_http_session):
        """Test successful arrivals retrieval."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {
                "icao24": "abc123",
                "firstSeen": 1609459200,
                "estArrivalAirport": "EDDF",
                "lastSeen": 1609459300,
                "callsign": "TEST01",
                "estDepartureAirport": "EDDM"
            }
        ]
        
        mock_http_session.request.return_value = mock_response
        
        begin = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        arrivals = authenticated_client.get_arrivals(
            airport="EDDF",
            begin=begin,
            end=end
        )
        
        assert len(arrivals) == 1
        assert arrivals[0].icao24 == "abc123"
        assert arrivals[0].arrival_airport == "EDDF"


class TestOpenSkyClientAircraftDatabase:
    """Test aircraft database endpoint."""
    
    def test_get_aircraft_database_success(self, anonymous_client, mock_http_session):
        """Test successful aircraft database lookup."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "icao24": "abc123",
            "registration": "D-ABCD",
            "model": "737-800"
        }
        
        mock_http_session.request.return_value = mock_response
        
        result = anonymous_client.get_aircraft_database(icao24="abc123")
        
        assert result["icao24"] == "abc123"
        assert result["registration"] == "D-ABCD"
    
    def test_get_aircraft_database_validation(self, anonymous_client):
        """Test validation for aircraft database endpoint."""
        with pytest.raises(ValidationError) as exc_info:
            # Must provide either icao24 or registration
            anonymous_client.get_aircraft_database()
        
        assert "Either icao24 or registration must be provided" in str(exc_info.value)
    
    def test_get_aircraft_database_icao24_validation(self, anonymous_client):
        """Test ICAO24 validation for aircraft database."""
        with pytest.raises(ValidationError) as exc_info:
            anonymous_client.get_aircraft_database(icao24="invalid")
        
        assert "Invalid ICAO24 address" in str(exc_info.value)


class TestOpenSkyClientHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_success(self, anonymous_client, mock_http_session):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "ok",
            "version": "1.0.0"
        }
        
        mock_http_session.request.return_value = mock_response
        
        result = anonymous_client.health_check()
        
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"


class TestOpenSkyClientOwnStates:
    """Test own states endpoint."""
    
    def test_get_my_states_requires_auth(self, anonymous_client):
        """Test that own states endpoint requires authentication."""
        with pytest.raises(AuthenticationError) as exc_info:
            anonymous_client.get_my_states()
        
        assert "OAuth2 authentication required" in str(exc_info.value)
    
    def test_get_my_states_success(self, authenticated_client, mock_http_session):
        """Test successful own states retrieval."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "time": 1609459200,
            "states": [
                ["abc123", "TEST01", "United States", 1609459200, 1609459200,
                 10.0, 20.0, 10000.0, False, 250.0, 180.0, 5.0, [], 9500.0,
                 "7700", False, 0]
            ]
        }
        
        mock_http_session.request.return_value = mock_response
        
        states = authenticated_client.get_my_states()
        
        assert len(states) == 1
        assert isinstance(states[0], StateVector)
        assert states[0].icao24 == "abc123"


class TestOpenSkyClientContextManager:
    """Test context manager functionality."""
    
    def test_context_manager_anonymous(self, mock_http_session):
        """Test context manager with anonymous client."""
        with OpenSkyClient(enable_logging=False) as client:
            assert isinstance(client, OpenSkyClient)
            # Client should be usable inside context
        
        # Session should be closed after context
        mock_http_session.close.assert_called_once()
    
    def test_context_manager_authenticated(self, mock_oauth_token_manager):
        """Test context manager with authenticated client."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            with OpenSkyClient(
                client_id="test_id",
                client_secret="test_secret",
                enable_logging=False
            ) as client:
                assert isinstance(client, OpenSkyClient)
            
            # Both session and token manager should be closed
            mock_session.close.assert_called_once()
            mock_oauth_token_manager.close.assert_called_once()


class TestOpenSkyClientErrorScenarios:
    """Test various error scenarios."""
    
    def test_parsing_error_in_get_states(self, anonymous_client, mock_http_session):
        """Test handling of parsing errors in get_states."""
        # Mock response with invalid data
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "time": 1609459200,
            "states": [
                ["invalid_data"]  # Incomplete data array
            ]
        }
        
        mock_http_session.request.return_value = mock_response
        
        # Should handle parsing error gracefully
        states = anonymous_client.get_states()
        
        # Parsing should fail but not crash
        assert len(states) == 0
    
    def test_empty_response_handling(self, anonymous_client, mock_http_session):
        """Test handling of empty responses."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {}  # Empty response
        
        mock_http_session.request.return_value = mock_response
        
        # Should handle empty response gracefully
        states = anonymous_client.get_states()
        
        assert len(states) == 0
    
    def test_rate_limit_respect(self, authenticated_client, mock_http_session):
        """Test that rate limiter is used."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True}
        
        mock_http_session.request.return_value = mock_response
        
        # Make multiple requests
        with patch.object(authenticated_client.rate_limiter, 'wait_if_needed') as mock_wait:
            for _ in range(3):
                authenticated_client._request('GET', '/test')
            
            # Rate limiter should be called before each request
            assert mock_wait.call_count == 3


class TestOpenSkyClientUtilityMethods:
    """Test utility methods."""
    
    def test_close_method(self, authenticated_client, mock_http_session, mock_oauth_token_manager):
        """Test close method."""
        authenticated_client.close()
        
        # Both session and token manager should be closed
        mock_http_session.close.assert_called_once()
        mock_oauth_token_manager.close.assert_called_once()
    
    def test_http_methods_wrappers(self, anonymous_client, mock_http_session):
        """Test HTTP method wrappers (get, post, etc.)."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True}
        
        mock_http_session.request.return_value = mock_response
        
        # Test GET
        result = anonymous_client.get('/test', params={'key': 'value'})
        assert result == {"success": True}
        
        call_args = mock_http_session.request.call_args
        assert call_args[0][0] == 'GET'
        assert call_args[1]['params'] == {'key': 'value'}
        
        # Test POST
        result = anonymous_client.post('/test', data={'key': 'value'})
        assert result == {"success": True}
        
        call_args = mock_http_session.request.call_args
        assert call_args[0][0] == 'POST'
        assert call_args[1]['json_data'] == {'key': 'value'}
        
        # Test PUT
        result = anonymous_client.put('/test', data={'key': 'value'})
        assert result == {"success": True}
        
        call_args = mock_http_session.request.call_args
        assert call_args[0][0] == 'PUT'
        
        # Test DELETE
        result = anonymous_client.delete('/test')
        assert result == {"success": True}
        
        call_args = mock_http_session.request.call_args
        assert call_args[0][0] == 'DELETE'