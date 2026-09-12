import os
import re
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError
from fastapi import Header, Request, Query
from pydantic import BaseModel

DEFAULT_DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class AuthenticatedUser(BaseModel):
    user_id: UUID
    email: str = "user@careeros.ai"
    is_demo: bool = False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize and validate an uploaded filename against path traversal and malicious characters.
    """
    if not filename or not filename.strip():
        raise CareerOSError(
            code="INVALID_FILENAME",
            message="Filename cannot be empty",
            status_code=400,
        )

    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename or "\0" in filename:
        raise CareerOSError(
            code="INVALID_FILENAME",
            message="Filename contains illegal path traversal characters",
            status_code=400,
        )

    # Extract base name just in case
    base_name = os.path.basename(filename.strip())

    # Ensure valid file characters
    if not re.match(r"^[a-zA-Z0-9_\-. ]+$", base_name):
        raise CareerOSError(
            code="INVALID_FILENAME",
            message="Filename contains prohibited characters",
            status_code=400,
        )

    return base_name


def verify_ownership(resource_user_id: UUID, current_user: AuthenticatedUser) -> None:
    """
    Strictly enforce user ownership boundary (RLS parity in Python backend).
    """
    if resource_user_id != current_user.user_id:
        raise CareerOSError(
            code="FORBIDDEN",
            message="Access forbidden: resource belongs to another user",
            status_code=403,
        )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> AuthenticatedUser:
    """
    Authenticate the current request.
    Extracts identity from Bearer token, X-User-Id header, query param token (for EventSource), 
    or falls back to demo user if enabled.
    """
    # 1. Direct explicit user header (used in internal integration tests / secure proxy)
    if x_user_id:
        try:
            uid = UUID(x_user_id)
            return AuthenticatedUser(user_id=uid, email="user@careeros.ai", is_demo=False)
        except ValueError:
            raise CareerOSError(
                code="UNAUTHORIZED",
                message="Invalid user identifier format",
                status_code=401,
            )

    # 2. Query parameter token (for EventSource compatibility, since it can't send custom headers)
    if token:
        try:
            uid = UUID(token)
            return AuthenticatedUser(user_id=uid, email="user@careeros.ai", is_demo=False)
        except ValueError:
            # In demo or test mode with arbitrary non-uuid token
            if settings.demo_mode or settings.app_env == "test":
                return AuthenticatedUser(
                    user_id=DEFAULT_DEMO_USER_ID,
                    email="demo@careeros.ai",
                    is_demo=True,
                )
        raise CareerOSError(
            code="UNAUTHORIZED",
            message="Invalid token format",
            status_code=401,
        )

    # 3. Authorization Bearer header
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token_str = parts[1].strip()
            # If token is a UUID string directly (test/mock token)
            try:
                uid = UUID(token_str)
                return AuthenticatedUser(user_id=uid, email="user@careeros.ai", is_demo=False)
            except ValueError:
                # In demo or test mode with arbitrary non-uuid token
                if settings.demo_mode or settings.app_env == "test":
                    return AuthenticatedUser(
                        user_id=DEFAULT_DEMO_USER_ID,
                        email="demo@careeros.ai",
                        is_demo=True,
                    )
        raise CareerOSError(
            code="UNAUTHORIZED",
            message="Invalid authorization token format",
            status_code=401,
        )

    # 4. Fallback to demo mode if allowed
    if settings.demo_mode or settings.app_env in ("development", "test"):
        return AuthenticatedUser(
            user_id=DEFAULT_DEMO_USER_ID,
            email="demo@careeros.ai",
            is_demo=True,
        )

    raise CareerOSError(
        code="UNAUTHORIZED",
        message="Authentication credentials required",
        status_code=401,
    )
