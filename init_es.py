from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

# 1. Проверка соединения
print("1. Проверка Elasticsearch...")
info = es.info()
print(f"   ✓ Версия: {info['version']['number']}")

# 2. Создание индекса
print("\n2. Создание индекса...")
mapping = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "analyzer": "russian"},
            "abstract": {"type": "text", "analyzer": "russian"},
            "content": {"type": "text", "analyzer": "russian"},
            "embedding": {
                "type": "dense_vector",
                "dims": 384,
                "similarity": "cosine"
            },
            "year": {"type": "integer"},
            "geography": {"type": "keyword"},
            "materials": {"type": "keyword"},
            "processes": {"type": "keyword"},
        }
    }
}
es.indices.create(index="scientific_docs", body=mapping, ignore=400)
print("   ✓ Индекс scientific_docs создан")

# 3. Загрузка тестовых документов
print("\n3. Загрузка документов...")
docs = [
    {"title": "Электроэкстракция никеля", "content": "Исследование электроэкстракции никеля при 60°C", "year": 2024, "materials": ["никель"], "processes": ["электроэкстракция"]},
    {"title": "Обессоливание шахтных вод", "content": "Очистка воды от сульфатов 200-300 мг/л", "year": 2023, "materials": ["сульфаты"], "processes": ["обессоливание"]},
    {"title": "Nickel electrowinning", "content": "Study of nickel electrowinning process", "year": 2024, "materials": ["nickel"], "processes": ["electrowinning"]},
]

for doc in docs:
    doc["embedding"] = [0.0] * 384  # Заглушка (потом заменится реальным эмбеддингом)
    es.index(index="scientific_docs", body=doc)

print(f"   ✓ Загружено {len(docs)} документов")

# 4. Проверка
print("\n4. Проверка...")
count = es.count(index="scientific_docs")["count"]
print(f"   ✓ Документов в индексе: {count}")

print("\n✅ Elasticsearch настроен!")