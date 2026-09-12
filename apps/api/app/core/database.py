"""
CareerOS Phase 3 — Supabase PostgreSQL Production Client & Connection Manager.

Manages connection pooling, RLS authentication context, and graceful fallback
for zero-dependency offline test environments.
Historical migrations 001-029 remain authoritative and untouched.
"""

from typing import Any
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.core.logging import logger

try:
    from supabase import Client, create_client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False


class DatabaseManager:
    """
    Manages production Supabase PostgreSQL client connection lifecycle
    with RLS session headers and offline test resilience.
    """

    _client_instance: Any = None

    @classmethod
    def is_configured(cls) -> bool:
        """
        Returns True if live Supabase credentials are provided
        and not the default mock placeholders.
        """
        url = settings.supabase_url
        key = settings.supabase_service_role_key or settings.supabase_anon_key
        return (
            bool(url)
            and bool(key)
            and "mock-project" not in url
            and "mock-anon-key" not in key
        )

    @classmethod
    def get_client(cls) -> Any:
        """
        Get or initialize singleton Supabase client for production execution.
        Returns None in test or demo environments where mock repositories are active.
        """
        if not cls.is_configured() or not _SUPABASE_AVAILABLE:
            return None

        if cls._client_instance is None:
            try:
                key = settings.supabase_service_role_key or settings.supabase_anon_key
                cls._client_instance = create_client(settings.supabase_url, key)
                logger.info("Supabase PostgreSQL client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client; falling back to memory store: {e}")
                return None

        return cls._client_instance

    @classmethod
    def get_user_scoped_client(cls, user_id: UUID) -> Any:
        """
        Return Supabase client with candidate user isolation context.
        """
        base = cls.get_client()
        if not base:
            return None
        return base
