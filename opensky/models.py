"""Data models for OpenSky API responses."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AircraftCategory(Enum):
    """Aircraft categories."""
    NO_INFO = 0
    NO_CATEGORY = 1
    LIGHT = 2
    SMALL = 3
    LARGE = 4
    HIGH_VORTEX_LARGE = 5
    HEAVY = 6
    HIGH_PERFORMANCE = 7
    ROTORCRAFT = 8
    GLIDER = 9
    LIGHTER_THAN_AIR = 10
    PARACHUTIST = 11
    ULTRALIGHT = 12
    RESERVED = 13
    UAV = 14
    SPACE = 15
    SURFACE_EMERGENCY = 16
    SURFACE_SERVICE = 17
    POINT_OBSTACLE = 18
    CLUSTER_OBSTACLE = 19
    LINE_OBSTACLE = 20


class PositionSource(Enum):
    """Position source types."""
    ADSB = 0
    ASTERIX = 1
    MLAT = 2
    FLARM = 3
    UNKNOWN = 4


@dataclass
class StateVector:
    """Represents a state vector from OpenSky."""
    
    icao24: str
    callsign: Optional[str] = None
    origin_country: Optional[str] = None
    time_position: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    altitude: Optional[float] = None  # in meters
    on_ground: Optional[bool] = None
    velocity: Optional[float] = None  # in m/s
    heading: Optional[float] = None  # in degrees
    vertical_rate: Optional[float] = None  # in m/s
    sensors: Optional[List[int]] = None
    geo_altitude: Optional[float] = None  # in meters
    squawk: Optional[str] = None
    spi: Optional[bool] = None  # Special purpose indicator
    position_source: Optional[PositionSource] = None
    
    @classmethod
    def from_api_response(cls, data: List[Any]) -> 'StateVector':
        """Create StateVector from API response array."""
        # OpenSky API returns state vectors as arrays
        # See: https://openskynetwork.github.io/opensky-api/rest.html#response
        return cls(
            icao24=str(data[0]) if data[0] is not None else None,
            callsign=str(data[1]).strip() if data[1] is not None else None,
            origin_country=str(data[2]) if data[2] is not None else None,
            time_position=datetime.fromtimestamp(data[3]) if data[3] else None,
            last_contact=datetime.fromtimestamp(data[4]) if data[4] else None,
            longitude=float(data[5]) if data[5] is not None else None,
            latitude=float(data[6]) if data[6] is not None else None,
            altitude=float(data[7]) if data[7] is not None else None,
            on_ground=bool(data[8]) if data[8] is not None else None,
            velocity=float(data[9]) if data[9] is not None else None,
            heading=float(data[10]) if data[10] is not None else None,
            vertical_rate=float(data[11]) if data[11] is not None else None,
            sensors=[int(s) for s in data[12]] if data[12] else None,
            geo_altitude=float(data[13]) if data[13] is not None else None,
            squawk=str(data[14]) if data[14] is not None else None,
            spi=bool(data[15]) if data[15] is not None else None,
            position_source=PositionSource(data[16]) if data[16] is not None else None
        )
    
    @property
    def altitude_ft(self) -> Optional[float]:
        """Get altitude in feet."""
        if self.altitude is not None:
            return self.altitude * 3.28084
        return None
    
    @property
    def velocity_kts(self) -> Optional[float]:
        """Get velocity in knots."""
        if self.velocity is not None:
            return self.velocity * 1.94384
        return None
    
    @property
    def vertical_rate_ftpm(self) -> Optional[float]:
        """Get vertical rate in feet per minute."""
        if self.vertical_rate is not None:
            return self.vertical_rate * 196.85
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, PositionSource):
                value = value.value
            result[field] = value
        return result


@dataclass
class FlightTrackPoint:
    """A single point in a flight track."""
    
    timestamp: datetime
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    heading: Optional[float] = None
    on_ground: Optional[bool] = None
    
    @property
    def altitude_ft(self) -> Optional[float]:
        """Get altitude in feet."""
        if self.altitude is not None:
            return self.altitude * 3.28084
        return None


@dataclass
class FlightTrack:
    """Represents a flight track from OpenSky."""
    
    icao24: str
    callsign: str
    start_time: datetime
    end_time: datetime
    path: List[FlightTrackPoint] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Get flight duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def duration_hours(self) -> float:
        """Get flight duration in hours."""
        return self.duration_seconds / 3600
    
    def to_geojson(self) -> Dict[str, Any]:
        """Convert flight track to GeoJSON LineString."""
        coordinates = []
        for point in self.path:
            coords = [point.longitude, point.latitude]
            if point.altitude is not None:
                coords.append(point.altitude)
            coordinates.append(coords)
        
        return {
            "type": "Feature",
            "properties": {
                "icao24": self.icao24,
                "callsign": self.callsign,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": self.duration_seconds
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            }
        }


@dataclass
class Airport:
    """Represents an airport."""
    
    icao: str
    iata: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None  # in meters
    
    @property
    def altitude_ft(self) -> Optional[float]:
        """Get altitude in feet."""
        if self.altitude is not None:
            return self.altitude * 3.28084
        return None


@dataclass
class Flight:
    """Represents a flight."""
    
    icao24: str
    first_seen: datetime
    last_seen: datetime
    callsign: Optional[str] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        """Get flight duration in seconds."""
        return (self.last_seen - self.first_seen).total_seconds()


@dataclass
class Arrival:
    """Represents an arrival at an airport."""
    
    icao24: str
    first_seen: datetime
    arrival_airport: str
    last_seen: datetime
    callsign: Optional[str] = None
    departure_airport: Optional[str] = None


@dataclass
class Departure:
    """Represents a departure from an airport."""
    
    icao24: str
    first_seen: datetime
    departure_airport: str
    last_seen: datetime
    callsign: Optional[str] = None
    arrival_airport: Optional[str] = None