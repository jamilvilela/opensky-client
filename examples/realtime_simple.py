"""
Simple real-time tracking example with OAuth2.
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from opensky import OpenSkyClient

load_dotenv()


def simple_tracker(bbox, interval=30, max_aircraft=10):
    """Simple real-time tracker."""
    
    # Create client (anonymous or authenticated)
    client = OpenSkyClient(
        client_id=os.getenv('OPENSKY_CLIENT_ID'),
        client_secret=os.getenv('OPENSKY_CLIENT_SECRET')
    )
    
    print("client: ", os.getenv('OPENSKY_CLIENT_ID'))
    print(f"Tracking flights in bounding box: {bbox}")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            try:
                # Get current states
                states = client.get_states(bbox=bbox)
                
                # Filter and sort
                airborne = [s for s in states if not s.on_ground]
                airborne.sort(key=lambda x: x.altitude or 0, reverse=True)
                
                # Display
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{now}] {len(airborne)} airborne aircraft")
                print("-" * 70)
                
                for i, aircraft in enumerate(airborne[:max_aircraft]):
                    callsign = aircraft.callsign or "N/A"
                    alt_ft = aircraft.altitude_ft or 0
                    speed_kts = aircraft.velocity_kts or 0
                    
                    print(f"{i+1:2d}. {callsign:8s} | "
                          f"Alt: {alt_ft:6.0f} ft | "
                          f"Spd: {speed_kts:4.0f} kts | "
                          f"Pos: {aircraft.latitude:.3f}, {aircraft.longitude:.3f}")
                
                if len(airborne) > max_aircraft:
                    print(f"... and {len(airborne) - max_aircraft} more")
                
            except Exception as e:
                print(f"Error: {e}")
            
            # Wait for next update
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nTracking stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    # Example: Track flights over Germany
    germany_bbox = (47.0, 5.0, 55.0, 15.0)
    
    # Example: Track flights over US East Coast
    # us_east_bbox = (25.0, -85.0, 45.0, -65.0)
    
    simple_tracker(
        bbox=germany_bbox,
        interval=20,  # 20 seconds between updates
        max_aircraft=15
    )