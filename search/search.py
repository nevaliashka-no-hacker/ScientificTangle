from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np

class SemanticSearchJSON:
    """
    Семантический поиск с JSON интерфейсом.
    Принимает JSON с документами, возвращает JSON с результатами.
    """
    
    def __init__(self, 
                 es_host: str = "http://localhost:9200",
                 model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 index_name: str = "documents"):
        """
        Args:
            es_host: Адрес Elasticsearch
            model_name: Модель для эмбеддингов
            index_name: Название индекса
        """
        self.es = Elasticsearch(es_host)
        self.model = SentenceTransformer(model_name)
        self.index_name = index_name
        self._init_index()
    
    def _init_index(self):
        """Инициализация индекса Elasticsearch"""
        mapping = {
            "mappings": {
                "properties": {
                    "название": {"type": "keyword"},
                    "содержание": {"type": "text", "analyzer": "russian"},
                    "тип_файла": {"type": "keyword"},
                    "количество_страниц": {"type": "integer"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
        }
        
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=mapping)
    
    def load_documents(self, json_data: Dict) -> Dict:
        """
        Загрузка документов из JSON.
        
        Входной формат:
        {
            "метаданные": {
                "дата_обработки": "2024-01-15T10:30:00",
                "общее_количество_документов": 3,
                "типы_документов": {".pdf": 2, ".docx": 1}
            },
            "документы": [
                {
                    "название": "папка1/документ.pdf",
                    "содержание": "Текст документа...",
                    "тип_файла": ".pdf",
                    "количество_страниц": 10
                }
            ]
        }
        
        Returns:
            {
                "статус": "success",
                "загружено": 3,
                "ошибки": []
            }
        """
        errors = []
        loaded = 0
        
        for doc in json_data.get("документы", []):
            try:
                # Создание эмбеддинга
                embedding = self.model.encode(doc["содержание"]).tolist()
                
                # Документ для Elasticsearch
                es_doc = {
                    "название": doc["название"],
                    "содержание": doc["содержание"],
                    "тип_файла": doc["тип_файла"],
                    "количество_страниц": doc.get("количество_страниц", 0),
                    "embedding": embedding,
                    "дата_загрузки": datetime.now().isoformat()
                }
                
                self.es.index(index=self.index_name, body=es_doc)
                loaded += 1
                
            except Exception as e:
                errors.append({
                    "файл": doc.get("название", "неизвестно"),
                    "ошибка": str(e)
                })
        
        return {
            "статус": "success" if loaded > 0 else "error",
            "загружено": loaded,
            "всего_в_пакете": json_data.get("метаданные", {}).get("общее_количество_документов", 0),
            "ошибки": errors
        }
    
    def search(self, request: Dict) -> Dict:
        """
        Поиск по документам.
        
        Входной формат:
        {
            "query": "обессоливание шахтных вод",
            "top_k": 5,
            "filters": {
                "тип_файла": ".pdf",
                "мин_страниц": 5
            },
            "min_score": 0.5
        }
        
        Returns:
        {
            "метаданные": {
                "дата_поиска": "2024-01-15T10:30:00",
                "время_выполнения_мс": 45.2,
                "запрос": "обессоливание шахтных вод",
                "всего_найдено": 15,
                "возвращено": 5
            },
            "результаты": [...],
            "рекомендации": [...]
        }
        """
        import time
        start_time = time.time()
        
        query = request.get("query", "")
        top_k = request.get("top_k", 5)
        filters = request.get("filters", {})
        min_score = request.get("min_score", 0.0)
        
        # Создание эмбеддинга запроса
        query_embedding = self.model.encode(query).tolist()
        
        # Построение поискового запроса
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k * 2,  # Больше кандидатов для фильтрации
                "num_candidates": 100
            },
            "_source": ["название", "содержание", "тип_файла", "количество_страниц"]
        }
        
        # Добавление фильтров
        if filters:
            filter_clauses = []
            
            if "тип_файла" in filters:
                filter_clauses.append({
                    "term": {"тип_файла": filters["тип_файла"]}
                })
            
            if "мин_страниц" in filters:
                filter_clauses.append({
                    "range": {
                        "количество_страниц": {
                            "gte": filters["мин_страниц"]
                        }
                    }
                })
            
            if filter_clauses:
                search_body["post_filter"] = {
                    "bool": {"must": filter_clauses}
                }
        
        # Выполнение поиска
        try:
            results = self.es.search(index=self.index_name, body=search_body)
        except Exception as e:
            return {
                "метаданные": SearchMetadata(
                    дата_поиска=datetime.now().isoformat(),
                    время_выполнения_мс=0,
                    запрос=query,
                    всего_найдено=0,
                    возвращено=0
                ),
                "результаты": [],
                "рекомендации": [f"Ошибка поиска: {str(e)}"]
            }
        
        # Обработка результатов
        search_results = []
        for hit in results["hits"]["hits"]:
            score = hit["_score"]
            
            # Фильтрация по минимальному score
            if score < min_score:
                continue
            
            source = hit["_source"]
            
            # Извлечение релевантного фрагмента
            fragment = self._extract_fragment(
                source.get("содержание", ""),
                query,
                max_length=200
            )
            
            search_results.append(SearchResultItem(
                название=source.get("название", ""),
                тип_файла=source.get("тип_файла", ""),
                релевантность=round(score, 4),
                фрагмент=fragment,
                страниц=source.get("количество_страниц", 0)
            ))
            
            if len(search_results) >= top_k:
                break
        
        # Время выполнения
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Рекомендации
        recommendations = self._generate_recommendations(
            query, search_results, filters
        )
        
        # Формирование ответа
        response = {
            "метаданные": {
                "дата_поиска": datetime.now().isoformat(),
                "время_выполнения_мс": round(elapsed_ms, 2),
                "запрос": query,
                "всего_найдено": results["hits"]["total"]["value"],
                "возвращено": len(search_results)
            },
            "результаты": [asdict(r) for r in search_results],
            "рекомендации": recommendations
        }
        
        return response
    
    def _extract_fragment(self, text: str, query: str, max_length: int = 200) -> str:
        """Извлечение релевантного фрагмента текста"""
        
        # Поиск ключевых слов запроса в тексте
        query_words = set(query.lower().split())
        sentences = text.replace('\n', ' ').split('.')
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Считаем пересечение слов
            sentence_words = set(sentence.lower().split())
            score = len(query_words & sentence_words)
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        if best_sentence:
            if len(best_sentence) > max_length:
                # Ищем позицию ключевых слов
                pos = len(best_sentence) // 2
                for word in query_words:
                    idx = best_sentence.lower().find(word)
                    if idx != -1:
                        pos = idx
                        break
                
                start = max(0, pos - max_length // 2)
                end = min(len(best_sentence), start + max_length)
                best_sentence = "..." + best_sentence[start:end] + "..."
            
            return best_sentence
        
        return text[:max_length] + "..."
    
    def _generate_recommendations(self, 
                                  query: str, 
                                  results: List[SearchResultItem],
                                  filters: Dict) -> List[str]:
        """Генерация рекомендаций на основе результатов"""
        
        recommendations = []
        
        if len(results) == 0:
            recommendations.append("📌 По вашему запросу ничего не найдено")
            recommendations.append("💡 Попробуйте:")
            recommendations.append("  • Использовать синонимы (например, 'деминерализация' вместо 'обессоливание')")
            recommendations.append("  • Убрать фильтры для расширения поиска")
            recommendations.append("  • Проверить запрос на английском языке")
        
        elif len(results) < 3:
            recommendations.append(f"📌 Найдено только {len(results)} результатов")
            recommendations.append("💡 Рекомендации:")
            recommendations.append("  • Попробуйте убрать фильтры")
            recommendations.append("  • Используйте более общие термины")
        
        else:
            # Анализ типов файлов
            file_types = {}
            for r in results:
                ft = r.тип_файла
                file_types[ft] = file_types.get(ft, 0) + 1
            
            if len(file_types) == 1:
                ft = list(file_types.keys())[0]
                recommendations.append(f"📌 Все результаты имеют формат {ft}")
                recommendations.append(f"💡 Возможно, стоит поискать документы других форматов")
            
            # Рекомендация по релевантности
            avg_score = np.mean([r.релевантность for r in results])
            if avg_score < 0.7:
                recommendations.append("📌 Средняя релевантность низкая")
                recommendations.append("💡 Попробуйте уточнить запрос")
        
        return recommendations