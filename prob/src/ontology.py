"""Онтология предметной области горно-металлургических R&D"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel

class EntityType(str, Enum):
    MATERIAL = "Material"
    PROCESS = "Process"
    EQUIPMENT = "Equipment"
    PROPERTY = "Property"
    EXPERIMENT = "Experiment"
    PUBLICATION = "Publication"
    PATENT = "Patent"
    EXPERT = "Expert"
    FACILITY = "Facility"
    CONDITION = "Condition"

class RelationType(str, Enum):
    USES_MATERIAL = "USES_MATERIAL"
    OPERATES_AT = "OPERATES_AT"
    PRODUCES = "PRODUCES"
    DESCRIBED_IN = "DESCRIBED_IN"
    VALIDATED_BY = "VALIDATED_BY"
    CONTRADICTS = "CONTRADICTS"
    AUTHORED = "AUTHORED"
    EXPERT_IN = "EXPERT_IN"
    APPLIED_IN = "APPLIED_IN"
    HAS_PARAMETER = "HAS_PARAMETER"
    PART_OF = "PART_OF"

# Таксономия материалов
MATERIAL_HIERARCHY = {
    "Металлы": ["Никель", "Медь", "Золото", "Серебро", "МПГ", "Кобальт"],
    "Соли": ["Сульфаты", "Хлориды", "Карбонаты"],
    "Минералы": ["Гипс", "Кальцит", "Кварц"],
    "Растворы": ["Католит", "Анолит", "Электролит", "Шахтные воды"],
    "Штейны": ["Медный штейн", "Никелевый штейн"],
    "Шлаки": ["Конвертерный шлак", "Печной шлак"],
}

# Таксономия процессов
PROCESS_HIERARCHY = {
    "Гидрометаллургия": [
        "Выщелачивание", "Кучное выщелачивание", 
        "Электроэкстракция", "Обессоливание",
        "Цементация", "Сорбция"
    ],
    "Пирометаллургия": [
        "Плавка", "Взвешенная плавка", 
        "Конвертирование", "Обжиг"
    ],
    "Экология": [
        "Очистка газов", "Очистка сточных вод",
        "Закачка шахтных вод", "Пылеулавливание"
    ],
}

# Единицы измерения
UNIT_MAPPINGS = {
    "мг/л": ["mg/l", "mg/L", "мг/дм³", "ppm"],
    "°C": ["°C", "C", "град"],
    "м/с": ["m/s", "м/с"],
    "т/сут": ["t/day", "тонн/сутки"],
    "%": ["проц", "percent"],
}

# Географическая классификация
GEO_CLASSIFICATION = {
    "Россия": ["РФ", "СССР", "Норильск", "Кольский", "Урал"],
    "Зарубежье": ["Канада", "Австралия", "Чили", "Китай", "Финляндия"],
}

class OntologyManager:
    """Управление онтологией и маппингом терминов"""
    
    def __init__(self, glossary_path: str):
        self.glossary = self.load_glossary(glossary_path)
        self.synonym_map = self.build_synonym_map()
    
    def load_glossary(self, path: str) -> Dict:
        """Загрузка глоссария"""
        import json
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def build_synonym_map(self) -> Dict[str, str]:
        """Построение карты синонимов"""
        syn_map = {}
        for canonical, variants in self.glossary.get('synonyms', {}).items():
            syn_map[canonical.lower()] = canonical
            for variant in variants:
                syn_map[variant.lower()] = canonical
        return syn_map
    
    def normalize_term(self, term: str) -> str:
        """Нормализация термина к канонической форме"""
        return self.synonym_map.get(term.lower(), term)
    
    def get_entity_type(self, term: str) -> Optional[EntityType]:
        """Определение типа сущности по термину"""
        normalized = self.normalize_term(term)
        
        for category, materials in MATERIAL_HIERARCHY.items():
            if normalized in materials:
                return EntityType.MATERIAL
        
        for category, processes in PROCESS_HIERARCHY.items():
            if normalized in processes or normalized in category.split():
                return EntityType.PROCESS
        
        return None