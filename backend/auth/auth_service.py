"""
Main authentication service
"""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
from sqlalchemy.orm import Session

from ..db.models.user import User, Organization
from ..core.config import get_settings
from .jwt.jwt_handler import JWTHandler
from .password_utils import PasswordUtils

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """
    Main authentication service handling login, registration, and token management
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.jwt_handler = JWTHandler()
        self.password_utils = PasswordUtils()
        
    async def register_user(self, 
                           email: str,
                           password: str,
                           first_name: str,
                           last_name: str,
                           organization_name: Optional[str] = None) -> Dict:
        """
        Register a new user
        """
        logger.info(f"Registering new user: {email}")
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Validate password strength
        if not self.password_utils.validate_password_strength(password):
            raise ValueError("Password does not meet security requirements")
        
        # Hash password
        password_hash = self.password_utils.hash_password(password)
        
        # Create or get organization
        organization = None
        if organization_name:
            organization = self.db.query(Organization).filter(
                Organization.name == organization_name
            ).first()
            
            if not organization:
                organization = Organization(
                    name=organization_name,
                    subscription_plan="trial",
                    is_active=True
                )
                self.db.add(organization)
                self.db.flush()  # Get the ID
        
        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            organization_id=organization.id if organization else None,
            is_active=True,
            is_verified=False,  # Email verification required
            role="user"
        )
        
        self.db.add(user)
        self.db.commit()
        
        # Generate tokens
        access_token = self.jwt_handler.create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        refresh_token = self.jwt_handler.create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        logger.info(f"User registered successfully: {email}")
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "role": user.role,
                "is_verified": user.is_verified
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def authenticate_user(self, email: str, password: str) -> Dict:
        """
        Authenticate user with email and password
        """
        logger.info(f"Authenticating user: {email}")
        
        # Get user from database
        user = self.db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not self.password_utils.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            raise ValueError("Invalid email or password")
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Generate tokens
        access_token = self.jwt_handler.create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        refresh_token = self.jwt_handler.create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        logger.info(f"User authenticated successfully: {email}")
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "role": user.role,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token
        """
        try:
            # Verify refresh token
            payload = self.jwt_handler.verify_token(refresh_token)
            email = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not email or not user_id:
                raise ValueError("Invalid token payload")
            
            # Get user from database
            user = self.db.query(User).filter(
                User.email == email,
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValueError("User not found or inactive")
            
            # Generate new access token
            new_access_token = self.jwt_handler.create_access_token(
                data={"sub": user.email, "user_id": str(user.id)}
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")
    
    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token
        """
        try:
            # Verify token
            payload = self.jwt_handler.verify_token(token)
            email = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not email or not user_id:
                raise ValueError("Invalid token payload")
            
            # Get user from database
            user = self.db.query(User).filter(
                User.email == email,
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValueError("User not found or inactive")
            
            return user
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Access token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid access token")
    
    async def change_password(self, 
                             user_id: str,
                             current_password: str,
                             new_password: str) -> bool:
        """
        Change user password
        """
        logger.info(f"Changing password for user: {user_id}")
        
        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Verify current password
        if not self.password_utils.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Validate new password strength
        if not self.password_utils.validate_password_strength(new_password):
            raise ValueError("New password does not meet security requirements")
        
        # Hash new password
        new_password_hash = self.password_utils.hash_password(new_password)
        
        # Update password
        user.password_hash = new_password_hash
        user.password_changed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Password changed successfully for user: {user_id}")
        return True
    
    async def reset_password_request(self, email: str) -> str:
        """
        Request password reset (generate reset token)
        """
        logger.info(f"Password reset requested for: {email}")
        
        # Get user
        user = self.db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        if not user:
            # Don't reveal if email exists or not
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return "reset_token_placeholder"
        
        # Generate reset token (expires in 1 hour)
        reset_token = self.jwt_handler.create_reset_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        # Store reset token in database (optional - for tracking)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        self.db.commit()
        
        # In production, send email with reset link
        # For now, return the token
        return reset_token
    
    async def reset_password(self, 
                            reset_token: str,
                            new_password: str) -> bool:
        """
        Reset password using reset token
        """
        try:
            # Verify reset token
            payload = self.jwt_handler.verify_token(reset_token)
            email = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not email or not user_id:
                raise ValueError("Invalid reset token")
            
            # Get user
            user = self.db.query(User).filter(
                User.email == email,
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValueError("User not found")
            
            # Check if token matches stored token (optional)
            if user.reset_token != reset_token:
                raise ValueError("Invalid reset token")
            
            # Check if token is expired
            if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
                raise ValueError("Reset token has expired")
            
            # Validate new password
            if not self.password_utils.validate_password_strength(new_password):
                raise ValueError("Password does not meet security requirements")
            
            # Hash new password
            new_password_hash = self.password_utils.hash_password(new_password)
            
            # Update password and clear reset token
            user.password_hash = new_password_hash
            user.password_changed_at = datetime.utcnow()
            user.reset_token = None
            user.reset_token_expires = None
            self.db.commit()
            
            logger.info(f"Password reset successfully for user: {email}")
            return True
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Reset token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid reset token")
    
    async def verify_email(self, verification_token: str) -> bool:
        """
        Verify user email using verification token
        """
        try:
            # Verify token
            payload = self.jwt_handler.verify_token(verification_token)
            email = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not email or not user_id:
                raise ValueError("Invalid verification token")
            
            # Get user
            user = self.db.query(User).filter(
                User.email == email,
                User.id == user_id
            ).first()
            
            if not user:
                raise ValueError("User not found")
            
            # Mark as verified
            user.is_verified = True
            user.verified_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Email verified successfully for user: {email}")
            return True
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Verification token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid verification token")
    
    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account
        """
        logger.info(f"Deactivating user: {user_id}")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.is_active = False
        user.deactivated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User deactivated successfully: {user_id}")
        return True
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """
        Get user permissions based on role and organization
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Basic permissions based on role
        permissions = []
        
        if user.role == "admin":
            permissions.extend([
                "create_project", "read_project", "update_project", "delete_project",
                "create_model", "read_model", "update_model", "delete_model",
                "run_analysis", "view_results", "export_data",
                "manage_users", "manage_organization"
            ])
        elif user.role == "engineer":
            permissions.extend([
                "create_project", "read_project", "update_project",
                "create_model", "read_model", "update_model",
                "run_analysis", "view_results", "export_data"
            ])
        elif user.role == "user":
            permissions.extend([
                "read_project", "read_model", "view_results"
            ])
        
        return permissions
    
    def get_auth_stats(self) -> Dict:
        """
        Get authentication statistics
        """
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        verified_users = self.db.query(User).filter(User.is_verified == True).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "verification_rate": verified_users / total_users if total_users > 0 else 0
        }