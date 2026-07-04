"""
Тесты для DocumentPipeline с правильными моками
"""
import unittest
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestDocumentPipeline(unittest.TestCase):
    """Тесты для DocumentPipeline"""
    
    @classmethod
    def setUpClass(cls):
        """Мокаем Elasticsearch и SentenceTransformer ДО импорта модулей"""
        cls.es_patcher = patch('elasticsearch.Elasticsearch')
        cls.model_patcher = patch('sentence_transformers.SentenceTransformer')
        
        cls.mock_es = cls.es_patcher.start()
        cls.mock_model = cls.model_patcher.start()
        
        cls.mock_es_instance = cls.mock_es.return_value
        cls.mock_es_instance.indices.exists.return_value = True
        cls.mock_es_instance.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        cls.mock_es_instance.index.return_value = {"_id": "test_id", "result": "created"}
        
        cls.mock_model_instance = cls.mock_model.return_value
        cls.mock_model_instance.encode.return_value = [0.1] * 384
        
        # Мокаем ocpg
        cls.ocpg_patcher = patch.dict('sys.modules', {'ocpg': Mock()})
        cls.mock_ocpg_module = cls.ocpg_patcher.start()
        
        # Теперь импортируем main
        from main import DocumentPipeline
        cls.DocumentPipeline = DocumentPipeline
    
    @classmethod
    def tearDownClass(cls):
        cls.es_patcher.stop()
        cls.model_patcher.stop()
        cls.ocpg_patcher.stop()
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.pipeline = self.DocumentPipeline()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        self.assertIsNotNone(self.pipeline.typizer)
        self.assertIsNotNone(self.pipeline.knowledge_graph)
        self.assertIsNotNone(self.pipeline.search_engine)
        self.assertEqual(self.pipeline.stats['documents_processed'], 0)
    
    def test_extract_entities(self):
        test_content = """
        Технология флотации медных руд включает использование дробилки 
        и шаровой мельницы. Процесс выщелачивания происходит при температуре 800°C 
        в реакторе. Для плавки используется печь. Плотность пульпы контролируется.
        """
        
        entities = self.pipeline._extract_entities(test_content, '.pdf')
        
        self.assertIsInstance(entities, list)
        self.assertGreater(len(entities), 0, "Должны быть найдены сущности")
        
        # Проверяем типы найденных сущностей
        entity_types = [e['type'] for e in entities]
        self.assertIn('Material', entity_types)
        self.assertIn('Process', entity_types)
        self.assertIn('Equipment', entity_types)
        self.assertIn('Property', entity_types)
        
        # Проверяем структуру
        for entity in entities:
            self.assertIn('type', entity)
            self.assertIn('properties', entity)
            self.assertIn('confidence', entity)
            self.assertIn('name', entity['properties'])
        
        # Проверяем конкретные сущности
        entity_names = [e['properties']['name'] for e in entities]
        self.assertIn('медь', entity_names)
        self.assertIn('флотация', entity_names)
        self.assertIn('дробилка', entity_names)
        self.assertIn('мельница', entity_names)
        self.assertIn('выщелачивание', entity_names)
        self.assertIn('температура', entity_names)
        self.assertIn('реактор', entity_names)
        self.assertIn('плавка', entity_names)
        self.assertIn('печь', entity_names)
        self.assertIn('плотность', entity_names)
    
    def test_extract_entities_empty_content(self):
        entities = self.pipeline._extract_entities("", '.pdf')
        self.assertEqual(entities, [])
    
    def test_extract_entities_no_matches(self):
        entities = self.pipeline._extract_entities(
            "Текст без ключевых слов из предметной области", 
            '.pdf'
        )
        self.assertEqual(entities, [])
    
    def test_generate_pipeline_report(self):
        self.pipeline.stats['documents_processed'] = 10
        self.pipeline.stats['entities_extracted'] = 25
        
        report = self.pipeline._generate_pipeline_report()
        
        self.assertEqual(report['статус'], 'completed')
        self.assertEqual(report['статистика']['documents_processed'], 10)
    
    def test_search_documents(self):
        with patch.object(self.pipeline.search_engine, 'search') as mock_search:
            mock_search.return_value = {
                "метаданные": {"всего_найдено": 1, "возвращено": 1},
                "результаты": [{"название": "test.pdf", "релевантность": 0.95}],
                "рекомендации": []
            }
            
            result = self.pipeline.search_documents("флотация меди", top_k=5)
        
        self.assertIsInstance(result, dict)
        self.assertIn('результаты', result)
    
    def test_search_and_relate(self):
        with patch.object(self.pipeline.search_engine, 'search') as mock_search:
            mock_search.return_value = {
                "метаданные": {"всего_найдено": 1, "возвращено": 1},
                "результаты": [{
                    "название": "test.pdf",
                    "тип_файла": ".pdf",
                    "релевантность": 0.95,
                    "фрагмент": "текст...",
                    "страниц": 10
                }],
                "рекомендации": []
            }
            
            with patch.object(self.pipeline.knowledge_graph, 'get_node_with_relationships') as mock_graph:
                mock_graph.return_value = {
                    'connected_nodes': {
                        'outgoing': [
                            {'properties': {'name': 'медь'}},
                            {'properties': {'name': 'флотация'}}
                        ]
                    }
                }
                
                result = self.pipeline.search_and_relate("флотация")
        
        self.assertIn('результаты', result)
        self.assertIn('related_entities', result['результаты'][0])
    
    def test_export_graph(self):
        export_path = os.path.join(self.test_dir, "test_export.json")
        
        with patch.object(self.pipeline.knowledge_graph, 'export_to_json') as mock_export:
            self.pipeline.export_graph(export_path)
            mock_export.assert_called_once_with(export_path)
    
    def test_load_graph(self):
        load_path = os.path.join(self.test_dir, "test_graph.json")
        
        test_graph = {
            "export_date": datetime.now().isoformat(),
            "nodes": [{"id": 1, "labels": ["Material"], "properties": {"name": "медь"}}],
            "relationships": []
        }
        
        with open(load_path, 'w', encoding='utf-8') as f:
            json.dump(test_graph, f)
        
        with patch.object(self.pipeline.knowledge_graph, 'load_from_json') as mock_load:
            mock_load.return_value = {
                'nodes_loaded': 1, 'relationships_loaded': 0,
                'nodes_skipped': 0, 'relationships_skipped': 0
            }
            
            self.pipeline.load_graph(load_path)
            mock_load.assert_called_once_with(load_path)
    
    def test_search_with_empty_query(self):
        with patch.object(self.pipeline.search_engine, 'search') as mock_search:
            mock_search.return_value = {
                "метаданные": {"всего_найдено": 0, "возвращено": 0},
                "результаты": [],
                "рекомендации": []
            }
            
            result = self.pipeline.search_documents("")
        
        self.assertEqual(result['метаданные']['всего_найдено'], 0)

    def test_extract_entities(self):
        test_content = """
        Технология флотации медных руд включает использование дробилки 
        и шаровой мельницы. Процесс выщелачивания происходит при температуре 800°C 
        в реакторе. Для плавки используется печь. Плотность пульпы контролируется.
        """
        
        print("\n" + "="*50)
        print("ОТЛАДКА: проверка ключевых слов в тексте")
        print("="*50)
        content_lower = test_content.lower()
        print(f"Текст: {content_lower[:100]}...")
        
        patterns = {
            'Material': ['железо', 'медь', 'никель', 'цинк', 'алюминий', 'сталь', 'чугун', 'бронза', 'латунь', 'титан'],
            'Process': ['плавка', 'обжиг', 'флотация', 'выщелачивание', 'электролиз', 'агломерация', 'дробление'],
            'Equipment': ['печь', 'дробилка', 'мельница', 'фильтр', 'центрифуга', 'реактор', 'конвейер'],
            'Property': ['температура', 'давление', 'плотность', 'вязкость', 'прочность', 'твердость', 'теплопроводность']
        }
        
        for entity_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in content_lower:
                    print(f" НАЙДЕНО: {entity_type} - {keyword}")
        
        print("="*50 + "\n")
        
        entities = self.pipeline._extract_entities(test_content, '.pdf')
        
        print(f"Количество найденных сущностей: {len(entities)}")
        for e in entities:
            print(f"  - {e['type']}: {e['properties']['name']}")
        
        self.assertIsInstance(entities, list)
        self.assertGreater(len(entities), 0, "Должны быть найдены сущности")
        
        entity_types = [e['type'] for e in entities]
        print(f"Типы сущностей: {entity_types}")
        
        self.assertIn('Material', entity_types)
        self.assertIn('Process', entity_types)
        self.assertIn('Equipment', entity_types)
        self.assertIn('Property', entity_types)


if __name__ == '__main__':
    unittest.main(verbosity=2)