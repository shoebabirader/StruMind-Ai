"""
JWT token handling utilities
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

from ...core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JWTHandler:
    """
    JWT token creation and verification handler
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.reset_token_expire_hours = 1
        
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created access token for user: {data.get('sub')}")
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict) -> str:
        """
        Create JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created refresh token for user: {data.get('sub')}")
        return encoded_jwt
    
    def create_reset_token(self, data: Dict) -> str:
        """
        Create JWT password reset token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=self.reset_token_expire_hours)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "reset"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created reset token for user: {data.get('sub')}")
        return encoded_jwt
    
    def create_verification_token(self, data: Dict) -> str:
        """
        Create JWT email verification token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=1)  # 24 hours to verify
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "verification"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created verification token for user: {data.get('sub')}")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise jwt.InvalidTokenError("Invalid token")
    
    def decode_token_without_verification(self, token: str) -> Dict:
        """
        Decode token without verification (for debugging)
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return {}
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get token expiry time
        """
        try:
            payload = self.decode_token_without_verification(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
            return None
        except Exception:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired
        """
        expiry = self.get_token_expiry(token)
        if expiry:
            return datetime.utcnow() > expiry
        return True
    
    def get_token_type(self, token: str) -> Optional[str]:
        """
        Get token type (access, refresh, reset, verification)
        """
        try:
            payload = self.decode_token_without_verification(token)
            return payload.get("type")
        except Exception:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create new access token from refresh token
        """
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token)
            
            # Check token type
            if payload.get("type") != "refresh":
                raise jwt.InvalidTokenError("Invalid token type")
            
            # Extract user data
            user_data = {
                "sub": payload.get("sub"),
                "user_id": payload.get("user_id")
            }
            
            # Create new access token
            new_access_token = self.create_access_token(user_data)
            
            logger.debug(f"Refreshed access token for user: {user_data.get('sub')}")
            return new_access_token
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            raise jwt.ExpiredSignatureError("Refresh token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise jwt.InvalidTokenError("Invalid refresh token")
    
    def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist (implement with Redis in production)
        """
        # This is a placeholder implementation
        # In production, you would store blacklisted tokens in Redis
        # with expiry time matching the token's expiry
        
        logger.info(f"Token blacklisted: {token[:20]}...")
        return True
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        """
        # This is a placeholder implementation
        # In production, check Redis for blacklisted tokens
        
        return False
    
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """
        Extract user information from token
        """
        try:
            payload = self.verify_token(token)
            return {
                "email": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "token_type": payload.get("type"),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0))
            }
        except Exception as e:
            logger.warning(f"Failed to extract user from token: {e}")
            return None
    
    def create_api_key_token(self, data: Dict, expires_days: int = 365) -> str:
        """
        Create long-lived API key token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=expires_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "api_key"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created API key token for user: {data.get('sub')}")
        return encoded_jwt
    
    def validate_token_format(self, token: str) -> bool:
        """
        Validate token format without verification
        """
        try:
            # Check if token has 3 parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            # Try to decode without verification
            self.decode_token_without_verification(token)
            return True
        except Exception:
            return False