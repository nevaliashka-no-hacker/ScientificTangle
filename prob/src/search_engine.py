"""Семантический поиск с использованием Elasticsearch"""

from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np

class SearchEngine:
    def __init__(self, config):
        self.es = Elasticsearch(config.ES_HOST)
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.index_name = config.ES_INDEX
        self._init_index()
    
    def _init_index(self):
        """Инициализация индекса Elasticsearch"""
        mapping = {
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "russian"},
                    "abstract": {"type": "text", "analyzer": "russian"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "year": {"type": "integer"},
                    "geography": {"type": "keyword"},
                    "materials": {"type": "keyword"},
                    "processes": {"type": "keyword"},
                }
            }
        }
        
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=mapping)
    
    def index_document(self, doc: Dict):
        """Индексация документа с эмбеддингами"""
        text = f"{doc.get('title', '')} {doc.get('abstract', '')}"
        embedding = self.model.encode(text).tolist()
        
        doc['embedding'] = embedding
        self.es.index(index=self.index_name, body=doc)
    
    def semantic_search(self, query: str, top_k: int = 20) -> List[Dict]:
        """Семантический поиск по эмбеддингам"""
        query_embedding = self.model.encode(query).tolist()
        
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k,
                "num_candidates": 100
            },
            "_source": ["title", "abstract", "year", "geography"]
        }
        
        results = self.es.search(index=self.index_name, body=search_body)
        
        return [
            {
                "title": hit["_source"]["title"],
                "abstract": hit["_source"].get("abstract", ""),
                "year": hit["_source"].get("year"),
                "score": hit["_score"]
            }
            for hit in results["hits"]["hits"]
        ]