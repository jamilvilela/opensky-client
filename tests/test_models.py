"""
Tests for data models.
"""

import pytest
from datetime import datetime
from opensky.models import (
    StateVector,
    FlightTrack,
    FlightTrackPoint,
    Airport,
    Flight,
    Arrival,
    Departure,
    AircraftCategory,
    PositionSource
)


class TestStateVector:
    """Test StateVector model."""
    
    def test_from_api_response(self):
        """Test creating StateVector from API response."""
        api_data = [
            "abc123",           # 0: icao24
            "TEST01 ",          # 1: callsign (with space)
            "United States",    # 2: origin_country
            1609459200,         # 3: time_position
            1609459200,         # 4: last_contact
            10.0,              # 5: longitude
            20.0,              # 6: latitude
            10000.0,           # 7: altitude
            False,             # 8: on_ground
            250.0,             # 9: velocity
            180.0,             # 10: heading
            5.0,               # 11: vertical_rate
            [1, 2, 3],         # 12: sensors
            9500.0,            # 13: geo_altitude
            "7700",            # 14: squawk
            False,             # 15: spi
            0                  # 16: position_source
        ]
        
        state = StateVector.from_api_response(api_data)
        
        assert state.icao24 == "abc123"
        assert state.callsign == "TEST01"  # Space should be trimmed
        assert state.origin_country == "United States"
        assert isinstance(state.time_position, datetime)
        assert state.longitude == 10.0
        assert state.latitude == 20.0
        assert state.altitude == 10000.0
        assert state.on_ground is False
        assert state.velocity == 250.0
        assert state.heading == 180.0
        assert state.vertical_rate == 5.0
        assert state.sensors == [1, 2, 3]
        assert state.geo_altitude == 9500.0
        assert state.squawk == "7700"
        assert state.spi is False
        assert state.position_source == PositionSource.ADSB
    
    def test_from_api_response_with_none_values(self):
        """Test creating StateVector with None values."""
        api_data = [
            "abc123",           # icao24
            None,               # callsign
            None,               # origin_country
            None,               # time_position
            None,               # last_contact
            None,               # longitude
            None,               # latitude
            None,               # altitude
            None,               # on_ground
            None,               # velocity
            None,               # heading
            None,               # vertical_rate
            None,               # sensors
            None,               # geo_altitude
            None,               # squawk
            None,               # spi
            None                # position_source
        ]
        
        state = StateVector.from_api_response(api_data)
        
        assert state.icao24 == "abc123"
        assert state.callsign is None
        assert state.longitude is None
        assert state.latitude is None
        assert state.altitude is None
    
    def test_property_converters(self):
        """Test property converters (feet, knots, etc.)."""
        state = StateVector(
            icao24="abc123",
            altitude=3048.0,  # 10000 feet in meters
            velocity=51.444,  # 100 knots in m/s
            vertical_rate=2.54  # 500 ft/min in m/s
        )
        
        # Test altitude conversion
        assert state.altitude_ft == pytest.approx(10000.0, rel=0.01)
        
        # Test velocity conversion
        assert state.velocity_kts == pytest.approx(100.0, rel=0.01)
        
        # Test vertical rate conversion
        assert state.vertical_rate_ftpm == pytest.approx(500.0, rel=0.01)
    
    def test_property_converters_with_none(self):
        """Test property converters with None values."""
        state = StateVector(icao24="abc123")
        
        assert state.altitude_ft is None
        assert state.velocity_kts is None
        assert state.vertical_rate_ftpm is None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = StateVector(
            icao24="abc123",
            callsign="TEST01",
            origin_country="United States",
            time_position=datetime(2023, 1, 1, 12, 0, 0),
            position_source=PositionSource.ADSB
        )
        
        result = state.to_dict()
        
        assert result["icao24"] == "abc123"
        assert result["callsign"] == "TEST01"
        assert result["origin_country"] == "United States"
        assert result["time_position"] == "2023-01-01T12:00:00"
        assert result["position_source"] == 0  # ADSB enum value


class TestFlightTrackPoint:
    """Test FlightTrackPoint model."""
    
    def test_initialization(self):
        """Test FlightTrackPoint initialization."""
        point = FlightTrackPoint(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            latitude=50.0,
            longitude=8.0,
            altitude=10000.0,
            heading=180.0,
            on_ground=False
        )
        
        assert point.latitude == 50.0
        assert point.longitude == 8.0
        assert point.altitude == 10000.0
        assert point.altitude_ft == pytest.approx(32808.4, rel=0.01)
        assert point.heading == 180.0
        assert point.on_ground is False


class TestFlightTrack:
    """Test FlightTrack model."""
    
    def test_initialization(self):
        """Test FlightTrack initialization."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 13, 30, 0)
        
        track = FlightTrack(
            icao24="abc123",
            callsign="TEST01",
            start_time=start,
            end_time=end,
            path=[
                FlightTrackPoint(
                    timestamp=start,
                    latitude=50.0,
                    longitude=8.0,
                    altitude=10000.0
                ),
                FlightTrackPoint(
                    timestamp=end,
                    latitude=51.0,
                    longitude=9.0,
                    altitude=11000.0
                )
            ]
        )
        
        assert track.icao24 == "abc123"
        assert track.callsign == "TEST01"
        assert track.duration_seconds == 5400.0  # 1.5 hours
        assert track.duration_hours == 1.5
        assert len(track.path) == 2
    
    def test_to_geojson(self):
        """Test GeoJSON conversion."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 12, 30, 0)
        
        track = FlightTrack(
            icao24="abc123",
            callsign="TEST01",
            start_time=start,
            end_time=end,
            path=[
                FlightTrackPoint(
                    timestamp=start,
                    latitude=50.0,
                    longitude=8.0,
                    altitude=10000.0
                ),
                FlightTrackPoint(
                    timestamp=end,
                    latitude=51.0,
                    longitude=9.0,
                    altitude=11000.0
                )
            ]
        )
        
        geojson = track.to_geojson()
        
        assert geojson["type"] == "Feature"
        assert geojson["properties"]["icao24"] == "abc123"
        assert geojson["properties"]["callsign"] == "TEST01"
        assert geojson["geometry"]["type"] == "LineString"
        assert len(geojson["geometry"]["coordinates"]) == 2
        assert geojson["geometry"]["coordinates"][0] == [8.0, 50.0, 10000.0]
        assert geojson["geometry"]["coordinates"][1] == [9.0, 51.0, 11000.0]


class TestAirport:
    """Test Airport model."""
    
    def test_initialization(self):
        """Test Airport initialization."""
        airport = Airport(
            icao="EDDF",
            iata="FRA",
            name="Frankfurt Airport",
            city="Frankfurt",
            country="Germany",
            latitude=50.0333,
            longitude=8.5706,
            altitude=111.0
        )
        
        assert airport.icao == "EDDF"
        assert airport.iata == "FRA"
        assert airport.name == "Frankfurt Airport"
        assert airport.city == "Frankfurt"
        assert airport.country == "Germany"
        assert airport.latitude == 50.0333
        assert airport.longitude == 8.5706
        assert airport.altitude == 111.0
        assert airport.altitude_ft == pytest.approx(364.17, rel=0.01)
    
    def test_altitude_conversion_none(self):
        """Test altitude conversion with None value."""
        airport = Airport(icao="EDDF")
        assert airport.altitude_ft is None


class TestFlight:
    """Test Flight model."""
    
    def test_initialization(self):
        """Test Flight initialization."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 14, 0, 0)
        
        flight = Flight(
            icao24="abc123",
            first_seen=start,
            last_seen=end,
            callsign="TEST01",
            departure_airport="EDDF",
            arrival_airport="EDDM"
        )
        
        assert flight.icao24 == "abc123"
        assert flight.callsign == "TEST01"
        assert flight.departure_airport == "EDDF"
        assert flight.arrival_airport == "EDDM"
        assert flight.duration_seconds == 7200.0  # 2 hours


class TestArrival:
    """Test Arrival model."""
    
    def test_initialization(self):
        """Test Arrival initialization."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 14, 0, 0)
        
        arrival = Arrival(
            icao24="abc123",
            first_seen=start,
            arrival_airport="EDDF",
            last_seen=end,
            callsign="TEST01",
            departure_airport="EDDM"
        )
        
        assert arrival.icao24 == "abc123"
        assert arrival.arrival_airport == "EDDF"
        assert arrival.departure_airport == "EDDM"
        assert arrival.callsign == "TEST01"


class TestDeparture:
    """Test Departure model."""
    
    def test_initialization(self):
        """Test Departure initialization."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 14, 0, 0)
        
        departure = Departure(
            icao24="abc123",
            first_seen=start,
            departure_airport="EDDF",
            last_seen=end,
            callsign="TEST01",
            arrival_airport="EDDM"
        )
        
        assert departure.icao24 == "abc123"
        assert departure.departure_airport == "EDDF"
        assert departure.arrival_airport == "EDDM"
        assert departure.callsign == "TEST01"


class TestEnums:
    """Test enum classes."""
    
    def test_aircraft_category_enum(self):
        """Test AircraftCategory enum."""
        assert AircraftCategory.HEAVY.value == 6
        assert AircraftCategory.UAV.value == 14
        assert len(list(AircraftCategory)) == 21
    
    def test_position_source_enum(self):
        """Test PositionSource enum."""
        assert PositionSource.ADSB.value == 0
        assert PositionSource.MLAT.value == 2
        assert PositionSource.UNKNOWN.value == 4