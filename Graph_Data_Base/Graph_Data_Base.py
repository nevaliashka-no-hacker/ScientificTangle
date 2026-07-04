import ocpg
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import json
import os

class ScientificTangleKnowledgeGraph:
    
    def __init__(self):
        self.graph = ocpg.Graph()
        self.cache = {
            'nodes': {},
            'relationships': {}
        }
        
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
        
        self.valid_relationships = [
            'uses_material',
            'operates_at_condition',
            'produces_output',
            'described_in',
            'validated_by',
            'contradicts'
        ]
        
        print("Knowledge Graph инициализирован")
        print(f"   Поддерживаемые сущности: {', '.join(self.entity_labels.keys())}")
        print(f"   Поддерживаемые отношения: {', '.join(self.valid_relationships)}")
    
    def _generate_cache_key(self, entity_type: str, properties: Dict[str, Any]) -> str:
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
        cache_key = self._generate_cache_key(entity_type, properties)
        if cache_key in self.cache['nodes']:
            return self.cache['nodes'][cache_key]
        
        unique_fields = self.unique_fields.get(entity_type, ['name'])
        
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
            print(f"Ошибка при поиске узла: {e}")
        
        return None
    
    def _find_existing_relationship(
        self,
        from_node: int,
        to_node: int,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        if properties is None:
            properties = {}
        
        cache_key = f"{from_node}|{to_node}|{rel_type}"
        if cache_key in self.cache['relationships']:
            return self.cache['relationships'][cache_key]
        
        query = f"""
        MATCH (a)-[r:{rel_type}]->(b)
        WHERE id(a) = {from_node} AND id(b) = {to_node}
        """
        
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
            print(f"Ошибка при поиске связи: {e}")
        
        return None
    
    def _find_node_by_name(self, name: str) -> Optional[int]:
        query = f"""
        MATCH (n) 
        WHERE toLower(n.name) = toLower('{name}') OR toLower(n.title) = toLower('{name}')
        RETURN id(n) LIMIT 1
        """
        try:
            result = self.graph.execute(query)
            if result and len(result.to_list()) > 0:
                return result.to_list()[0][0]
        except:
            pass
        return None
    
    def add_entity(
        self,
        entity_type: str,
        properties: Dict[str, Any],
        force_create: bool = False
    ) -> int:
        if entity_type not in self.entity_labels:
            raise ValueError(f"Неизвестный тип сущности: {entity_type}. "
                           f"Доступные типы: {', '.join(self.entity_labels.keys())}")
        
        properties = self._normalize_properties(properties)
        
        if not force_create:
            existing_id = self._find_existing_node(entity_type, properties)
            if existing_id is not None:
                entity_name = properties.get('name', properties.get('title', 'без имени'))
                print(f"{entity_type} '{entity_name}' уже существует (ID: {existing_id})")
                return existing_id
        
        label = entity_type
        node_id = self.graph.create_node([label], properties)
        
        cache_key = self._generate_cache_key(entity_type, properties)
        self.cache['nodes'][cache_key] = node_id
        
        entity_name = properties.get('name', properties.get('title', 'без имени'))
        print(f"Создан новый {entity_type}: '{entity_name}' (ID: {node_id})")
        
        return node_id
    
    def add_relationship(
        self,
        from_node: Union[int, str],
        to_node: Union[int, str],
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        if properties is None:
            properties = {}
        
        if rel_type not in self.valid_relationships:
            raise ValueError(f"Неизвестный тип связи: {rel_type}. "
                           f"Доступные типы: {', '.join(self.valid_relationships)}")
        
        if isinstance(from_node, str):
            from_node = self._find_node_by_name(from_node)
            if from_node is None:
                raise ValueError(f"Узел с именем '{from_node}' не найден")
        
        if isinstance(to_node, str):
            to_node = self._find_node_by_name(to_node)
            if to_node is None:
                raise ValueError(f"Узел с именем '{to_node}' не найден")
        
        existing_id = self._find_existing_relationship(from_node, to_node, rel_type, properties)
        if existing_id is not None:
            print(f"Связь '{rel_type}' уже существует (ID: {existing_id})")
            return existing_id
        
        rel_id = self.graph.create_relationship(from_node, to_node, rel_type, properties)
        
        cache_key = f"{from_node}|{to_node}|{rel_type}"
        self.cache['relationships'][cache_key] = rel_id
        
        print(f"Создана новая связь '{rel_type}' (ID: {rel_id})")
        return rel_id
    
    def add_entity_with_relationship(
        self,
        from_entity_type: str,
        from_properties: Dict[str, Any],
        to_entity_type: str,
        to_properties: Dict[str, Any],
        rel_type: str,
        rel_properties: Optional[Dict[str, Any]] = None
    ) -> tuple:
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
        from_id = self._find_node_by_name(from_name)
        if from_id is None:
            raise ValueError(f"Узел с именем '{from_name}' не найден")
        
        to_id = self._find_node_by_name(to_name)
        if to_id is None:
            raise ValueError(f"Узел с именем '{to_name}' не найден")
        
        return self.add_relationship(from_id, to_id, rel_type, rel_properties)
    
    def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if params is None:
            params = {}
        result = self.graph.execute(cypher_query, params)
        return result.to_list() if result else []
    
    def find_by_properties(self, entity_type: str, properties: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        dir_symbol = '-' if direction == 'outgoing' else '<-'
        rel_filter = f":{rel_type}" if rel_type else ""
        
        query = f"""
        MATCH (n){dir_symbol}[r{rel_filter}]->(connected)
        WHERE id(n) = {node_id}
        RETURN connected, type(r) as relationship_type, r as relationship_properties
        """
        
        return self.query(query)
    
    def get_node_info(self, node_id: int) -> Dict[str, Any]:
        query = f"MATCH (n) WHERE id(n) = {node_id} RETURN n"
        result = self.query(query)
        if result:
            return result[0].get('n', {})
        return {}
    
    def print_graph_summary(self):
        print("\n" + "="*60)
        print("СВОДКА ПО ГРАФУ ЗНАНИЙ")
        print("="*60)
        print(f"Всего узлов: {self.graph.node_count()}")
        print(f"Всего связей: {self.graph.edge_count()}")
        print(f"Размер кэша узлов: {len(self.cache['nodes'])}")
        print(f"Размер кэша связей: {len(self.cache['relationships'])}")
        
        print("\nСтатистика по типам сущностей:")
        for entity_type in self.entity_labels.keys():
            query = f"MATCH (n:{entity_type}) RETURN count(n) as count"
            result = self.query(query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"   {entity_type}: {count}")
        
        print("\nСтатистика по типам связей:")
        for rel_type in self.valid_relationships:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = self.query(query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"   {rel_type}: {count}")
        
        print("="*60)
    
    def export_to_json(self, filepath: str):
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
        
        print(f"Граф экспортирован в {filepath}")

    def find_nodes_by_properties(
        self,
        entity_type: Optional[str] = None,
        properties: Dict[str, Any] = None,
        return_type: str = 'full'
    ) -> List[Dict[str, Any]]:
        if properties is None:
            properties = {}
        
        query = "MATCH (n"
        if entity_type:
            query += f":{entity_type}"
        query += ") WHERE "
        
        conditions = []
        for key, value in properties.items():
            if isinstance(value, str):
                conditions.append(f"toLower(n.{key}) CONTAINS toLower('{value}')")
            elif isinstance(value, (int, float)):
                conditions.append(f"n.{key} = {value}")
            elif isinstance(value, bool):
                conditions.append(f"n.{key} = {value}")
            elif isinstance(value, list):
                if value:
                    list_value = value[0]
                    if isinstance(list_value, str):
                        conditions.append(f"ANY(item IN n.{key} WHERE toLower(item) CONTAINS toLower('{list_value}'))")
                    else:
                        conditions.append(f"ANY(item IN n.{key} WHERE item = {list_value})")
            else:
                conditions.append(f"n.{key} = {value}")
        
        if not conditions:
            query = "MATCH (n"
            if entity_type:
                query += f":{entity_type}"
            query += ") RETURN n, labels(n) as labels, id(n) as id"
        else:
            query += " AND ".join(conditions)
            query += " RETURN n, labels(n) as labels, id(n) as id"
        
        results = self.query(query)
        
        if return_type == 'ids':
            return [row['id'] for row in results]
        elif return_type == 'names':
            return [row['n'].get('name', row['n'].get('title', 'Без имени')) for row in results]
        else:
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
        
        node_info = self.get_node_info(node_id)
        result['node'] = node_info
        
        rel_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"
        
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
        
        if depth > 1:
            for direction in ['incoming', 'outgoing']:
                for connected_node in result['connected_nodes'][direction]:
                    if connected_node['id'] != node_id:
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
        if isinstance(node_identifier, int):
            node_info = self.get_node_info(node_identifier)
            if node_info:
                return node_identifier
            return None
        
        if isinstance(node_identifier, str):
            if entity_type:
                query = f"""
                MATCH (n:{entity_type})
                WHERE toLower(n.name) = toLower('{node_identifier}') 
                   OR toLower(n.title) = toLower('{node_identifier}')
                RETURN id(n) LIMIT 1
                """
            else:
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
        
        if isinstance(node_identifier, dict):
            results = self.find_nodes_by_properties(entity_type, node_identifier, return_type='ids')
            if results:
                return results[0]
            return None
        
        return None
    
    def delete_relationship_by_id(self, relationship_id: int) -> bool:
        try:
            query = f"MATCH ()-[r]->() WHERE id(r) = {relationship_id} RETURN id(r)"
            result = self.query(query)
            if not result:
                print(f"Связь с ID {relationship_id} не найдена")
                return False
            
            query = f"MATCH ()-[r]->() WHERE id(r) = {relationship_id} DELETE r"
            self.graph.execute(query)
            
            for key in list(self.cache['relationships'].keys()):
                if self.cache['relationships'][key] == relationship_id:
                    del self.cache['relationships'][key]
                    break
            
            print(f"Связь с ID {relationship_id} удалена")
            return True
            
        except Exception as e:
            print(f"Ошибка при удалении связи: {e}")
            return False
    
    def delete_relationships_by_type(
        self,
        from_node: Optional[int] = None,
        to_node: Optional[int] = None,
        rel_type: Optional[str] = None
    ) -> int:
        try:
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
            
            count_query = query + " RETURN count(r) as count"
            count_result = self.query(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            if count == 0:
                print("Связей для удаления не найдено")
                return 0
            
            delete_query = query + " DELETE r"
            self.graph.execute(delete_query)
            
            self.cache['relationships'] = {}
            
            print(f"Удалено {count} связей")
            return count
            
        except Exception as e:
            print(f"Ошибка при удалении связей: {e}")
            return 0
    
    def delete_node_by_id(
        self,
        node_id: int,
        cascade: bool = True
    ) -> bool:
        try:
            node_info = self.get_node_info(node_id)
            if not node_info:
                print(f"Узел с ID {node_id} не найден")
                return False
            
            query = f"""
            MATCH (n)-[r]-()
            WHERE id(n) = {node_id}
            RETURN count(r) as count
            """
            result = self.query(query)
            rel_count = result[0]['count'] if result else 0
            
            if rel_count > 0 and not cascade:
                print(f"Узел имеет {rel_count} связей. Используйте cascade=True для удаления всех связей")
                return False
            
            if rel_count > 0 and cascade:
                delete_rels_query = f"""
                MATCH (n)-[r]-()
                WHERE id(n) = {node_id}
                DELETE r
                """
                self.graph.execute(delete_rels_query)
                print(f"   Удалено {rel_count} связей")
            
            delete_node_query = f"MATCH (n) WHERE id(n) = {node_id} DELETE n"
            self.graph.execute(delete_node_query)
            
            for key in list(self.cache['nodes'].keys()):
                if self.cache['nodes'][key] == node_id:
                    del self.cache['nodes'][key]
            
            self.cache['relationships'] = {}
            
            node_name = node_info.get('name', node_info.get('title', 'без имени'))
            print(f"Узел '{node_name}' (ID: {node_id}) удален")
            return True
            
        except Exception as e:
            print(f"Ошибка при удалении узла: {e}")
            return False
    
    def delete_node_by_properties(
        self,
        entity_type: Optional[str] = None,
        properties: Dict[str, Any] = None,
        cascade: bool = True,
        delete_all_matching: bool = False
    ) -> int:
        if properties is None:
            properties = {}
        
        nodes = self.find_nodes_by_properties(entity_type, properties, return_type='ids')
        
        if not nodes:
            print("Узлов для удаления не найдено")
            return 0
        
        if not delete_all_matching:
            nodes = [nodes[0]]
        
        deleted_count = 0
        for node_id in nodes:
            if self.delete_node_by_id(node_id, cascade):
                deleted_count += 1
        
        print(f"Удалено {deleted_count} узлов")
        return deleted_count
    
    def delete_node_by_name(
        self,
        name: str,
        entity_type: Optional[str] = None,
        cascade: bool = True
    ) -> bool:
        node_id = self._resolve_node_id(name, entity_type)
        if node_id is None:
            print(f"Узел с именем '{name}' не найден")
            return False
        
        return self.delete_node_by_id(node_id, cascade)
    
    def delete_all_nodes(self, cascade: bool = True) -> int:
        try:
            count_query = "MATCH (n) RETURN count(n) as count"
            count_result = self.query(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            if count == 0:
                print("Граф уже пуст")
                return 0
            
            if cascade:
                self.graph.execute("MATCH (n) DETACH DELETE n")
            else:
                self.graph.execute("MATCH (n) WHERE NOT (n)--() DELETE n")
            
            self.cache = {'nodes': {}, 'relationships': {}}
            
            print(f"Удалено {count} узлов")
            return count
            
        except Exception as e:
            print(f"Ошибка при удалении всех узлов: {e}")
            return 0
    
    def find_orphan_nodes(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN n, labels(n) as labels, id(n) as id
        """
        return self.query(query)
    
    def get_node_degree(self, node_id: int) -> Dict[str, int]:
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
    
    def load_from_json(
        self,
        filepath: str,
        clear_existing: bool = True,
        skip_duplicates: bool = True,
        verbose: bool = True
    ) -> Dict[str, int]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл {filepath} не найден")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print("="*60)
            print("ЗАГРУЗКА ГРАФА ИЗ JSON")
            print("="*60)
            print(f"Файл: {filepath}")
            print(f"Дата экспорта: {data.get('export_date', 'не указана')}")
            print(f"Узлов в файле: {len(data.get('nodes', []))}")
            print(f"Связей в файле: {len(data.get('relationships', []))}")
            print("-"*60)
        
        if clear_existing:
            if verbose:
                print("Очистка существующего графа...")
            self.delete_all_nodes(cascade=True)
            self.cache = {'nodes': {}, 'relationships': {}}
        
        stats = {
            'nodes_loaded': 0,
            'relationships_loaded': 0,
            'nodes_skipped': 0,
            'relationships_skipped': 0
        }
        
        id_mapping = {}
        
        if verbose:
            print("\nЗагрузка узлов...")
        
        for node_data in data.get('nodes', []):
            try:
                old_id = node_data.get('id')
                labels = node_data.get('labels', [])
                properties = node_data.get('properties', {})
                
                if not labels:
                    if verbose:
                        print(f" Пропущен узел без меток (ID: {old_id})")
                    stats['nodes_skipped'] += 1
                    continue
                
                entity_type = labels[0]
                
                if skip_duplicates:
                    existing_id = self._find_existing_node(entity_type, properties)
                    if existing_id is not None:
                        id_mapping[old_id] = existing_id
                        stats['nodes_skipped'] += 1
                        if verbose:
                            name = properties.get('name', properties.get('title', 'без имени'))
                            print(f"  Пропущен дубликат: {entity_type} '{name}' (ID: {old_id} -> {existing_id})")
                        continue
                
                new_id = self.graph.create_node(labels, properties)
                
                id_mapping[old_id] = new_id
                stats['nodes_loaded'] += 1
                
                if verbose and stats['nodes_loaded'] % 10 == 0:
                    print(f"  Загружено {stats['nodes_loaded']} узлов...")
                    
            except Exception as e:
                if verbose:
                    print(f"  Ошибка при загрузке узла (ID: {old_id}): {e}")
                stats['nodes_skipped'] += 1
        
        if verbose:
            print(f"  Загружено узлов: {stats['nodes_loaded']}")
            print(f"  Пропущено узлов: {stats['nodes_skipped']}")
        
        if verbose:
            print("\nЗагрузка связей...")
        
        for rel_data in data.get('relationships', []):
            try:
                old_id = rel_data.get('id')
                rel_type = rel_data.get('type')
                from_old = rel_data.get('from')
                to_old = rel_data.get('to')
                properties = rel_data.get('properties', {})
                
                if not rel_type:
                    if verbose:
                        print(f"  Пропущена связь без типа (ID: {old_id})")
                    stats['relationships_skipped'] += 1
                    continue
                
                if from_old not in id_mapping or to_old not in id_mapping:
                    if verbose:
                        print(f"  Пропущена связь с неизвестными узлами (ID: {old_id})")
                    stats['relationships_skipped'] += 1
                    continue
                
                from_new = id_mapping[from_old]
                to_new = id_mapping[to_old]
                
                if skip_duplicates:
                    existing_id = self._find_existing_relationship(from_new, to_new, rel_type, properties)
                    if existing_id is not None:
                        stats['relationships_skipped'] += 1
                        if verbose:
                            print(f"  Пропущен дубликат связи: {rel_type} (ID: {old_id} -> {existing_id})")
                        continue
                
                self.graph.create_relationship(from_new, to_new, rel_type, properties)
                stats['relationships_loaded'] += 1
                
                if verbose and stats['relationships_loaded'] % 10 == 0:
                    print(f"  Загружено {stats['relationships_loaded']} связей...")
                    
            except Exception as e:
                if verbose:
                    print(f"  Ошибка при загрузке связи (ID: {old_id}): {e}")
                stats['relationships_skipped'] += 1
        
        if verbose:
            print(f"  Загружено связей: {stats['relationships_loaded']}")
            print(f"  Пропущено связей: {stats['relationships_skipped']}")
        
        if verbose:
            print("\n" + "="*60)
            print("ИТОГИ ЗАГРУЗКИ")
            print("="*60)
            print(f"Загружено узлов: {stats['nodes_loaded']}")
            print(f"Загружено связей: {stats['relationships_loaded']}")
            print(f"Пропущено узлов: {stats['nodes_skipped']}")
            print(f"Пропущено связей: {stats['relationships_skipped']}")
            print(f"Всего узлов в графе: {self.graph.node_count()}")
            print(f"Всего связей в графе: {self.graph.edge_count()}")
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
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл {filepath} не найден")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print("="*60)
            print("ЗАГРУЗКА ГРАФА ИЗ JSON (ПОРЦИЯМИ)")
            print("="*60)
            print(f"Файл: {filepath}")
            print(f"Дата экспорта: {data.get('export_date', 'не указана')}")
            print(f"Узлов в файле: {len(data.get('nodes', []))}")
            print(f"Связей в файле: {len(data.get('relationships', []))}")
            print(f"Размер порции: {batch_size}")
            print("-"*60)
        
        if clear_existing:
            if verbose:
                print("Очистка существующего графа...")
            self.delete_all_nodes(cascade=True)
            self.cache = {'nodes': {}, 'relationships': {}}
        
        stats = {
            'nodes_loaded': 0,
            'relationships_loaded': 0,
            'nodes_skipped': 0,
            'relationships_skipped': 0
        }
        
        id_mapping = {}
        
        if verbose:
            print("\nЗагрузка узлов порциями...")
        
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
                print(f"  Загружено {min(i+batch_size, total_nodes)} из {total_nodes} узлов...")
        
        if verbose:
            print(f"  Загружено узлов: {stats['nodes_loaded']}")
            print(f"  Пропущено узлов: {stats['nodes_skipped']}")
        
        if verbose:
            print("\nЗагрузка связей порциями...")
        
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
                print(f"  Загружено {min(i+batch_size, total_rels)} из {total_rels} связей...")
        
        if verbose:
            print(f"  Загружено связей: {stats['relationships_loaded']}")
            print(f"  Пропущено связей: {stats['relationships_skipped']}")
        
        if verbose:
            print("\n" + "="*60)
            print("ИТОГИ ЗАГРУЗКИ")
            print("="*60)
            print(f"Загружено узлов: {stats['nodes_loaded']}")
            print(f"Загружено связей: {stats['relationships_loaded']}")
            print(f"Пропущено узлов: {stats['nodes_skipped']}")
            print(f"Пропущено связей: {stats['relationships_skipped']}")
            print(f"Всего узлов в графе: {self.graph.node_count()}")
            print(f"Всего связей в графе: {self.graph.edge_count()}")
            print("="*60)
        
        return stats

    def validate_json_schema(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            required_fields = ['nodes', 'relationships']
            for field in required_fields:
                if field not in data:
                    print(f"Отсутствует обязательное поле: {field}")
                    return False
            
            for node in data.get('nodes', []):
                if 'id' not in node or 'labels' not in node or 'properties' not in node:
                    print(f"Неверная структура узла: {node}")
                    return False
            
            for rel in data.get('relationships', []):
                required_rel_fields = ['id', 'type', 'from', 'to']
                for field in required_rel_fields:
                    if field not in rel:
                        print(f"Неверная структура связи: {rel}")
                        return False
            
            print("JSON-файл соответствует схеме")
            return True
            
        except Exception as e:
            print(f"Ошибка при проверке схемы: {e}")
            return False

    def get_import_preview(self, filepath: str, limit: int = 5) -> Dict[str, Any]:
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
        
        for node in data.get('nodes', []):
            for label in node.get('labels', []):
                preview['node_types'][label] = preview['node_types'].get(label, 0) + 1
        
        for rel in data.get('relationships', []):
            rel_type = rel.get('type')
            preview['relationship_types'][rel_type] = preview['relationship_types'].get(rel_type, 0) + 1
        
        return preview