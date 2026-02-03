"""
Real-time flight tracking example with OAuth2 authentication.
Tracks flights in a specified area and displays live aircraft data.
"""

import os
import time
from datetime import datetime
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from opensky import OpenSkyClient
from opensky.models import StateVector


class RealTimeTracker:
    """Real-time flight tracker with OAuth2 authentication."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        update_interval: int = 15,
        enable_logging: bool = True
    ):
        """
        Initialize real-time tracker.
        
        Args:
            client_id: OAuth2 client ID (optional for anonymous access)
            client_secret: OAuth2 client secret (optional)
            update_interval: Update interval in seconds
            enable_logging: Enable logging output
        """
        # Get credentials from environment if not provided
        if not client_id:
            client_id = os.getenv('OPENSKY_CLIENT_ID')
        if not client_secret:
            client_secret = os.getenv('OPENSKY_CLIENT_SECRET')
        
        # Initialize OpenSky client
        self.client = OpenSkyClient(
            client_id=client_id,
            client_secret=client_secret,
            enable_logging=enable_logging
        )
        
        self.update_interval = update_interval
        self.tracked_flights = {}
        self.total_updates = 0
        self.start_time = datetime.now()
        
        # Display mode
        self.display_modes = ['simple', 'detailed', 'summary']
        self.current_display_mode = 'simple'
        
        print(f"RealTimeTracker initialized (OAuth2: {bool(client_id and client_secret)})")
    
    def track_area(
        self,
        bbox: Tuple[float, float, float, float],
        max_flights: int = 20,
        duration_minutes: Optional[int] = None
    ):
        """
        Track flights in a bounding box.
        
        Args:
            bbox: Bounding box (lamin, lomin, lamax, lomax) in decimal degrees
            max_flights: Maximum number of flights to display
            duration_minutes: Duration to track in minutes (None = infinite)
        """
        print(f"\n{'='*60}")
        print("REAL-TIME FLIGHT TRACKER")
        print(f"{'='*60}")
        print(f"Tracking area: {bbox}")
        print(f"Update interval: {self.update_interval} seconds")
        print(f"Display mode: {self.current_display_mode}")
        print(f"Max flights displayed: {max_flights}")
        
        if duration_minutes:
            print(f"Duration: {duration_minutes} minutes")
        else:
            print("Duration: Continuous (press Ctrl+C to stop)")
        
        print(f"\n{'='*60}")
        print("Press 'm' to cycle display modes")
        print("Press 's' to show statistics")
        print("Press 'q' to quit")
        print(f"{'='*60}\n")
        
        try:
            start_time = datetime.now()
            update_count = 0
            
            while True:
                # Check for user input (non-blocking)
                self._check_user_input()
                
                # Update and display
                self._update_display(bbox, max_flights)
                update_count += 1
                
                # Check duration limit
                if duration_minutes:
                    elapsed = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed >= duration_minutes:
                        print(f"\nTracking completed ({duration_minutes} minutes elapsed)")
                        break
                
                # Wait for next update
                print(f"\nNext update in {self.update_interval} seconds...")
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n\nTracking interrupted by user")
        except Exception as e:
            print(f"\nError in tracking: {e}")
        finally:
            self._show_tracking_summary()
            self.client.close()
    
    def track_around_location(
        self,
        lat: float,
        lon: float,
        radius_km: float = 100,
        **kwargs
    ):
        """
        Track flights around a specific location.
        
        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Radius in kilometers
            **kwargs: Additional arguments passed to track_area
        """
        print(f"\nTracking flights within {radius_km}km of ({lat:.4f}, {lon:.4f})")
        
        # Calculate bounding box
        bbox = self._calculate_bounding_box(lat, lon, radius_km)
        
        # Start tracking
        self.track_area(bbox, **kwargs)
    
    def _calculate_bounding_box(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box around a point.
        
        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Radius in kilometers
            
        Returns:
            Tuple of (lamin, lomin, lamax, lomax)
        """
        # Earth's radius in km
        earth_radius = 6371.0
        
        # Convert radius to degrees (approximate)
        lat_delta = (radius_km / earth_radius) * (180 / 3.141592653589793)
        lon_delta = lat_delta / abs(3.141592653589793 / 180 * lat) if lat != 0 else lat_delta
        
        return (
            lat - lat_delta,
            lon - lon_delta,
            lat + lat_delta,
            lon + lon_delta
        )
    
    def _update_display(self, bbox: Tuple[float, float, float, float], max_flights: int):
        """Update and display flight information."""
        try:
            # Get current state vectors
            states = self.client.get_states(bbox=bbox)
            
            # Filter out states with no position
            valid_states = [s for s in states if s.latitude is not None and s.longitude is not None]
            
            # Sort by altitude (highest first)
            valid_states.sort(key=lambda x: x.altitude or 0, reverse=True)
            
            # Display based on current mode
            if self.current_display_mode == 'simple':
                self._display_simple(valid_states, max_flights)
            elif self.current_display_mode == 'detailed':
                self._display_detailed(valid_states, max_flights)
            elif self.current_display_mode == 'summary':
                self._display_summary(valid_states)
            
            # Update tracking statistics
            self._update_tracking_stats(valid_states)
            
        except Exception as e:
            print(f"\n⚠️  Error fetching data: {e}")
    
    def _display_simple(self, states: list[StateVector], max_flights: int):
        """Display simple flight information."""
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{current_time}] Tracking {len(states)} aircraft")
        print("-" * 80)
        
        for i, state in enumerate(states[:max_flights]):
            callsign = state.callsign or "N/A"
            altitude = f"{state.altitude_ft:.0f} ft" if state.altitude_ft else "N/A"
            speed = f"{state.velocity_kts:.0f} kts" if state.velocity_kts else "N/A"
            heading = f"{state.heading:.0f}°" if state.heading else "N/A"
            country = state.origin_country or "Unknown"
            
            print(f"{i+1:2d}. {callsign:8s} ({state.icao24}) | "
                  f"Alt: {altitude:7s} | "
                  f"Spd: {speed:6s} | "
                  f"Hdg: {heading:5s} | "
                  f"Country: {country:15s}")
    
    def _display_detailed(self, states: list[StateVector], max_flights: int):
        """Display detailed flight information."""
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{current_time}] Tracking {len(states)} aircraft")
        print("=" * 100)
        
        for i, state in enumerate(states[:max_flights]):
            callsign = state.callsign or "N/A"
            altitude = f"{state.altitude_ft:.0f} ft ({state.altitude:.0f} m)" if state.altitude else "N/A"
            speed = f"{state.velocity_kts:.0f} kts ({state.velocity:.0f} m/s)" if state.velocity else "N/A"
            vertical_rate = f"{state.vertical_rate_ftpm:+.0f} ft/min" if state.vertical_rate else "N/A"
            heading = f"{state.heading:.0f}°" if state.heading else "N/A"
            squawk = state.squawk or "N/A"
            country = state.origin_country or "Unknown"
            
            print(f"\nAircraft {i+1}: {callsign} ({state.icao24})")
            print(f"  Country:   {country}")
            print(f"  Position:  {state.latitude:.4f}°N, {state.longitude:.4f}°E")
            print(f"  Altitude:  {altitude}")
            print(f"  Speed:     {speed}")
            print(f"  Heading:   {heading}")
            print(f"  Vert Rate: {vertical_rate}")
            print(f"  Squawk:    {squawk}")
            print(f"  On Ground: {state.on_ground}")
        
        if len(states) > max_flights:
            print(f"\n... and {len(states) - max_flights} more aircraft")
    
    def _display_summary(self, states: list[StateVector]):
        """Display summary statistics."""
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Calculate statistics
        total = len(states)
        airborne = len([s for s in states if not s.on_ground])
        on_ground = len([s for s in states if s.on_ground])
        
        # Average altitude (excluding None values)
        altitudes = [s.altitude_ft for s in states if s.altitude_ft is not None]
        avg_alt = sum(altitudes) / len(altitudes) if altitudes else 0
        
        # Group by country
        countries = {}
        for state in states:
            country = state.origin_country or "Unknown"
            countries[country] = countries.get(country, 0) + 1
        
        # Most common country
        most_common = max(countries.items(), key=lambda x: x[1]) if countries else ("None", 0)
        
        print(f"\n[{current_time}] Summary - {total} aircraft in area")
        print("-" * 60)
        print(f"Airborne:    {airborne}")
        print(f"On Ground:   {on_ground}")
        print(f"Avg Altitude: {avg_alt:.0f} ft")
        print(f"Most Common Country: {most_common[0]} ({most_common[1]} aircraft)")
        
        # Top 5 countries
        if countries:
            print("\nTop Countries:")
            sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]
            for country, count in sorted_countries:
                print(f"  {country}: {count} aircraft")
    
    def _update_tracking_stats(self, states: list[StateVector]):
        """Update tracking statistics."""
        self.total_updates += 1
        
        for state in states:
            if state.icao24 not in self.tracked_flights:
                self.tracked_flights[state.icao24] = {
                    'first_seen': datetime.now(),
                    'callsign': state.callsign,
                    'country': state.origin_country,
                    'updates': 0,
                    'last_position': (state.latitude, state.longitude),
                    'max_altitude': state.altitude
                }
            
            # Update flight info
            flight_info = self.tracked_flights[state.icao24]
            flight_info['updates'] += 1
            flight_info['last_seen'] = datetime.now()
            flight_info['last_position'] = (state.latitude, state.longitude)
            
            # Update max altitude
            if state.altitude and (flight_info['max_altitude'] is None or state.altitude > flight_info['max_altitude']):
                flight_info['max_altitude'] = state.altitude
    
    def _check_user_input(self):
        """Check for user input (non-blocking)."""
        try:
            import select
            import sys
            
            # Check if input is available (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                
                if key == 'm':
                    # Cycle display mode
                    current_index = self.display_modes.index(self.current_display_mode)
                    next_index = (current_index + 1) % len(self.display_modes)
                    self.current_display_mode = self.display_modes[next_index]
                    print(f"\nDisplay mode changed to: {self.current_display_mode}")
                
                elif key == 's':
                    # Show statistics
                    self._show_current_stats()
                
                elif key == 'q':
                    # Quit
                    print("\nQuitting...")
                    self._show_tracking_summary()
                    self.client.close()
                    exit(0)
        
        except Exception:
            # Input checking not available on all platforms
            pass
    
    def _show_current_stats(self):
        """Show current tracking statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        
        print(f"\n{'='*60}")
        print("CURRENT TRACKING STATISTICS")
        print(f"{'='*60}")
        print(f"Tracking duration: {elapsed:.1f} minutes")
        print(f"Total updates: {self.total_updates}")
        print(f"Unique aircraft tracked: {len(self.tracked_flights)}")
        
        if self.tracked_flights:
            # Find aircraft with most updates
            most_tracked = max(self.tracked_flights.items(), key=lambda x: x[1]['updates'])
            print(f"\nMost tracked aircraft:")
            print(f"  ICAO24: {most_tracked[0]}")
            print(f"  Callsign: {most_tracked[1]['callsign'] or 'N/A'}")
            print(f"  Updates: {most_tracked[1]['updates']}")
            print(f"  First seen: {most_tracked[1]['first_seen'].strftime('%H:%M:%S')}")
        
        print(f"{'='*60}")
    
    def _show_tracking_summary(self):
        """Show final tracking summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        
        print(f"\n{'='*80}")
        print("FINAL TRACKING SUMMARY")
        print(f"{'='*80}")
        print(f"Total tracking time: {elapsed:.1f} minutes")
        print(f"Total updates performed: {self.total_updates}")
        print(f"Unique aircraft tracked: {len(self.tracked_flights)}")
        
        if self.tracked_flights:
            # Calculate statistics
            total_updates_all = sum(info['updates'] for info in self.tracked_flights.values())
            avg_updates_per_aircraft = total_updates_all / len(self.tracked_flights)
            
            # Find most tracked aircraft
            most_tracked = max(self.tracked_flights.items(), key=lambda x: x[1]['updates'])
            
            print(f"\nStatistics:")
            print(f"  Average updates per aircraft: {avg_updates_per_aircraft:.1f}")
            print(f"  Most tracked aircraft: {most_tracked[0]} "
                  f"({most_tracked[1]['updates']} updates)")
            
            # Show top 10 most tracked aircraft
            print(f"\nTop 10 Most Tracked Aircraft:")
            sorted_flights = sorted(
                self.tracked_flights.items(),
                key=lambda x: x[1]['updates'],
                reverse=True
            )[:10]
            
            for i, (icao24, info) in enumerate(sorted_flights, 1):
                callsign = info['callsign'] or 'N/A'
                duration = (info['last_seen'] - info['first_seen']).total_seconds() / 60
                print(f"  {i:2d}. {icao24} - {callsign:8s} "
                      f"({info['updates']:3d} updates, {duration:.1f} min)")
        
        print(f"{'='*80}")


def main():
    """Main function to run real-time tracking examples."""
    # Load environment variables
    load_dotenv()
    
    # Get OAuth2 credentials
    client_id = os.getenv('OPENSKY_CLIENT_ID')
    client_secret = os.getenv('OPENSKY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("⚠️  Warning: OAuth2 credentials not found in environment.")
        print("Running in anonymous mode (limited functionality).")
        print("Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in .env file for full access.")
        print()
    
    # Create tracker
    tracker = RealTimeTracker(
        client_id=client_id,
        client_secret=client_secret,
        update_interval=20,  # Update every 20 seconds
        enable_logging=True
    )
    
    # Example 1: Track around a specific location
    print("\nExample 1: Tracking flights around Frankfurt Airport")
    print("-" * 60)
    
    # Frankfurt Airport coordinates
    frankfurt_lat = 50.0333
    frankfurt_lon = 8.5706
    
    # Track for 2 minutes (for demonstration)
    tracker.track_around_location(
        lat=frankfurt_lat,
        lon=frankfurt_lon,
        radius_km=150,  # 150km radius
        max_flights=15,
        duration_minutes=2  # Demo duration
    )
    
    # Example 2: Track in a specific bounding box
    print("\n\nExample 2: Tracking flights in Germany bounding box")
    print("-" * 60)
    
    # Germany bounding box
    germany_bbox = (47.0, 5.0, 55.0, 15.0)
    
    # Change display mode to detailed
    tracker.current_display_mode = 'detailed'
    
    # Track for 2 minutes
    tracker.track_area(
        bbox=germany_bbox,
        max_flights=10,
        duration_minutes=2
    )
    
    # Example 3: Continuous tracking (uncomment to use)
    """
    print("\n\nExample 3: Continuous tracking around London")
    print("-" * 60)
    
    # London coordinates
    london_lat = 51.5074
    london_lon = -0.1278
    
    tracker.current_display_mode = 'summary'
    tracker.track_around_location(
        lat=london_lat,
        lon=london_lon,
        radius_km=200,
        max_flights=20
        # No duration limit = continuous tracking
    )
    """


def quick_start():
    """Quick start function for immediate use."""
    load_dotenv()
    
    print("OpenSky Real-Time Flight Tracker")
    print("=" * 50)
    
    # Ask for display mode
    print("\nSelect display mode:")
    print("1. Simple (default)")
    print("2. Detailed")
    print("3. Summary")
    
    mode_choice = input("Enter choice (1-3): ").strip()
    modes = ['simple', 'detailed', 'summary']
    display_mode = modes[int(mode_choice) - 1] if mode_choice in ['1', '2', '3'] else 'simple'
    
    # Ask for area
    print("\nSelect tracking area:")
    print("1. Europe")
    print("2. North America")
    print("3. Custom bounding box")
    
    area_choice = input("Enter choice (1-3): ").strip()
    
    if area_choice == '1':
        bbox = (35.0, -10.0, 60.0, 40.0)  # Europe
        area_name = "Europe"
    elif area_choice == '2':
        bbox = (25.0, -125.0, 50.0, -65.0)  # North America
        area_name = "North America"
    elif area_choice == '3':
        print("\nEnter bounding box coordinates:")
        lamin = float(input("Minimum latitude: "))
        lomin = float(input("Minimum longitude: "))
        lamax = float(input("Maximum latitude: "))
        lomax = float(input("Maximum longitude: "))
        bbox = (lamin, lomin, lamax, lomax)
        area_name = "Custom Area"
    else:
        bbox = (35.0, -10.0, 60.0, 40.0)  # Default to Europe
        area_name = "Europe"
    
    # Ask for duration
    print("\nTracking duration:")
    print("0. Continuous (until Ctrl+C)")
    print("1. 5 minutes")
    print("2. 15 minutes")
    print("3. 30 minutes")
    print("4. 60 minutes")
    
    duration_choice = input("Enter choice (0-4): ").strip()
    durations = {0: None, 1: 5, 2: 15, 3: 30, 4: 60}
    duration = durations.get(int(duration_choice) if duration_choice.isdigit() else 0, None)
    
    # Create and start tracker
    tracker = RealTimeTracker(
        update_interval=15,
        enable_logging=True
    )
    tracker.current_display_mode = display_mode
    
    print(f"\nStarting tracker for {area_name}...")
    print(f"Display mode: {display_mode}")
    print(f"Update interval: 15 seconds")
    if duration:
        print(f"Duration: {duration} minutes")
    else:
        print("Duration: Continuous")
    
    input("\nPress Enter to start tracking...")
    
    tracker.track_area(
        bbox=bbox,
        max_flights=20,
        duration_minutes=duration
    )


if __name__ == "__main__":
    # Uncomment one of the following:
    
    # Run the full example
    # main()
    
    # Or run the quick start interactive version
    quick_start()