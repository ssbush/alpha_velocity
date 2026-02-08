"""
Audit Logging Middleware

Records security-relevant events for compliance and forensics.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Set
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# Events that require audit logging
AUDIT_EVENTS = {
    'authentication': ['POST /api/v1/auth/login', 'POST /api/v1/auth/register'],
    'authorization': ['DELETE /api/v1/portfolio/{id}', 'PUT /api/v1/user/{id}'],
    'data_modification': ['POST', 'PUT', 'PATCH', 'DELETE'],
    'sensitive_access': ['GET /api/v1/user/{id}', 'GET /api/v1/admin/']
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging.

    Logs security-relevant events including:
    - Authentication attempts
    - Authorization failures
    - Data modifications
    - Access to sensitive resources
    - Failed requests
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_audit: bool = True,
        log_all_requests: bool = False
    ):
        """
        Initialize audit middleware.

        Args:
            app: ASGI application
            enable_audit: Enable audit logging
            log_all_requests: Log all requests (for high-security environments)
        """
        super().__init__(app)
        self.enable_audit = enable_audit
        self.log_all_requests = log_all_requests

    def _should_audit(self, method: str, path: str, status_code: int) -> bool:
        """
        Determine if request should be audited.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code

        Returns:
            True if should be audited
        """
        if self.log_all_requests:
            return True

        # Always audit authentication endpoints
        if '/auth/' in path:
            return True

        # Always audit failures
        if status_code >= 400:
            return True

        # Audit data modification
        if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return True

        # Audit admin endpoints
        if '/admin/' in path:
            return True

        return False

    def _get_user_context(self, request: Request) -> dict:
        """
        Extract user context from request.

        Args:
            request: FastAPI request

        Returns:
            User context dictionary
        """
        context = {
            'user_id': None,
            'username': None,
            'ip_address': request.client.host if request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown')
        }

        # Extract user from request state (if authenticated)
        if hasattr(request.state, 'user'):
            user = request.state.user
            context['user_id'] = getattr(user, 'id', None)
            context['username'] = getattr(user, 'username', None)

        return context

    async def dispatch(self, request: Request, call_next):
        """Process request and log audit events."""

        if not self.enable_audit:
            return await call_next(request)

        # Record request time
        timestamp = datetime.utcnow().isoformat()

        # Get user context
        user_context = self._get_user_context(request)

        # Process request
        response = await call_next(request)

        # Check if should audit
        if self._should_audit(
            request.method,
            request.url.path,
            response.status_code
        ):
            # Build audit log entry
            audit_entry = {
                'timestamp': timestamp,
                'event_type': self._classify_event(
                    request.method,
                    request.url.path,
                    response.status_code
                ),
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'request_id': getattr(request.state, 'request_id', 'unknown'),
                **user_context
            }

            # Log based on severity
            if response.status_code >= 500:
                logger.error(
                    f"AUDIT: Server error - {request.method} {request.url.path}",
                    extra={'audit': audit_entry}
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"AUDIT: Client error - {request.method} {request.url.path}",
                    extra={'audit': audit_entry}
                )
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                logger.info(
                    f"AUDIT: Data modification - {request.method} {request.url.path}",
                    extra={'audit': audit_entry}
                )
            elif '/auth/' in request.url.path:
                logger.info(
                    f"AUDIT: Authentication - {request.method} {request.url.path}",
                    extra={'audit': audit_entry}
                )
            else:
                logger.info(
                    f"AUDIT: {request.method} {request.url.path}",
                    extra={'audit': audit_entry}
                )

        return response

    def _classify_event(self, method: str, path: str, status_code: int) -> str:
        """
        Classify event type for audit log.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code

        Returns:
            Event type classification
        """
        if '/auth/login' in path:
            return 'authentication_attempt'
        elif '/auth/register' in path:
            return 'user_registration'
        elif '/auth/logout' in path:
            return 'logout'
        elif status_code == 401:
            return 'authentication_failure'
        elif status_code == 403:
            return 'authorization_failure'
        elif status_code >= 500:
            return 'server_error'
        elif status_code >= 400:
            return 'client_error'
        elif method == 'POST':
            return 'resource_creation'
        elif method == 'PUT':
            return 'resource_update'
        elif method == 'PATCH':
            return 'resource_partial_update'
        elif method == 'DELETE':
            return 'resource_deletion'
        elif method == 'GET' and '/admin/' in path:
            return 'admin_access'
        else:
            return 'general_access'
