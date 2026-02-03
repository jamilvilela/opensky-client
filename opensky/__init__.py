"""
OpenSky Python Client
A Python client library for the OpenSky Network API with OAuth2 authentication.
"""

from opensky.client import OpenSkyClient
from opensky.auth import OAuth2TokenManager
from opensky.models import (
    StateVector,
    FlightTrack,
    Airport,
    Flight,
    Arrival,
    Departure
)
from opensky.exceptions import (
    OpenSkyError,
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError,
    TokenExpiredError
)

__version__ = "2.0.0"
__author__ = "Jamil Miranda Vilela"
__email__ = "jamilvilela@gmail.com"

__all__ = [
    "OpenSkyClient",
    "OAuth2TokenManager",
    "StateVector",
    "FlightTrack",
    "Airport",
    "Flight",
    "Arrival",
    "Departure",
    "OpenSkyError",
    "AuthenticationError",
    "APIError",
    "RateLimitError",
    "ValidationError",
    "TokenExpiredError",
]