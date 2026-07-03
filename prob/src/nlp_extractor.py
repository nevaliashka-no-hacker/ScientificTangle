"""NLP-пайплайн для извлечения сущностей из научных текстов"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import spacy
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from loguru import logger

@dataclass
class ExtractedEntity:
    text: str
    type: str
    value: Optional[float] = None
    unit: Optional[str] = None
    condition: Optional[str] = None
    confidence: float = 1.0

@dataclass
class ExtractedRelation:
    source: ExtractedEntity
    relation: str
    target: ExtractedEntity
    confidence: float = 1.0

class ScientificNLP:
    """NLP-пайплайн для горно-металлургической предметной области"""
    
    def __init__(self, config):
        self.config = config
        
        # Загрузка spaCy для русского языка
        try:
            self.nlp_ru = spacy.load("ru_core_news_sm")
        except:
            logger.warning("ru_core_news_sm не найден, загрузка...")
            spacy.cli.download("ru_core_news_sm")
            self.nlp_ru = spacy.load("ru_core_news_sm")
        
        # Инициализация NER через transformers (ruBERT)
        self.ner_tokenizer = AutoTokenizer.from_pretrained(config.NER_MODEL)
        self.ner_model = AutoModelForTokenClassification.from_pretrained(config.NER_MODEL)
        self.ner_pipeline = pipeline(
            "ner", 
            model=self.ner_model, 
            tokenizer=self.ner_tokenizer,
            aggregation_strategy="simple"
        )
        
        # Паттерны для извлечения числовых значений с единицами
        self.value_pattern = re.compile(
            r'(\d+[.,]?\d*)\s*(мг/л|mg/l|мг/дм³|ppm|°C|м/с|т/сут|%|г/л|кг/м³)',
            re.IGNORECASE
        )
        
        # Паттерны для диапазонов
        self.range_pattern = re.compile(
            r'(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)\s*(мг/л|mg/l|°C|м/с|т/сут|%)',
            re.IGNORECASE
        )
        
        # Специализированные словари
        self.materials = self._build_material_dict()
        self.processes = self._build_process_dict()
        self.equipment = self._build_equipment_dict()
        
    def _build_material_dict(self) -> Dict[str, str]:
        """Словарь материалов"""
        return {
            'никель': 'Ni', 'никелевый': 'Ni',
            'медь': 'Cu', 'медный': 'Cu',
            'золото': 'Au', 'серебро': 'Ag',
            'сульфат': 'сульфаты', 'хлорид': 'хлориды',
            'католит': 'католит', 'анолит': 'анолит',
            'электролит': 'электролит',
            'гипс': 'гипс', 'шлак': 'шлак',
            'штейн': 'штейн', 'уголь': 'уголь',
        }
    
    def _build_process_dict(self) -> Dict[str, str]:
        """Словарь процессов"""
        return {
            'электроэкстракция': 'Электроэкстракция',
            'electrowinning': 'Электроэкстракция',
            'выщелачивание': 'Выщелачивание',
            'leaching': 'Выщелачивание',
            'кучное выщелачивание': 'Кучное выщелачивание',
            'обессоливание': 'Обессоливание',
            'desalination': 'Обессоливание',
            'плавка': 'Плавка',
            'взвешенная плавка': 'Взвешенная плавка',
            'ПВП': 'Взвешенная плавка',
            'очистка': 'Очистка',
            'закачка': 'Закачка шахтных вод',
        }
    
    def _build_equipment_dict(self) -> Dict[str, str]:
        """Словарь оборудования"""
        return {
            'ванна': 'Ванна электроэкстракции',
            'электролизер': 'Электролизер',
            'печь': 'Печь',
            'диафрагменная ячейка': 'Диафрагменная ячейка',
            'фильтр': 'Фильтр',
            'центрифуга': 'Центрифуга',
        }
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Извлечение всех сущностей из текста"""
        entities = []
        
        # Извлечение через spaCy
        doc = self.nlp_ru(text)
        for ent in doc.ents:
            entities.append(ExtractedEntity(
                text=ent.text,
                type=ent.label_,
                confidence=0.9
            ))
        
        # Извлечение числовых значений с единицами
        for match in self.value_pattern.finditer(text):
            value = float(match.group(1).replace(',', '.'))
            unit = match.group(2)
            entities.append(ExtractedEntity(
                text=f"{value} {unit}",
                type="PARAMETER",
                value=value,
                unit=unit,
                confidence=0.95
            ))
        
        # Извлечение диапазонов
        for match in self.range_pattern.finditer(text):
            min_val = float(match.group(1).replace(',', '.'))
            max_val = float(match.group(2).replace(',', '.'))
            unit = match.group(3)
            entities.append(ExtractedEntity(
                text=f"{min_val}-{max_val} {unit}",
                type="RANGE",
                value=max_val,  # Верхняя граница
                unit=unit,
                condition=f"min={min_val}",
                confidence=0.95
            ))
        
        # Извлечение материалов
        for term, canonical in self.materials.items():
            if term.lower() in text.lower():
                entities.append(ExtractedEntity(
                    text=canonical,
                    type="MATERIAL",
                    confidence=0.85
                ))
        
        # Извлечение процессов
        for term, canonical in self.processes.items():
            if term.lower() in text.lower():
                entities.append(ExtractedEntity(
                    text=canonical,
                    type="PROCESS",
                    confidence=0.85
                ))
        
        # Извлечение оборудования
        for term, canonical in self.equipment.items():
            if term.lower() in text.lower():
                entities.append(ExtractedEntity(
                    text=canonical,
                    type="EQUIPMENT",
                    confidence=0.85
                ))
        
        return entities
    
    def extract_relations(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """Извлечение связей между сущностями"""
        relations = []
        
        # Правила для связей
        relation_patterns = [
            (r'(.+) применяется для (.+)', 'APPLIED_FOR'),
            (r'(.+) содержит (.+)', 'CONTAINS'),
            (r'(.+) показал (.+)', 'SHOWED'),
            (r'(.+) используется в (.+)', 'USED_IN'),
        ]
        
        for pattern, rel_type in relation_patterns:
            for match in re.finditer(pattern, text):
                if len(entities) >= 2:
                    relations.append(ExtractedRelation(
                        source=entities[0],
                        relation=rel_type,
                        target=entities[-1],
                        confidence=0.75
                    ))
        
        # Связи на основе близости в тексте
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:i+3]:
                if e1.type == "PROCESS" and e2.type == "MATERIAL":
                    relations.append(ExtractedRelation(
                        source=e1,
                        relation="USES_MATERIAL",
                        target=e2,
                        confidence=0.7
                    ))
        
        return relations
    
    def parse_query(self, query: str) -> Dict:
        """Парсинг запроса на естественном языке для поиска"""
        entities = self.extract_entities(query)
        
        # Классификация намерения запроса
        intent = self._classify_intent(query)
        
        # Извлечение ограничений
        constraints = {
            'materials': [],
            'processes': [],
            'parameters': [],
            'geography': None,
            'time_range': None,
        }
        
        for ent in entities:
            if ent.type == "MATERIAL":
                constraints['materials'].append(ent.text)
            elif ent.type == "PROCESS":
                constraints['processes'].append(ent.text)
            elif ent.type in ["PARAMETER", "RANGE"]:
                constraints['parameters'].append({
                    'value': ent.value,
                    'unit': ent.unit,
                    'condition': ent.condition
                })
        
        # Определение географии
        if any(word in query.lower() for word in ['россия', 'отечествен', 'рф', 'ссср']):
            constraints['geography'] = 'Россия'
        elif any(word in query.lower() for word in ['мир', 'зарубеж', 'мировой']):
            constraints['geography'] = 'Зарубежье'
        
        return {
            'intent': intent,
            'constraints': constraints,
            'original_query': query,
        }
    
    def _classify_intent(self, query: str) -> str:
        """Классификация намерения запроса"""
        query_lower = query.lower()
        
        if any(w in query_lower for w in ['какой метод', 'способ', 'техническое решение']):
            return 'FIND_METHOD'
        elif any(w in query_lower for w in ['показать все', 'список', 'перечислить']):
            return 'LIST_ALL'
        elif any(w in query_lower for w in ['сравнить', 'vs', 'против']):
            return 'COMPARE'
        elif any(w in query_lower for w in ['оптимальн', 'лучш', 'рекоменд']):
            return 'FIND_OPTIMAL'
        else:
            return 'SEMANTIC_SEARCH'