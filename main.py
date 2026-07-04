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
        archive_path: str,
        output_json: str = "documents.json",
        build_graph: bool = True,
        index_for_search: bool = True) -> Dict:
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
                'железо', 'медь', 'никель', 'цинк', 'алюминий',
                'сталь', 'чугун', 'бронза', 'латунь', 'титан'
            ],
            'Process': [
                'плавка', 'обжиг', 'флотация', 'выщелачивание',
                'электролиз', 'агломерация', 'дробление'
            ],
            'Equipment': [
                'печь', 'дробилка', 'мельница', 'фильтр',
                'центрифуга', 'реактор', 'конвейер'
            ],
            'Property': [
                'температура', 'давление', 'плотность', 'вязкость',
                'прочность', 'твердость', 'теплопроводность'
            ]
        }
        
        for entity_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in content_lower:
                    entities.append({
                        'type': entity_type,
                        'properties': {
                            'name': keyword,
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


def demo_pipeline():
    
    pipeline = DocumentPipeline()
    
    result = pipeline.process_archive(
        archive_path="sample_data.zip",
        build_graph=True,
        index_for_search=True
    )
    
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
    print("="*70)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\nПОИСК ПО ДОКУМЕНТАМ...")
    search_result = pipeline.search_and_relate("технология флотации медных руд")
    print(json.dumps(search_result, ensure_ascii=False, indent=2))
    
    pipeline.export_graph("knowledge_graph.json")
    
    return pipeline


if __name__ == "__main__":
    pipeline = demo_pipeline()