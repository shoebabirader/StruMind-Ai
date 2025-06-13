"""
Main API router for StruMind Backend v1
"""

from fastapi import APIRouter

from .auth.router import router as auth_router
from .projects.router import router as projects_router
from .models.router import router as models_router
from .analysis.router import router as analysis_router
from .design.router import router as design_router
from .results.router import router as results_router

api_router = APIRouter()

# Include all sub-routers
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    projects_router,
    prefix="/projects",
    tags=["Projects"]
)

api_router.include_router(
    models_router,
    prefix="/models",
    tags=["Structural Models"]
)

api_router.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["Structural Analysis"]
)

api_router.include_router(
    design_router,
    prefix="/design",
    tags=["Structural Design"]
)

api_router.include_router(
    results_router,
    prefix="/results",
    tags=["Results & Visualization"]
)