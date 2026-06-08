import logging

from postgrest.exceptions import APIError

from app.db.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_supabase_connection():
    client = get_supabase_client()
    assert client is not None
    logger.info("Supabase client initialized")

    try:
        response = client.table("documents").select("id", count="exact").limit(1).execute()
        logger.info("Supabase API reachable, documents count=%s", response.count)
    except APIError as exc:
        if exc.code == "PGRST205":
            logger.info("Supabase API reachable (documents table: STEP 2에서 생성 예정)")
        else:
            raise
