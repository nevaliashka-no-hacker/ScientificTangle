from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

class SemanticSearchJSONDemo:
    """
    Демо-версия семантического поиска.
    Работает без Elasticsearch, хранит всё в памяти.
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)
        self.documents: List[Dict] = []
        self.embeddings: List[np.ndarray] = []
    
    def load_documents(self, json_data: Dict) -> Dict:
        """Загрузка документов в память"""
        
        errors = []
        loaded = 0
        
        for doc in json_data.get("документы", []):
            try:
                embedding = self.model.encode(doc["содержание"])
                
                self.documents.append({
                    "название": doc["название"],
                    "содержание": doc["содержание"],
                    "тип_файла": doc["тип_файла"],
                    "количество_страниц": doc.get("количество_страниц", 0)
                })
                self.embeddings.append(embedding)
                loaded += 1
                
            except Exception as e:
                errors.append({"файл": doc.get("название"), "ошибка": str(e)})
        
        return {
            "статус": "success" if loaded > 0 else "error",
            "загружено": loaded,
            "ошибки": errors
        }
    
    def search(self, request: Dict) -> Dict:
        """Поиск по документам в памяти"""
        import time
        start_time = time.time()
        
        query = request.get("query", "")
        top_k = request.get("top_k", 5)
        filters = request.get("filters", {})
        min_score = request.get("min_score", 0.0)
        
        # Эмбеддинг запроса
        query_embedding = self.model.encode(query)
        
        # Расчёт сходства со всеми документами
        similarities = []
        for i, doc_emb in enumerate(self.embeddings):
            # Косинусное сходство
            sim = np.dot(query_embedding, doc_emb) / \
                  (np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb))
            similarities.append((sim, i))
        
        # Сортировка по убыванию
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Применение фильтров и формирование результатов
        results = []
        for score, idx in similarities:
            if score < min_score:
                continue
            
            doc = self.documents[idx]
            
            # Фильтрация
            if filters:
                if "тип_файла" in filters:
                    if doc["тип_файла"] != filters["тип_файла"]:
                        continue
                if "мин_страниц" in filters:
                    if doc["количество_страниц"] < filters["мин_страниц"]:
                        continue
            
            # Фрагмент текста
            fragment = doc["содержание"][:200] + "..."
            
            results.append({
                "название": doc["название"],
                "тип_файла": doc["тип_файла"],
                "релевантность": round(float(score), 4),
                "фрагмент": fragment,
                "страниц": doc["количество_страниц"]
            })
            
            if len(results) >= top_k:
                break
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "метаданные": {
                "дата_поиска": datetime.now().isoformat(),
                "время_выполнения_мс": round(elapsed_ms, 2),
                "запрос": query,
                "всего_найдено": len(similarities),
                "возвращено": len(results)
            },
            "результаты": results,
            "рекомендации": self._get_recommendations(results, filters)
        }
    
    def _get_recommendations(self, results: List, filters: Dict) -> List[str]:
        """Рекомендации"""
        if len(results) == 0:
            return [
                "Ничего не найдено. Попробуйте изменить запрос.",
                "Уберите фильтры для расширения поиска."
            ]
        return []


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

def test_semantic_search():
    """Тестирование семантического поиска"""
    
    print("="*70)
    print("ТЕСТИРОВАНИЕ СЕМАНТИЧЕСКОГО ПОИСКА (JSON)")
    print("="*70)
    
    # Тестовые данные в JSON формате
    input_json = {
        "метаданные": {
            "дата_обработки": "2024-01-15T10:30:00",
            "общее_количество_документов": 6,
            "типы_документов": {
                ".pdf": 3,
                ".docx": 2,
                ".txt": 1
            }
        },
        "документы": [
            {
                "название": "отчёты/электроэкстракция_никеля.pdf",
                "содержание": "Исследование процесса электроэкстракции никеля из сульфатных растворов. "
                             "Оптимальная температура 60°C, скорость циркуляции католита 0.08 м/с. "
                             "Выход по току достигает 95% при плотности тока 200 А/м².",
                "тип_файла": ".pdf",
                "количество_страниц": 15
            },
            {
                "название": "зарубежные/nickel_electrowinning.pdf",
                "содержание": "Study of nickel electrowinning from chloride media. "
                             "Optimal conditions: temperature 65°C, current density 250 A/m². "
                             "Current efficiency up to 92%.",
                "тип_файла": ".pdf",
                "количество_страниц": 12
            },
            {
                "название": "отчёты/обессоливание_шахтных_вод.docx",
                "содержание": "Применение обратного осмоса для обессоливания шахтных вод. "
                             "Исходная концентрация сульфатов 200-300 мг/л, хлоридов 150-250 мг/л. "
                             "После очистки содержание солей менее 50 мг/л. "
                             "Производительность установки 100 м³/сут.",
                "тип_файла": ".docx",
                "количество_страниц": 25
            },
            {
                "название": "зарубежные/mine_water_desalination.pdf",
                "содержание": "Desalination of mine water using electrodialysis. "
                             "Removal of sulfates up to 500 mg/L with efficiency >90%. "
                             "Energy consumption 2.5 kWh/m³.",
                "тип_файла": ".pdf",
                "количество_страниц": 18
            },
            {
                "название": "отчёты/плавка_меди_ПВП.docx",
                "содержание": "Исследование распределения золота и серебра между штейном и шлаком "
                             "при плавке медного концентрата в печи взвешенной плавки. "
                             "Извлечение золота в штейн 98%, серебра 95%.",
                "тип_файла": ".docx",
                "количество_страниц": 30
            },
            {
                "название": "заметки/идеи.txt",
                "содержание": "Идея: проверить кучное выщелачивание никеля в холодном климате. "
                             "Нет данных по этому направлению.",
                "тип_файла": ".txt",
                "количество_страниц": 1
            }
        ]
    }
    
    # Создаём поисковый движок
    print("\n1. Инициализация поискового движка...")
    search_engine = SemanticSearchJSONDemo()
    print("✓ Демо-режим (без Elasticsearch)")
    
    # Загружаем документы
    print("\n2. Загрузка документов...")
    result = search_engine.load_documents(input_json)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Тестовые запросы
    test_queries = [
        {
            "query": "Какие методы обессоливания шахтных вод существуют?",
            "top_k": 3,
            "min_score": 0.3
        },
        {
            "query": "оптимальные параметры электроэкстракции никеля",
            "top_k": 3,
            "filters": {"тип_файла": ".pdf"}
        },
        {
            "query": "nickel electrowinning temperature current density",
            "top_k": 3
        },
        {
            "query": "распределение драгоценных металлов при плавке",
            "top_k": 5,
            "filters": {"мин_страниц": 20}
        },
        {
            "query": "кучное выщелачивание холодный климат",
            "top_k": 3,
            "min_score": 0.5
        }
    ]
    
    print("\n3. Выполнение поисковых запросов...")
    
    for i, test_query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"ЗАПРОС {i}: {test_query['query']}")
        if test_query.get('filters'):
            print(f"Фильтры: {json.dumps(test_query['filters'], ensure_ascii=False)}")
        print('-'*70)
        
        results = search_engine.search(test_query)
        
        # Красивый вывод
        print(f"⏱ Время: {results['метаданные']['время_выполнения_мс']} мс")
        print(f"📊 Найдено: {results['метаданные']['всего_найдено']}, "
              f"показано: {results['метаданные']['возвращено']}")
        
        for j, result in enumerate(results['результаты'], 1):
            score_bar = "█" * int(result['релевантность'] * 20)
            print(f"\n  {j}. {result['название']}")
            print(f"     Тип: {result['тип_файла']} | "
                  f"Страниц: {result['страниц']}")
            print(f"     Релевантность: [{score_bar}] {result['релевантность']:.4f}")
            print(f"     Фрагмент: {result['фрагмент'][:100]}...")
        
        if results.get('рекомендации'):
            print(f"\n  💡 Рекомендации:")
            for rec in results['рекомендации']:
                print(f"     {rec}")
    
    # Экспорт результатов в JSON
    print(f"\n{'='*70}")
    print("4. Экспорт результатов...")
    
    export_query = {
        "query": "обессоливание воды от сульфатов",
        "top_k": 3
    }
    
    export_results = search_engine.search(export_query)
    
    with open("search_results.json", "w", encoding="utf-8") as f:
        json.dump(export_results, f, indent=2, ensure_ascii=False)
    
    print("✓ Результаты сохранены в search_results.json")
    
    print(f"\n{'='*70}")
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print('='*70)


if __name__ == "__main__":
    test_semantic_search()