"""
Tests for custom exceptions.
"""

import pytest
from opensky.exceptions import (
    OpenSkyError,
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError,
    TokenExpiredError
)


class TestOpenSkyError:
    """Test base OpenSkyError."""
    
    def test_initialization(self):
        """Test exception initialization."""
        error = OpenSkyError("Test error")
        assert str(error) == "Test error"
    
    def test_inheritance(self):
        """Test that all exceptions inherit from OpenSkyError."""
        assert issubclass(AuthenticationError, OpenSkyError)
        assert issubclass(APIError, OpenSkyError)
        assert issubclass(RateLimitError, APIError)  # And also OpenSkyError
        assert issubclass(ValidationError, OpenSkyError)
        assert issubclass(TokenExpiredError, AuthenticationError)


class TestAuthenticationError:
    """Test AuthenticationError."""
    
    def test_initialization(self):
        """Test exception initialization with details."""
        error = AuthenticationError(
            "Authentication failed",
            status_code=401,
            response="Invalid token"
        )
        
        assert str(error) == "Authentication failed"
        assert error.status_code == 401
        assert error.response == "Invalid token"
    
    def test_default_values(self):
        """Test default values for optional parameters."""
        error = AuthenticationError("Simple error")
        assert error.status_code is None
        assert error.response is None


class TestAPIError:
    """Test APIError."""
    
    def test_initialization(self):
        """Test exception initialization with details."""
        error = APIError(
            "API error occurred",
            status_code=500,
            response={"error": "Server error"}
        )
        
        assert str(error) == "API error occurred"
        assert error.status_code == 500
        assert error.response == {"error": "Server error"}
    
    def test_inheritance_chain(self):
        """Test that RateLimitError inherits from APIError."""
        error = RateLimitError("Rate limited")
        assert isinstance(error, APIError)
        assert isinstance(error, OpenSkyError)


class TestRateLimitError:
    """Test RateLimitError."""
    
    def test_initialization(self):
        """Test exception initialization."""
        error = RateLimitError(
            "Rate limit exceeded",
            status_code=429,
            response="Try again later"
        )
        
        assert str(error) == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.response == "Try again later"


class TestValidationError:
    """Test ValidationError."""
    
    def test_initialization(self):
        """Test exception initialization."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"


class TestTokenExpiredError:
    """Test TokenExpiredError."""
    
    def test_initialization(self):
        """Test exception initialization."""
        error = TokenExpiredError(
            "Token expired",
            status_code=401,
            response="Token has expired"
        )
        
        assert str(error) == "Token expired"
        assert error.status_code == 401
        assert error.response == "Token has expired"
    
    def test_inheritance(self):
        """Test inheritance chain."""
        error = TokenExpiredError("Test")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, OpenSkyError)