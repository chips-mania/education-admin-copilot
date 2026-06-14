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
        .select(
            "id, document_id, chunk_no, chapter, heading, content, source_type, metadata",
            count="exact",
        )
        .limit(1)
        .execute()
    )

    logger.info("chunks table OK, count=%s", response.count)
    assert response.count is not None


def test_match_documents_rpc_exists():
    client = get_supabase_client()
    zero_vector = [0.0] * 1024
    params = {
        "query_embedding": zero_vector,
        "match_count": 5,
        "match_threshold": 0.5,
    }

    for rpc_name in ("match_documents_v1", "match_documents_v2", "match_documents"):
        response = client.rpc(rpc_name, params).execute()
        logger.info("%s RPC OK, results=%s", rpc_name, len(response.data))
        assert isinstance(response.data, list)
