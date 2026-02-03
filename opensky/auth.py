"""
Authentication module for OpenSky OAuth2 Client Credentials flow.
Documentation: https://openskynetwork.github.io/opensky-api/rest.html#oauth2-client-credentials-flow
"""

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import requests
from requests.exceptions import RequestException

from opensky.exceptions import AuthenticationError, APIError

logger = logging.getLogger(__name__)


class OAuth2TokenManager:
    """Manages OAuth2 token acquisition and refresh for OpenSky API."""
    
    # OAuth2 endpoints
    TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    TOKEN_EXPIRY_BUFFER = 60  # Refresh token 60 seconds before expiry
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str = None,
        timeout: int = 30
    ):
        """
        Initialize OAuth2 token manager.
        
        Args:
            client_id: OAuth2 client ID from OpenSky
            client_secret: OAuth2 client secret from OpenSky
            token_url: Custom token URL (optional)
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url or self.TOKEN_URL
        self.timeout = timeout
        
        # Token state
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.token_type: Optional[str] = None
        self.scope: Optional[str] = None
        
        # Session for token requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OpenSkyPythonClient/2.0.0',
            'Accept': 'application/json',
        })
    
    def _request_token(self) -> Dict[str, Any]:
        """
        Request a new access token from OAuth2 server.
        
        Returns:
            Token response as dictionary
            
        Raises:
            AuthenticationError: If token request fails
        """
        try:
            logger.debug(f"Requesting OAuth2 token from {self.token_url}")
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            response = self.session.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if not response.ok:
                error_msg = f"Token request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('error_description', error_data)}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                raise AuthenticationError(error_msg, status_code=response.status_code)
            
            token_data = response.json()
            
            # Validate required fields
            if 'access_token' not in token_data:
                raise AuthenticationError("Token response missing 'access_token' field")
            
            return token_data
            
        except RequestException as e:
            raise AuthenticationError(f"Token request failed: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Unexpected error during token request: {str(e)}")
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if not expired
            
        Returns:
            Valid access token string
        """
        # Force refresh if requested
        if force_refresh:
            logger.debug("Forcing token refresh")
            return self._refresh_token()
        
        # Check if token is expired or about to expire
        if self.access_token is None or self.token_expires_at is None:
            logger.debug("No token available, requesting new one")
            return self._refresh_token()
        
        # Check if token is expired (with buffer)
        expiry_buffer = timedelta(seconds=self.TOKEN_EXPIRY_BUFFER)
        if datetime.now() >= (self.token_expires_at - expiry_buffer):
            logger.debug("Token expired or near expiry, refreshing")
            return self._refresh_token()
        
        # Token is still valid
        return self.access_token
    
    def _refresh_token(self) -> str:
        """
        Refresh the access token and update state.
        
        Returns:
            New access token string
        """
        token_data = self._request_token()
        
        # Update token state
        self.access_token = token_data['access_token']
        self.token_type = token_data.get('token_type', 'Bearer')
        self.scope = token_data.get('scope')
        
        # Calculate expiry time (default 30 minutes if not provided)
        expires_in = token_data.get('expires_in', 1800)  # 30 minutes in seconds
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info(f"Obtained new OAuth2 token, expires at {self.token_expires_at}")
        return self.access_token
    
    def clear_token(self) -> None:
        """Clear the current token (force next request to get a new one)."""
        self.access_token = None
        self.token_expires_at = None
        self.token_type = None
        self.scope = None
        logger.debug("Cleared OAuth2 token")
    
    @property
    def token_info(self) -> Dict[str, Any]:
        """Get current token information."""
        return {
            'has_token': self.access_token is not None,
            'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'token_type': self.token_type,
            'scope': self.scope,
            'seconds_until_expiry': (
                (self.token_expires_at - datetime.now()).total_seconds()
                if self.token_expires_at else None
            ),
        }
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()