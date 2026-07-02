# ─── Cell 8: Qdrant Vector Store (in-memory) ─────────────────────────────────
#
# QdrantClient(":memory:") = zero infrastructure required.
# To persist to disk:  QdrantClient(path="./qdrant_data")
# To use a server:     QdrantClient(host="localhost", port=6333)
#
# Collections:
#   topic_embeddings   : canonical topic names + aliases -> vector
#   summary_embeddings : topic summaries -> vector

class QdrantStore:
    'In-memory Qdrant vector store for semantic topic search.'

    TOPIC_COLL   = "topic_embeddings"
    SUMMARY_COLL = "summary_embeddings"
    VECTOR_SIZE  = 1536   # text-embedding-3-small dimensionality

    def __init__(self):
        self.client = QdrantClient(":memory:")
        self._embeddings = OpenAIEmbeddings(
            model=MODELS["embedding"],
            openai_api_key=OPENAI_API_KEY,
        )
        self._init_collections()

    def _init_collections(self):
        existing = {c.name for c in self.client.get_collections().collections}
        for name in [self.TOPIC_COLL, self.SUMMARY_COLL]:
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )

    # -- Embedding helpers --

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        'Embed in batches to respect API rate limits.'
        result = []
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            result.extend(self._embeddings.embed_documents(batch))
        return result

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    # -- Upsert --

    def upsert_topic(self, canonical_id: str, name: str,
                     aliases: List[str], embedding: List[float]):
        self.client.upsert(
            collection_name=self.TOPIC_COLL,
            points=[PointStruct(
                id=canonical_id,
                vector=embedding,
                payload={"canonical_id": canonical_id,
                         "canonical_name": name,
                         "aliases": aliases},
            )],
        )

    def upsert_summary(self, canonical_id: str, name: str,
                       summary: str, embedding: List[float]):
        self.client.upsert(
            collection_name=self.SUMMARY_COLL,
            points=[PointStruct(
                id=canonical_id,
                vector=embedding,
                payload={"canonical_id": canonical_id,
                         "canonical_name": name,
                         "summary": summary},
            )],
        )

    # -- Search --

    def search_similar_topics(self, query_vec: List[float], top_k: int = 5) -> List[Dict]:
        hits = self.client.search(
            collection_name=self.TOPIC_COLL,
            query_vector=query_vec,
            limit=top_k,
        )
        return [{"canonical_id":   h.payload["canonical_id"],
                 "canonical_name": h.payload["canonical_name"],
                 "aliases":        h.payload.get("aliases", []),
                 "score":          h.score} for h in hits]

    def search_summaries(self, query_vec: List[float], top_k: int = 5) -> List[Dict]:
        hits = self.client.search(
            collection_name=self.SUMMARY_COLL,
            query_vector=query_vec,
            limit=top_k,
        )
        return [{"canonical_id":   h.payload["canonical_id"],
                 "canonical_name": h.payload["canonical_name"],
                 "summary":        h.payload.get("summary", ""),
                 "score":          h.score} for h in hits]


qdrant_store = QdrantStore()
print("✅ Qdrant in-memory vector store ready")
print(f"   Collections: {[c.name for c in qdrant_store.client.get_collections().collections]}")
