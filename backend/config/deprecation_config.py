"""
Deprecation Configuration for Legacy (Unversioned) Endpoints

Defines which legacy routes are deprecated and their v1 replacements.
The DeprecationMiddleware uses this to add RFC 8594 deprecation headers.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Optional sunset date (ISO 8601). Set to None to omit the Sunset header.
SUNSET_DATE: str | None = "2026-06-30"

# Each entry: (compiled regex, v1 replacement template)
# The regex uses named groups so the replacement can reference captured segments.
_DEPRECATED_ROUTE_DEFINITIONS: list[tuple[str, str]] = [
    (r"^/momentum/top/(?P<limit>[^/]+)$", "/api/v1/momentum/top/{limit}"),
    (r"^/momentum/(?P<ticker>[^/]+)$", "/api/v1/momentum/{ticker}"),
    (r"^/portfolio/analysis/by-categories$", "/api/v1/portfolio/analysis/by-categories"),
    (r"^/portfolio/analyze/by-categories$", "/api/v1/portfolio/analyze/by-categories"),
    (r"^/portfolio/analysis$", "/api/v1/portfolio/analysis"),
    (r"^/portfolio/analyze$", "/api/v1/portfolio/analyze"),
    (r"^/categories/(?P<name>[^/]+)/analysis$", "/api/v1/categories/{name}/analysis"),
    (r"^/categories/(?P<name>[^/]+)/tickers$", "/api/v1/categories/{name}/tickers"),
    (r"^/categories$", "/api/v1/categories"),
    (r"^/cache/status$", "/api/v1/cache/status"),
    (r"^/cache/clear$", "/api/v1/cache/clear"),
]

DEPRECATED_ROUTES: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern), replacement)
    for pattern, replacement in _DEPRECATED_ROUTE_DEFINITIONS
]


def get_deprecated_route_info(path: str) -> str | None:
    """
    Check if a request path matches a deprecated legacy route.

    Returns the v1 replacement path (with captured segments substituted),
    or None if the path is not deprecated.
    """
    normalized = path.rstrip("/")
    for regex, template in DEPRECATED_ROUTES:
        match = regex.match(normalized)
        if match:
            return template.format(**match.groupdict())
    return None
