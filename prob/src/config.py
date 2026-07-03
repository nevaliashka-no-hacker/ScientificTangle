import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Elasticsearch
    ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
    ES_INDEX = "scientific_docs"
    
    # NLP Models
    NER_MODEL = "DeepPavlov/rubert-base-cased"
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Paths
    GLOSSARY_PATH = "data/glossary.json"
    ONTOLOGY_PATH = "data/ontology.yaml"
    
    # Search
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7
    MAX_GRAPH_HOPS = 4