# -*- coding: utf-8 -*-
import ocpg
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import json
import os

class ScientificTangleKnowledgeGraph:
    #Knowledge Graph для горно-металлургических исследований.
    #Поддерживает 8 типов сущностей и 6 типов отношений.
    
    
    def __init__(self):
        #Инициализация графа и кэша.
        self.graph = ocpg.Graph()
        self.cache = {
            'nodes': {},      # Кэш узлов
            'relationships': {}  # Кэш связей
        }
        
        # Определяем уникальные поля для каждого типа сущности
        self.unique_fields = {
            'Material': ['name'],
            'Process': ['name'],
            'Equipment': ['name', 'model'],
            'Property': ['name', 'unit'],
            'Experiment': ['id', 'name'],
            'Publication': ['doi', 'title'],
            'Expert': ['name', 'email'],
            'Facility': ['name', 'location']
        }
        
        # Метки для каждого типа сущности
        self.entity_labels = {
            'Material': ['Material'],
            'Process': ['Process'],
            'Equipment': ['Equipment'],
            'Property': ['Property'],
            'Experiment': ['Experiment'],
            'Publication': ['Publication'],
            'Expert': ['Expert'],
            'Facility': ['Facility']
        }
        
        # Допустимые типы отношений
        self.valid_relationships = [
            'uses_material',
            'operates_at_condition',
            'produces_output',
            'described_in',
            'validated_by',
            'contradicts'
        ]
        
        print("✅ Knowledge Graph инициализирован")
        print(f"   Поддерживаемые сущности: {', '.join(self.entity_labels.keys())}")
        print(f"   Поддерживаемые отношения: {', '.join(self.valid_relationships)}")
    
    # ==================== вспомогательные ф-ии ====================
    
    def _generate_cache_key(self, entity_type: str, properties: Dict[str, Any]) -> str:
        #Генерация ключа#
        unique_fields = self.unique_fields.get(entity_type, ['name'])
        key_parts = [entity_type]
        
        for field in unique_fields:
            if field in properties:
                value = properties[field]
                if isinstance(value, str):
                    key_parts.append(f"{field}={value.lower()}")
                else:
                    key_parts.append(f"{field}={value}")
        
        return "|".join(key_parts)
    
    def _normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        #Нормализация свойств
        normalized = {}
        for key, value in properties.items():
            if isinstance(value, str):
                normalized[key] = value.strip()
            elif isinstance(value, list):
                normalized[key] = [v.strip() if isinstance(v, str) else v for v in value]
            elif isinstance(value, dict):
                normalized[key] = self._normalize_properties(value)
            else:
                normalized[key] = value
        return normalized
    
    def _find_existing_node(
        self, 
        entity_type: str, 
        properties: Dict[str, Any]
    ) -> Optional[int]:
        #
        #Ищет существующий узел по уникальным полям.
        #Returns:
        #    Optional[int]: ID узла или None
        # Проверяем кэш
        cache_key = self._generate_cache_key(entity_type, properties)
        if cache_key in self.cache['nodes']:
            return self.cache['nodes'][cache_key]
        
        unique_fields = self.unique_fields.get(entity_type, ['name'])
        
        # Формируем запрос
        label = entity_type
        query = f"MATCH (n:{label}) WHERE "
        conditions = []
        
        for field in unique_fields:
            if field in properties:
                value = properties[field]
                if isinstance(value, str):
                    conditions.append(f"toLower(n.{field}) = toLower('{value}')")
                elif isinstance(value, (int, float)):
                    conditions.append(f"n.{field} = {value}")
                elif isinstance(value, bool):
                    conditions.append(f"n.{field} = {value}")
                elif isinstance(value, list):
                    list_str = "['" + "','".join([str(v) for v in value]) + "']"
                    conditions.append(f"n.{field} = {list_str}")
                else:
                    conditions.append(f"n.{field} = {value}")
        
        if not conditions:
            return None
        
        query += " AND ".join(conditions)
        query += " RETURN id(n) LIMIT 1"
        
        try:
            result = self.graph.execute(query)
            if result and len(result.to_list()) > 0:
                node_id = result.to_list()[0][0]
                self.cache['nodes'][cache_key] = node_id
                return node_id
        except Exception as e:
            print(f"⚠️ Ошибка при поиске узла: {e}")
        
        return None
    
    def _find_existing_relationship(
        self,
        from_node: int,
        to_node: int,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        #
        #Ищет существующую связь между узлами.
        #
        #Returns:
        #    Optional[int]: ID связи или None
        #
        if properties is None:
            properties = {}
        
        # Ключ для кэша
        cache_key = f"{from_node}|{to_node}|{rel_type}"
        if cache_key in self.cache['relationships']:
            return self.cache['relationships'][cache_key]
        
        # Формируем запрос
        query = f"""
        MATCH (a)-[r:{rel_type}]->(b)
        WHERE id(a) = {from_node} AND id(b) = {to_node}
        """
        
        # Добавляем проверку свойств, если они указаны
        if properties:
            query += " AND "
            conditions = []
            for key, value in properties.items():
                if isinstance(value, str):
                    conditions.append(f"r.{key} = '{value}'")
                elif isinstance(value, (int, float)):
                    conditions.append(f"r.{key} = {value}")
                elif isinstance(value, bool):
                    conditions.append(f"r.{key} = {value}")
                else:
                    conditions.append(f"r.{key} = {value}")
            query += " AND ".join(conditions)
        
        query += " RETURN id(r) LIMIT 1"
        
        try:
            result = self.graph.execute(query)
            if result and len(result.to_list()) > 0:
                rel_id = result.to_list()[0][0]
                self.cache['relationships'][cache_key] = rel_id
                return rel_id
        except Exception as e:
            print(f"⚠️ Ошибка при поиске связи: {e}")
        
        return None
    
    def _find_node_by_name(self, name: str) -> Optional[int]:
        #Ищет узел по имени.#
        #query = f#
        #MATCH (n) 
        #WHERE toLower(n.name) = toLower('{name}') OR toLower(n.title) = toLower('{name}')
        #RETURN id(n) LIMIT 1
        #
        try:
            result = self.graph.execute(query)
            if result and len(result.to_list()) > 0:
                return result.to_list()[0][0]
        except:
            pass
        return None
    
    # ==================== ДОБАВЛЕНИЕ СУЩНОСТЕЙ ====================
    
    def add_entity(
        self,
        entity_type: str,
        properties: Dict[str, Any],
        force_create: bool = False
    ) -> int:
        #
        #Добавляет сущность в граф с проверкой дубликатов.
        #
        #Args:
        #    entity_type: тип сущности (Material, Process, Equipment, Property, 
        #               Experiment, Publication, Expert, Facility)
        #    properties: словарь свойств сущности (произвольный формат)
        #    force_create: принудительно создать новый узел
        #
        #Returns:
        #    int: ID узла
        #
        # Проверяем корректность типа
        if entity_type not in self.entity_labels:
            raise ValueError(f"Неизвестный тип сущности: {entity_type}. "
                           f"Доступные типы: {', '.join(self.entity_labels.keys())}")
        
        # Нормализуем свойства
        properties = self._normalize_properties(properties)
        
        # Проверяем, существует ли уже такой узел
        if not force_create:
            existing_id = self._find_existing_node(entity_type, properties)
            if existing_id is not None:
                entity_name = properties.get('name', properties.get('title', 'без имени'))
                print(f"ℹ️ {entity_type} '{entity_name}' уже существует (ID: {existing_id})")
                return existing_id
        
        # Создаем новый узел
        label = entity_type
        node_id = self.graph.create_node([label], properties)
        
        # Добавляем в кэш
        cache_key = self._generate_cache_key(entity_type, properties)
        self.cache['nodes'][cache_key] = node_id
        
        entity_name = properties.get('name', properties.get('title', 'без имени'))
        print(f"✅ Создан новый {entity_type}: '{entity_name}' (ID: {node_id})")
        
        return node_id
    
    # ==================== ДОБАВЛЕНИЕ СВЯЗЕЙ ====================
    
    def add_relationship(
        self,
        from_node: Union[int, str],
        to_node: Union[int, str],
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        #
        #Добавляет связь между узлами с проверкой дубликатов.
        #
        #Args:
        #    from_node: ID или имя начального узла
        #    to_node: ID или имя конечного узла
        #    rel_type: тип связи (uses_material, operates_at_condition, 
        #             produces_output, described_in, validated_by, contradicts)
        #    properties: свойства связи (произвольный формат)
        #
        #Returns:
        #   int: ID связи
        #
        if properties is None:
            properties = {}
        
        # Проверяем корректность типа связи
        if rel_type not in self.valid_relationships:
            raise ValueError(f"Неизвестный тип связи: {rel_type}. "
                           f"Доступные типы: {', '.join(self.valid_relationships)}")
        
        # Если переданы имена, ищем их ID
        if isinstance(from_node, str):
            from_node = self._find_node_by_name(from_node)
            if from_node is None:
                raise ValueError(f"Узел с именем '{from_node}' не найден")
        
        if isinstance(to_node, str):
            to_node = self._find_node_by_name(to_node)
            if to_node is None:
                raise ValueError(f"Узел с именем '{to_node}' не найден")
        
        # Проверяем существование связи
        existing_id = self._find_existing_relationship(from_node, to_node, rel_type, properties)
        if existing_id is not None:
            print(f"ℹ️ Связь '{rel_type}' уже существует (ID: {existing_id})")
            return existing_id
        
        # Создаем новую связь
        rel_id = self.graph.create_relationship(from_node, to_node, rel_type, properties)
        
        # Добавляем в кэш
        cache_key = f"{from_node}|{to_node}|{rel_type}"
        self.cache['relationships'][cache_key] = rel_id
        
        print(f"✅ Создана новая связь '{rel_type}' (ID: {rel_id})")
        return rel_id
    
    # ==================== УДОБНЫЕ МЕТОДЫ ====================
    
    def add_entity_with_relationship(
        self,
        from_entity_type: str,
        from_properties: Dict[str, Any],
        to_entity_type: str,
        to_properties: Dict[str, Any],
        rel_type: str,
        rel_properties: Optional[Dict[str, Any]] = None
    ) -> tuple:
        #
        #Добавляет две сущности и связь между ними.
        #
        #Returns:
        #   tuple: (from_node_id, to_node_id, relationship_id)
        
        from_id = self.add_entity(from_entity_type, from_properties)
        to_id = self.add_entity(to_entity_type, to_properties)
        rel_id = self.add_relationship(from_id, to_id, rel_type, rel_properties)
        
        return (from_id, to_id, rel_id)
    
    def connect_by_names(
        self,
        from_name: str,
        to_name: str,
        rel_type: str,
        rel_properties: Optional[Dict[str, Any]] = None
    ) -> int:
        #
        #Создает связь между двумя узлами по их именам.
        #
        from_id = self._find_node_by_name(from_name)
        if from_id is None:
            raise ValueError(f"Узел с именем '{from_name}' не найден")
        
        to_id = self._find_node_by_name(to_name)
        if to_id is None:
            raise ValueError(f"Узел с именем '{to_name}' не найден")
        
        return self.add_relationship(from_id, to_id, rel_type, rel_properties)
    
    # ==================== ЗАПРОСЫ ====================
    
    def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        #Выполняет Cypher-запрос.#
        if params is None:
            params = {}
        result = self.graph.execute(cypher_query, params)
        return result.to_list() if result else []
    
    def find_by_properties(self, entity_type: str, properties: Dict[str, Any]) -> List[Dict[str, Any]]:
        #Находит сущности по произвольным свойствам.#
        query = f"MATCH (n:{entity_type}) WHERE "
        conditions = []
        
        for key, value in properties.items():
            if isinstance(value, str):
                conditions.append(f"toLower(n.{key}) = toLower('{value}')")
            elif isinstance(value, (int, float)):
                conditions.append(f"n.{key} = {value}")
            else:
                conditions.append(f"n.{key} = {value}")
        
        query += " AND ".join(conditions)
        query += " RETURN n"
        
        return self.query(query)
    
    def find_connected(
        self, 
        node_id: int, 
        rel_type: Optional[str] = None,
        direction: str = 'outgoing'
    ) -> List[Dict[str, Any]]:
        #Находит связанные узлы.#
        dir_symbol = '-' if direction == 'outgoing' else '<-'
        rel_filter = f":{rel_type}" if rel_type else ""
        
        query = f"""
        MATCH (n){dir_symbol}[r{rel_filter}]->(connected)
        WHERE id(n) = {node_id}
        RETURN connected, type(r) as relationship_type, r as relationship_properties
        """
        
        return self.query(query)
    
    def get_node_info(self, node_id: int) -> Dict[str, Any]:
        #Получает информацию об узле.#
        query = f"MATCH (n) WHERE id(n) = {node_id} RETURN n"
        result = self.query(query)
        if result:
            return result[0].get('n', {})
        return {}
    
    # ==================== АНАЛИТИКА ====================
    
    def print_graph_summary(self):
        #Выводит сводку по графу.#
        print("\n" + "="*60)
        print("📊 СВОДКА ПО ГРАФУ ЗНАНИЙ")
        print("="*60)
        print(f"Всего узлов: {self.graph.node_count()}")
        print(f"Всего связей: {self.graph.edge_count()}")
        print(f"Размер кэша узлов: {len(self.cache['nodes'])}")
        print(f"Размер кэша связей: {len(self.cache['relationships'])}")
        
        # Статистика по типам сущностей
        print("\n📌 Статистика по типам сущностей:")
        for entity_type in self.entity_labels.keys():
            query = f"MATCH (n:{entity_type}) RETURN count(n) as count"
            result = self.query(query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"   {entity_type}: {count}")
        
        # Статистика по типам связей
        print("\n📌 Статистика по типам связей:")
        for rel_type in self.valid_relationships:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = self.query(query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"   {rel_type}: {count}")
        
        print("="*60)
    
    def export_to_json(self, filepath: str):
        #Экспортирует граф в JSON.#
        nodes_query = "MATCH (n) RETURN labels(n) as labels, n, id(n) as id"
        rels_query = """
        MATCH (a)-[r]->(b) 
        RETURN type(r) as type, r, id(r) as id, 
               id(startNode(r)) as from, id(endNode(r)) as to
        """
        
        nodes = self.query(nodes_query)
        rels = self.query(rels_query)
        
        data = {
            'export_date': datetime.now().isoformat(),
            'nodes': [
                {
                    'id': node['id'],
                    'labels': node['labels'],
                    'properties': node['n']
                }
                for node in nodes
            ],
            'relationships': [
                {
                    'id': rel['id'],
                    'type': rel['type'],
                    'from': rel['from'],
                    'to': rel['to'],
                    'properties': rel['r']
                }
                for rel in rels
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Граф экспортирован в {filepath}")

    # ==================== ПОИСК И ПОЛУЧЕНИЕ ДАННЫХ ====================
    
    def find_nodes_by_properties(
        self,
        entity_type: Optional[str] = None,
        properties: Dict[str, Any] = None,
        return_type: str = 'full'
    ) -> List[Dict[str, Any]]:
        """
        Находит узлы по части свойств.
        
        Args:
            entity_type: тип сущности (Material, Process, etc.) или None для всех типов
            properties: словарь с частичными свойствами для поиска
            return_type: 'full' - полная информация, 'ids' - только ID, 'names' - только имена
        
        Returns:
            List[Dict[str, Any]]: список найденных узлов
        """
        if properties is None:
            properties = {}
        
        # Формируем запрос
        query = "MATCH (n"
        if entity_type:
            query += f":{entity_type}"
        query += ") WHERE "
        
        conditions = []
        for key, value in properties.items():
            if isinstance(value, str):
                # Поиск по части строки (содержит)
                conditions.append(f"toLower(n.{key}) CONTAINS toLower('{value}')")
            elif isinstance(value, (int, float)):
                conditions.append(f"n.{key} = {value}")
            elif isinstance(value, bool):
                conditions.append(f"n.{key} = {value}")
            elif isinstance(value, list):
                # Для списков проверяем наличие элемента
                if value:
                    list_value = value[0]
                    if isinstance(list_value, str):
                        conditions.append(f"ANY(item IN n.{key} WHERE toLower(item) CONTAINS toLower('{list_value}'))")
                    else:
                        conditions.append(f"ANY(item IN n.{key} WHERE item = {list_value})")
            else:
                conditions.append(f"n.{key} = {value}")
        
        if not conditions:
            # Если нет условий, возвращаем все узлы
            query = "MATCH (n"
            if entity_type:
                query += f":{entity_type}"
            query += ") RETURN n, labels(n) as labels, id(n) as id"
        else:
            query += " AND ".join(conditions)
            query += " RETURN n, labels(n) as labels, id(n) as id"
        
        # Выполняем запрос
        results = self.query(query)
        
        if return_type == 'ids':
            return [row['id'] for row in results]
        elif return_type == 'names':
            return [row['n'].get('name', row['n'].get('title', 'Без имени')) for row in results]
        else:  # 'full'
            return results
    
    def get_node_with_relationships(
        self,
        node_identifier: Union[int, str, Dict[str, Any]],
        entity_type: Optional[str] = None,
        include_incoming: bool = True,
        include_outgoing: bool = True,
        relationship_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Получает узел и все его связи.
        
        Args:
            node_identifier: ID узла, имя узла или словарь свойств для поиска
            entity_type: тип сущности (если поиск по имени или свойствам)
            include_incoming: включить входящие связи
            include_outgoing: включить исходящие связи
            relationship_types: фильтр по типам отношений (None - все типы)
            depth: глубина обхода (1 - только прямые связи)
        
        Returns:
            Dict[str, Any]: структура с узлом и его связями
        """
        # Определяем ID узла
        node_id = self._resolve_node_id(node_identifier, entity_type)
        if node_id is None:
            raise ValueError(f"Узел не найден: {node_identifier}")
        
        result = {
            'node': {},
            'relationships': {
                'incoming': [],
                'outgoing': []
            },
            'connected_nodes': {
                'incoming': [],
                'outgoing': []
            },
            'full_graph': []
        }
        
        # Получаем информацию об узле
        node_info = self.get_node_info(node_id)
        result['node'] = node_info
        
        # Формируем фильтр по типам отношений
        rel_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"
        
        # Получаем исходящие связи
        if include_outgoing:
            outgoing_query = f"""
            MATCH (n)-[r{rel_filter}]->(connected)
            WHERE id(n) = {node_id}
            RETURN connected, labels(connected) as connected_labels, 
                   id(connected) as connected_id,
                   type(r) as relationship_type,
                   r as relationship_properties,
                   id(r) as relationship_id
            """
            outgoing_results = self.query(outgoing_query)
            
            for row in outgoing_results:
                result['relationships']['outgoing'].append({
                    'relationship_id': row['relationship_id'],
                    'type': row['relationship_type'],
                    'properties': row['relationship_properties'],
                    'to_node_id': row['connected_id']
                })
                
                result['connected_nodes']['outgoing'].append({
                    'id': row['connected_id'],
                    'labels': row['connected_labels'],
                    'properties': row['connected'],
                    'relationship_type': row['relationship_type']
                })
                
                result['full_graph'].append({
                    'from': node_id,
                    'to': row['connected_id'],
                    'relationship_type': row['relationship_type'],
                    'relationship_properties': row['relationship_properties']
                })
        
        # Получаем входящие связи
        if include_incoming:
            incoming_query = f"""
            MATCH (connected)-[r{rel_filter}]->(n)
            WHERE id(n) = {node_id}
            RETURN connected, labels(connected) as connected_labels,
                   id(connected) as connected_id,
                   type(r) as relationship_type,
                   r as relationship_properties,
                   id(r) as relationship_id
            """
            incoming_results = self.query(incoming_query)
            
            for row in incoming_results:
                result['relationships']['incoming'].append({
                    'relationship_id': row['relationship_id'],
                    'type': row['relationship_type'],
                    'properties': row['relationship_properties'],
                    'from_node_id': row['connected_id']
                })
                
                result['connected_nodes']['incoming'].append({
                    'id': row['connected_id'],
                    'labels': row['connected_labels'],
                    'properties': row['connected'],
                    'relationship_type': row['relationship_type']
                })
                
                result['full_graph'].append({
                    'from': row['connected_id'],
                    'to': node_id,
                    'relationship_type': row['relationship_type'],
                    'relationship_properties': row['relationship_properties']
                })
        
        # Если глубина > 1, рекурсивно получаем связи связанных узлов
        if depth > 1:
            for direction in ['incoming', 'outgoing']:
                for connected_node in result['connected_nodes'][direction]:
                    if connected_node['id'] != node_id:  # Избегаем циклов
                        sub_result = self.get_node_with_relationships(
                            connected_node['id'],
                            depth=depth - 1,
                            include_incoming=include_incoming,
                            include_outgoing=include_outgoing,
                            relationship_types=relationship_types
                        )
                        result['full_graph'].extend(sub_result['full_graph'])
        
        return result
    
    def _resolve_node_id(
        self,
        node_identifier: Union[int, str, Dict[str, Any]],
        entity_type: Optional[str] = None
    ) -> Optional[int]:
        """
        Преобразует идентификатор узла в ID.
        
        Args:
            node_identifier: ID, имя или свойства для поиска
            entity_type: тип сущности (для поиска по имени или свойствам)
        
        Returns:
            Optional[int]: ID узла или None
        """
        # Если передан ID
        if isinstance(node_identifier, int):
            # Проверяем существование узла
            node_info = self.get_node_info(node_identifier)
            if node_info:
                return node_identifier
            return None
        
        # Если передано имя
        if isinstance(node_identifier, str):
            if entity_type:
                # Ищем по типу и имени
                query = f"""
                MATCH (n:{entity_type})
                WHERE toLower(n.name) = toLower('{node_identifier}') 
                   OR toLower(n.title) = toLower('{node_identifier}')
                RETURN id(n) LIMIT 1
                """
            else:
                # Ищем по имени в любом типе
                query = f"""
                MATCH (n)
                WHERE toLower(n.name) = toLower('{node_identifier}') 
                   OR toLower(n.title) = toLower('{node_identifier}')
                RETURN id(n) LIMIT 1
                """
            
            results = self.query(query)
            if results:
                return results[0].get('id(n)', None)
            return None
        
        # Если передан словарь свойств
        if isinstance(node_identifier, dict):
            results = self.find_nodes_by_properties(entity_type, node_identifier, return_type='ids')
            if results:
                return results[0]
            return None
        
        return None
    
    # ==================== УДАЛЕНИЕ УЗЛОВ И СВЯЗЕЙ ====================
    
    def delete_relationship_by_id(self, relationship_id: int) -> bool:
        """
        Удаляет связь по ID.
        
        Args:
            relationship_id: ID связи
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            # Проверяем существование связи
            query = f"MATCH ()-[r]->() WHERE id(r) = {relationship_id} RETURN id(r)"
            result = self.query(query)
            if not result:
                print(f"⚠️ Связь с ID {relationship_id} не найдена")
                return False
            
            # Удаляем связь
            query = f"MATCH ()-[r]->() WHERE id(r) = {relationship_id} DELETE r"
            self.graph.execute(query)
            
            # Удаляем из кэша
            for key in list(self.cache['relationships'].keys()):
                if self.cache['relationships'][key] == relationship_id:
                    del self.cache['relationships'][key]
                    break
            
            print(f"✅ Связь с ID {relationship_id} удалена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при удалении связи: {e}")
            return False
    
    def delete_relationships_by_type(
        self,
        from_node: Optional[int] = None,
        to_node: Optional[int] = None,
        rel_type: Optional[str] = None
    ) -> int:
        """
        Удаляет связи по фильтрам.
        
        Args:
            from_node: ID начального узла (None - любой)
            to_node: ID конечного узла (None - любой)
            rel_type: тип связи (None - любой)
        
        Returns:
            int: количество удаленных связей
        """
        try:
            # Формируем запрос на поиск
            query = "MATCH (a)-[r"
            if rel_type:
                query += f":{rel_type}"
            query += "]->(b) "
            
            conditions = []
            if from_node is not None:
                conditions.append(f"id(a) = {from_node}")
            if to_node is not None:
                conditions.append(f"id(b) = {to_node}")
            
            if conditions:
                query += "WHERE " + " AND ".join(conditions)
            
            # Сначала считаем количество
            count_query = query + " RETURN count(r) as count"
            count_result = self.query(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            if count == 0:
                print("ℹ️ Связей для удаления не найдено")
                return 0
            
            # Удаляем
            delete_query = query + " DELETE r"
            self.graph.execute(delete_query)
            
            # Очищаем кэш
            self.cache['relationships'] = {}
            
            print(f"✅ Удалено {count} связей")
            return count
            
        except Exception as e:
            print(f"❌ Ошибка при удалении связей: {e}")
            return 0
    
    def delete_node_by_id(
        self,
        node_id: int,
        cascade: bool = True
    ) -> bool:
        """
        Удаляет узел по ID.
        
        Args:
            node_id: ID узла
            cascade: удалить все связи узла (True) или только если нет связей (False)
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            # Проверяем существование узла
            node_info = self.get_node_info(node_id)
            if not node_info:
                print(f"⚠️ Узел с ID {node_id} не найден")
                return False
            
            # Проверяем наличие связей
            query = f"""
            MATCH (n)-[r]-()
            WHERE id(n) = {node_id}
            RETURN count(r) as count
            """
            result = self.query(query)
            rel_count = result[0]['count'] if result else 0
            
            if rel_count > 0 and not cascade:
                print(f"⚠️ Узел имеет {rel_count} связей. Используйте cascade=True для удаления всех связей")
                return False
            
            # Удаляем все связи
            if rel_count > 0 and cascade:
                delete_rels_query = f"""
                MATCH (n)-[r]-()
                WHERE id(n) = {node_id}
                DELETE r
                """
                self.graph.execute(delete_rels_query)
                print(f"   Удалено {rel_count} связей")
            
            # Удаляем узел
            delete_node_query = f"MATCH (n) WHERE id(n) = {node_id} DELETE n"
            self.graph.execute(delete_node_query)
            
            # Удаляем из кэша
            for key in list(self.cache['nodes'].keys()):
                if self.cache['nodes'][key] == node_id:
                    del self.cache['nodes'][key]
            
            # Очищаем кэш связей
            self.cache['relationships'] = {}
            
            node_name = node_info.get('name', node_info.get('title', 'без имени'))
            print(f"✅ Узел '{node_name}' (ID: {node_id}) удален")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при удалении узла: {e}")
            return False
    
    def delete_node_by_properties(
        self,
        entity_type: Optional[str] = None,
        properties: Dict[str, Any] = None,
        cascade: bool = True,
        delete_all_matching: bool = False
    ) -> int:
        """
        Удаляет узлы по свойствам.
        
        Args:
            entity_type: тип сущности (None - все типы)
            properties: свойства для поиска узлов
            cascade: удалить все связи узлов
            delete_all_matching: удалить все найденные узлы (True) или только первый (False)
        
        Returns:
            int: количество удаленных узлов
        """
        if properties is None:
            properties = {}
        
        # Находим узлы для удаления
        nodes = self.find_nodes_by_properties(entity_type, properties, return_type='ids')
        
        if not nodes:
            print("ℹ️ Узлов для удаления не найдено")
            return 0
        
        if not delete_all_matching:
            nodes = [nodes[0]]
        
        deleted_count = 0
        for node_id in nodes:
            if self.delete_node_by_id(node_id, cascade):
                deleted_count += 1
        
        print(f"✅ Удалено {deleted_count} узлов")
        return deleted_count
    
    def delete_node_by_name(
        self,
        name: str,
        entity_type: Optional[str] = None,
        cascade: bool = True
    ) -> bool:
        """
        Удаляет узел по имени.
        
        Args:
            name: имя узла
            entity_type: тип сущности
            cascade: удалить все связи
        
        Returns:
            bool: True если успешно
        """
        node_id = self._resolve_node_id(name, entity_type)
        if node_id is None:
            print(f"⚠️ Узел с именем '{name}' не найден")
            return False
        
        return self.delete_node_by_id(node_id, cascade)
    
    def delete_all_nodes(self, cascade: bool = True) -> int:
        """
        Удаляет все узлы и связи.
        
        Args:
            cascade: удалить все связи
        
        Returns:
            int: количество удаленных узлов
        """
        try:
            # Получаем количество узлов
            count_query = "MATCH (n) RETURN count(n) as count"
            count_result = self.query(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            if count == 0:
                print("ℹ️ Граф уже пуст")
                return 0
            
            # Очищаем граф
            if cascade:
                # Удаляем все связи и узлы
                self.graph.execute("MATCH (n) DETACH DELETE n")
            else:
                # Удаляем только узлы без связей
                self.graph.execute("MATCH (n) WHERE NOT (n)--() DELETE n")
            
            # Очищаем кэш
            self.cache = {'nodes': {}, 'relationships': {}}
            
            print(f"✅ Удалено {count} узлов")
            return count
            
        except Exception as e:
            print(f"❌ Ошибка при удалении всех узлов: {e}")
            return 0
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ====================
    
    def find_orphan_nodes(self) -> List[Dict[str, Any]]:
        """
        Находит узлы без связей.
        
        Returns:
            List[Dict[str, Any]]: список узлов без связей
        """
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN n, labels(n) as labels, id(n) as id
        """
        return self.query(query)
    
    def get_node_degree(self, node_id: int) -> Dict[str, int]:
        """
        Получает степень узла (количество связей).
        
        Args:
            node_id: ID узла
        
        Returns:
            Dict[str, int]: словарь с количеством входящих и исходящих связей
        """
        result = {
            'incoming': 0,
            'outgoing': 0,
            'total': 0
        }
        
        query = f"""
        MATCH (n)-[r]->(connected)
        WHERE id(n) = {node_id}
        RETURN count(r) as count
        """
        out_result = self.query(query)
        result['outgoing'] = out_result[0]['count'] if out_result else 0
        
        query = f"""
        MATCH (connected)-[r]->(n)
        WHERE id(n) = {node_id}
        RETURN count(r) as count
        """
        in_result = self.query(query)
        result['incoming'] = in_result[0]['count'] if in_result else 0
        
        result['total'] = result['incoming'] + result['outgoing']
        
        return result
    
    # ==================== ЗАГРУЗКА ИЗ JSON ====================
    
    def load_from_json(
        self,
        filepath: str,
        clear_existing: bool = True,
        skip_duplicates: bool = True,
        verbose: bool = True
    ) -> Dict[str, int]:
        """
        Загружает граф из JSON-файла.
        
        Args:
            filepath: путь к JSON-файлу
            clear_existing: очистить существующий граф перед загрузкой
            skip_duplicates: пропускать дубликаты (True) или пересоздавать (False)
            verbose: выводить подробную информацию
        
        Returns:
            Dict[str, int]: статистика загрузки {
                'nodes_loaded': количество загруженных узлов,
                'relationships_loaded': количество загруженных связей,
                'nodes_skipped': пропущенных узлов,
                'relationships_skipped': пропущенных связей
            }
        """
        # Проверяем существование файла
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл {filepath} не найден")
        
        # Загружаем JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print("="*60)
            print("📥 ЗАГРУЗКА ГРАФА ИЗ JSON")
            print("="*60)
            print(f"📁 Файл: {filepath}")
            print(f"📅 Дата экспорта: {data.get('export_date', 'не указана')}")
            print(f"📊 Узлов в файле: {len(data.get('nodes', []))}")
            print(f"📊 Связей в файле: {len(data.get('relationships', []))}")
            print("-"*60)
        
        # Очищаем существующий граф если нужно
        if clear_existing:
            if verbose:
                print("🧹 Очистка существующего графа...")
            self.delete_all_nodes(cascade=True)
            # Очищаем кэш
            self.cache = {'nodes': {}, 'relationships': {}}
        
        # Статистика
        stats = {
            'nodes_loaded': 0,
            'relationships_loaded': 0,
            'nodes_skipped': 0,
            'relationships_skipped': 0
        }
        
        # Словарь для маппинга старых ID на новые
        id_mapping = {}
        
        # ===== 1. ЗАГРУЗКА УЗЛОВ =====
        if verbose:
            print("\n📌 Загрузка узлов...")
        
        for node_data in data.get('nodes', []):
            try:
                # Получаем данные узла
                old_id = node_data.get('id')
                labels = node_data.get('labels', [])
                properties = node_data.get('properties', {})
                
                if not labels:
                    if verbose:
                        print(f"   ⚠️ Пропущен узел без меток (ID: {old_id})")
                    stats['nodes_skipped'] += 1
                    continue
                
                # Определяем тип сущности (первая метка)
                entity_type = labels[0]
                
                # Проверяем, существует ли уже такой узел
                if skip_duplicates:
                    existing_id = self._find_existing_node(entity_type, properties)
                    if existing_id is not None:
                        id_mapping[old_id] = existing_id
                        stats['nodes_skipped'] += 1
                        if verbose:
                            name = properties.get('name', properties.get('title', 'без имени'))
                            print(f"   ⏭️ Пропущен дубликат: {entity_type} '{name}' (ID: {old_id} -> {existing_id})")
                        continue
                
                # Создаем новый узел
                new_id = self.graph.create_node(labels, properties)
                
                # Сохраняем маппинг
                id_mapping[old_id] = new_id
                stats['nodes_loaded'] += 1
                
                if verbose and stats['nodes_loaded'] % 10 == 0:
                    print(f"   ✅ Загружено {stats['nodes_loaded']} узлов...")
                    
            except Exception as e:
                if verbose:
                    print(f"   ❌ Ошибка при загрузке узла (ID: {old_id}): {e}")
                stats['nodes_skipped'] += 1
        
        if verbose:
            print(f"   ✅ Загружено узлов: {stats['nodes_loaded']}")
            print(f"   ⏭️ Пропущено узлов: {stats['nodes_skipped']}")
        
        # ===== 2. ЗАГРУЗКА СВЯЗЕЙ =====
        if verbose:
            print("\n📌 Загрузка связей...")
        
        for rel_data in data.get('relationships', []):
            try:
                # Получаем данные связи
                old_id = rel_data.get('id')
                rel_type = rel_data.get('type')
                from_old = rel_data.get('from')
                to_old = rel_data.get('to')
                properties = rel_data.get('properties', {})
                
                # Проверяем наличие всех необходимых данных
                if not rel_type:
                    if verbose:
                        print(f"   ⚠️ Пропущена связь без типа (ID: {old_id})")
                    stats['relationships_skipped'] += 1
                    continue
                
                if from_old not in id_mapping or to_old not in id_mapping:
                    if verbose:
                        print(f"   ⚠️ Пропущена связь с неизвестными узлами (ID: {old_id})")
                    stats['relationships_skipped'] += 1
                    continue
                
                from_new = id_mapping[from_old]
                to_new = id_mapping[to_old]
                
                # Проверяем, существует ли уже такая связь
                if skip_duplicates:
                    existing_id = self._find_existing_relationship(from_new, to_new, rel_type, properties)
                    if existing_id is not None:
                        stats['relationships_skipped'] += 1
                        if verbose:
                            print(f"   ⏭️ Пропущен дубликат связи: {rel_type} (ID: {old_id} -> {existing_id})")
                        continue
                
                # Создаем новую связь
                self.graph.create_relationship(from_new, to_new, rel_type, properties)
                stats['relationships_loaded'] += 1
                
                if verbose and stats['relationships_loaded'] % 10 == 0:
                    print(f"   ✅ Загружено {stats['relationships_loaded']} связей...")
                    
            except Exception as e:
                if verbose:
                    print(f"   ❌ Ошибка при загрузке связи (ID: {old_id}): {e}")
                stats['relationships_skipped'] += 1
        
        if verbose:
            print(f"   ✅ Загружено связей: {stats['relationships_loaded']}")
            print(f"   ⏭️ Пропущено связей: {stats['relationships_skipped']}")
        
        # ===== 3. ИТОГИ =====
        if verbose:
            print("\n" + "="*60)
            print("📊 ИТОГИ ЗАГРУЗКИ")
            print("="*60)
            print(f"✅ Загружено узлов: {stats['nodes_loaded']}")
            print(f"✅ Загружено связей: {stats['relationships_loaded']}")
            print(f"⏭️ Пропущено узлов: {stats['nodes_skipped']}")
            print(f"⏭️ Пропущено связей: {stats['relationships_skipped']}")
            print(f"📊 Всего узлов в графе: {self.graph.node_count()}")
            print(f"📊 Всего связей в графе: {self.graph.edge_count()}")
            print("="*60)
        
        return stats

    def load_from_json_batch(
        self,
        filepath: str,
        batch_size: int = 1000,
        clear_existing: bool = True,
        skip_duplicates: bool = True,
        verbose: bool = True
    ) -> Dict[str, int]:
        """
        Загружает граф из JSON-файла порциями (для больших файлов).
        
        Args:
            filepath: путь к JSON-файлу
            batch_size: размер порции
            clear_existing: очистить существующий граф перед загрузкой
            skip_duplicates: пропускать дубликаты
            verbose: выводить подробную информацию
        
        Returns:
            Dict[str, int]: статистика загрузки
        """
        # Проверяем существование файла
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл {filepath} не найден")
        
        # Загружаем JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print("="*60)
            print("📥 ЗАГРУЗКА ГРАФА ИЗ JSON (ПОРЦИЯМИ)")
            print("="*60)
            print(f"📁 Файл: {filepath}")
            print(f"📅 Дата экспорта: {data.get('export_date', 'не указана')}")
            print(f"📊 Узлов в файле: {len(data.get('nodes', []))}")
            print(f"📊 Связей в файле: {len(data.get('relationships', []))}")
            print(f"📦 Размер порции: {batch_size}")
            print("-"*60)
        
        # Очищаем существующий граф если нужно
        if clear_existing:
            if verbose:
                print("🧹 Очистка существующего графа...")
            self.delete_all_nodes(cascade=True)
            self.cache = {'nodes': {}, 'relationships': {}}
        
        # Статистика
        stats = {
            'nodes_loaded': 0,
            'relationships_loaded': 0,
            'nodes_skipped': 0,
            'relationships_skipped': 0
        }
        
        # Словарь для маппинга старых ID на новые
        id_mapping = {}
        
        # ===== 1. ЗАГРУЗКА УЗЛОВ ПОРЦИЯМИ =====
        if verbose:
            print("\n📌 Загрузка узлов порциями...")
        
        nodes = data.get('nodes', [])
        total_nodes = len(nodes)
        
        for i in range(0, total_nodes, batch_size):
            batch = nodes[i:i+batch_size]
            
            for node_data in batch:
                try:
                    old_id = node_data.get('id')
                    labels = node_data.get('labels', [])
                    properties = node_data.get('properties', {})
                    
                    if not labels:
                        stats['nodes_skipped'] += 1
                        continue
                    
                    entity_type = labels[0]
                    
                    if skip_duplicates:
                        existing_id = self._find_existing_node(entity_type, properties)
                        if existing_id is not None:
                            id_mapping[old_id] = existing_id
                            stats['nodes_skipped'] += 1
                            continue
                    
                    new_id = self.graph.create_node(labels, properties)
                    id_mapping[old_id] = new_id
                    stats['nodes_loaded'] += 1
                    
                except Exception as e:
                    stats['nodes_skipped'] += 1
            
            if verbose:
                print(f"   ✅ Загружено {min(i+batch_size, total_nodes)} из {total_nodes} узлов...")
        
        if verbose:
            print(f"   ✅ Загружено узлов: {stats['nodes_loaded']}")
            print(f"   ⏭️ Пропущено узлов: {stats['nodes_skipped']}")
        
        # ===== 2. ЗАГРУЗКА СВЯЗЕЙ ПОРЦИЯМИ =====
        if verbose:
            print("\n📌 Загрузка связей порциями...")
        
        relationships = data.get('relationships', [])
        total_rels = len(relationships)
        
        for i in range(0, total_rels, batch_size):
            batch = relationships[i:i+batch_size]
            
            for rel_data in batch:
                try:
                    old_id = rel_data.get('id')
                    rel_type = rel_data.get('type')
                    from_old = rel_data.get('from')
                    to_old = rel_data.get('to')
                    properties = rel_data.get('properties', {})
                    
                    if not rel_type or from_old not in id_mapping or to_old not in id_mapping:
                        stats['relationships_skipped'] += 1
                        continue
                    
                    from_new = id_mapping[from_old]
                    to_new = id_mapping[to_old]
                    
                    if skip_duplicates:
                        existing_id = self._find_existing_relationship(from_new, to_new, rel_type, properties)
                        if existing_id is not None:
                            stats['relationships_skipped'] += 1
                            continue
                    
                    self.graph.create_relationship(from_new, to_new, rel_type, properties)
                    stats['relationships_loaded'] += 1
                    
                except Exception as e:
                    stats['relationships_skipped'] += 1
            
            if verbose:
                print(f"   ✅ Загружено {min(i+batch_size, total_rels)} из {total_rels} связей...")
        
        if verbose:
            print(f"   ✅ Загружено связей: {stats['relationships_loaded']}")
            print(f"   ⏭️ Пропущено связей: {stats['relationships_skipped']}")
        
        # ===== 3. ИТОГИ =====
        if verbose:
            print("\n" + "="*60)
            print("📊 ИТОГИ ЗАГРУЗКИ")
            print("="*60)
            print(f"✅ Загружено узлов: {stats['nodes_loaded']}")
            print(f"✅ Загружено связей: {stats['relationships_loaded']}")
            print(f"⏭️ Пропущено узлов: {stats['nodes_skipped']}")
            print(f"⏭️ Пропущено связей: {stats['relationships_skipped']}")
            print(f"📊 Всего узлов в графе: {self.graph.node_count()}")
            print(f"📊 Всего связей в графе: {self.graph.edge_count()}")
            print("="*60)
        
        return stats

    def validate_json_schema(self, filepath: str) -> bool:
        """
        Проверяет, соответствует ли JSON-файл схеме графа.
        
        Args:
            filepath: путь к JSON-файлу
        
        Returns:
            bool: True если схема валидна
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем наличие обязательных полей
            required_fields = ['nodes', 'relationships']
            for field in required_fields:
                if field not in data:
                    print(f"❌ Отсутствует обязательное поле: {field}")
                    return False
            
            # Проверяем структуру узлов
            for node in data.get('nodes', []):
                if 'id' not in node or 'labels' not in node or 'properties' not in node:
                    print(f"❌ Неверная структура узла: {node}")
                    return False
            
            # Проверяем структуру связей
            for rel in data.get('relationships', []):
                required_rel_fields = ['id', 'type', 'from', 'to']
                for field in required_rel_fields:
                    if field not in rel:
                        print(f"❌ Неверная структура связи: {rel}")
                        return False
            
            print("✅ JSON-файл соответствует схеме")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке схемы: {e}")
            return False

    def get_import_preview(self, filepath: str, limit: int = 5) -> Dict[str, Any]:
        """
        Показывает превью данных перед импортом.
        
        Args:
            filepath: путь к JSON-файлу
            limit: количество примеров для показа
        
        Returns:
            Dict: превью данных
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        preview = {
            'total_nodes': len(data.get('nodes', [])),
            'total_relationships': len(data.get('relationships', [])),
            'export_date': data.get('export_date', 'не указана'),
            'sample_nodes': [],
            'sample_relationships': [],
            'node_types': {},
            'relationship_types': {}
        }
        
        # Собираем статистику по типам узлов
        for node in data.get('nodes', [])[:limit]:
            preview['sample_nodes'].append({
                'id': node.get('id'),
                'labels': node.get('labels'),
                'properties': node.get('properties', {})
            })
        
        for rel in data.get('relationships', [])[:limit]:
            preview['sample_relationships'].append({
                'type': rel.get('type'),
                'from': rel.get('from'),
                'to': rel.get('to')
            })
        
        # Считаем типы
        for node in data.get('nodes', []):
            for label in node.get('labels', []):
                preview['node_types'][label] = preview['node_types'].get(label, 0) + 1
        
        for rel in data.get('relationships', []):
            rel_type = rel.get('type')
            preview['relationship_types'][rel_type] = preview['relationship_types'].get(rel_type, 0) + 1
        
        return preview
# ==================== ПРИМЕР ИСПОЛЬЗОВАНИЯ ====================

def demo_search_and_delete():
    """Демонстрация поиска и удаления узлов."""
    
    # Создаем граф
    kg = ScientificTangleKnowledgeGraph()
    
    # Добавляем тестовые данные
    print("="*60)
    print("ДОБАВЛЕНИЕ ТЕСТОВЫХ ДАННЫХ")
    print("="*60)
    
    # Материалы
    ni_id = kg.add_entity('Material', {
        'name': 'Никель',
        'type': 'металл',
        'purity': '99.9%',
        'density': 8.9
    })
    
    cu_id = kg.add_entity('Material', {
        'name': 'Медь',
        'type': 'металл',
        'purity': '99.5%',
        'density': 8.96
    })
    
    slag_id = kg.add_entity('Material', {
        'name': 'Шлак',
        'type': 'отход',
        'composition': 'SiO2, CaO'
    })
    
    # Процессы
    smelting_id = kg.add_entity('Process', {
        'name': 'Плавка',
        'temperature': 1450,
        'efficiency': 92.3
    })
    
    leaching_id = kg.add_entity('Process', {
        'name': 'Выщелачивание',
        'temperature': 80,
        'pressure': 1.5
    })
    
    # Связи
    kg.add_relationship(smelting_id, ni_id, 'uses_material')
    kg.add_relationship(smelting_id, slag_id, 'produces_output')
    kg.add_relationship(leaching_id, cu_id, 'uses_material')
    kg.add_relationship(leaching_id, ni_id, 'produces_output')
    
    print("\n✅ Тестовые данные добавлены\n")
    
    # ===== 1. ПОИСК УЗЛОВ =====
    
    print("="*60)
    print("1. ПОИСК УЗЛОВ ПО СВОЙСТВАМ")
    print("="*60)
    
    # Поиск по части имени
    print("\n🔍 Поиск материалов, содержащих 'ник' в имени:")
    results = kg.find_nodes_by_properties(
        'Material',
        {'name': 'ник'}
    )
    for row in results:
        print(f"   • {row['n'].get('name')} (ID: {row['id']})")
    
    # Поиск по точным свойствам
    print("\n🔍 Поиск материалов с плотностью 8.96:")
    results = kg.find_nodes_by_properties(
        'Material',
        {'density': 8.96}
    )
    for row in results:
        print(f"   • {row['n'].get('name')} (плотность: {row['n'].get('density')})")
    
    # ===== 2. ПОЛУЧЕНИЕ УЗЛА СО СВЯЗЯМИ =====
    
    print("\n" + "="*60)
    print("2. ПОЛУЧЕНИЕ УЗЛА СО СВЯЗЯМИ")
    print("="*60)
    
    print("\n🔍 Получение узла 'Никель' со всеми связями:")
    node_data = kg.get_node_with_relationships('Никель', 'Material')
    
    print(f"\n📌 Узел: {node_data['node'].get('name')}")
    print(f"   Свойства: {node_data['node']}")
    
    print(f"\n📌 Исходящие связи ({len(node_data['relationships']['outgoing'])}):")
    for rel in node_data['relationships']['outgoing']:
        connected = next(
            (n for n in node_data['connected_nodes']['outgoing'] 
             if n['id'] == rel['to_node_id']), 
            {}
        )
        print(f"   → {rel['type']} -> {connected.get('properties', {}).get('name', 'без имени')}")
    
    print(f"\n📌 Входящие связи ({len(node_data['relationships']['incoming'])}):")
    for rel in node_data['relationships']['incoming']:
        connected = next(
            (n for n in node_data['connected_nodes']['incoming'] 
             if n['id'] == rel['from_node_id']), 
            {}
        )
        print(f"   ← {rel['type']} <- {connected.get('properties', {}).get('name', 'без имени')}")
    
    # ===== 3. УДАЛЕНИЕ УЗЛОВ =====
    
    print("\n" + "="*60)
    print("3. УДАЛЕНИЕ УЗЛОВ")
    print("="*60)
    
    # Удаление по имени
    print("\n🗑️ Удаление узла 'Шлак' с каскадом:")
    kg.delete_node_by_name('Шлак', 'Material', cascade=True)
    
    # Удаление по свойствам
    print("\n🗑️ Удаление материала с плотностью 8.96 (только первый):")
    kg.delete_node_by_properties('Material', {'density': 8.96}, cascade=True, delete_all_matching=False)
    
    # Показать оставшиеся узлы
    print("\n📊 Оставшиеся узлы:")
    remaining = kg.find_nodes_by_properties(None, {})
    for row in remaining:
        name = row['n'].get('name', row['n'].get('title', 'без имени'))
        print(f"   • {name} (ID: {row['id']}, тип: {row['labels']})")
    
    # ===== 4. УДАЛЕНИЕ СВЯЗЕЙ =====
    
    print("\n" + "="*60)
    print("4. УДАЛЕНИЕ СВЯЗЕЙ")
    print("="*60)
    
    # Добавим новые связи для демонстрации
    mat_id = kg.add_entity('Material', {'name': 'Тестовый материал'})
    proc_id = kg.add_entity('Process', {'name': 'Тестовый процесс'})
    kg.add_relationship(mat_id, proc_id, 'uses_material')
    kg.add_relationship(mat_id, proc_id, 'produces_output')
    
    # Удаление всех связей между узлами
    print("\n🗑️ Удаление всех связей между тестовыми узлами:")
    kg.delete_relationships_by_type(
        from_node=mat_id,
        to_node=proc_id
    )
    
    # ===== 5. ПОИСК УЗЛОВ БЕЗ СВЯЗЕЙ =====
    
    print("\n" + "="*60)
    print("5. ПОИСК УЗЛОВ БЕЗ СВЯЗЕЙ")
    print("="*60)
    
    orphans = kg.find_orphan_nodes()
    print(f"🔍 Найдено узлов без связей: {len(orphans)}")
    for row in orphans:
        name = row['n'].get('name', row['n'].get('title', 'без имени'))
        print(f"   • {name} (ID: {row['id']})")
    
    # ===== 6. СТАТИСТИКА =====
    
    print("\n" + "="*60)
    print("6. СТАТИСТИКА")
    print("="*60)
    
    kg.print_graph_summary()
    
    print("\n✅ Демонстрация завершена!")

if __name__ == "__main__":
    demo_search_and_delete()    

# ==================== ПРИМЕР ИСПОЛЬЗОВАНИЯ ====================

def main():
    #Демонстрация работы Knowledge Graph.#
    
    # Создаем экземпляр графа
    kg = ScientificTangleKnowledgeGraph()
    
    print("\n" + "="*60)
    print("🚀 ДЕМОНСТРАЦИЯ РАБОТЫ")
    print("="*60 + "\n")
    
    # ===== 1. ДОБАВЛЕНИЕ СУЩНОСТЕЙ С ПРОИЗВОЛЬНЫМИ СВОЙСТВАМИ =====
    
    print("📌 1. Добавление сущностей с произвольными свойствами:")
    print("-" * 50)
    
    # Material - произвольные свойства
    ni_matte = kg.add_entity('Material', {
        'name': 'Никелевый штейн',
        'type': 'промежуточный продукт',
        'composition': 'Ni 45%, Cu 20%, Fe 15%, S 10%',
        'nickel_content': 45.5,
        'melting_point': 1100,
        'density': 5.2,
        'origin': 'Норильск',
        'color': 'серый'
    })
    
    slag = kg.add_entity('Material', {
        'name': 'Шлак',
        'type': 'отход производства',
        'composition': 'SiO2 40%, CaO 25%, FeO 20%',
        'density': 3.8,
        'melting_point': 1400
    })
    
    copper = kg.add_entity('Material', {
        'name': 'Медь',
        'type': 'металл',
        'purity': '99.9%',
        'density': 8.96,
        'conductivity': '58 MS/m'
    })
    
    # Process
    smelting = kg.add_entity('Process', {
        'name': 'Плавка в печи взвешенной плавки',
        'type': 'пирометаллургический',
        'temperature': 1450,
        'pressure': 1.2,
        'productivity': 1500,
        'efficiency': 92.3,
        'oxygen_enrichment': 35.0
    })
    
    electrowinning = kg.add_entity('Process', {
        'name': 'Электроэкстракция никеля',
        'type': 'гидрометаллургический',
        'temperature': 60,
        'current_density': 200,
        'voltage': 3.5,
        'efficiency': 95.5,
        'flow_rate': 2.5
    })
    
    # Equipment
    furnace = kg.add_entity('Equipment', {
        'name': 'Печь взвешенной плавки ПВП-500',
        'model': 'ПВП-500',
        'manufacturer': 'Уралмаш',
        'capacity': 500,
        'power_consumption': 1500,
        'max_temperature': 1600,
        'year_installed': 2020
    })
    
    cell = kg.add_entity('Equipment', {
        'name': 'Электролизная ванна ЭВ-100',
        'model': 'ЭВ-100',
        'manufacturer': 'Казцинк',
        'capacity': 100,
        'voltage_range': '2-5',
        'material': 'Титан'
    })
    
    # Property
    property1 = kg.add_entity('Property', {
        'name': 'Температура плавления',
        'unit': '°C',
        'value_range': '800-1600',
        'measurement_method': 'DSC'
    })
    
    # Experiment
    exp1 = kg.add_entity('Experiment', {
        'id': 'EXP-2025-001',
        'name': 'Исследование распределения металлов',
        'date': '2025-01-15',
        'temperature': 1450,
        'duration': 720,
        'sample_size': 100,
        'replicates': 3,
        'equipment_used': ['ПВП-500', 'Анализатор']
    })
    
    # Publication
    pub1 = kg.add_entity('Publication', {
        'title': 'Распределение благородных металлов между штейном и шлаком',
        'authors': ['Иванов И.И.', 'Петров П.П.'],
        'year': 2023,
        'journal': 'Металлургия',
        'doi': '10.1234/met.2023.001',
        'language': 'ru',
        'pages': '45-67'
    })
    
    pub2 = kg.add_entity('Publication', {
        'title': 'Optimization of Nickel Electrowinning Process',
        'authors': ['Smith J.', 'Johnson M.'],
        'year': 2022,
        'journal': 'Hydrometallurgy',
        'doi': '10.5678/hyd.2022.002',
        'language': 'en',
        'pages': '112-128'
    })
    
    # Expert
    expert1 = kg.add_entity('Expert', {
        'name': 'Иванов Иван Иванович',
        'department': 'Лаборатория гидрометаллургии',
        'position': 'Заведующий лабораторией',
        'experience_years': 25,
        'expertise_areas': ['никель', 'электролиз', 'гидрометаллургия'],
        'email': 'ivanov@institute.ru'
    })
    
    expert2 = kg.add_entity('Expert', {
        'name': 'Петров Петр Петрович',
        'department': 'Лаборатория пирометаллургии',
        'position': 'Старший научный сотрудник',
        'experience_years': 15,
        'expertise_areas': ['плавка', 'шлаки', 'распределение металлов'],
        'email': 'petrov@institute.ru'
    })
    
    # Facility
    facility = kg.add_entity('Facility', {
        'name': 'Лаборатория металлургических процессов',
        'location': 'Москва',
        'department': 'НИИ Металлургии',
        'equipment': ['ПВП-500', 'ЭВ-100'],
        'capacity': 'до 1000 кг'
    })
    
    print("\n✅ Все сущности успешно добавлены\n")
    
    # ===== 2. ДОБАВЛЕНИЕ СВЯЗЕЙ =====
    
    print("📌 2. Добавление связей:")
    print("-" * 50)
    
    # uses_material - процесс использует материал
    kg.add_relationship(smelting, ni_matte, 'uses_material', {
        'role': 'исходное сырье',
        'consumption': 1000,
        'unit': 'кг/т'
    })
    
    kg.add_relationship(electrowinning, copper, 'uses_material', {
        'role': 'электролит',
        'concentration': 50,
        'unit': 'г/л'
    })
    
    # produces_output - процесс производит материал
    kg.add_relationship(smelting, slag, 'produces_output', {
        'type': 'отход',
        'amount': 400,
        'unit': 'кг/т',
        'metal_loss': 2.5
    })
    
    kg.add_relationship(electrowinning, copper, 'produces_output', {
        'type': 'продукт',
        'purity': '99.9%',
        'yield': 98.5
    })
    
    # operates_at_condition - процесс работает при условиях
    kg.add_relationship(smelting, property1, 'operates_at_condition', {
        'value': 1450,
        'unit': '°C',
        'tolerance': 50
    })
    
    # described_in - публикация описывает процесс или материал
    kg.add_relationship(pub1, smelting, 'described_in', {
        'relevance': 'high',
        'confidence': 0.95
    })
    
    kg.add_relationship(pub2, electrowinning, 'described_in', {
        'relevance': 'medium',
        'confidence': 0.90
    })
    
    kg.add_relationship(pub1, ni_matte, 'described_in', {
        'relevance': 'high'
    })
    
    # validated_by - эксперимент подтвержден экспертом
    kg.add_relationship(exp1, expert1, 'validated_by', {
        'date': '2025-01-20',
        'confidence': 0.95,
        'comments': 'Результаты подтверждены'
    })
    
    kg.add_relationship(exp1, expert2, 'validated_by', {
        'date': '2025-01-22',
        'confidence': 0.90
    })
    
    # contradicts - противоречие между публикациями
    kg.add_relationship(pub1, pub2, 'contradicts', {
        'reason': 'Различные оптимальные температуры',
        'confidence': 0.70
    })
    
    # Дополнительные связи
    kg.add_relationship(furnace, smelting, 'uses_material', {
        'role': 'оборудование'
    })
    
    kg.add_relationship(cell, electrowinning, 'uses_material', {
        'role': 'оборудование'
    })
    
    kg.add_relationship(expert1, facility, 'validated_by', {
        'role': 'руководитель'
    })
    
    print("\n✅ Все связи успешно добавлены\n")
    
    # ===== 3. ПРОВЕРКА ДЕДУПЛИКАЦИИ =====
    
    print("📌 3. Проверка дедупликации:")
    print("-" * 50)
    
    # Попытка добавить существующую сущность
    duplicate = kg.add_entity('Material', {
        'name': 'Никелевый штейн',
        'type': 'промежуточный продукт'
    })
    print(f"   Возвращен ID существующего узла: {duplicate}")
    
    # Попытка создать существующую связь
    duplicate_rel = kg.add_relationship(
        pub1, smelting,
        'described_in',
        {'relevance': 'high'}
    )
    print(f"   Возвращен ID существующей связи: {duplicate_rel}\n")
    
    # ===== 4. ВЫПОЛНЕНИЕ ЗАПРОСОВ =====
    
    print("📌 4. Выполнение запросов:")
    print("-" * 50)
    
    # Запрос 1: Найти все процессы, использующие никелевый штейн
    query = """
    MATCH (p:Process)-[:uses_material]->(m:Material)
    WHERE toLower(m.name) CONTAINS 'никелевый'
    RETURN p.name as process, m.name as material, 
           p.temperature as temperature, p.efficiency as efficiency
    """
    results = kg.query(query)
    print("🔍 Процессы, использующие никелевый штейн:")
    for row in results:
        print(f"   • {row['process']} (T={row.get('temperature', 'N/A')}°C, η={row.get('efficiency', 'N/A')}%)")
    
    # Запрос 2: Найти публикации, описывающие процессы
    query = """
    MATCH (pub:Publication)-[:described_in]->(p:Process)
    RETURN pub.title as publication, p.name as process, pub.year as year
    ORDER BY pub.year DESC
    """
    results = kg.query(query)
    print("\n🔍 Публикации, описывающие процессы:")
    for row in results:
        print(f"   • {row['publication']} ({row['year']}) -> {row['process']}")
    
    # Запрос 3: Найти экспертов по теме
    query = """
    MATCH (e:Expert)-[:validated_by]->(exp:Experiment)
    MATCH (exp)-[:validated_by]->(p:Process)
    RETURN e.name as expert, e.department as department, 
           count(exp) as experiments_count
    ORDER BY experiments_count DESC
    """
    results = kg.query(query)
    print("\n🔍 Эксперты по количеству валидированных экспериментов:")
    for row in results:
        print(f"   • {row['expert']} ({row['department']}) - {row['experiments_count']} экспериментов")
    
    # Запрос 4: Найти противоречия
    query = """
    MATCH (pub1:Publication)-[:contradicts]->(pub2:Publication)
    RETURN pub1.title as pub1, pub2.title as pub2, 
           pub1.year as year1, pub2.year as year2
    """
    results = kg.query(query)
    print("\n🔍 Противоречия между публикациями:")
    for row in results:
        print(f"   • {row['pub1']} ({row['year1']}) ↔ {row['pub2']} ({row['year2']})")
    
    # ===== 5. ПОИСК ПО ПРОИЗВОЛЬНЫМ СВОЙСТВАМ =====
    
    print("\n📌 5. Поиск по произвольным свойствам:")
    print("-" * 50)
    
    # Найти материалы с плотностью > 5
    materials = kg.find_by_properties('Material', {'density': 5.2})
    print(f"🔍 Найдено материалов с density=5.2: {len(materials)}")
    
    # Найти экспертов с опытом > 20 лет
    experts = kg.find_by_properties('Expert', {'experience_years': 25})
    print(f"🔍 Найдено экспертов с опытом 25 лет: {len(experts)}")
    
    # ===== 6. ВЫВОД СВОДКИ =====
    
    kg.print_graph_summary()
    
    # ===== 7. ЭКСПОРТ =====
    
    kg.export_to_json('knowledge_graph_export.json')
    
    print("\n✅ Демонстрация завершена!")

if __name__ == "__main__":
    main()