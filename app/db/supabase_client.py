import logging

from supabase import Client, create_client

from app.config.settings import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    global _client

    settings.validate_supabase()

    if _client is None:
        logger.info("Initializing Supabase client")
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    return _client
