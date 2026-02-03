# tests/test_with_mocks.py
import pytest
from unittest.mock import patch
from mocks import (
    create_mock_authenticated_client,
    create_mock_anonymous_client,
    MockSession,
    mock_states_response
)

def test_get_states_with_mock():
    """Test get_states using mock client."""
    # Create mock client
    client = create_mock_authenticated_client()
    
    # Get states
    states = client.get_states()
    
    # Verify
    assert len(states) == 5  # Default mock response has 5 states
    assert states[0].icao24 == "abc1230"
    assert states[0].callsign == "TEST0100"


def test_get_states_with_custom_mock():
    """Test get_states with custom mock responses."""
    from mocks import MockResponse
    
    # Create custom mock session
    mock_session = MockSession()
    mock_session.add_mock_response(
        "GET",
        "https://opensky-network.org/api/states/all",
        MockResponse(json_data={
            "time": 1609459200,
            "states": [
                ["test123", "FLIGHT01", "Germany", 1609459200, 1609459200,
                 10.0, 20.0, 10000.0, False, 250.0, 180.0, 5.0, [], 
                 9500.0, "7700", False, 0]
            ]
        })
    )
    
    # Create client with custom session
    client = create_mock_authenticated_client(mock_session=mock_session)
    
    # Get states
    states = client.get_states()
    
    # Verify custom response
    assert len(states) == 1
    assert states[0].icao24 == "test123"
    assert states[0].callsign == "FLIGHT01"


def test_rate_limit_error():
    """Test handling of rate limit errors."""
    from mocks import create_mock_client_with_rate_limit
    
    client = create_mock_client_with_rate_limit()
    
    with pytest.raises(Exception) as exc_info:
        client.get_states()
    
    # Should get rate limit error
    assert "Rate limit" in str(exc_info.value)


def test_request_history():
    """Test that requests are recorded in history."""
    client = create_mock_authenticated_client()
    
    # Make multiple requests
    client.get_states()
    client.get_airports()
    client.health_check()
    
    # Check request history
    assert client.session.request_count == 3
    assert client.session.get_count == 3
    
    # Check specific request was made
    client.session.assert_request_made("GET", "/states/all", min_count=1)
    client.session.assert_request_made("GET", "/airports", min_count=1)
    client.session.assert_request_made("GET", "/health", min_count=1)


@patch('opensky.client.requests.Session')
def test_with_patch(mock_session_class):
    """Test using unittest.mock.patch."""
    from opensky import OpenSkyClient
    
    # Create mock session
    mock_session = MockSession()
    mock_session_class.return_value = mock_session
    
    # Create client (will use mocked session)
    client = OpenSkyClient(
        client_id="test_id",
        client_secret="test_secret",
        enable_logging=False
    )
    
    # Get states
    states = client.get_states()
    
    # Verify
    assert len(states) == 5
    assert mock_session.request_count == 1