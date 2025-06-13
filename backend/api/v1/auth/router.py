"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

from db.database import get_db
from db.models.user import User, Organization, OrganizationMember, UserRole, SubscriptionPlan
from core.config import get_settings
from core.exceptions import AuthenticationError, ValidationError

settings = get_settings()

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models for request/response
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    organization_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: str
    organization_id: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    organization_id: Optional[str] = None
    created_at: datetime

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(user_id: str = Depends(verify_token), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {"status": "healthy", "service": "auth"}

@router.post("/register", response_model=Token)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization if provided
    organization = None
    if user_data.organization_name:
        organization = Organization(
            name=user_data.organization_name,
            slug=user_data.organization_name.lower().replace(" ", "-"),
            subscription_plan=SubscriptionPlan.FREE
        )
        db.add(organization)
        db.flush()  # Get organization ID
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.email,  # Use email as username for now
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        company=user_data.organization_name,
        is_active=True
    )
    
    db.add(user)
    db.flush()  # Get user ID
    
    # Create organization membership if organization exists
    if organization:
        membership = OrganizationMember(
            user_id=user.id,
            organization_id=organization.id,
            role=UserRole.OWNER,
            is_active=True
        )
        db.add(membership)
    
    db.commit()
    db.refresh(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        organization_id=str(organization.id) if organization else None
    )

@router.post("/login", response_model=Token)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Get user's organization (if any)
    organization_id = None
    if user.organization_memberships:
        organization_id = str(user.organization_memberships[0].organization_id)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        organization_id=organization_id
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    # Get user's organization (if any)
    organization_id = None
    if current_user.organization_memberships:
        organization_id = str(current_user.organization_memberships[0].organization_id)
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        organization_id=organization_id,
        created_at=current_user.created_at
    )

@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None
    )