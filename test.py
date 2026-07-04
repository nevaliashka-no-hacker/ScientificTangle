"""
Тесты для DocumentPipeline (main.py)
"""
import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from main import DocumentPipeline


class TestDocumentPipeline(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        self.es_patcher = patch('elasticsearch.Elasticsearch')
        self.model_patcher = patch('sentence_transformers.SentenceTransformer')
        self.ocpg_patcher = patch('Graph_Data_Base.Graph_Data_Base.ocpg')
        
        self.mock_es = self.es_patcher.start()
        self.mock_model = self.model_patcher.start()
        self.mock_ocpg = self.ocpg_patcher.start()
        
        self.mock_es_instance = self.mock_es.return_value
        self.mock_es_instance.indices.exists.return_value = False
        self.mock_es_instance.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        
        self.mock_model_instance = self.mock_model.return_value
        self.mock_model_instance.encode.return_value = [0.1] * 384
        
        self.pipeline = DocumentPipeline()
    
    def tearDown(self):
        self.es_patcher.stop()
        self.model_patcher.stop()
        self.ocpg_patcher.stop()
        
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        self.assertIsNotNone(self.pipeline.typizer)
        self.assertIsNotNone(self.pipeline.knowledge_graph)
        self.assertIsNotNone(self.pipeline.search_engine)
        self.assertEqual(self.pipeline.stats['documents_processed'], 0)
        self.assertEqual(self.pipeline.stats['entities_extracted'], 0)
    
    def test_process_archive_empty(self):
        import zipfile
        zip_path = os.path.join(self.test_dir, "empty.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            pass
        
        with patch.object(self.pipeline.typizer, 'process_zip_file') as mock_process:
            mock_process.return_value = []
            
            with patch('builtins.open', unittest.mock.mock_open(read_data='{}')):
                result = self.pipeline.process_archive(
                    zip_path,
                    build_graph=False,
                    index_for_search=False
                )
        
        self.assertEqual(result['статус'], 'completed')
        self.assertEqual(result['статистика']['documents_processed'], 0)
    
    def test_process_archive_with_documents(self):
        import zipfile
        zip_path = os.path.join(self.test_dir, "test.zip")
        
        test_docs = {
            "метаданные": {
                "дата_обработки": datetime.now().isoformat(),
                "общее_количество_документов": 2
            },
            "документы": [
                {
                    "название": "test1.pdf",
                    "содержание": "Технология флотации медных руд",
                    "тип_файла": ".pdf",
                    "количество_страниц": 10,
                    "статус": "success"
                },
                {
                    "название": "test2.docx",
                    "содержание": "Процесс выщелачивания никеля",
                    "тип_файла": ".docx",
                    "количество_страниц": 5,
                    "статус": "success"
                }
            ]
        }
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('test.json', json.dumps(test_docs))
        
        with patch.object(self.pipeline.typizer, 'process_zip_file') as mock_process:
            mock_process.return_value = test_docs['документы']
            
            mock_open = unittest.mock.mock_open(read_data=json.dumps(test_docs))
            with patch('builtins.open', mock_open):
                result = self.pipeline.process_archive(
                    zip_path,
                    build_graph=True,
                    index_for_search=True
                )
        
        self.assertEqual(result['статус'], 'completed')
        self.assertEqual(result['статистика']['documents_processed'], 2)
    
    def test_extract_entities(self):
        test_content = """
        Технология флотации медных руд включает использование дробилки 
        и флотационных машин. Процесс происходит при температуре 800°C.
        Для выщелачивания используется серная кислота.
        """
        
        entities = self.pipeline._extract_entities(test_content, '.pdf')
        
        self.assertIsInstance(entities, list)
        self.assertGreater(len(entities), 0)
        
        # Проверяем типы сущностей
        entity_types = [e['type'] for e in entities]
        self.assertIn('Material', entity_types)
        self.assertIn('Process', entity_types)
        self.assertIn('Equipment', entity_types)
        
        for entity in entities:
            self.assertIn('type', entity)
            self.assertIn('properties', entity)
            self.assertIn('confidence', entity)
            self.assertIn(self.pipeline.entity_labels.keys(), entity['type'])
    
    def test_extract_entities_empty_content(self):
        entities = self.pipeline._extract_entities("", '.pdf')
        self.assertEqual(entities, [])
    
    def test_search_documents(self):
        # Мокаем search_engine.search
        with patch.object(self.pipeline.search_engine, 'search') as mock_search:
            mock_search.return_value = {
                "метаданные": {"всего_найдено": 1, "возвращено": 1},
                "результаты": [{"название": "test.pdf", "релевантность": 0.95}],
                "рекомендации": []
            }
            
            result = self.pipeline.search_documents(
                "флотация меди",
                top_k=5
            )
        
        self.assertIsInstance(result, dict)
        self.assertIn('результаты', result)
        mock_search.assert_called_once()
    
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
        self.assertEqual(len(result['результаты'][0]['related_entities']), 2)
    
    def test_export_graph(self):
        export_path = os.path.join(self.test_dir, "test_export.json")
        
        with patch.object(self.pipeline.knowledge_graph, 'export_to_json') as mock_export:
            self.pipeline.export_graph(export_path)
            mock_export.assert_called_once_with(export_path)
    
    def test_load_graph(self):
        load_path = os.path.join(self.test_dir, "test_graph.json")
        
        test_graph = {
            "export_date": datetime.now().isoformat(),
            "nodes": [
                {
                    "id": 1,
                    "labels": ["Material"],
                    "properties": {"name": "медь"}
                }
            ],
            "relationships": []
        }
        
        with open(load_path, 'w', encoding='utf-8') as f:
            json.dump(test_graph, f)
        
        with patch.object(self.pipeline.knowledge_graph, 'load_from_json') as mock_load:
            mock_load.return_value = {
                'nodes_loaded': 1,
                'relationships_loaded': 0,
                'nodes_skipped': 0,
                'relationships_skipped': 0
            }
            
            self.pipeline.load_graph(load_path)
            mock_load.assert_called_once_with(load_path)
    
    def test_generate_pipeline_report(self):
        self.pipeline.stats['documents_processed'] = 10
        self.pipeline.stats['entities_extracted'] = 25
        
        report = self.pipeline._generate_pipeline_report()
        
        self.assertEqual(report['статус'], 'completed')
        self.assertEqual(report['статистика']['documents_processed'], 10)
        self.assertEqual(report['статистика']['entities_extracted'], 25)
    
    def test_pipeline_with_invalid_archive(self):
        invalid_path = os.path.join(self.test_dir, "nonexistent.zip")
        
        with self.assertRaises(FileNotFoundError):
            self.pipeline.process_archive(invalid_path)
    
    def test_search_with_empty_query(self):
        with patch.object(self.pipeline.search_engine, 'search') as mock_search:
            mock_search.return_value = {
                "метаданные": {"всего_найдено": 0, "возвращено": 0},
                "результаты": [],
                "рекомендации": ["Пустой запрос"]
            }
            
            result = self.pipeline.search_documents("")
        
        self.assertEqual(result['метаданные']['всего_найдено'], 0)


class TestDocumentPipelineIntegration(unittest.TestCase):
    
    @unittest.skipIf(True, "Пропуск интеграционных тестов (нужен Elasticsearch)")
    def test_full_pipeline_integration(self):
        import zipfile
        import tempfile
        
        test_dir = tempfile.mkdtemp()
        zip_path = os.path.join(test_dir, "test_archive.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('doc1.txt', 'Тестовая документация по флотации')
            zf.writestr('doc2.txt', 'Методика выщелачивания никеля')
        
        try:
            pipeline = DocumentPipeline()
            result = pipeline.process_archive(zip_path)
            
            self.assertEqual(result['статус'], 'completed')
            
            search_result = pipeline.search_documents("флотация", top_k=1)
            self.assertIn('результаты', search_result)
            
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)