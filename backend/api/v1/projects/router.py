"""
Projects API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def projects_health():
    """Projects service health check"""
    return {"status": "healthy", "service": "projects"}