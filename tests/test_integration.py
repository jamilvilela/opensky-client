"""
Integration tests for OpenSky client.
These tests may make actual API calls (use with caution).
"""

import pytest
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestOpenSkyClientIntegration:
    """Integration tests for OpenSkyClient."""
    
    @pytest.fixture(autouse=True)
    def setup_integration_tests(self):
        """Setup for integration tests."""
        load_dotenv()
        
        # Skip integration tests if no credentials
        self.client_id = os.getenv('OPENSKY_CLIENT_ID')
        self.client_secret = os.getenv('OPENSKY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            pytest.skip("Skipping integration tests - OAuth2 credentials not found")
    
    def test_anonymous_states_integration(self):
        """Test anonymous states retrieval (makes actual API call)."""
        from opensky import OpenSkyClient
        
        client = OpenSkyClient(enable_logging=False)
        
        try:
            states = client.get_states()
            
            # Should get some states (if API is working)
            assert isinstance(states, list)
            
            if states:  # If we got data
                state = states[0]
                assert hasattr(state, 'icao24')
                assert hasattr(state, 'callsign')
                assert hasattr(state, 'latitude')
                assert hasattr(state, 'longitude')
        
        finally:
            client.close()
    
    def test_authenticated_states_integration(self):
        """Test authenticated states retrieval (makes actual API call)."""
        from opensky import OpenSkyClient
        
        client = OpenSkyClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            enable_logging=False
        )
        
        try:
            states = client.get_states()
            
            # Should get some states
            assert isinstance(states, list)
            
            # Test token info
            token_info = client.get_token_info()
            assert token_info is not None
            assert 'has_token' in token_info
            assert token_info['has_token'] is True
        
        finally:
            client.close()
    
    def test_airports_integration(self):
        """Test airports retrieval (makes actual API call)."""
        from opensky import OpenSkyClient
        
        client = OpenSkyClient(enable_logging=False)
        
        try:
            airports = client.get_airports(icao="EDDF")
            
            # Should get Frankfurt airport
            assert len(airports) == 1
            airport = airports[0]
            
            assert airport.icao == "EDDF"
            assert airport.iata == "FRA"
            assert airport.name == "Frankfurt am Main Airport"
            assert airport.country == "Germany"
        
        finally:
            client.close()
    
    @pytest.mark.slow
    def test_historical_flights_integration(self):
        """Test historical flights retrieval (makes actual API call)."""
        from opensky import OpenSkyClient
        
        client = OpenSkyClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            enable_logging=False
        )
        
        try:
            # Get flights from 1 hour ago to now
            end = datetime.now()
            begin = end - timedelta(hours=1)
            
            flights = client.get_flights(begin=begin, end=end)
            
            # Should get a list of flights
            assert isinstance(flights, list)
            
            if flights:  # If we got data
                flight = flights[0]
                assert hasattr(flight, 'icao24')
                assert hasattr(flight, 'first_seen')
                assert hasattr(flight, 'last_seen')
        
        finally:
            client.close()
    
    def test_health_check_integration(self):
        """Test health check endpoint (makes actual API call)."""
        from opensky import OpenSkyClient
        
        client = OpenSkyClient(enable_logging=False)
        
        try:
            health = client.health_check()
            
            # Should get health status
            assert isinstance(health, dict)
            assert 'status' in health
            assert health['status'] in ['ok', 'degraded', 'down']
        
        finally:
            client.close()