"""
Mock HTTP session and token manager for testing.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from unittest.mock import Mock, MagicMock, AsyncMock
from urllib.parse import urljoin, urlparse, parse_qs

from opensky.auth import OAuth2TokenManager
from opensky.client import OpenSkyClient
from opensky.exceptions import AuthenticationError, APIError

from .mock_responses import (
    MockResponse,
    mock_token_response,
    mock_states_response,
    mock_flights_response,
    mock_track_response,
    mock_airport_response,
    mock_airports_all_response,
    mock_aircraft_response,
    mock_health_response,
    mock_error_response,
    mock_rate_limit_response,
    mock_unauthorized_response,
    mock_connection_error_response,
    mock_parse_error_response,
    mock_own_states_response
)


class MockTokenManager:
    """
    Mock OAuth2 token manager for testing.
    """
    
    def __init__(
        self,
        client_id: str = "test_client_id",
        client_secret: str = "test_client_secret",
        token_url: str = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
        auto_refresh: bool = True,
        initial_token: Optional[str] = "test_access_token_12345"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.auto_refresh = auto_refresh
        
        self.access_token = initial_token
        self.token_expires_at = None
        self.token_type = "Bearer"
        self.scope = "read"
        
        if initial_token and auto_refresh:
            self.token_expires_at = datetime.now() + timedelta(minutes=30)
        
        self.get_token_call_count = 0
        self.clear_token_call_count = 0
        self.refresh_token_call_count = 0
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        Mock get_token method.
        """
        self.get_token_call_count += 1
        
        if force_refresh:
            self.refresh_token()
        
        if self.access_token is None:
            self.access_token = "new_mock_token_" + str(int(time.time()))
            self.token_expires_at = datetime.now() + timedelta(minutes=30)
        
        return self.access_token
    
    def refresh_token(self) -> str:
        """
        Mock refresh_token method.
        """
        self.refresh_token_call_count += 1
        self.access_token = "refreshed_mock_token_" + str(int(time.time()))
        self.token_expires_at = datetime.now() + timedelta(minutes=30)
        return self.access_token
    
    def clear_token(self) -> None:
        """
        Mock clear_token method.
        """
        self.clear_token_call_count += 1
        self.access_token = None
        self.token_expires_at = None
    
    @property
    def token_info(self) -> Dict[str, Any]:
        """
        Mock token_info property.
        """
        return {
            'has_token': self.access_token is not None,
            'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'token_type': self.token_type,
            'scope': self.scope,
            'seconds_until_expiry': (
                (self.token_expires_at - datetime.now()).total_seconds()
                if self.token_expires_at else None
            ),
        }
    
    def close(self) -> None:
        """Mock close method."""
        pass


class MockSession:
    """
    Mock HTTP session for testing.
    Supports request history, response mocking, and error simulation.
    """
    
    def __init__(self, base_url: str = "https://opensky-network.org/api"):
        self.base_url = base_url
        self.headers = {}
        self.auth = None
        
        # Request history
        self.requests = []
        
        # Mock responses by (method, endpoint_pattern)
        self._mock_responses = {}
        
        # Default responses
        self._setup_default_responses()
        
        # Call counters
        self.request_count = 0
        self.get_count = 0
        self.post_count = 0
        self.put_count = 0
        self.delete_count = 0
    
    def _setup_default_responses(self):
        """Setup default mock responses."""
        # Token endpoint
        self.add_mock_response(
            "POST",
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
            MockResponse(json_data=mock_token_response())
        )
        
        # States endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/states/all",
            MockResponse(json_data=mock_states_response())
        )
        
        # Flights endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/flights/all",
            MockResponse(json_data=mock_flights_response())
        )
        
        # Track endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/tracks/all",
            MockResponse(json_data=mock_track_response())
        )
        
        # Airports endpoint (all)
        self.add_mock_response(
            "GET",
            f"{self.base_url}/airports",
            MockResponse(json_data=mock_airports_all_response())
        )
        
        # Single airport endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/airports/EDDF",
            MockResponse(json_data=mock_airport_response())
        )
        
        # Aircraft database endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/aircraft-database",
            MockResponse(json_data=mock_aircraft_response())
        )
        
        # Health endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/health",
            MockResponse(json_data=mock_health_response())
        )
        
        # Own states endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/states/own",
            MockResponse(json_data=mock_own_states_response())
        )
        
        # Arrivals endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/flights/arrival",
            MockResponse(json_data=mock_flights_response())
        )
        
        # Departures endpoint
        self.add_mock_response(
            "GET",
            f"{self.base_url}/flights/departure",
            MockResponse(json_data=mock_flights_response())
        )
    
    def add_mock_response(
        self,
        method: str,
        url_pattern: str,
        response: MockResponse
    ):
        """
        Add a mock response for a specific method and URL pattern.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url_pattern: URL pattern (can contain wildcards)
            response: MockResponse to return
        """
        key = (method.upper(), url_pattern)
        self._mock_responses[key] = response
    
    def add_mock_response_callback(
        self,
        method: str,
        url_pattern: str,
        callback: Callable[[str, Dict], MockResponse]
    ):
        """
        Add a callback for generating mock responses dynamically.
        
        Args:
            method: HTTP method
            url_pattern: URL pattern
            callback: Function that returns MockResponse
        """
        self.add_mock_response(method, url_pattern, callback)
    
    def _find_mock_response(self, method: str, url: str) -> Optional[MockResponse]:
        """
        Find a mock response for the given method and URL.
        
        Args:
            method: HTTP method
            url: Request URL
            
        Returns:
            MockResponse or None
        """
        # Try exact match first
        key = (method.upper(), url)
        if key in self._mock_responses:
            response = self._mock_responses[key]
            if callable(response):
                return response(method, url)
            return response
        
        # Try pattern matching (simple substring match)
        for (resp_method, pattern), response in self._mock_responses.items():
            if resp_method == method.upper() and pattern in url:
                if callable(response):
                    return response(method, url)
                return response
        
        # Default 404 response
        return MockResponse(
            json_data={"error": f"No mock response for {method} {url}"},
            status_code=404,
            reason="Not Found",
            ok=False
        )
    
    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> MockResponse:
        """
        Mock request method.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Request headers
            timeout: Request timeout
            **kwargs: Additional arguments
            
        Returns:
            MockResponse
        """
        # Record request
        request_info = {
            "method": method,
            "url": url,
            "params": params,
            "data": data,
            "json": json_data,
            "headers": headers,
            "timeout": timeout,
            "timestamp": datetime.now(),
            **kwargs
        }
        self.requests.append(request_info)
        self.request_count += 1
        
        # Update method-specific counters
        method_upper = method.upper()
        if method_upper == "GET":
            self.get_count += 1
        elif method_upper == "POST":
            self.post_count += 1
        elif method_upper == "PUT":
            self.put_count += 1
        elif method_upper == "DELETE":
            self.delete_count += 1
        
        # Find mock response
        response = self._find_mock_response(method, url)
        
        # Check for simulated errors based on URL
        if "simulate-connection-error" in url:
            raise ConnectionError("Simulated connection error")
        
        if "simulate-timeout" in url:
            raise Timeout("Simulated timeout")
        
        # Handle token endpoint specially
        if "auth/realms/opensky-network/protocol/openid-connect/token" in url:
            # Check for invalid credentials
            if data and data.get('client_id') == 'invalid':
                return MockResponse(
                    json_data={"error": "invalid_client"},
                    status_code=401,
                    reason="Unauthorized",
                    ok=False
                )
        
        return response
    
    def get(self, url, params=None, **kwargs):
        return self.request("GET", url, params=params, **kwargs)
    
    def post(self, url, data=None, json=None, **kwargs):
        return self.request("POST", url, data=data, json_data=json, **kwargs)
    
    def put(self, url, data=None, json=None, **kwargs):
        return self.request("PUT", url, data=data, json_data=json, **kwargs)
    
    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)
    
    def close(self):
        """Mock close method."""
        pass
    
    def reset(self):
        """Reset request history and counters."""
        self.requests.clear()
        self.request_count = 0
        self.get_count = 0
        self.post_count = 0
        self.put_count = 0
        self.delete_count = 0
    
    def get_last_request(self):
        """Get the last request made."""
        return self.requests[-1] if self.requests else None
    
    def get_requests_by_method(self, method: str) -> List[Dict]:
        """Get all requests for a specific method."""
        return [r for r in self.requests if r["method"].upper() == method.upper()]
    
    def assert_request_made(
        self,
        method: str,
        url_contains: str,
        min_count: int = 1,
        max_count: Optional[int] = None
    ):
        """
        Assert that a request was made.
        
        Args:
            method: HTTP method
            url_contains: String that should be in the URL
            min_count: Minimum number of requests expected
            max_count: Maximum number of requests expected
            
        Raises:
            AssertionError: If request count doesn't match expectations
        """
        matching_requests = [
            r for r in self.requests
            if r["method"].upper() == method.upper() and url_contains in r["url"]
        ]
        
        count = len(matching_requests)
        
        if count < min_count:
            raise AssertionError(
                f"Expected at least {min_count} {method} request(s) containing "
                f"'{url_contains}', but got {count}"
            )
        
        if max_count is not None and count > max_count:
            raise AssertionError(
                f"Expected at most {max_count} {method} request(s) containing "
                f"'{url_contains}', but got {count}"
            )


class MockAsyncSession:
    """
    Mock async HTTP session for testing async clients.
    """
    
    def __init__(self, base_url: str = "https://opensky-network.org/api"):
        self.base_url = base_url
        self.headers = {}
        self.requests = []
        self._mock_responses = {}
        self._setup_default_responses()
    
    def _setup_default_responses(self):
        """Setup default async mock responses."""
        # Similar to MockSession but returns async responses
        pass
    
    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> MockResponse:
        """
        Mock async request method.
        """
        request_info = {
            "method": method,
            "url": url,
            "params": params,
            "data": data,
            "json": json,
            "headers": headers,
            "timeout": timeout,
            "timestamp": datetime.now(),
            **kwargs
        }
        self.requests.append(request_info)
        
        # Find mock response (simplified)
        response = MockResponse(json_data=mock_states_response())
        
        # Simulate async delay
        import asyncio
        await asyncio.sleep(0.01)
        
        return response
    
    async def get(self, url, params=None, **kwargs):
        return await self.request("GET", url, params=params, **kwargs)
    
    async def post(self, url, data=None, json=None, **kwargs):
        return await self.request("POST", url, data=data, json=json, **kwargs)
    
    async def close(self):
        """Mock async close method."""
        pass


def create_mock_session_with_responses(
    custom_responses: Optional[Dict[tuple, MockResponse]] = None,
    base_url: str = "https://opensky-network.org/api"
) -> MockSession:
    """
    Create a mock session with custom responses.
    
    Args:
        custom_responses: Dictionary of (method, url_pattern) -> MockResponse
        base_url: Base URL for the API
        
    Returns:
        MockSession with custom responses
    """
    session = MockSession(base_url=base_url)
    
    if custom_responses:
        for (method, url_pattern), response in custom_responses.items():
            session.add_mock_response(method, url_pattern, response)
    
    return session


def create_mock_authenticated_client(
    client_id: str = "test_client_id",
    client_secret: str = "test_client_secret",
    mock_session: Optional[MockSession] = None
) -> OpenSkyClient:
    """
    Create a mock authenticated OpenSkyClient for testing.
    
    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        mock_session: Custom mock session (optional)
        
    Returns:
        OpenSkyClient with mocked dependencies
    """
    # Create mock token manager
    mock_token_manager = MockTokenManager(
        client_id=client_id,
        client_secret=client_secret,
        initial_token="mock_access_token_12345"
    )
    
    # Create or use provided mock session
    if mock_session is None:
        mock_session = MockSession()
    
    # Create client instance
    client = OpenSkyClient(
        client_id=client_id,
        client_secret=client_secret,
        enable_logging=False
    )
    
    # Replace actual dependencies with mocks
    client.token_manager = mock_token_manager
    client.session = mock_session
    
    # Mock the rate limiter to not actually wait
    mock_rate_limiter = Mock()
    mock_rate_limiter.wait_if_needed = Mock()
    client.rate_limiter = mock_rate_limiter
    
    return client


def create_mock_anonymous_client(
    mock_session: Optional[MockSession] = None
) -> OpenSkyClient:
    """
    Create a mock anonymous OpenSkyClient for testing.
    
    Args:
        mock_session: Custom mock session (optional)
        
    Returns:
        OpenSkyClient with mocked dependencies
    """
    # Create or use provided mock session
    if mock_session is None:
        mock_session = MockSession()
    
    # Create client instance
    client = OpenSkyClient(enable_logging=False)
    
    # Replace actual dependencies with mocks
    client.session = mock_session
    
    # Mock the rate limiter to not actually wait
    mock_rate_limiter = Mock()
    mock_rate_limiter.wait_if_needed = Mock()
    client.rate_limiter = mock_rate_limiter
    
    return client


def create_mock_client(
    authenticated: bool = True,
    custom_responses: Optional[Dict[tuple, MockResponse]] = None
) -> OpenSkyClient:
    """
    Create a mock OpenSkyClient with optional custom responses.
    
    Args:
        authenticated: Whether to create authenticated client
        custom_responses: Custom mock responses
        
    Returns:
        Mock OpenSkyClient
    """
    # Create mock session with custom responses
    mock_session = create_mock_session_with_responses(custom_responses)
    
    if authenticated:
        return create_mock_authenticated_client(mock_session=mock_session)
    else:
        return create_mock_anonymous_client(mock_session=mock_session)


# Convenience functions for common test scenarios
def create_mock_client_with_rate_limit() -> OpenSkyClient:
    """Create mock client that simulates rate limiting."""
    custom_responses = {
        ("GET", "/states/all"): mock_rate_limit_response()
    }
    return create_mock_client(custom_responses=custom_responses)


def create_mock_client_with_auth_error() -> OpenSkyClient:
    """Create mock client that simulates authentication errors."""
    custom_responses = {
        ("POST", "auth/realms/opensky-network/protocol/openid-connect/token"):
            mock_unauthorized_response()
    }
    return create_mock_client(custom_responses=custom_responses)


def create_mock_client_with_connection_error() -> OpenSkyClient:
    """Create mock client that simulates connection errors."""
    mock_session = MockSession()
    
    # Override request method to always raise ConnectionError
    def raise_connection_error(*args, **kwargs):
        raise ConnectionError("Simulated connection error")
    
    mock_session.request = raise_connection_error
    
    return create_mock_authenticated_client(mock_session=mock_session)


def create_mock_client_with_timeout() -> OpenSkyClient:
    """Create mock client that simulates timeouts."""
    mock_session = MockSession()
    
    # Override request method to always raise Timeout
    def raise_timeout(*args, **kwargs):
        raise Timeout("Simulated timeout")
    
    mock_session.request = raise_timeout
    
    return create_mock_authenticated_client(mock_session=mock_session)


def create_mock_client_with_parse_error() -> OpenSkyClient:
    """Create mock client that simulates JSON parsing errors."""
    custom_responses = {
        ("GET", "/states/all"): mock_parse_error_response()
    }
    return create_mock_client(custom_responses=custom_responses)


# Patch utilities for use in tests
def patch_opensky_client(monkeypatch, mock_client: OpenSkyClient):
    """
    Patch OpenSkyClient to return a mock instance.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_client: Mock OpenSkyClient instance
    """
    def mock_init(self, *args, **kwargs):
        # Copy attributes from mock client
        for attr, value in vars(mock_client).items():
            setattr(self, attr, value)
    
    monkeypatch.setattr(OpenSkyClient, "__init__", mock_init)


def patch_token_manager(monkeypatch, mock_token_manager: MockTokenManager):
    """
    Patch OAuth2TokenManager to return a mock instance.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_token_manager: Mock token manager instance
    """
    def mock_init(self, *args, **kwargs):
        for attr, value in vars(mock_token_manager).items():
            setattr(self, attr, value)
    
    monkeypatch.setattr(OAuth2TokenManager, "__init__", mock_init)