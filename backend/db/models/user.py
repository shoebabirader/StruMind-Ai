"""
User and Organization models for multi-tenant SaaS architecture
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy import String as SQLString

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class UserRole(str, Enum):
    """User roles within an organization"""
    OWNER = "owner"
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class SubscriptionPlan(str, Enum):
    """Subscription plans"""
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class User(Base):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile
    phone = Column(String(20), nullable=True)
    company = Column(String(200), nullable=True)
    job_title = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Preferences
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization_memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Organization(Base):
    """Organization model for multi-tenant SaaS"""
    
    __tablename__ = "organizations"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Address
    address_line1 = Column(String(200), nullable=True)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Subscription
    subscription_plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    subscription_status = Column(String(50), default="active", nullable=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Limits
    max_users = Column(Integer, default=5, nullable=False)
    max_projects = Column(Integer, default=10, nullable=False)
    max_storage_gb = Column(Integer, default=10, nullable=False)
    
    # Settings
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationMember(Base):
    """Organization membership with roles"""
    
    __tablename__ = "organization_members"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Membership Details
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="organization_memberships")
    organization = relationship("Organization", back_populates="members")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="unique_user_organization"),
    )
    
    def __repr__(self) -> str:
        return f"<OrganizationMember(user_id={self.user_id}, org_id={self.organization_id}, role={self.role})>"