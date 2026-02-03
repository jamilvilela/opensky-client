"""
Tests for OAuth2 authentication module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from opensky.auth import OAuth2TokenManager
from opensky.exceptions import AuthenticationError


class TestOAuth2TokenManager:
    """Test OAuth2TokenManager class."""
    
    def test_initialization(self):
        """Test token manager initialization."""
        manager = OAuth2TokenManager(
            client_id="test_id",
            client_secret="test_secret"
        )
        
        assert manager.client_id == "test_id"
        assert manager.client_secret == "test_secret"
        assert manager.access_token is None
        assert manager.token_expires_at is None
    
    @patch('requests.Session')
    def test_successful_token_request(self, mock_session_class):
        """Test successful token acquisition."""
        # Setup mock response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 1800,
            "scope": "read"
        }
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Create manager and request token
        manager = OAuth2TokenManager("test_id", "test_secret")
        token = manager.get_token()
        
        # Verify
        assert token == "test_token"
        assert manager.access_token == "test_token"
        assert manager.token_type == "Bearer"
        assert manager.token_expires_at is not None
    
    @patch('requests.Session')
    def test_token_request_failure(self, mock_session_class):
        """Test failed token request."""
        # Setup mock response with error
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "invalid_client"}
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Create manager and attempt to get token
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        with pytest.raises(AuthenticationError) as exc_info:
            manager.get_token()
        
        assert "Token request failed" in str(exc_info.value)
        assert exc_info.value.status_code == 401
    
    @patch('requests.Session')
    def test_token_refresh_logic(self, mock_session_class):
        """Test token refresh logic."""
        # Setup mock for successful token request
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 1800
        }
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Create manager
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        # First token request
        token1 = manager.get_token()
        assert token1 == "new_token"
        
        # Reset for second request
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 1800
        }
        
        # Force refresh by clearing token
        manager.clear_token()
        token2 = manager.get_token()
        
        assert token2 == "refreshed_token"
        assert token1 != token2
    
    def test_token_expiry_check(self):
        """Test token expiry checking."""
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        # No token yet
        assert manager.access_token is None
        
        # Set expired token
        manager.access_token = "expired_token"
        manager.token_expires_at = datetime.now() - timedelta(seconds=60)
        
        # Token should be considered expired
        # Note: We're testing the internal state, not the get_token logic
        assert manager.token_expires_at < datetime.now()
    
    @patch('requests.Session')
    def test_network_error_handling(self, mock_session_class):
        """Test handling of network errors."""
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Network error")
        mock_session_class.return_value = mock_session
        
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        with pytest.raises(AuthenticationError) as exc_info:
            manager.get_token()
        
        assert "Token request failed" in str(exc_info.value)
    
    def test_token_info_property(self):
        """Test token_info property."""
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        # Initially no token
        info = manager.token_info
        assert info['has_token'] is False
        assert info['expires_at'] is None
        
        # Set token
        manager.access_token = "test_token"
        manager.token_type = "Bearer"
        manager.token_expires_at = datetime.now() + timedelta(minutes=30)
        
        info = manager.token_info
        assert info['has_token'] is True
        assert info['token_type'] == "Bearer"
        assert info['seconds_until_expiry'] > 0
    
    def test_clear_token(self):
        """Test clearing token."""
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        # Set token
        manager.access_token = "test_token"
        manager.token_type = "Bearer"
        manager.token_expires_at = datetime.now() + timedelta(minutes=30)
        
        # Clear token
        manager.clear_token()
        
        assert manager.access_token is None
        assert manager.token_expires_at is None
        assert manager.token_type is None
    
    @patch('requests.Session')
    def test_missing_access_token_in_response(self, mock_session_class):
        """Test handling of missing access token in response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "token_type": "Bearer",  # Missing access_token
            "expires_in": 1800
        }
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        manager = OAuth2TokenManager("test_id", "test_secret")
        
        with pytest.raises(AuthenticationError) as exc_info:
            manager.get_token()
        
        assert "missing 'access_token' field" in str(exc_info.value)
    
    def test_close_method(self):
        """Test close method."""
        mock_session = Mock()
        
        with patch('requests.Session', return_value=mock_session):
            manager = OAuth2TokenManager("test_id", "test_secret")
            manager.close()
        
        mock_session.close.assert_called_once()