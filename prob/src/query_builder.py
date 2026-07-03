"""Конвертер запросов на естественном языке в Cypher"""

from typing import Dict, List, Any
from .nlp_extractor import ScientificNLP
from loguru import logger

class QueryBuilder:
    """Построение графовых запросов из NL"""
    
    def __init__(self, nlp: ScientificNLP):
        self.nlp = nlp
    
    def build_cypher_query(self, natural_query: str) -> Dict[str, Any]:
        """Основной метод конвертации NL → Cypher"""
        
        # Парсинг запроса
        parsed = self.nlp.parse_query(natural_query)
        intent = parsed['intent']
        constraints = parsed['constraints']
        
        # Маршрутизация по типу запроса
        if intent == 'FIND_METHOD':
            return self._build_method_query(constraints)
        elif intent == 'LIST_ALL':
            return self._build_list_query(constraints)
        elif intent == 'COMPARE':
            return self._build_compare_query(constraints)
        elif intent == 'FIND_OPTIMAL':
            return self._build_optimal_query(constraints)
        else:
            return self._build_semantic_query(constraints)
    
    def _build_method_query(self, constraints: Dict) -> Dict:
        """Запрос на поиск методов"""
        cypher = """
        MATCH (m:Material)
        WHERE m.name IN $materials
        
        MATCH (proc:Process)-[:APPLIED_IN]-(exp:Experiment)-[:USES_MATERIAL]->(m)
        """
        
        params = {
            'materials': constraints.get('materials', [])
        }
        
        # Добавление фильтрации по параметрам
        if constraints.get('parameters'):
            cypher += """
            MATCH (exp)-[:HAS_PARAMETER]->(p:Parameter)
            WHERE 
            """
            param_conditions = []
            for i, param in enumerate(constraints['parameters']):
                if param.get('condition') and 'min' in param['condition']:
                    min_val = float(param['condition'].split('=')[1])
                    param_conditions.append(
                        f"(p.name CONTAINS 'сульфат' AND p.value >= {min_val} AND p.value <= {param['value']})"
                    )
                else:
                    param_conditions.append(
                        f"(p.value <= {param['value']})"
                    )
            cypher += " OR ".join(param_conditions)
        
        # Географический фильтр
        if constraints.get('geography'):
            cypher += """
            OPTIONAL MATCH (pub:Publication)-[:DESCRIBED_IN]-(exp)
            WHERE pub.geography = $geography
            """
            params['geography'] = constraints['geography']
        
        cypher += """
        RETURN DISTINCT 
            proc.name as method,
            exp.title as description,
            collect(DISTINCT p.value) as values
        ORDER BY method
        LIMIT 20
        """
        
        return {
            'cypher': cypher,
            'params': params,
            'description': f"Поиск методов для {', '.join(constraints.get('materials', []))}"
        }
    
    def _build_list_query(self, constraints: Dict) -> Dict:
        """Запрос на перечисление всех экспериментов/публикаций"""
        cypher = """
        MATCH (exp:Experiment)
        """
        
        if constraints.get('materials'):
            cypher += """
            MATCH (exp)-[:USES_MATERIAL]->(m:Material)
            WHERE m.name IN $materials
            """
        
        if constraints.get('time_range'):
            cypher += """
            MATCH (pub:Publication)-[:DESCRIBED_IN]-(exp)
            WHERE pub.year >= $year_from AND pub.year <= $year_to
            """
        
        cypher += """
        OPTIONAL MATCH (exp)-[:APPLIED_IN]->(proc:Process)
        OPTIONAL MATCH (pub:Publication)-[:DESCRIBED_IN]-(exp)
        OPTIONAL MATCH (auth:Expert)-[:AUTHORED]->(pub)
        
        RETURN 
            exp.id as id,
            exp.title as experiment,
            proc.name as process,
            collect(DISTINCT auth.name) as authors,
            pub.year as year
        ORDER BY pub.year DESC
        LIMIT 50
        """
        
        return {
            'cypher': cypher,
            'params': {
                'materials': constraints.get('materials', []),
                'year_from': constraints.get('time_range', [None, None])[0],
                'year_to': constraints.get('time_range', [None, None])[1]
            },
            'description': "Список экспериментов и публикаций"
        }
    
    def _build_optimal_query(self, constraints: Dict) -> Dict:
        """Поиск оптимальных параметров"""
        cypher = """
        MATCH (proc:Process {name: $process})
        MATCH (exp:Experiment)-[:APPLIED_IN]->(proc)
        MATCH (exp)-[:HAS_PARAMETER]->(p:Parameter)
        
        WITH p, exp, proc,
             CASE 
                WHEN p.value IS NOT NULL THEN p.value 
                ELSE 0 
             END as param_value
        
        RETURN 
            proc.name as process,
            p.name as parameter,
            p.unit as unit,
            avg(param_value) as avg_value,
            min(param_value) as min_value,
            max(param_value) as max_value,
            stDev(param_value) as std_dev,
            count(exp) as experiment_count
        ORDER BY experiment_count DESC
        """
        
        return {
            'cypher': cypher,
            'params': {
                'process': constraints.get('processes', [''])[0]
            },
            'description': "Поиск оптимальных значений параметров"
        }
    
    def _build_compare_query(self, constraints: Dict) -> Dict:
        """Сравнительный анализ технологий"""
        cypher = """
        MATCH (p1:Process {name: $process_1})
        MATCH (p2:Process {name: $process_2})
        
        OPTIONAL MATCH (exp1:Experiment)-[:APPLIED_IN]->(p1)
        OPTIONAL MATCH (exp2:Experiment)-[:APPLIED_IN]->(p2)
        
        OPTIONAL MATCH (exp1)-[:HAS_PARAMETER]->(param1:Parameter)
        OPTIONAL MATCH (exp2)-[:HAS_PARAMETER]->(param2:Parameter)
        
        RETURN 
            p1.name as technology_1,
            count(DISTINCT exp1) as experiments_1,
            collect(DISTINCT param1.name) as params_1,
            p2.name as technology_2,
            count(DISTINCT exp2) as experiments_2,
            collect(DISTINCT param2.name) as params_2
        """
        
        return {
            'cypher': cypher,
            'params': {
                'process_1': constraints.get('processes', ['', ''])[0],
                'process_2': constraints.get('processes', ['', ''])[1] if len(constraints.get('processes', [])) > 1 else ''
            },
            'description': "Сравнение технологий"
        }
    
    def _build_semantic_query(self, constraints: Dict) -> Dict:
        """Семантический поиск (fallback)"""
        cypher = """
        CALL db.index.fulltext.queryNodes('publications', $query) 
        YIELD node, score
        RETURN node.title as title, node.abstract as abstract, score
        ORDER BY score DESC
        LIMIT 20
        """
        
        return {
            'cypher': cypher,
            'params': {
                'query': ' '.join(constraints.get('materials', []) + constraints.get('processes', []))
            },
            'description': "Семантический поиск"
        }