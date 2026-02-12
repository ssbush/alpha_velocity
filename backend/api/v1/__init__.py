"""
API v1 Package

Version 1 of the AlphaVelocity API.
"""

from fastapi import APIRouter

# Import all v1 routers
from .momentum import router as momentum_router
from .momentum_paginated import router as momentum_paginated_router
from .momentum_batch import router as momentum_batch_router
from .portfolio import router as portfolio_router
from .portfolio_paginated import router as portfolio_paginated_router
from .categories import router as categories_router
from .cache import router as cache_router
from .cache_admin import router as cache_admin_router
from .metrics import router as metrics_router
from .historical import router as historical_router

# Create v1 API router
api_router = APIRouter()

# Include all routers
api_router.include_router(momentum_router, prefix="/momentum", tags=["momentum"])
api_router.include_router(momentum_paginated_router, prefix="/momentum", tags=["momentum-paginated"])
api_router.include_router(momentum_batch_router, prefix="/momentum", tags=["momentum-batch"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(portfolio_paginated_router, prefix="/portfolio", tags=["portfolio-paginated"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(cache_router, prefix="/cache", tags=["cache"])
api_router.include_router(cache_admin_router, prefix="/cache", tags=["cache-admin"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(historical_router, prefix="/historical", tags=["historical"])

# Auth, user, and transaction routers will be added when database is available
try:
    from .auth import router as auth_router
    from .user import router as user_router
    api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
    api_router.include_router(user_router, prefix="/user", tags=["user"])
except ImportError:
    pass  # Auth/user endpoints not available without database

try:
    from .transactions import router as transactions_router
    api_router.include_router(transactions_router, prefix="/user", tags=["user-transactions"])
except ImportError:
    pass  # Transaction endpoints not available without database
