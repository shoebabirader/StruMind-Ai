"""
Structural Analysis API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def analysis_health():
    """Analysis service health check"""
    return {"status": "healthy", "service": "analysis"}