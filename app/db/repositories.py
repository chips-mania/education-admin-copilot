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

    def list_document_ids(self) -> list[int]:
        response = self.client.table("documents").select("id").execute()
        return [row["id"] for row in (response.data or [])]

    def delete_all_documents(self) -> int:
        document_ids = self.list_document_ids()
        for document_id in document_ids:
            self.delete_document(document_id)
        logger.info("Deleted %d document(s) from Supabase", len(document_ids))
        return len(document_ids)

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

    @staticmethod
    def _resolve_chunk_fields(chunk: dict[str, Any]) -> tuple[str, str, str, str, list[float], list[float]]:
        content = chunk.get("content")
        embedding_v1 = chunk.get("embedding_v1")
        embedding_v2 = chunk.get("embedding_v2")

        if content is None:
            raise ValueError(f"Chunk {chunk.get('chunk_no')} missing content")
        if embedding_v1 is None or embedding_v2 is None:
            raise ValueError(f"Chunk {chunk.get('chunk_no')} missing embedding_v1/embedding_v2")

        metadata = chunk.get("metadata") or {}
        return (
            str(chunk.get("chapter") or metadata.get("chapter") or ""),
            str(chunk.get("heading") or metadata.get("heading") or metadata.get("section") or ""),
            str(content),
            chunk.get("source_type") or "",
            embedding_v1,
            embedding_v2,
        )

    def insert_chunks(
        self,
        document_id: int,
        source_type: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        rows = []
        for chunk in chunks:
            chapter, heading, content, _, embedding_v1, embedding_v2 = self._resolve_chunk_fields(chunk)

            rows.append(
                {
                    "document_id": document_id,
                    "chunk_no": chunk["chunk_no"],
                    "chapter": chapter,
                    "heading": heading,
                    "content": content,
                    "source_type": source_type,
                    "metadata": chunk.get("metadata", {}),
                    "embedding_v1": embedding_v1,
                    "embedding_v2": embedding_v2,
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

    def list_documents(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("documents")
            .select("id, title, file_name, file_path, source_type, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        documents = response.data or []
        for document in documents:
            document["chunk_count"] = self.count_chunks_for_document(document["id"])
        logger.info("Listed %d document(s)", len(documents))
        return documents

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
