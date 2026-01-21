"""
Supabase client helper for database operations.

Key Types (2025+):
- sb_publishable_... : Public key for client-side (replaces legacy 'anon' key)
- sb_secret_...      : Secret key for server-side (replaces legacy 'service_role' key)

For backend cron jobs, use the sb_secret_... key as it bypasses RLS.
"""
from supabase import create_client
from django.conf import settings


def get_supabase_client():
    """
    Create and return a Supabase client instance.
    Uses sb_secret_... key for backend operations (bypasses RLS, full read/write access).
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
