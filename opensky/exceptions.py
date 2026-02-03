"""Custom exceptions for the OpenSky client."""


class OpenSkyError(Exception):
    """Base exception for all OpenSky errors."""
    pass


class AuthenticationError(OpenSkyError):
    """Raised when OAuth2 authentication fails."""
    
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class APIError(OpenSkyError):
    """Raised when the API returns an error."""
    
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass


class ValidationError(OpenSkyError):
    """Raised when input validation fails."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when OAuth2 token has expired."""
    pass