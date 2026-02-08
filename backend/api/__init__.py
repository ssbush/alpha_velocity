"""
API Package

Versioned API routers for AlphaVelocity.
"""

from fastapi import APIRouter

# Import v1 router
from .v1 import api_router as v1_router

# Create main API router
api_router = APIRouter()

# Include v1 routes
api_router.include_router(v1_router, prefix="/v1", tags=["v1"])
