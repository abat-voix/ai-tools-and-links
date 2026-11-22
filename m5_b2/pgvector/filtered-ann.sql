\set ON_ERROR_STOP on
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extversion AS pgvector FROM pg_extension WHERE extname = 'vector';

CREATE TEMP TABLE demo_documents (
    id integer PRIMARY KEY,
    organization_id integer NOT NULL,
    embedding vector(3) NOT NULL
);

SELECT setseed(0.42);
INSERT INTO demo_documents
SELECT n,
       CASE WHEN n % 100 = 0 THEN 42 ELSE 7 END,
       ARRAY[random(), random(), random()]::vector(3)
FROM generate_series(1, 12000) AS s(n);

CREATE INDEX demo_documents_hnsw ON demo_documents USING hnsw (embedding vector_cosine_ops);
ANALYZE demo_documents;
SELECT count(*) AS total, count(*) FILTER (WHERE organization_id = 42) AS matching
FROM demo_documents;

-- План фиксируется только для учебного сравнения. В приложении решение принимает планировщик.
SET LOCAL enable_seqscan = off;
SET LOCAL hnsw.ef_search = 40;
SET LOCAL hnsw.iterative_scan = off;

\echo HNSW, ef_search=40, повторный обход выключен
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM demo_documents
WHERE organization_id = 42
ORDER BY embedding <=> '[1,0,0]'::vector
LIMIT 10;

SET LOCAL hnsw.iterative_scan = strict_order;

\echo HNSW, strict_order
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM demo_documents
WHERE organization_id = 42
ORDER BY embedding <=> '[1,0,0]'::vector
LIMIT 10;

SET LOCAL enable_seqscan = on;
SET LOCAL enable_indexscan = off;
SET LOCAL enable_bitmapscan = off;

\echo Точный контроль с тем же фильтром
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM demo_documents
WHERE organization_id = 42
ORDER BY embedding <=> '[1,0,0]'::vector
LIMIT 10;

ROLLBACK;
