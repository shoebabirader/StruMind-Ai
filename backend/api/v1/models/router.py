"""
Structural Models API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def models_health():
    """Models service health check"""
    return {"status": "healthy", "service": "models"}