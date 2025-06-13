"""
Results & Visualization API routes
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def results_health():
    """Results service health check"""
    return {"status": "healthy", "service": "results"}