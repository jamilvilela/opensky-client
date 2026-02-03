"""Main client class for OpenSky API with OAuth2 authentication."""

import requests
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple
from urllib.parse import urljoin

from opensky.auth import OAuth2TokenManager
from opensky.models import (
    StateVector,
    FlightTrack,
    Flight,
    Arrival,
    Departure,
    Airport
)
from opensky.exceptions import (
    OpenSkyError,
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError
)
from opensky.utils import (
    parse_timestamp,
    to_unix_timestamp,
    validate_icao24,
    validate_callsign,
    calculate_bounding_box,
    RateLimiter,
    setup_logging
)
import logging


class OpenSkyClient:
    """Client for OpenSky Network API with OAuth2 authentication.
    
    Documentation: https://openskynetwork.github.io/opensky-api/rest.html
    """
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = None,
        timeout: int = 30,
        rate_limit: float = 10.0,
        enable_logging: bool = True
    ):
        """
        Initialize OpenSky client with OAuth2 authentication.
        
        Args:
            client_id: OAuth2 client ID (optional, for authenticated access)
            client_secret: OAuth2 client secret (optional)
            base_url: Base API URL (defaults to official API)
            timeout: Request timeout in seconds
            rate_limit: Maximum API calls per second
            enable_logging: Enable logging
            
        Note:
            If client_id and client_secret are not provided, the client will
            operate in anonymous mode with limited access.
        """
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit)
        
        # Setup logging
        if enable_logging:
            setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # OAuth2 token manager
        self.token_manager: Optional[OAuth2TokenManager] = None
        if client_id and client_secret:
            self.token_manager = OAuth2TokenManager(
                client_id=client_id,
                client_secret=client_secret,
                timeout=timeout
            )
            self.logger.info("OAuth2 authentication enabled")
        else:
            self.logger.warning("No OAuth2 credentials provided - operating in anonymous mode")
        
        # Session for API requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OpenSkyPythonClient/2.0.0',
            'Accept': 'application/json',
        })
        
        self.logger.info("OpenSky client initialized")
    
    def _get_auth_header(self) -> Dict[str, str]:
        """
        Get authentication header for API requests.
        
        Returns:
            Dictionary with Authorization header if authenticated,
            empty dict for anonymous access.
            
        Raises:
            AuthenticationError: If token acquisition fails
        """
        if self.token_manager:
            try:
                token = self.token_manager.get_token()
                return {'Authorization': f'Bearer {token}'}
            except AuthenticationError as e:
                self.logger.error(f"Failed to get OAuth2 token: {e}")
                raise
        return {}
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retries: int = 3,
        backoff_factor: float = 0.5
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OpenSky API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            retries: Number of retries on failure
            backoff_factor: Backoff factor for retries
            
        Returns:
            API response as dictionary
            
        Raises:
            AuthenticationError: If authentication fails
            APIError: If API returns an error
            RateLimitError: If rate limit is exceeded
        """
        url = urljoin(self.base_url, endpoint)
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        for attempt in range(retries):
            try:
                # Get authentication header
                headers = self._get_auth_header()
                
                self.logger.debug(f"Making {method} request to {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Check for authentication error (HTTP 401)
                if response.status_code == 401:
                    # If we have a token manager, try refreshing the token once
                    if self.token_manager and attempt == 0:
                        self.logger.warning("Token may be expired, attempting refresh")
                        try:
                            self.token_manager.clear_token()
                            # Retry with new token
                            continue
                        except AuthenticationError:
                            pass  # Fall through to raise AuthenticationError
                    
                    raise AuthenticationError(
                        "Authentication failed. Check OAuth2 credentials and token.",
                        status_code=401,
                        response=response.text
                    )
                
                # Check for rate limiting (HTTP 429)
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 60)
                    self.logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds",
                        status_code=429,
                        response=response.text
                    )
                
                # Check for other errors
                if not response.ok:
                    error_msg = f"HTTP {response.status_code}: {response.reason}"
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    
                    raise APIError(
                        error_msg,
                        status_code=response.status_code,
                        response=response.text
                    )
                
                # Return JSON response
                return response.json()
                
            except (requests.exceptions.ConnectionError, 
                   requests.exceptions.Timeout) as e:
                if attempt == retries - 1:
                    raise APIError(f"Request failed after {retries} retries: {e}")
                
                # Exponential backoff
                sleep_time = backoff_factor * (2 ** attempt)
                self.logger.warning(f"Request failed, retrying in {sleep_time:.1f}s: {e}")
                time.sleep(sleep_time)
            
            except (AuthenticationError, RateLimitError, APIError):
                # Re-raise these immediately
                raise
            
            except Exception as e:
                raise APIError(f"Unexpected error: {e}")
    
    # Public API methods (same as before but with OAuth2 auth)
    
    def get_states(
        self,
        icao24: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        time_secs: Optional[int] = None
    ) -> List[StateVector]:
        """
        Get state vectors for aircraft.
        
        Args:
            icao24: Filter by ICAO24 address (optional)
            bbox: Bounding box (lamin, lomin, lamax, lomax) in decimal degrees
            time_secs: Unix timestamp for historical data (requires OAuth2 auth)
            
        Returns:
            List of StateVector objects
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
            AuthenticationError: If historical data requested without OAuth2 auth
        """
        params = {}
        
        # Validate and add parameters
        if icao24:
            if not validate_icao24(icao24):
                raise ValidationError(f"Invalid ICAO24 address: {icao24}")
            params['icao24'] = icao24
        
        if bbox:
            if len(bbox) != 4:
                raise ValidationError("Bounding box must have 4 values")
            lamin, lomin, lamax, lomax = bbox
            params['lamin'] = lamin
            params['lomin'] = lomin
            params['lamax'] = lamax
            params['lomax'] = lomax
        
        if time_secs is not None:
            if not self.token_manager:
                raise AuthenticationError(
                    "OAuth2 authentication required for historical data. "
                    "Provide client_id and client_secret."
                )
            params['time'] = time_secs
        
        try:
            response = self._request('GET', '/states/all', params=params)
            
            states = []
            for state_data in response.get('states', []):
                try:
                    state = StateVector.from_api_response(state_data)
                    states.append(state)
                except Exception as e:
                    self.logger.warning(f"Failed to parse state vector: {e}")
            
            self.logger.info(f"Retrieved {len(states)} state vectors")
            return states
            
        except Exception as e:
            self.logger.error(f"Failed to get states: {e}")
            raise
    
    def get_flights(
        self,
        begin: datetime,
        end: datetime,
        icao24: Optional[str] = None
    ) -> List[Flight]:
        """
        Get flights within a time interval.
        
        Args:
            begin: Start time
            end: End time
            icao24: Filter by ICAO24 address (optional)
            
        Returns:
            List of Flight objects
            
        Note: Requires OAuth2 authentication
        """
        if not self.token_manager:
            raise AuthenticationError(
                "OAuth2 authentication required for flights endpoint. "
                "Provide client_id and client_secret."
            )
        
        params = {
            'begin': to_unix_timestamp(begin),
            'end': to_unix_timestamp(end)
        }
        
        if icao24:
            if not validate_icao24(icao24):
                raise ValidationError(f"Invalid ICAO24 address: {icao24}")
            params['icao24'] = icao24
        
        try:
            response = self._request('GET', '/flights/all', params=params)
            
            flights = []
            for flight_data in response:
                try:
                    flight = Flight(
                        icao24=flight_data['icao24'],
                        first_seen=parse_timestamp(flight_data['firstSeen']),
                        last_seen=parse_timestamp(flight_data['lastSeen']),
                        callsign=flight_data.get('callsign'),
                        departure_airport=flight_data.get('estDepartureAirport'),
                        arrival_airport=flight_data.get('estArrivalAirport')
                    )
                    flights.append(flight)
                except Exception as e:
                    self.logger.warning(f"Failed to parse flight: {e}")
            
            self.logger.info(f"Retrieved {len(flights)} flights")
            return flights
            
        except Exception as e:
            self.logger.error(f"Failed to get flights: {e}")
            raise
    
    # Other methods remain similar but use OAuth2 authentication...
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current OAuth2 token.
        
        Returns:
            Token information dictionary or None if not authenticated
        """
        if self.token_manager:
            return self.token_manager.token_info
        return None
    
    def refresh_token(self) -> None:
        """Force refresh the OAuth2 token."""
        if self.token_manager:
            self.token_manager.clear_token()
            self.token_manager.get_token()
    
    def close(self):
        """Close the client session and token manager."""
        if self.token_manager:
            self.token_manager.close()
        self.session.close()
        self.logger.info("OpenSky client closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()