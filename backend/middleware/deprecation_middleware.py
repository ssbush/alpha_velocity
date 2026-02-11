"""
Deprecation Middleware

Adds RFC 8594 deprecation headers to responses for legacy (unversioned)
endpoints, directing consumers to the equivalent /api/v1/ endpoint.

Headers added to deprecated routes:
  - Deprecation: true
  - Sunset: <date>  (if SUNSET_DATE is configured)
  - Link: </api/v1/...>; rel="successor-version"
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config.deprecation_config import get_deprecated_route_info, SUNSET_DATE

logger = logging.getLogger(__name__)


class DeprecationMiddleware(BaseHTTPMiddleware):
    """Middleware that adds deprecation headers to legacy endpoint responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        v1_path = get_deprecated_route_info(request.url.path)
        if v1_path is not None:
            response.headers["Deprecation"] = "true"
            response.headers["Link"] = f"<{v1_path}>; rel=\"successor-version\""
            if SUNSET_DATE:
                response.headers["Sunset"] = SUNSET_DATE

        return response
