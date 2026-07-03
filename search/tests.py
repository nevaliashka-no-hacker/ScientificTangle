from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import numpy as np
import json

# Класс конфигурации (упрощённый)
class Config:
    ES_HOST = "http://localhost:9200"
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    ES_INDEX = "test_scientific_docs"

class Search:
    def __init__(self, config):
        self.es = Elasticsearch(config.ES_HOST)
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.index_name = config.ES_INDEX
        self._init_index()

    def _init_index(self):
        mapping = {
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text", 
                        "analyzer": "russian"
                    },
                    "abstract": {
                        "type": "text", 
                        "analyzer": "russian"
                    },
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
            print(f"✓ Индекс '{self.index_name}' создан")
        else:
            print(f"✓ Индекс '{self.index_name}' уже существует")

    def index_document(self, doc):
        text = f"{doc.get('title', '')} {doc.get('abstract', '')}"
        embedding = self.model.encode(text).tolist()
        doc['embedding'] = embedding
        self.es.index(index=self.index_name, body=doc)
        print(f"✓ Документ '{doc.get('title', '')}' добавлен")

    def semantic_search(self, request, top_k=20):
        embedding = self.model.encode(request).tolist()
        
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": top_k,
                "num_candidates": 100
            },
            "_source": ["title", "abstract", "year", "geography"]
        }
        
        results = self.es.search(index=self.index_name, body=search_body)
        
        return [
            {
                "title": hit["_source"]["title"],
                "abstract": hit["_source"].get("abstract", "")[:200] + "...",
                "year": hit["_source"].get("year"),
                "score": hit["_score"]
            }
            for hit in results["hits"]["hits"]
        ]

# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

print("=" * 60)
print("ТЕСТИРОВАНИЕ СЕМАНТИЧЕСКОГО ПОИСКА")
print("=" * 60)

# 1. Инициализация
print("\n1. Инициализация поискового движка...")
config = Config()
search = Search(config)
print("✓ Движок готов")

# 2. Добавление тестовых документов
print("\n2. Добавление тестовых документов...")

test_docs = [
    {
        "title": "Электроэкстракция никеля из сульфатных растворов",
        "abstract": "Исследование процесса электроэкстракции никеля. Оптимальная температура 60°C, скорость потока католита 0.08 м/с. Выход по току 95%.",
        "year": 2024,
        "geography": "Россия",
        "materials": ["никель", "сульфаты", "католит"],
        "processes": ["электроэкстракция"]
    },
    {
        "title": "Electrowinning of nickel from chloride media",
        "abstract": "Study of nickel electrowinning process using chloride-based electrolytes. Optimal conditions: 65°C, current density 200 A/m².",
        "year": 2023,
        "geography": "Зарубежье",
        "materials": ["никель", "хлориды", "электролит"],
        "processes": ["электроэкстракция"]
    },
    {
        "title": "Обессоливание шахтных вод методом обратного осмоса",
        "abstract": "Применение обратного осмоса для очистки шахтных вод от сульфатов и хлоридов. Исходная концентрация 200-300 мг/л, после очистки менее 50 мг/л.",
        "year": 2024,
        "geography": "Россия",
        "materials": ["сульфаты", "хлориды"],
        "processes": ["обессоливание", "обратный осмос"]
    },
    {
        "title": "Desalination of mine water using electrodialysis",
        "abstract": "Electrodialysis treatment of mining wastewater containing sulfates up to 500 mg/L. Removal efficiency >90%.",
        "year": 2023,
        "geography": "Зарубежье",
        "materials": ["сульфаты"],
        "processes": ["обессоливание", "электродиализ"]
    },
    {
        "title": "Плавка медного концентрата в печи взвешенной плавки",
        "abstract": "Исследование распределения золота и серебра между штейном и шлаком при плавке медного концентрата. Извлечение Au 98%, Ag 95%.",
        "year": 2022,
        "geography": "Россия",
        "materials": ["медь", "золото", "серебро", "штейн", "шлак"],
        "processes": ["плавка", "взвешенная плавка"]
    },
    {
        "title": "Кучное выщелачивание золота в холодном климате",
        "abstract": "Особенности кучного выщелачивания золотосодержащих руд при отрицательных температурах. Применение цианида натрия.",
        "year": 2021,
        "geography": "Россия",
        "materials": ["золото"],
        "processes": ["выщелачивание", "кучное выщелачивание"]
    }
]

for doc in test_docs:
    search.index_document(doc)

print(f"✓ Добавлено {len(test_docs)} документов")

# 3. Тестовые запросы
print("\n3. Выполнение тестовых запросов...")

test_queries = [
    {
        "query": "Какие методы обессоливания шахтных вод существуют?",
        "description": "Поиск методов обессоливания"
    },
    {
        "query": "электроэкстракция никеля оптимальные параметры",
        "description": "Параметры электроэкстракции"
    },
    {
        "query": "nickel electrowinning from sulfate solution",
        "description": "Английский запрос"
    },
    {
        "query": "извлечение драгоценных металлов при плавке",
        "description": "Плавка и драгметаллы"
    },
    {
        "query": "выщелачивание золота при низких температурах",
        "description": "Холодный климат"
    },
    {
        "query": "очистка воды от солей",
        "description": "Синонимы обессоливания"
    }
]

for test in test_queries:
    print(f"\n{'='*60}")
    print(f"Запрос: '{test['query']}'")
    print(f"Тема: {test['description']}")
    print('-'*60)
    
    results = search.semantic_search(test['query'], top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. {result['title']}")
        print(f"     Год: {result['year']}")
        print(f"     Релевантность: {result['score']:.4f}")
        print(f"     Аннотация: {result['abstract']}")

# 4. Проверка понимания синонимов
print(f"\n{'='*60}")
print("ПРОВЕРКА ПОНИМАНИЯ СИНОНИМОВ")
print('='*60)

synonym_tests = [
    ("обессоливание воды", "desalination"),
    ("электроэкстракция", "electrowinning"),
    ("очистка", "purification"),
    ("шахтные воды", "mine water"),
]

for ru_word, en_word in synonym_tests:
    emb_ru = search.model.encode(ru_word)
    emb_en = search.model.encode(en_word)
    
    # Косинусное сходство
    similarity = np.dot(emb_ru, emb_en) / (np.linalg.norm(emb_ru) * np.linalg.norm(emb_en))
    
    print(f"\n  '{ru_word}' ↔ '{en_word}'")
    print(f"  Сходство: {similarity:.4f} {'✓' if similarity > 0.7 else '✗'}")

# 5. Очистка (опционально)
print(f"\n{'='*60}")
print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
print(f"Для очистки индекса выполните:")
print(f"  curl -X DELETE http://localhost:9200/{config.ES_INDEX}")
print('='*60)