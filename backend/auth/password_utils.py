"""
Password utilities for hashing and validation
"""

import bcrypt
import re
from typing import List
import logging

logger = logging.getLogger(__name__)


class PasswordUtils:
    """
    Password hashing and validation utilities
    """
    
    def __init__(self):
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special_chars = True
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        logger.debug("Password hashed successfully")
        return password_hash.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> bool:
        """
        Validate password strength according to security requirements
        """
        errors = self.get_password_strength_errors(password)
        return len(errors) == 0
    
    def get_password_strength_errors(self, password: str) -> List[str]:
        """
        Get list of password strength validation errors
        """
        errors = []
        
        # Check length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if len(password) > self.max_length:
            errors.append(f"Password must be no more than {self.max_length} characters long")
        
        # Check for uppercase letters
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check for lowercase letters
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check for digits
        if self.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        # Check for special characters
        if self.require_special_chars:
            special_char_pattern = f"[{re.escape(self.special_chars)}]"
            if not re.search(special_char_pattern, password):
                errors.append(f"Password must contain at least one special character ({self.special_chars})")
        
        # Check for common weak patterns
        weak_patterns = [
            (r'(.)\1{2,}', "Password cannot contain more than 2 consecutive identical characters"),
            (r'(012|123|234|345|456|567|678|789|890)', "Password cannot contain sequential numbers"),
            (r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', "Password cannot contain sequential letters"),
        ]
        
        for pattern, message in weak_patterns:
            if re.search(pattern, password.lower()):
                errors.append(message)
        
        # Check against common passwords
        if self._is_common_password(password):
            errors.append("Password is too common, please choose a more unique password")
        
        return errors
    
    def _is_common_password(self, password: str) -> bool:
        """
        Check if password is in common passwords list
        """
        # Common weak passwords
        common_passwords = {
            "password", "123456", "123456789", "12345678", "12345",
            "1234567", "password123", "admin", "qwerty", "abc123",
            "letmein", "monkey", "1234567890", "dragon", "111111",
            "baseball", "iloveyou", "trustno1", "1234", "sunshine",
            "master", "123123", "welcome", "shadow", "ashley",
            "football", "jesus", "michael", "ninja", "mustang"
        }
        
        return password.lower() in common_passwords
    
    def get_password_strength_score(self, password: str) -> int:
        """
        Get password strength score (0-100)
        """
        score = 0
        
        # Length score (up to 25 points)
        if len(password) >= 8:
            score += min(25, len(password) * 2)
        
        # Character variety score (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(f"[{re.escape(self.special_chars)}]", password):
            score += 10
        
        # Uniqueness score (up to 35 points)
        unique_chars = len(set(password))
        score += min(15, unique_chars)
        
        # Penalty for common patterns
        if re.search(r'(.)\1{2,}', password):
            score -= 10
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            score -= 10
        if self._is_common_password(password):
            score -= 20
        
        return max(0, min(100, score))
    
    def get_password_strength_level(self, password: str) -> str:
        """
        Get password strength level description
        """
        score = self.get_password_strength_score(password)
        
        if score >= 80:
            return "Very Strong"
        elif score >= 60:
            return "Strong"
        elif score >= 40:
            return "Medium"
        elif score >= 20:
            return "Weak"
        else:
            return "Very Weak"
    
    def generate_password_suggestions(self, base_password: str) -> List[str]:
        """
        Generate password suggestions based on a base password
        """
        suggestions = []
        
        # Add numbers
        suggestions.append(f"{base_password}123")
        suggestions.append(f"{base_password}2024")
        
        # Add special characters
        suggestions.append(f"{base_password}!")
        suggestions.append(f"{base_password}@#")
        
        # Capitalize first letter
        if base_password and base_password[0].islower():
            suggestions.append(base_password.capitalize())
        
        # Mix case
        if len(base_password) > 3:
            mixed_case = ""
            for i, char in enumerate(base_password):
                if i % 2 == 0:
                    mixed_case += char.upper()
                else:
                    mixed_case += char.lower()
            suggestions.append(mixed_case)
        
        # Add prefix/suffix
        suggestions.append(f"My{base_password}!")
        suggestions.append(f"{base_password}Secure1")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def check_password_history(self, new_password: str, password_history: List[str]) -> bool:
        """
        Check if new password is different from recent passwords
        """
        for old_password_hash in password_history:
            if self.verify_password(new_password, old_password_hash):
                return False
        return True
    
    def get_password_requirements(self) -> Dict:
        """
        Get password requirements configuration
        """
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "require_uppercase": self.require_uppercase,
            "require_lowercase": self.require_lowercase,
            "require_digits": self.require_digits,
            "require_special_chars": self.require_special_chars,
            "special_chars": self.special_chars
        }
    
    def set_password_requirements(self, 
                                 min_length: int = None,
                                 max_length: int = None,
                                 require_uppercase: bool = None,
                                 require_lowercase: bool = None,
                                 require_digits: bool = None,
                                 require_special_chars: bool = None):
        """
        Update password requirements
        """
        if min_length is not None:
            self.min_length = min_length
        if max_length is not None:
            self.max_length = max_length
        if require_uppercase is not None:
            self.require_uppercase = require_uppercase
        if require_lowercase is not None:
            self.require_lowercase = require_lowercase
        if require_digits is not None:
            self.require_digits = require_digits
        if require_special_chars is not None:
            self.require_special_chars = require_special_chars
        
        logger.info("Password requirements updated")