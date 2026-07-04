from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import time
import os


@dataclass
class SearchResultItem:
    название: str
    тип_файла: str
    релевантность: float
    фрагмент: str
    страниц: int = 0


@dataclass
class SearchMetadata:
    дата_поиска: str
    время_выполнения_мс: float
    запрос: str
    всего_найдено: int
    возвращено: int


class SemanticSearchJSON:
    def __init__(self, 
                 es_host: str = "http://localhost:9200",
                 model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 index_name: str = "documents"):
        
        self.es = Elasticsearch(es_host)
        self.model = SentenceTransformer(model_name)
        self.index_name = index_name
        self._init_index()
    
    def _init_index(self):
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
        errors = []
        loaded = 0
        
        for doc in json_data.get("документы", []):
            try:
                embedding = self.model.encode(doc["содержание"]).tolist()
                
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
    
    def search(self, request: Dict, output_file: Optional[str] = None) -> Dict:
        start_time = time.time()
        
        query = request.get("query", "")
        top_k = request.get("top_k", 5)
        filters = request.get("filters", {})
        min_score = request.get("min_score", 0.0)
        
        query_embedding = self.model.encode(query).tolist()
        
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k * 2,  
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
        
        try:
            results = self.es.search(index=self.index_name, body=search_body)
        except Exception as e:
            error_response = {
                "метаданные": {
                    "дата_поиска": datetime.now().isoformat(),
                    "время_выполнения_мс": 0,
                    "запрос": query,
                    "всего_найдено": 0,
                    "возвращено": 0,
                    "статус": "error",
                    "ошибка": str(e)
                },
                "результаты": [],
                "рекомендации": [f"Ошибка поиска: {str(e)}"]
            }
            
            if output_file is None:
                output_file = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            self._save_to_json(error_response, output_file)
            return error_response
        
        search_results = []
        for hit in results["hits"]["hits"]:
            score = hit["_score"]
            
            if score < min_score:
                continue
            
            source = hit["_source"]
            
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
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        recommendations = self._generate_recommendations(
            query, search_results, filters
        )
        
        response = {
            "метаданные": {
                "дата_поиска": datetime.now().isoformat(),
                "время_выполнения_мс": round(elapsed_ms, 2),
                "запрос": query,
                "всего_найдено": results["hits"]["total"]["value"],
                "возвращено": len(search_results),
                "статус": "success"
            },
            "результаты": [asdict(r) for r in search_results],
            "рекомендации": recommendations
        }
        
        if output_file is None:
            output_file = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        self._save_to_json(response, output_file)
        
        return response
    
    def _save_to_json(self, data: Dict, output_file: str):
        try:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"Результаты поиска сохранены в: {output_file}")
            
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
    
    def _extract_fragment(self, text: str, query: str, max_length: int = 200) -> str:
        query_words = set(query.lower().split())
        sentences = text.replace('\n', ' ').split('.')
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_words = set(sentence.lower().split())
            score = len(query_words & sentence_words)
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        if best_sentence:
            if len(best_sentence) > max_length:
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
        
        recommendations = []
        
        if len(results) == 0:
            recommendations.append("По вашему запросу ничего не найдено")
            recommendations.append("Попробуйте:")
            recommendations.append("  - Использовать синонимы (например, 'деминерализация' вместо 'обессоливание')")
            recommendations.append("  - Убрать фильтры для расширения поиска")
            recommendations.append("  - Проверить запрос на английском языке")
        
        elif len(results) < 3:
            recommendations.append(f"Найдено только {len(results)} результатов")
            recommendations.append("Рекомендации:")
            recommendations.append("  - Попробуйте убрать фильтры")
            recommendations.append("  - Используйте более общие термины")
        
        else:
            # Анализ типов файлов
            file_types = {}
            for r in results:
                ft = r.тип_файла
                file_types[ft] = file_types.get(ft, 0) + 1
            
            if len(file_types) == 1:
                ft = list(file_types.keys())[0]
                recommendations.append(f"Все результаты имеют формат {ft}")
                recommendations.append(f"Возможно, стоит поискать документы других форматов")
            
            avg_score = np.mean([r.релевантность for r in results])
            if avg_score < 0.7:
                recommendations.append("Средняя релевантность низкая")
                recommendations.append("Попробуйте уточнить запрос")
        
        return recommendations