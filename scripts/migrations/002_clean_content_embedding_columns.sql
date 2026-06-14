-- Clean schema: content_v1/v2 + embedding_v1/v2 only (drop legacy content/embedding)
-- Use this when migrating an existing DB. For fresh install, run setup_schema.sql instead.

alter table chunks add column if not exists content_v1 text;
alter table chunks add column if not exists content_v2 text;
alter table chunks add column if not exists embedding_v1 vector(1024);
alter table chunks add column if not exists embedding_v2 vector(1024);

-- Backfill from legacy columns / metadata
update chunks
set content_v2 = coalesce(content_v2, content),
    embedding_v2 = coalesce(embedding_v2, embedding)
where content is not null or embedding is not null;

update chunks
set content_v1 = coalesce(content_v1, metadata->>'body', content_v2),
    embedding_v1 = coalesce(embedding_v1, embedding_v2)
where content_v1 is null or embedding_v1 is null;

alter table chunks alter column content_v1 set not null;
alter table chunks alter column content_v2 set not null;

alter table chunks drop column if exists content;
alter table chunks drop column if exists embedding;

drop index if exists chunks_embedding_idx;

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
        c.content_v1 as content,
        c.source_type,
        c.metadata,
        case
            when embed_version = 'v1' then 1 - (c.embedding_v1 <=> query_embedding)
            else 1 - (c.embedding_v2 <=> query_embedding)
        end as similarity,
        d.title as document_title,
        d.file_name,
        d.file_path
    from chunks c
    join documents d on d.id = c.document_id
    where (
        (embed_version = 'v1' and c.embedding_v1 is not null)
        or (embed_version <> 'v1' and c.embedding_v2 is not null)
    )
      and (
        case
            when embed_version = 'v1' then 1 - (c.embedding_v1 <=> query_embedding)
            else 1 - (c.embedding_v2 <=> query_embedding)
        end
      ) > match_threshold
    order by
        case
            when embed_version = 'v1' then c.embedding_v1 <=> query_embedding
            else c.embedding_v2 <=> query_embedding
        end
    limit match_count;
$$;
