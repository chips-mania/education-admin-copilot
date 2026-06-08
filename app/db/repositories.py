import logging
from typing import Any

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class DocumentRepository:
    def __init__(self, client=None):
        self.client = client or get_supabase_client()

    def find_document_id_by_file_path(self, file_path: str) -> int | None:
        response = (
            self.client.table("documents")
            .select("id")
            .eq("file_path", file_path)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["id"]
        return None

    def delete_document(self, document_id: int) -> None:
        logger.info("Deleting document id=%s", document_id)
        self.client.table("documents").delete().eq("id", document_id).execute()

    def insert_document(
        self,
        title: str,
        source_type: str,
        file_name: str,
        file_path: str,
    ) -> int:
        payload = {
            "title": title,
            "source_type": source_type,
            "file_name": file_name,
            "file_path": file_path,
        }
        logger.info("Inserting document: %s", file_path)
        response = self.client.table("documents").insert(payload).execute()

        if not response.data:
            raise RuntimeError(f"Failed to insert document: {file_path}")

        document_id = response.data[0]["id"]
        logger.info("Inserted document id=%s", document_id)
        return document_id

    def insert_chunks(
        self,
        document_id: int,
        source_type: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        rows = []
        for chunk in chunks:
            if "embedding" not in chunk:
                raise ValueError(f"Chunk {chunk.get('chunk_no')} missing embedding")

            rows.append(
                {
                    "document_id": document_id,
                    "chunk_no": chunk["chunk_no"],
                    "content": chunk["content"],
                    "source_type": source_type,
                    "metadata": chunk.get("metadata", {}),
                    "embedding": chunk["embedding"],
                }
            )

        logger.info("Inserting %d chunk(s) for document id=%s", len(rows), document_id)
        response = self.client.table("chunks").insert(rows).execute()

        if not response.data:
            raise RuntimeError(f"Failed to insert chunks for document id={document_id}")

        logger.info("Inserted %d chunk(s)", len(response.data))
        return len(response.data)

    def count_chunks_for_document(self, document_id: int) -> int:
        response = (
            self.client.table("chunks")
            .select("id", count="exact")
            .eq("document_id", document_id)
            .execute()
        )
        return response.count or 0

    def count_all_chunks(self) -> int:
        response = self.client.table("chunks").select("id", count="exact").execute()
        return response.count or 0

    def ingest_embedding_document(self, payload: dict[str, Any], replace: bool = True) -> dict[str, int]:
        file_path = payload["file_path"]
        chunks = payload["chunks"]

        if replace:
            existing_id = self.find_document_id_by_file_path(file_path)
            if existing_id is not None:
                self.delete_document(existing_id)

        document_id = self.insert_document(
            title=payload["title"],
            source_type=payload["source_type"],
            file_name=payload["file_name"],
            file_path=file_path,
        )
        inserted = self.insert_chunks(document_id, payload["source_type"], chunks)
        stored = self.count_chunks_for_document(document_id)

        return {
            "document_id": document_id,
            "expected_chunks": len(chunks),
            "inserted_chunks": inserted,
            "stored_chunks": stored,
        }
