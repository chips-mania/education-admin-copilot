-- Structured chunks: chapter/heading/content columns + split RPCs
-- Fresh install: use setup_schema.sql instead.

alter table chunks add column if not exists chapter text not null default '';
alter table chunks add column if not exists heading text not null default '';

-- Migrate chapter/heading from metadata when present
update chunks
set chapter = coalesce(nullif(chapter, ''), metadata->>'chapter', ''),
    heading = coalesce(nullif(heading, ''), metadata->>'heading', '')
where metadata ? 'chapter' or metadata ? 'heading';

-- Normalize content from content_v1 or legacy fields
alter table chunks add column if not exists content text;
update chunks
set content = coalesce(
    nullif(content, ''),
    content_v1,
    metadata->>'body',
    content_v2,
    ''
)
where content is null or content = '';

alter table chunks alter column content set not null;

alter table chunks drop column if exists content_v1;
alter table chunks drop column if exists content_v2;
alter table chunks drop column if exists embedding;
drop index if exists chunks_embedding_idx;

create index if not exists chunks_chapter_idx on chunks (chapter);
create index if not exists chunks_heading_idx on chunks (heading);

create or replace function match_documents_v1(
    query_embedding vector(1024),
    match_count int default 5,
    match_threshold float default 0.5
)
returns table (
    id bigint,
    document_id bigint,
    chunk_no integer,
    chapter text,
    heading text,
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
        c.chapter,
        c.heading,
        c.content,
        c.source_type,
        c.metadata,
        1 - (c.embedding_v1 <=> query_embedding) as similarity,
        d.title as document_title,
        d.file_name,
        d.file_path
    from chunks c
    join documents d on d.id = c.document_id
    where c.embedding_v1 is not null
      and 1 - (c.embedding_v1 <=> query_embedding) > match_threshold
    order by c.embedding_v1 <=> query_embedding
    limit match_count;
$$;

create or replace function match_documents_v2(
    query_embedding vector(1024),
    match_count int default 5,
    match_threshold float default 0.5
)
returns table (
    id bigint,
    document_id bigint,
    chunk_no integer,
    chapter text,
    heading text,
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
        c.chapter,
        c.heading,
        c.content,
        c.source_type,
        c.metadata,
        1 - (c.embedding_v2 <=> query_embedding) as similarity,
        d.title as document_title,
        d.file_name,
        d.file_path
    from chunks c
    join documents d on d.id = c.document_id
    where c.embedding_v2 is not null
      and 1 - (c.embedding_v2 <=> query_embedding) > match_threshold
    order by c.embedding_v2 <=> query_embedding
    limit match_count;
$$;

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
language plpgsql stable
as $$
begin
    if embed_version = 'v1' then
        return query
        select
            r.id,
            r.document_id,
            r.chunk_no,
            r.content,
            r.source_type,
            r.metadata,
            r.similarity,
            r.document_title,
            r.file_name,
            r.file_path
        from match_documents_v1(query_embedding, match_count, match_threshold) r;
    end if;

    return query
    select
        r.id,
        r.document_id,
        r.chunk_no,
        r.content,
        r.source_type,
        r.metadata,
        r.similarity,
        r.document_title,
        r.file_name,
        r.file_path
    from match_documents_v2(query_embedding, match_count, match_threshold) r;
end;
$$;
