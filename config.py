import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).parent
    
    # Настройки базы данных
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Настройки поиска
    DEFAULT_MAX_RESULTS = 20
    DEFAULT_SEARCH_DEPTH = 3
    
    # Пути к данным
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models"
    
    # Настройки кэширования
    CACHE_TTL = 3600
    
    # Настройки визуализации
    GRAPHVIZ_ENGINE = "dot"
    PYVIS_OPTIONS = {
        "height": "500px",
        "width": "100%",
        "directed": True
    }


config = Config()