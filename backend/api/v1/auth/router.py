"""
Authentication API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {"status": "healthy", "service": "auth"}