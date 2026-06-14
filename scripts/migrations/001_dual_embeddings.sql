-- Dual embedding columns (V1 body-only vs V2 breadcrumb context)
-- Run in Supabase SQL Editor after setup_schema.sql

alter table chunks add column if not exists embedding_v1 vector(1024);
alter table chunks add column if not exists embedding_v2 vector(1024);

-- Backfill from legacy single embedding column (treat as V2)
update chunks
set embedding_v2 = embedding
where embedding is not null
  and embedding_v2 is null;

create index if not exists chunks_embedding_v1_idx
    on chunks using hnsw (embedding_v1 vector_cosine_ops);

create index if not exists chunks_embedding_v2_idx
    on chunks using hnsw (embedding_v2 vector_cosine_ops);

create or replace function match_documents(
    query_embedding vector(1024),
    match_count int default 5,
    match_threshold float default 0.5,
    embed_version text default 'v2'
)
returns table (
    id bigint,
    document_id bigint,
    chunk_no integer,
    content text,
    source_type text,
    metadata jsonb,
    similarity float,
    document_title text,
    file_name text,
    file_path text
)
language sql stable
as $$
    select
        c.id,
        c.document_id,
        c.chunk_no,
        c.content,
        c.source_type,
        c.metadata,
        case
            when embed_version = 'v1' then 1 - (c.embedding_v1 <=> query_embedding)
            else 1 - (coalesce(c.embedding_v2, c.embedding) <=> query_embedding)
        end as similarity,
        d.title as document_title,
        d.file_name,
        d.file_path
    from chunks c
    join documents d on d.id = c.document_id
    where (
        (embed_version = 'v1' and c.embedding_v1 is not null)
        or (embed_version <> 'v1' and coalesce(c.embedding_v2, c.embedding) is not null)
    )
      and (
        case
            when embed_version = 'v1' then 1 - (c.embedding_v1 <=> query_embedding)
            else 1 - (coalesce(c.embedding_v2, c.embedding) <=> query_embedding)
        end
      ) > match_threshold
    order by
        case
            when embed_version = 'v1' then c.embedding_v1 <=> query_embedding
            else coalesce(c.embedding_v2, c.embedding) <=> query_embedding
        end
    limit match_count;
$$;
