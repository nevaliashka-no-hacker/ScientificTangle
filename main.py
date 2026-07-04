import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from Data_Typization_Realization.typed import DocumentTypizer
from Graph_Data_Base.Graph_Data_Base import ScientificTangleKnowledgeGraph
from search.search import SemanticSearchJSON


class DocumentPipeline:
    def __init__(
        self,
        es_host: str = "http://localhost:9200",
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        index_name: str = "scientific_docs"
    ):
        
        self.typizer = DocumentTypizer()
        self.knowledge_graph = ScientificTangleKnowledgeGraph()
        self.search_engine = SemanticSearchJSON(
            es_host=es_host,
            model_name=model_name,
            index_name=index_name
        )
        
        self.stats = {
            'documents_processed': 0,
            'entities_extracted': 0,
            'relationships_created': 0,
            'search_index_size': 0
        }
    
    def process_archive(self,
        archive_path: str = None,
        output_json: str = "documents.json",
        build_graph: bool = True,
        index_for_search: bool = True
        ) -> Dict:

        if archive_path is None:
            archive_path = self._ask_archive_path()

        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Файл не найден: {archive_path}")
        
        if not archive_path.lower().endswith('.zip'):
            print("Предупреждение: Файл не имеет расширения .zip")
            user_confirm = input("Продолжить? (y/n): ").strip().lower()
            if user_confirm != 'y':
                print("Операция отменена")
                return {'статус': 'cancelled', 'статистика': self.stats}

        print("\n" + "="*70)
        print("ЗАПУСК ПАЙПЛАЙНА ОБРАБОТКИ ДОКУМЕНТОВ")
        print("="*70)
        
        print("\nЭТАП 1: Типизация документов...")
        documents = self.typizer.process_zip_file(archive_path, output_json)
        
        with open(output_json, 'r', encoding='utf-8') as f:
            typed_data = json.load(f)
        
        self.stats['documents_processed'] = len(documents)
        
        if index_for_search:
            print("\nЭТАП 2: Индексация для семантического поиска...")
            index_result = self.search_engine.load_documents(typed_data)
            self.stats['search_index_size'] = index_result.get('загружено', 0)
            print(f"  Проиндексировано: {index_result.get('загружено', 0)} документов")
        
        if build_graph:
            print("\nЭТАП 3: Построение графа знаний...")
            self._build_knowledge_graph(typed_data)
            self.knowledge_graph.print_graph_summary()
        
        return self._generate_pipeline_report()
    
    def _build_knowledge_graph(self, typed_data: Dict):
        for doc in typed_data.get('документы', []):
            if doc.get('статус') != 'success':
                continue
            
            content = doc.get('содержание', '')
            doc_name = doc.get('название', '')
            doc_type = doc.get('тип_файла', '')
            
            entities = self._extract_entities(content, doc_type)
            
            doc_node = self.knowledge_graph.add_entity(
                'Publication',
                {
                    'title': doc_name,
                    'type': doc_type,
                    'source': 'document_processing',
                    'processed_date': datetime.now().isoformat()
                }
            )
            
            for entity in entities:
                entity_node = self.knowledge_graph.add_entity(
                    entity['type'],
                    entity['properties']
                )
                
                self.knowledge_graph.add_relationship(
                    doc_node,
                    entity_node,
                    'described_in',
                    {'confidence': entity.get('confidence', 0.5)}
                )
                
                self.stats['entities_extracted'] += 1
                self.stats['relationships_created'] += 1
    
    def _extract_entities(self, content: str, doc_type: str) -> List[Dict]:
        entities = []
        content_lower = content.lower()
        
        patterns = {
            'Material': [
                'желез', 'мед', 'никел', 'цинк', 'алюмини',
                'стал', 'чугун', 'бронз', 'латун', 'титан'
            ],
            'Process': [
                'плавк', 'обжиг', 'флотац', 'выщелачива',
                'электролиз', 'агломерац', 'дроблен'
            ],
            'Equipment': [
                'печ', 'дробилк', 'мельниц', 'фильтр',
                'центрифуг', 'реактор', 'конвейер'
            ],
            'Property': [
                'температур', 'давлен', 'плотност', 'вязкост',
                'прочност', 'твердост', 'теплопроводност'
            ]
        }
        
        found_entities = set()
        
        for entity_type, roots in patterns.items():
            for root in roots:
                if root in content_lower:
                    full_names = {
                        'желез': 'железо', 'мед': 'медь', 'никел': 'никель',
                        'цинк': 'цинк', 'алюмини': 'алюминий', 'стал': 'сталь',
                        'чугун': 'чугун', 'бронз': 'бронза', 'латун': 'латунь',
                        'титан': 'титан', 'плавк': 'плавка', 'обжиг': 'обжиг',
                        'флотац': 'флотация', 'выщелачива': 'выщелачивание',
                        'электролиз': 'электролиз', 'агломерац': 'агломерация',
                        'дроблен': 'дробление', 'печ': 'печь',
                        'дробилк': 'дробилка', 'мельниц': 'мельница',
                        'фильтр': 'фильтр', 'центрифуг': 'центрифуга',
                        'реактор': 'реактор', 'конвейер': 'конвейер',
                        'температур': 'температура', 'давлен': 'давление',
                        'плотност': 'плотность', 'вязкост': 'вязкость',
                        'прочност': 'прочность', 'твердост': 'твердость',
                        'теплопроводност': 'теплопроводность'
                    }
                    
                    entity_key = f"{entity_type}:{root}"
                    if entity_key not in found_entities:
                        found_entities.add(entity_key)
                        entities.append({
                            'type': entity_type,
                            'properties': {
                                'name': full_names.get(root, root),
                                'source_document_type': doc_type
                            },
                            'confidence': 0.7
                        })
        
        return entities
    
    def search_documents(self, query: str, **kwargs) -> Dict:
        search_request = {
            "query": query,
            **kwargs
        }
        return self.search_engine.search(search_request)
    
    def search_and_relate(self, query: str, top_k: int = 5) -> Dict:
        search_results = self.search_documents(query, top_k=top_k)
        
        enriched_results = []
        for result in search_results.get('результаты', []):
            doc_name = result.get('название', '')
            
            try:
                node_info = self.knowledge_graph.get_node_with_relationships(
                    doc_name,
                    entity_type='Publication',
                    depth=1
                )
                result['related_entities'] = [
                    conn['properties'].get('name', '')
                    for conn in node_info.get('connected_nodes', {}).get('outgoing', [])
                ]
            except:
                result['related_entities'] = []
            
            enriched_results.append(result)
        
        search_results['результаты'] = enriched_results
        return search_results
    
    def export_graph(self, filepath: str = "knowledge_graph.json"):
        self.knowledge_graph.export_to_json(filepath)
    
    def load_graph(self, filepath: str):
        self.knowledge_graph.load_from_json(filepath)
    
    def _generate_pipeline_report(self) -> Dict:
        return {
            'статус': 'completed',
            'статистика': self.stats,
            'граф_знаний': {
                'узлов': self.knowledge_graph.graph.node_count(),
                'связей': self.knowledge_graph.graph.edge_count()
            }
        }