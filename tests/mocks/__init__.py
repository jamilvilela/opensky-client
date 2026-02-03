"""
Mock modules for OpenSky client tests.
Provides mock responses and sessions for testing OpenSky API client.
"""

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
    mock_unauthorized_response
)

from .mock_session import (
    MockSession,
    MockTokenManager,
    create_mock_client,
    create_mock_session_with_responses,
    create_mock_authenticated_client,
    create_mock_anonymous_client
)

__all__ = [
    # Responses
    "MockResponse",
    "mock_token_response",
    "mock_states_response",
    "mock_flights_response",
    "mock_track_response",
    "mock_airport_response",
    "mock_airports_all_response",
    "mock_aircraft_response",
    "mock_health_response",
    "mock_error_response",
    "mock_rate_limit_response",
    "mock_unauthorized_response",
    
    # Sessions
    "MockSession",
    "MockTokenManager",
    "create_mock_client",
    "create_mock_session_with_responses",
    "create_mock_authenticated_client",
    "create_mock_anonymous_client",
]