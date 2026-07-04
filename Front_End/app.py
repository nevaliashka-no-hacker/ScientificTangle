import streamlit as st
import json
import time
from typing import Dict, Any, List, Optional

# Импорт вашей готовой логики поиска
# Убедитесь, что путь соответствует структуре вашего проекта
try:
    from search.searcher import Searcher
    from Graph_Data_Base.graph_client import GraphClient
    from Data_Typization_Realization.data_processor import DataProcessor
except ImportError as e:
    st.error(f"Ошибка импорта модулей проекта: {e}")
    st.info("Убедитесь, что структура папок сохранена: search/, Graph_Data_Base/, Data_Typization_Realization/")
    st.stop()

class ScientificTangleFrontend:
    def __init__(self):
        self.initialize_session_state()
        self.setup_page_config()
        self.load_engine()
        
    def setup_page_config(self):
        st.set_page_config(
            page_title="ScientificTangle - Knowledge Graph",
            page_icon="",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def initialize_session_state(self):
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "search_history" not in st.session_state:
            st.session_state.search_history = []
        if "current_result" not in st.session_state:
            st.session_state.current_result = None
        if "graph_ready" not in st.session_state:
            st.session_state.graph_ready = False
            
    @st.cache_resource
    def load_engine():
        try:
            searcher = Searcher()
            graph_client = GraphClient()
            processor = DataProcessor()
            return {
                "searcher": searcher,
                "graph": graph_client,
                "processor": processor
            }
        except Exception as e:
            st.error(f"Не удалось загрузить движок: {e}")
            return None
            
    def perform_search(self, query: str) -> Dict[str, Any]:
        engine = self.load_engine()
        if engine is None:
            return {"error": "Движок не загружен"}
            
        try:
            start_time = time.time()
            
            result = engine["searcher"].search(query)
            
            if engine["graph"]:
                graph_data = engine["graph"].get_related_nodes(query)
                result["graph_data"] = graph_data
                
            result["execution_time"] = time.time() - start_time
            return result
            
        except Exception as e:
            return {"error": str(e)}
            
    def render_sidebar(self):
        with st.sidebar:
            st.title("ScientificTangle")
            st.markdown("---")
            
            st.subheader("Настройки")
            max_results = st.slider("Максимум результатов", 5, 50, 20)
            depth = st.slider("Глубина поиска", 1, 5, 3)
            
            st.markdown("---")
            st.subheader("История запросов")
            for i, q in enumerate(st.session_state.search_history[-10:]):
                if st.button(f"{i+1}. {q[:30]}...", key=f"history_{i}"):
                    st.session_state.current_query = q
                    st.rerun()
                    
            st.markdown("---")
            st.caption("ScientificTangle v1.0")
            st.caption("Knowledge Graph System")
            
            return {"max_results": max_results, "depth": depth}
            
    def render_query_input(self):
        col1, col2, col3 = st.columns([5, 1, 1])
        with col1:
            query = st.text_input(
                "Введите ваш запрос",
                placeholder="Например: какие документы связаны с квантовой физикой?",
                key="query_input",
                label_visibility="collapsed"
            )
        with col2:
            search_clicked = st.button("Найти", type="primary", use_container_width=True)
        with col3:
            clear_clicked = st.button("Очистить", use_container_width=True)
            
        if clear_clicked:
            st.session_state.messages = []
            st.session_state.current_result = None
            st.rerun()
            
        return query, search_clicked
        
    def render_results(self, result: Dict[str, Any]):
        if "error" in result:
            st.error(f"Ошибка: {result['error']}")
            return
            
        col_results, col_graph = st.columns([3, 2])
        
        with col_results:
            st.subheader("Результаты поиска")
            
            if "execution_time" in result:
                st.caption(f"Время выполнения: {result['execution_time']:.3f} сек.")
                
            if "answer" in result:
                st.markdown("### Ответ")
                st.write(result["answer"])
                
            if "documents" in result:
                st.markdown("### Найденные документы")
                for doc in result["documents"][:10]:
                    with st.expander(doc.get("title", "Документ")):
                        st.write(doc.get("content", "Нет содержимого")[:300] + "...")
                        st.caption(f"Релевантность: {doc.get('score', 0):.2f}")
                        
            if "entities" in result:
                st.markdown("### Сущности")
                entities = result["entities"]
                cols = st.columns(3)
                for i, entity in enumerate(entities):
                    with cols[i % 3]:
                        st.info(entity)
                        
        with col_graph:
            st.subheader("Визуализация графа")
            
            if "graph_data" in result and result["graph_data"]:
                graph_data = result["graph_data"]
                
                # Генерация DOT-представления для Graphviz
                dot = self.generate_graphviz_dot(graph_data)
                if dot:
                    st.graphviz_chart(dot, use_container_width=True)
                    
                # Альтернативный вариант с PyVis в HTML
                if self.is_pyvis_available():
                    html = self.generate_pyvis_html(graph_data)
                    if html:
                        st.components.v1.html(html, height=500, scrolling=True)
            else:
                st.info("Нет данных для визуализации графа")
                
    def generate_graphviz_dot(self, graph_data: Dict) -> Optional[str]:
        try:
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])
            
            if not nodes:
                return None
                
            dot = "graph KnowledgeGraph {\n"
            dot += "  node [shape=box, style=filled, fillcolor=lightblue];\n"
            
            for node in nodes:
                node_id = node.get("id", str(id(node)))
                label = node.get("label", node_id)
                dot += f'  "{node_id}" [label="{label}"];\n'
                
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                label = edge.get("label", "")
                if source and target:
                    dot += f'  "{source}" -- "{target}" [label="{label}"];\n'
                    
            dot += "}"
            return dot
        except Exception:
            return None
            
    def is_pyvis_available(self) -> bool:
        try:
            import pyvis
            return True
        except ImportError:
            return False
            
    def generate_pyvis_html(self, graph_data: Dict) -> Optional[str]:
        try:
            from pyvis.network import Network
            
            net = Network(height="500px", width="100%", directed=True)
            net.set_options("""
            var options = {
              "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100}
              }
            }
            """)
            
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])
            
            for node in nodes:
                node_id = node.get("id", str(id(node)))
                label = node.get("label", node_id)
                group = node.get("group", "default")
                net.add_node(node_id, label=label, group=group)
                
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                label = edge.get("label", "")
                if source and target:
                    net.add_edge(source, target, title=label)
                    
            return net.generate_html()
        except Exception:
            return None
            
    def render_chat_interface(self):
        st.subheader("Диалоговый интерфейс")
        
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages[-20:]:
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    st.chat_message("assistant").write(msg["content"])
                    
    def run(self):
        settings = self.render_sidebar()
        
        st.title("ScientificTangle")
        st.markdown("Система поиска по графу знаний")
        st.markdown("---")
        
        query, search_clicked = self.render_query_input()

        if search_clicked and query:
            st.session_state.search_history.append(query)
            st.session_state.messages.append({"role": "user", "content": query})
            
            with st.spinner("Обработка запроса..."):
                result = self.perform_search(query)
                st.session_state.current_result = result
                
                if "error" not in result:
                    answer = result.get("answer", "Результат получен")
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"Ошибка: {result['error']}"})
                    
            st.rerun()
            
        if st.session_state.current_result:
            self.render_results(st.session_state.current_result)
            
        self.render_chat_interface()
        
        st.markdown("---")
        st.caption("ScientificTangle Knowledge Graph System")
        st.caption("Используйте запросы для поиска по связанным данным")


def main():
    frontend = ScientificTangleFrontend()
    frontend.run()


if __name__ == "__main__":
    main()