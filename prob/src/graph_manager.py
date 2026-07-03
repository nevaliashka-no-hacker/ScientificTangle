"""Менеджер графа знаний Neo4j"""

from typing import List, Dict, Optional, Any
from neo4j import GraphDatabase, Transaction
from loguru import logger
from datetime import datetime
import json

class GraphManager:
    """Управление графом знаний в Neo4j"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()
    
    def _init_schema(self):
        """Создание индексов и ограничений"""
        with self.driver.session() as session:
            # Индексы для быстрого поиска
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (m:Material) ON (m.name)",
                "CREATE INDEX IF NOT EXISTS FOR (p:Process) ON (p.name)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Equipment) ON (e.name)",
                "CREATE INDEX IF NOT EXISTS FOR (exp:Experiment) ON (exp.id)",
                "CREATE INDEX IF NOT EXISTS FOR (pub:Publication) ON (pub.title)",
                "CREATE INDEX IF NOT EXISTS FOR (ex:Expert) ON (ex.name)",
            ]
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.warning(f"Index already exists: {e}")
    
    def create_material(self, name: str, properties: Dict = None) -> str:
        """Создание узла материала"""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (m:Material {name: $name})
                SET m += $props, m.updated_at = datetime()
                RETURN m.name as name
                """,
                name=name,
                props=properties or {}
            )
            return result.single()['name']
    
    def create_process(self, name: str, properties: Dict = None) -> str:
        """Создание узла процесса"""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (p:Process {name: $name})
                SET p += $props, p.updated_at = datetime()
                RETURN p.name as name
                """,
                name=name,
                props=properties or {}
            )
            return result.single()['name']
    
    def create_experiment(self, experiment_data: Dict) -> str:
        """Создание узла эксперимента с параметрами"""
        with self.driver.session() as session:
            # Создаем эксперимент
            result = session.run(
                """
                CREATE (exp:Experiment {
                    id: randomUUID(),
                    title: $title,
                    description: $description,
                    date: $date,
                    confidence: $confidence,
                    created_at: datetime()
                })
                
                // Связываем с материалами
                FOREACH (mat IN $materials |
                    MERGE (m:Material {name: mat})
                    MERGE (exp)-[:USES_MATERIAL]->(m)
                )
                
                // Добавляем параметры как узлы
                FOREACH (param IN $parameters |
                    CREATE (p:Parameter {
                        name: param.name,
                        value: param.value,
                        unit: param.unit,
                        condition: param.condition
                    })
                    CREATE (exp)-[:HAS_PARAMETER]->(p)
                )
                
                // Связываем с процессом
                FOREACH (proc IN $processes |
                    MERGE (pr:Process {name: proc})
                    MERGE (exp)-[:APPLIED_IN]->(pr)
                )
                
                RETURN exp.id as exp_id
                """,
                **experiment_data
            )
            return result.single()['exp_id']
    
    def create_publication(self, pub_data: Dict) -> str:
        """Создание узла публикации"""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (pub:Publication {doi: $doi})
                SET pub.title = $title,
                    pub.authors = $authors,
                    pub.year = $year,
                    pub.type = $type,
                    pub.geography = $geography,
                    pub.abstract = $abstract,
                    pub.created_at = datetime()
                
                FOREACH (author IN $authors |
                    MERGE (ex:Expert {name: author})
                    MERGE (ex)-[:AUTHORED]->(pub)
                    MERGE (ex)-[:EXPERT_IN]->(pub)
                )
                
                RETURN pub.doi as doi
                """,
                **pub_data
            )
            return result.single()['doi']
    
    def create_contradiction(self, exp1_id: str, exp2_id: str, 
                            description: str, parameter: str):
        """Создание связи противоречия между экспериментами"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (e1:Experiment {id: $exp1_id})
                MATCH (e2:Experiment {id: $exp2_id})
                CREATE (e1)-[:CONTRADICTS {
                    description: $description,
                    parameter: $parameter,
                    created_at: datetime()
                }]->(e2)
                """,
                exp1_id=exp1_id,
                exp2_id=exp2_id,
                description=description,
                parameter=parameter
            )
    
    def search_by_material_and_conditions(
        self, 
        material: str, 
        parameters: List[Dict],
        geography: Optional[str] = None,
        year_range: Optional[Tuple[int, int]] = None
    ) -> List[Dict]:
        """Поиск методов для материала с ограничениями"""
        
        # Построение условий для параметров
        param_conditions = []
        for i, param in enumerate(parameters):
            if 'condition' in param and 'min' in param['condition']:
                # Диапазон
                min_val = float(param['condition'].split('=')[1])
                param_conditions.append(
                    f"p{i}.name = '{param.get('name', '')}' AND "
                    f"p{i}.value >= {min_val} AND p{i}.value <= {param['value']}"
                )
            else:
                # Точное значение или верхняя граница
                if param.get('value'):
                    param_conditions.append(
                        f"p{i}.name = '{param.get('name', '')}' AND "
                        f"p{i}.value <= {param['value']}"
                    )
        
        with self.driver.session() as session:
            query = """
            MATCH (m:Material {name: $material})
            MATCH (exp:Experiment)-[:USES_MATERIAL]->(m)
            MATCH (exp)-[:APPLIED_IN]->(proc:Process)
            OPTIONAL MATCH (exp)-[:HAS_PARAMETER]->(p:Parameter)
            OPTIONAL MATCH (pub:Publication)-[:DESCRIBED_IN]-(exp)
            WHERE 1=1
            """
            
            if param_conditions:
                query += " AND " + " AND ".join(param_conditions)
            
            if geography:
                query += " AND pub.geography = $geography"
            
            if year_range:
                query += " AND pub.year >= $year_from AND pub.year <= $year_to"
            
            query += """
            RETURN 
                proc.name as method,
                exp.title as experiment,
                exp.description as description,
                collect(DISTINCT p) as parameters,
                collect(DISTINCT pub) as publications
            ORDER BY exp.confidence DESC
            LIMIT 20
            """
            
            result = session.run(
                query,
                material=material,
                geography=geography,
                year_from=year_range[0] if year_range else None,
                year_to=year_range[1] if year_range else None
            )
            
            return [dict(record) for record in result]
    
    def find_experts_by_topic(self, topic: str) -> List[Dict]:
        """Поиск экспертов по теме"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (ex:Expert)-[:AUTHORED|EXPERT_IN]->(pub:Publication)
                WHERE pub.title CONTAINS $topic 
                   OR pub.abstract CONTAINS $topic
                
                OPTIONAL MATCH (ex)-[:AUTHORED]->(pub2:Publication)
                RETURN 
                    ex.name as expert,
                    count(DISTINCT pub) as relevant_papers,
                    collect(DISTINCT pub2.title)[0..5] as recent_works
                ORDER BY relevant_papers DESC
                LIMIT 10
                """,
                topic=topic
            )
            return [dict(record) for record in result]
    
    def find_contradictions(self, domain: str) -> List[Dict]:
        """Поиск противоречий в предметной области"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e1:Experiment)-[c:CONTRADICTS]->(e2:Experiment)
                OPTIONAL MATCH (e1)-[:APPLIED_IN]->(p1:Process)
                OPTIONAL MATCH (e2)-[:APPLIED_IN]->(p2:Process)
                OPTIONAL MATCH (pub1:Publication)-[:DESCRIBED_IN]-(e1)
                OPTIONAL MATCH (pub2:Publication)-[:DESCRIBED_IN]-(e2)
                RETURN 
                    c.description as contradiction,
                    c.parameter as parameter,
                    e1.title as experiment_1,
                    e2.title as experiment_2,
                    pub1.title as source_1,
                    pub2.title as source_2
                """
            )
            return [dict(record) for record in result]
    
    def get_knowledge_gaps(self) -> List[Dict]:
        """Выявление пробелов в знаниях"""
        with self.driver.session() as session:
            result = session.run(
                """
                // Находим комбинации материал-процесс без экспериментов
                MATCH (m:Material), (p:Process)
                WHERE NOT EXISTS {
                    MATCH (exp:Experiment)-[:USES_MATERIAL]->(m)
                    WHERE (exp)-[:APPLIED_IN]->(p)
                }
                RETURN 
                    m.name as material,
                    p.name as process,
                    'Нет экспериментов' as gap_type
                LIMIT 20
                """
            )
            return [dict(record) for record in result]
    
    def close(self):
        """Закрытие соединения"""
        self.driver.close()