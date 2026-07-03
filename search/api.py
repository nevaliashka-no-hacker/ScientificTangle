from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

class ESSearch:
    def __init__(self):
        self.es = Elasticsearch('http://localhost:9200')
        self.model = SentenceTransformer('model-name')
        self._create_index()
    
    def _create_index(self):
        mapping = {
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "similarity": "cosine"
                    }
                }
            }
        }
        self.es.indices.create(index="docs", body=mapping)
    
    def add(self, text):
        emb = self.model.encode(text).tolist()
        self.es.index(index="docs", body={
            "text": text,
            "embedding": emb
        })
    
    def search(self, query, top_k=5):
        q_emb = self.model.encode(query).tolist()
        # Нужно знать синтаксис kNN запроса
        return self.es.search(index="docs", body={
            "knn": {
                "field": "embedding",
                "query_vector": q_emb,
                "k": top_k
            }
        })