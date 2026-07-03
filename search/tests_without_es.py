# test_without_es.py - работает без Elasticsearch
from sentence_transformers import SentenceTransformer
import numpy as np

print("=" * 60)
print("ТЕСТ СЕМАНТИЧЕСКОГО ПОИСКА (БЕЗ ELASTICSEARCH)")
print("=" * 60)

# 1. Загрузка модели
print("\n1. Загрузка модели...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("✓ Модель загружена")

# 2. Тестовые документы
print("\n2. Подготовка документов...")
documents = [
    {
        "title": "Электроэкстракция никеля из сульфатных растворов",
        "abstract": "Исследование процесса электроэкстракции никеля. Оптимальная температура 60°C, скорость потока католита 0.08 м/с.",
        "year": 2024,
        "geography": "Россия"
    },
    {
        "title": "Electrowinning of nickel from chloride media",
        "abstract": "Study of nickel electrowinning process using chloride-based electrolytes.",
        "year": 2023,
        "geography": "Зарубежье"
    },
    {
        "title": "Обессоливание шахтных вод обратным осмосом",
        "abstract": "Очистка шахтных вод от сульфатов и хлоридов. Концентрация 200-300 мг/л.",
        "year": 2024,
        "geography": "Россия"
    },
    {
        "title": "Desalination of mine water using electrodialysis",
        "abstract": "Electrodialysis treatment of mining wastewater containing sulfates up to 500 mg/L.",
        "year": 2023,
        "geography": "Зарубежье"
    },
    {
        "title": "Плавка медного концентрата в печи взвешенной плавки",
        "abstract": "Исследование распределения золота и серебра между штейном и шлаком.",
        "year": 2022,
        "geography": "Россия"
    }
]

# 3. Создание эмбеддингов
print("\n3. Создание эмбеддингов для документов...")
for doc in documents:
    text = f"{doc['title']} {doc['abstract']}"
    doc['embedding'] = model.encode(text)
    print(f"  ✓ {doc['title'][:50]}...")

# 4. Функция поиска
def semantic_search(query, documents, top_k=3):
    query_embedding = model.encode(query)
    
    results = []
    for doc in documents:
        # Косинусное сходство
        similarity = np.dot(query_embedding, doc['embedding']) / \
                     (np.linalg.norm(query_embedding) * np.linalg.norm(doc['embedding']))
        results.append({
            "title": doc['title'],
            "year": doc['year'],
            "geography": doc['geography'],
            "similarity": float(similarity)
        })
    
    # Сортировка по убыванию сходства
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]

# 5. Тестовые запросы
print("\n4. Выполнение тестовых запросов...")

test_queries = [
    "Какие методы обессоливания шахтных вод существуют?",
    "электроэкстракция никеля оптимальные параметры",
    "nickel electrowinning process",
    "извлечение драгоценных металлов при плавке",
    "очистка воды от солей и сульфатов",
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"🔍 Запрос: '{query}'")
    print('-'*60)
    
    results = semantic_search(query, documents, top_k=3)
    
    for i, result in enumerate(results, 1):
        # Визуализация релевантности
        bar = "█" * int(result['similarity'] * 20)
        print(f"\n  {i}. {result['title']}")
        print(f"     Год: {result['year']} | Страна: {result['geography']}")
        print(f"     Релевантность: [{bar}] {result['similarity']:.4f}")

# 6. Проверка мультиязычности
print(f"\n{'='*60}")
print("🌍 ПРОВЕРКА МУЛЬТИЯЗЫЧНОСТИ")
print('='*60)

synonym_pairs = [
    ("обессоливание воды", "water desalination"),
    ("электроэкстракция", "electrowinning"),
    ("очистка шахтных вод", "mine water treatment"),
    ("никель", "nickel"),
    ("платина", "platinum"),
]

for ru, en in synonym_pairs:
    emb_ru = model.encode(ru)
    emb_en = model.encode(en)
    
    similarity = np.dot(emb_ru, emb_en) / \
                 (np.linalg.norm(emb_ru) * np.linalg.norm(emb_en))
    
    status = "✓" if similarity > 0.7 else "✗"
    print(f"  '{ru}' ↔ '{en}' = {similarity:.4f} {status}")

# 7. Проверка скорости
import time

print(f"\n{'='*60}")
print("⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
print('='*60)

start = time.time()
for _ in range(100):
    semantic_search("электроэкстракция никеля", documents, top_k=3)
end = time.time()

print(f"  100 поисков за {end - start:.3f} секунд")
print(f"  Среднее время: {(end - start)/100*1000:.1f} мс на запрос")

print(f"\n{'='*60}")
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
print('='*60)