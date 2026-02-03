"""Basic example of OpenSky client with OAuth2 authentication."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from opensky import OpenSkyClient


def main():
    """Demonstrate OAuth2 authentication and basic API usage."""
    
    # Get OAuth2 credentials from environment
    client_id = os.getenv('OPENSKY_CLIENT_ID')
    client_secret = os.getenv('OPENSKY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("ERROR: OAuth2 credentials not found in environment variables.")
        print("Please set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET.")
        return
    
    # Create authenticated client
    print("Creating OpenSky client with OAuth2 authentication...")
    client = OpenSkyClient(
        client_id=client_id,
        client_secret=client_secret,
        enable_logging=True
    )
    
    try:
        # Display token information
        token_info = client.get_token_info()
        print(f"\nOAuth2 Token Information:")
        print(f"  Has token: {token_info['has_token']}")
        print(f"  Expires at: {token_info['expires_at']}")
        print(f"  Seconds until expiry: {token_info['seconds_until_expiry']:.0f}")
        
        # Example 1: Get current state vectors
        print("\n1. Getting current state vectors...")
        states = client.get_states()
        print(f"   Retrieved {len(states)} aircraft")
        
        if states:
            for i, state in enumerate(states[:3]):
                print(f"   Aircraft {i+1}: {state.callsign or 'N/A'} "
                      f"({state.icao24}) at {state.altitude_ft:.0f} ft")
        
        # Example 2: Get historical flights (requires OAuth2)
        print("\n2. Getting historical flights (last hour)...")
        end = datetime.now()
        begin = end - timedelta(hours=1)
        
        flights = client.get_flights(begin=begin, end=end)
        print(f"   Retrieved {len(flights)} flights")
        
        if flights:
            for i, flight in enumerate(flights[:3]):
                print(f"   Flight {i+1}: {flight.callsign or 'N/A'} "
                      f"from {flight.departure_airport or 'N/A'} "
                      f"to {flight.arrival_airport or 'N/A'}")
        
        # Example 3: Get airports
        print("\n3. Getting airport information...")
        airports = client.get_airports(icao="EDDF")
        if airports:
            frankfurt = airports[0]
            print(f"   {frankfurt.name} ({frankfurt.icao}): "
                  f"{frankfurt.city}, {frankfurt.country}")
        
        # Example 4: Get states in bounding box
        print("\n4. Getting states in Germany bounding box...")
        bbox = (47.0, 5.0, 55.0, 15.0)  # Germany
        states_de = client.get_states(bbox=bbox)
        print(f"   {len(states_de)} aircraft in Germany")
        
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        client.close()
        print("\nClient closed.")


if __name__ == "__main__":
    main()