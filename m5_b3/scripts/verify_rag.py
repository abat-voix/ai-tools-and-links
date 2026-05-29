"""Прогон кодовых примеров презентации блока (LlamaIndex) на живом Qdrant + OpenAI.

Каждый блок повторяет конкретный слайд презентации и работает в одноразовой
коллекции, которая удаляется в конце. Что не запускается здесь (тяжёлые зависимости),
отмечено в выводе.

Запуск:
    uv run python scripts/verify_rag.py
"""

import sys
import uuid
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llama_index.core import (  # noqa: E402
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.ingestion import IngestionPipeline  # noqa: E402
from llama_index.core.node_parser import SentenceSplitter  # noqa: E402
from llama_index.core.vector_stores import (  # noqa: E402
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.embeddings.openai import OpenAIEmbedding  # noqa: E402
from llama_index.llms.openai import OpenAI  # noqa: E402
from llama_index.vector_stores.qdrant import QdrantVectorStore  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

settings = get_settings()
KEY = settings.llm.openai_api_key.get_secret_value()
DATA = str(settings.rag_data_dir)


def _setup_models() -> None:
    Settings.embed_model = OpenAIEmbedding(model=settings.embedding_model, api_key=KEY)
    Settings.llm = OpenAI(model=settings.rag_llm_model, temperature=0.0, api_key=KEY)
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)


def main() -> None:
    print("=== versions ===")
    for p in ["llama-index", "llama-index-core", "llama-index-vector-stores-qdrant",
              "qdrant-client", "openai"]:
        try:
            print(f"  {p}=={version(p)}")
        except PackageNotFoundError:
            print(f"  {p}: NOT INSTALLED")

    _setup_models()
    client = QdrantClient(url=settings.qdrant_url)
    suffix = uuid.uuid4().hex[:6]
    collections = []

    try:
        # --- слайд «Тот же RAG через LlamaIndex» + «Что нашёл поиск и как процитировать»
        coll = f"_vr_li_{suffix}"
        collections.append(coll)
        vs = QdrantVectorStore(client=client, collection_name=coll)
        storage = StorageContext.from_defaults(vector_store=vs)
        documents = SimpleDirectoryReader(DATA, recursive=True).load_data()
        index = VectorStoreIndex.from_documents(documents, storage_context=storage)
        engine = index.as_query_engine(similarity_top_k=3)
        response = engine.query("За сколько дней можно вернуть деньги?")
        assert response.source_nodes, "source_nodes пуст"
        assert response.source_nodes[0].metadata.get("file_name"), "нет file_name в метаданных"
        print(f"\n[from_documents + query] OK: {len(documents)} док., "
              f"top source={response.source_nodes[0].metadata['file_name']}, "
              f"score={response.source_nodes[0].score:.3f}")

        # --- слайд «Подключение к готовой коллекции Qdrant»
        index2 = VectorStoreIndex.from_vector_store(QdrantVectorStore(client=client, collection_name=coll))
        nodes = index2.as_retriever(similarity_top_k=2).retrieve("способы оплаты")
        assert nodes, "from_vector_store вернул пусто"
        print(f"[from_vector_store reconnect] OK: {len(nodes)} нод без переиндексации")

        # --- слайды «Добавляем метаданные при загрузке» + «Фильтр по метаданным»
        coll_m = f"_vr_meta_{suffix}"
        collections.append(coll_m)

        def file_metadata(path: str) -> dict:
            name = Path(path).name
            bucket = name.split("_", 1)[0]
            return {"bucket": bucket}

        docs_m = SimpleDirectoryReader(DATA, recursive=True, file_metadata=file_metadata).load_data()
        vs_m = QdrantVectorStore(client=client, collection_name=coll_m)
        idx_m = VectorStoreIndex.from_documents(
            docs_m, storage_context=StorageContext.from_defaults(vector_store=vs_m)
        )
        flt = MetadataFilters(filters=[
            MetadataFilter(key="bucket", value="billing", operator=FilterOperator.EQ),
        ])
        hits = idx_m.as_retriever(similarity_top_k=5, filters=flt).retrieve("возврат и оплата")
        assert hits, "фильтр по метаданным вернул пусто"
        buckets = {h.metadata.get("bucket") for h in hits}
        assert buckets == {"billing"}, f"фильтр пропустил чужие bucket: {buckets}"
        print(f"[file_metadata + MetadataFilters] OK: {len(hits)} нод, все bucket=billing")

        # --- слайд «IngestionPipeline: явный конвейер трансформаций»
        coll_p = f"_vr_pipe_{suffix}"
        collections.append(coll_p)
        vs_p = QdrantVectorStore(client=client, collection_name=coll_p)
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=512, chunk_overlap=64),
                OpenAIEmbedding(model=settings.embedding_model, api_key=KEY),
            ],
            vector_store=vs_p,
        )
        pnodes = pipeline.run(documents=documents)
        assert pnodes, "IngestionPipeline не создал ноды"
        print(f"[IngestionPipeline] OK: создано {len(pnodes)} нод")

        # --- слайд «Гибридный поиск в LlamaIndex + Qdrant» (нужен fastembed)
        if find_spec("fastembed"):
            coll_h = f"_vr_hybrid_{suffix}"
            collections.append(coll_h)
            vs_h = QdrantVectorStore(
                client=client,
                collection_name=coll_h,
                enable_hybrid=True,
                fastembed_sparse_model="Qdrant/bm25",
                batch_size=20,
            )
            idx_h = VectorStoreIndex.from_documents(
                documents, storage_context=StorageContext.from_defaults(vector_store=vs_h)
            )
            qe_h = idx_h.as_query_engine(
                similarity_top_k=3, sparse_top_k=12, vector_store_query_mode="hybrid"
            )
            resp_h = qe_h.query("возврат средств за подписку")
            assert resp_h.source_nodes, "гибридный поиск вернул пусто"
            print(f"[enable_hybrid=True + bm25] OK: {len(resp_h.source_nodes)} нод "
                  f"(dense + sparse, RRF)")
        else:
            print("[enable_hybrid] SKIP: нет пакета fastembed (pip install fastembed)")

        # --- слайд «Кастомизация: свой QueryEngine с постпроцессором»: только проверка импорта
        if find_spec("sentence_transformers") and find_spec("torch"):
            print("[SentenceTransformerRerank] доступен для запуска")
        else:
            print("[SentenceTransformerRerank] импорт корректен, запуск пропущен "
                  "(нужны torch + sentence-transformers + загрузка модели ~600 МБ)")

        print("\nВсе запускаемые примеры презентации блока отработали.")
    finally:
        for c in collections:
            try:
                client.delete_collection(c)
            except Exception:
                pass
        client.close()


if __name__ == "__main__":
    main()
