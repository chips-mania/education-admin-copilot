import logging

from app.db.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_documents_table_exists():
    client = get_supabase_client()
    response = (
        client.table("documents")
        .select("id, title, source_type, file_name, file_path", count="exact")
        .limit(1)
        .execute()
    )

    logger.info("documents table OK, count=%s", response.count)
    assert response.count is not None


def test_chunks_table_exists():
    client = get_supabase_client()
    response = (
        client.table("chunks")
        .select("id, document_id, chunk_no, content, source_type, metadata", count="exact")
        .limit(1)
        .execute()
    )

    logger.info("chunks table OK, count=%s", response.count)
    assert response.count is not None


def test_match_documents_rpc_exists():
    client = get_supabase_client()
    zero_vector = [0.0] * 1024

    response = client.rpc(
        "match_documents",
        {
            "query_embedding": zero_vector,
            "match_count": 5,
            "match_threshold": 0.5,
        },
    ).execute()

    logger.info("match_documents RPC OK, results=%s", len(response.data))
    assert isinstance(response.data, list)
