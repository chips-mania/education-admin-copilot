-- STEP 2: Supabase SQL Editor에서 실행


create extension if not exists vector;

create table documents (
    id bigint generated always as identity primary key,
    title text not null,
    source_type text not null,
    file_name text not null,
    file_path text not null,
    created_at timestamptz default now(),

    constraint documents_source_type_check check (
        source_type in ('manual', 'law', 'regulation', 'interpretation')
    )
);

create table chunks (
    id bigint generated always as identity primary key,
    document_id bigint not null references documents(id) on delete cascade,
    chunk_no integer not null,
    content text not null,
    source_type text not null,
    metadata jsonb default '{}'::jsonb,
    embedding vector(1024),

    constraint chunks_source_type_check check (
        source_type in ('manual', 'law', 'regulation', 'interpretation')
    )
);

create index chunks_embedding_idx
    on chunks using hnsw (embedding vector_cosine_ops);

create index chunks_metadata_idx
    on chunks using gin (metadata);

create or replace function match_documents(
    query_embedding vector(1024),
    match_count int default 5,
    match_threshold float default 0.5
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
        1 - (c.embedding <=> query_embedding) as similarity,
        d.title as document_title,
        d.file_name,
        d.file_path
    from chunks c
    join documents d on d.id = c.document_id
    where c.embedding is not null
      and 1 - (c.embedding <=> query_embedding) > match_threshold
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
