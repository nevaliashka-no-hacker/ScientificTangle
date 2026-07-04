"""
main.py - Пайплайн обработки документов и поиска информации.
Возвращает структурированные данные для фронтенда в формате JSON.
"""

import json
import os
from typing import Dict, List
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
    
    def process_archive(self, archive_path: str, output_json: str = "documents.json",
                        build_graph: bool = True, index_for_search: bool = True) -> Dict:
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Файл не найден: {archive_path}")
        
        documents = self.typizer.process_zip_file(archive_path, output_json)
        
        with open(output_json, 'r', encoding='utf-8') as f:
            typed_data = json.load(f)
        
        self.stats['documents_processed'] = len(documents)
        
        if index_for_search:
            self.stats['search_index_size'] = self.search_engine.load_documents(typed_data).get('загружено', 0)
        
        if build_graph:
            self._build_knowledge_graph(typed_data)
        
        return {'статус': 'ok', 'обработано_документов': self.stats['documents_processed']}
    
    def _build_knowledge_graph(self, typed_data: Dict):
        for doc in typed_data.get('документы', []):
            if doc.get('статус') != 'success':
                continue
            
            content = doc.get('содержание', '')
            doc_name = doc.get('название', '')
            doc_type = doc.get('тип_файла', '')
            
            entities = self._extract_entities(content, doc_type)
            
            doc_node = self.knowledge_graph.add_entity('Publication', {
                'title': doc_name, 'type': doc_type,
                'source': 'document_processing',
                'processed_date': datetime.now().isoformat()
            })
            
            for entity in entities:
                entity_node = self.knowledge_graph.add_entity(entity['type'], entity['properties'])
                self.knowledge_graph.add_relationship(doc_node, entity_node, 'described_in',
                    {'confidence': entity.get('confidence', 0.5)})
                self.stats['entities_extracted'] += 1
                self.stats['relationships_created'] += 1
            
            materials = [e for e in entities if e['type'] == 'Material']
            processes = [e for e in entities if e['type'] == 'Process']
            equipments = [e for e in entities if e['type'] == 'Equipment']
            
            for m in materials:
                mn = self.knowledge_graph.add_entity('Material', m['properties'])
                for p in processes:
                    pn = self.knowledge_graph.add_entity('Process', p['properties'])
                    self.knowledge_graph.add_relationship(mn, pn, 'processed_by', {'document': doc_name})
                    for e in equipments:
                        en = self.knowledge_graph.add_entity('Equipment', e['properties'])
                        self.knowledge_graph.add_relationship(pn, en, 'uses_equipment', {'document': doc_name})
    
    def _extract_entities(self, content: str, doc_type: str) -> List[Dict]:
        content_lower = content.lower()
        patterns = {
            'Material': ['желез', 'мед', 'никел', 'цинк', 'алюмини', 'стал', 'чугун', 'бронз', 'латун', 'титан', 'золот', 'серебр'],
            'Process': ['плавк', 'обжиг', 'флотац', 'выщелачива', 'электролиз', 'агломерац', 'дроблен', 'кучн'],
            'Equipment': ['печ', 'дробилк', 'мельниц', 'фильтр', 'центрифуг', 'реактор', 'конвейер', 'флотомашин'],
            'Property': ['температур', 'давлен', 'плотност', 'вязкост', 'прочност', 'твердост', 'влажност']
        }
        full = {
            'желез': 'железо', 'мед': 'медь', 'никел': 'никель', 'цинк': 'цинк', 'алюмини': 'алюминий',
            'стал': 'сталь', 'чугун': 'чугун', 'бронз': 'бронза', 'латун': 'латунь', 'титан': 'титан',
            'золот': 'золото', 'серебр': 'серебро', 'плавк': 'плавка', 'обжиг': 'обжиг',
            'флотац': 'флотация', 'выщелачива': 'выщелачивание', 'электролиз': 'электролиз',
            'агломерац': 'агломерация', 'дроблен': 'дробление', 'кучн': 'кучное выщелачивание',
            'печ': 'печь', 'дробилк': 'дробилка', 'мельниц': 'мельница', 'фильтр': 'фильтр',
            'центрифуг': 'центрифуга', 'реактор': 'реактор', 'конвейер': 'конвейер', 'флотомашин': 'флотомашина',
            'температур': 'температура', 'давлен': 'давление', 'плотност': 'плотность',
            'вязкост': 'вязкость', 'прочност': 'прочность', 'твердост': 'твердость', 'влажност': 'влажность'
        }
        found, entities = set(), []
        for entity_type, roots in patterns.items():
            for root in roots:
                if root in content_lower:
                    key = f"{entity_type}:{root}"
                    if key not in found:
                        found.add(key)
                        entities.append({
                            'type': entity_type,
                            'properties': {'name': full.get(root, root), 'source_document_type': doc_type},
                            'confidence': 0.7
                        })
        return entities
    
    def search(self, query: str) -> Dict:
        if not query:
            return {'статус': 'error', 'сообщение': 'Пустой запрос'}
        
        t0 = datetime.now()
        
        entities = self._extract_entities(query, 'query')
        materials = [e['properties']['name'] for e in entities if e['type'] == 'Material']
        processes = [e['properties']['name'] for e in entities if e['type'] == 'Process']
        equipments = [e['properties']['name'] for e in entities if e['type'] == 'Equipment']
        
        return {
            'статус': 'ok',
            'запрос': query,
            'время_выполнения': f"{(datetime.now() - t0).total_seconds():.2f} сек",
            'извлечено_из_запроса': {
                'материалы': materials,
                'процессы': processes,
                'оборудование': equipments
            },
            'цепочки': self._chains(materials, processes, equipments),
            'пробелы': self._gaps(materials, processes),
            'материалы': self._materials_info(materials),
            'эксперты': self._experts(materials, processes),
            'лаборатории': self._facilities(materials, processes),
            'литература': self._literature(query),
            'граф': self._graph()
        }
    
    def _chains(self, materials, processes, equipments):
        chains = []
        for mat in materials:
            for proc in processes:
                for equip in equipments:
                    docs = self._find_chain_docs(mat, proc, equip)
                    chains.append({
                        'цепочка': f"{mat} → {proc} → {equip}",
                        'материал': mat,
                        'процесс': proc,
                        'оборудование': equip,
                        'результат': self._predict(mat, proc, equip),
                        'подтверждено_документами': len(docs),
                        'документы': docs[:5],
                        'статус': 'подтверждена' if docs else 'предположительная'
                    })
        chains.sort(key=lambda x: x['подтверждено_документами'], reverse=True)
        return chains
    
    def _find_chain_docs(self, mat, proc, equip):
        docs = set()
        try:
            mn = self.knowledge_graph.find_nodes_by_properties('Material', {'name': mat})
            pn = self.knowledge_graph.find_nodes_by_properties('Process', {'name': proc})
            for m in mn:
                c = self.knowledge_graph.get_node_with_relationships(m.get('id'), depth=2)
                for r in c.get('full_graph', []):
                    d = r.get('relationship_properties', {}).get('document', '')
                    if d:
                        docs.add(d)
        except:
            pass
        return list(docs)
    
    def _predict(self, mat, proc, equip):
        p = {
            ('медь', 'флотация', 'флотомашина'): 'медный концентрат',
            ('медь', 'плавка', 'печь'): 'черновая медь',
            ('медь', 'электролиз', 'реактор'): 'катодная медь',
            ('никель', 'выщелачивание', 'реактор'): 'никелевый раствор',
            ('цинк', 'обжиг', 'печь'): 'цинковый огарок',
            ('алюминий', 'электролиз', 'реактор'): 'первичный алюминий',
        }
        return p.get((mat, proc, equip), f"продукт переработки {mat}")
    
    def _gaps(self, materials, processes):
        gaps = []
        for mat in materials:
            for proc in processes:
                if not self._has_experiments(mat, proc):
                    gaps.append({
                        'тип': 'нет_экспериментов',
                        'сообщение': f"Нет экспериментов для комбинации: {mat} + {proc}",
                        'материал': mat,
                        'процесс': proc
                    })
                if not self._has_properties(mat):
                    gaps.append({
                        'тип': 'нет_свойств',
                        'сообщение': f"Нет данных о свойствах материала: {mat}",
                        'материал': mat
                    })
        return gaps
    
    def _has_experiments(self, mat, proc):
        try:
            r = self.knowledge_graph.query(
                f"MATCH (e:Experiment)-[:uses_material]->(m:Material) "
                f"WHERE toLower(m.name)=toLower('{mat}') AND toLower(e.name) CONTAINS toLower('{proc}') "
                f"RETURN count(e) as c")
            return r[0]['c'] > 0 if r else False
        except:
            return False
    
    def _has_properties(self, mat):
        try:
            mn = self.knowledge_graph.find_nodes_by_properties('Material', {'name': mat})
            if not mn:
                return False
            c = self.knowledge_graph.get_node_with_relationships(mn[0].get('id'), depth=1)
            return any('Property' in n.get('labels', []) for n in c.get('connected_nodes', {}).get('outgoing', []))
        except:
            return False
    
    def _materials_info(self, materials):
        info = []
        for name in materials:
            item = {'название': name, 'свойства': [], 'процессы': [], 'оборудование': [], 'документы': []}
            try:
                for m in self.knowledge_graph.find_nodes_by_properties('Material', {'name': name}):
                    c = self.knowledge_graph.get_node_with_relationships(m.get('id'), depth=2, include_incoming=True, include_outgoing=True)
                    for n in c.get('connected_nodes', {}).get('outgoing', []):
                        p = n.get('properties', {})
                        if 'Property' in n.get('labels', []):
                            item['свойства'].append({'свойство': p.get('name'), 'ед.': p.get('unit', '')})
                        if 'Process' in n.get('labels', []):
                            item['процессы'].append(p.get('name'))
                        if 'Equipment' in n.get('labels', []):
                            item['оборудование'].append(p.get('name'))
                    for n in c.get('connected_nodes', {}).get('incoming', []):
                        if 'Publication' in n.get('labels', []):
                            item['документы'].append(n.get('properties', {}).get('title', ''))
            except:
                pass
            info.append(item)
        return info
    
    def _experts(self, materials, processes):
        experts = []
        for term in materials + processes:
            try:
                r = self.knowledge_graph.query(
                    f"MATCH (e:Expert)-[:validated_by|described_in]->(n) "
                    f"WHERE toLower(n.name) CONTAINS toLower('{term}') "
                    f"RETURN DISTINCT e.name as name, e.email as email LIMIT 10")
                for row in r:
                    experts.append({'имя': row.get('name', '?'), 'контакт': row.get('email', '?'), 'тема': term})
            except:
                pass
        if not experts:
            experts.append({'сообщение': 'Эксперты не найдены.'})
        return experts
    
    def _facilities(self, materials, processes):
        facilities = []
        for term in materials + processes:
            try:
                r = self.knowledge_graph.query(
                    f"MATCH (f:Facility)-[:described_in|operates_at_condition]->(n) "
                    f"WHERE toLower(n.name) CONTAINS toLower('{term}') "
                    f"RETURN DISTINCT f.name as name, f.location as location LIMIT 10")
                for row in r:
                    facilities.append({'название': row.get('name', '?'), 'расположение': row.get('location', '?'), 'тема': term})
            except:
                pass
        if not facilities:
            facilities.append({'сообщение': 'Лаборатории не найдены.'})
        return facilities
    
    def _literature(self, query):
        """Поиск литературы с проверкой доступности"""
        if self.search_engine is None:
            return [{
                'название': 'Поисковый движок недоступен',
                'тип': 'system',
                'релевантность': 0,
                'фрагмент': 'Настройте модуль поиска или проверьте Elasticsearch',
                'ключевые_слова': [],
                'страниц': 0
            }]
        
        try:
            r = self.search_engine.search({"query": query, "top_k": 10})
            return [{
                'название': d.get('название', ''),
                'тип': d.get('тип_файла', ''),
                'релевантность': round(d.get('релевантность', 0) * 100, 1),
                'фрагмент': d.get('фрагмент', '')[:300],
                'ключевые_слова': d.get('related_entities', []),
                'страниц': d.get('страниц', 0)
            } for d in r.get('результаты', [])]
        except Exception as e:
            print(f"[WARNING] Ошибка поиска литературы: {e}", file=sys.stderr)
            return [{
                'название': f'Ошибка поиска',
                'тип': 'error',
                'релевантность': 0,
                'фрагмент': str(e)[:300],
                'ключевые_слова': [],
                'страниц': 0
            }]
    
    def _graph(self):
        g = {'узлы': [], 'связи': []}
        try:
            for n in self.knowledge_graph.query("MATCH (n) RETURN labels(n) as l, n, id(n) as id LIMIT 200"):
                g['узлы'].append({'id': n.get('id'), 'тип': n.get('l', [''])[0], 'данные': n.get('n', {})})
            for e in self.knowledge_graph.query("MATCH (a)-[r]->(b) RETURN type(r) as t, id(a) as a, id(b) as b LIMIT 300"):
                g['связи'].append({'от': e.get('a'), 'к': e.get('b'), 'тип': e.get('t')})
        except:
            pass
        return g
    
    # ============================================================
    # ОДИН JSON-ФАЙЛ СО ВСЕМИ РЕЗУЛЬТАТАМИ
    # ============================================================
    
    def get_full_json(self, query: str, filepath: str = None) -> str:
        """
        Возвращает один JSON со всеми результатами поиска.
        Если указан filepath — сохраняет в файл.
        """
        result = self.search(query)
        result['дата_экспорта'] = datetime.now().isoformat()
        
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    def export_graph(self, path: str = "knowledge_graph.json"):
        self.knowledge_graph.export_to_json(path)


# ============================================================
# API ДЛЯ ФРОНТЕНДА (Запуск через командную строку)
# ============================================================
import argparse
import sys
import json
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScientificTangle Backend API")
    parser.add_argument("--query", type=str, required=True, help="Поисковый запрос от пользователя")
    args = parser.parse_args()

    FIXED_OUTPUT_FILE = Path(__file__).parent / "result.json"

    try:
        print(f"[BACKEND] Инициализация пайплайна...", file=sys.stderr)
        pipeline = DocumentPipeline()
        
        print(f"[BACKEND] Выполнение поиска по запросу: '{args.query}'", file=sys.stderr)
        
        # Пробуем выполнить полный поиск
        pipeline.get_full_json(args.query, filepath=str(FIXED_OUTPUT_FILE))
        
        print(f"[BACKEND] Успешно сохранено в {FIXED_OUTPUT_FILE}", file=sys.stderr)
        
    except Exception as e:
        error_message = str(e)
        print(f"[BACKEND WARNING] Ошибка поиска: {error_message}", file=sys.stderr)
        
        # FALLBACK: Если упали (например, нет индекса Elastic), 
        # все равно сохраняем валидный JSON, чтобы фронтенд не упал с ошибкой
        fallback_result = {
            "статус": "error",
            "сообщение": f"Не удалось выполнить полный поиск: {error_message}. Возможно, не создан индекс Elasticsearch или не загружены документы.",
            "запрос": args.query,
            "время_выполнения": "0 сек",
            "извлечено_из_запроса": {"материалы": [], "процессы": [], "оборудование": []},
            "цепочки": [],
            "пробелы": [],
            "материалы": [],
            "эксперты": [],
            "лаборатории": [],
            "литература": [], # Ошибка была тут
            "граф": {"узлы": [], "связи": []}
        }
        
        with open(FIXED_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(fallback_result, f, ensure_ascii=False, indent=2)
            
        print(f"[BACKEND] Сохранен fallback-результат (пустой JSON) в {FIXED_OUTPUT_FILE}", file=sys.stderr)