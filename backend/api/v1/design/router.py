"""
Structural Design API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def design_health():
    """Design service health check"""
    return {"status": "healthy", "service": "design"}