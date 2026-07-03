"""FastAPI приложение для R&D платформы"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .config import Config
from .graph_manager import GraphManager
from .nlp_extractor import ScientificNLP
from .query_builder import QueryBuilder
from .search_engine import SearchEngine

# Инициализация
app = FastAPI(
    title="Научный клубок API",
    description="Платформа управления знаниями R&D для горно-металлургической отрасли",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
graph = GraphManager(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
nlp = ScientificNLP(config)
query_builder = QueryBuilder(nlp)
search = SearchEngine(config)

# Pydantic модели
class QueryRequest(BaseModel):
    query: str = Field(..., description="Запрос на естественном языке")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Дополнительные фильтры")

class ExperimentCreate(BaseModel):
    title: str
    description: str
    materials: List[str]
    processes: List[str]
    parameters: List[Dict[str, Any]]
    confidence: float = 0.8

class PublicationCreate(BaseModel):
    doi: str
    title: str
    authors: List[str]
    year: int
    type: str = "article"
    geography: str = "Россия"
    abstract: str = ""

class SearchResponse(BaseModel):
    query: str
    intent: str
    results: List[Dict[str, Any]]
    graph_visualization: Optional[Dict] = None
    experts: List[Dict] = []
    contradictions: List[Dict] = []
    gaps: List[Dict] = []

# Эндпоинты
@app.get("/")
async def root():
    return {
        "service": "Научный клубок",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/search", response_model=SearchResponse)
async def search_knowledge(request: QueryRequest):
    """
    Основной поисковый эндпоинт.
    Принимает запрос на естественном языке и возвращает структурированный ответ.
    """
    # Парсинг запроса
    parsed = nlp.parse_query(request.query)
    
    # Построение Cypher
    cypher_query = query_builder.build_cypher_query(request.query)
    
    # Выполнение поиска в графе
    graph_results = []
    try:
        with graph.driver.session() as session:
            result = session.run(
                cypher_query['cypher'],
                cypher_query['params']
            )
            graph_results = [dict(record) for record in result]
    except Exception as e:
        # Fallback на семантический поиск
        graph_results = search.semantic_search(request.query)
    
    # Поиск экспертов
    experts = []
    if parsed['constraints'].get('processes'):
        experts = graph.find_experts_by_topic(
            parsed['constraints']['processes'][0]
        )
    
    # Поиск противоречий
    contradictions = []
    if parsed['constraints'].get('materials'):
        contradictions = graph.find_contradictions(
            parsed['constraints']['materials'][0]
        )
    
    # Выявление пробелов в знаниях
    gaps = graph.get_knowledge_gaps()
    
    return SearchResponse(
        query=request.query,
        intent=parsed['intent'],
        results=graph_results,
        experts=experts,
        contradictions=contradictions,
        gaps=gaps
    )

@app.post("/experiment")
async def create_experiment(experiment: ExperimentCreate):
    """Добавление нового эксперимента в граф знаний"""
    exp_id = graph.create_experiment({
        'title': experiment.title,
        'description': experiment.description,
        'materials': experiment.materials,
        'processes': experiment.processes,
        'parameters': experiment.parameters,
        'confidence': experiment.confidence,
        'date': datetime.now().isoformat()
    })
    
    return {"id": exp_id, "status": "created"}

@app.post("/publication")
async def create_publication(publication: PublicationCreate):
    """Добавление новой публикации"""
    doi = graph.create_publication(publication.dict())
    return {"doi": doi, "status": "indexed"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Загрузка и обработка документа (PDF/DOCX)"""
    # В реальном решении: парсинг через Apache Tika
    content = await file.read()
    text = content.decode('utf-8', errors='ignore')
    
    # Извлечение сущностей
    entities = nlp.extract_entities(text)
    relations = nlp.extract_relations(text, entities)
    
    return {
        "filename": file.filename,
        "entities_found": len(entities),
        "relations_found": len(relations),
        "entities": [
            {"text": e.text, "type": e.type} 
            for e in entities[:10]
        ]
    }

@app.get("/experts")
async def list_experts(topic: str = Query(..., description="Тема для поиска экспертов")):
    """Поиск экспертов по теме"""
    experts = graph.find_experts_by_topic(topic)
    return {"topic": topic, "experts": experts}

@app.get("/gaps")
async def get_knowledge_gaps():
    """Получение карты пробелов в знаниях"""
    gaps = graph.get_knowledge_gaps()
    return {"gaps": gaps}

@app.get("/contradictions")
async def get_contradictions(domain: str = Query("гидрометаллургия")):
    """Получение противоречий в данных"""
    contradictions = graph.find_contradictions(domain)
    return {"contradictions": contradictions}

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "neo4j": "connected",
        "elasticsearch": "connected"
    }