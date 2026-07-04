import streamlit as st
from typing import Dict, Any, List
import html

class UIComponents:
    @staticmethod
    def render_metrics_card(title: str, value: Any, icon: str = ""):
        safe_title = html.escape(str(title))
        safe_value = html.escape(str(value))
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin: 5px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        ">
            <h3 style="margin:0; color:#555;">{icon} {safe_title}</h3>
            <h2 style="margin:10px 0 0 0; color:#1f77b4;">{safe_value}</h2>
        </div>
        """, unsafe_allow_html=True)
        
    @staticmethod
    def render_entity_list(entities: List[str], columns: int = 3):
        if not entities:
            st.info("Связанные сущности не найдены.")
            return
            
        cols = st.columns(columns)
        for i, entity in enumerate(entities):
            safe_entity = html.escape(entity)
            with cols[i % columns]:
                st.markdown(f"""
                <div style="
                    background: #e1f5fe;
                    padding: 10px;
                    border-radius: 20px;
                    margin: 5px 0;
                    text-align: center;
                    font-size: 14px;
                    color: #0277bd;
                    border: 1px solid #b3e5fc;
                ">
                    {safe_entity}
                </div>
                """, unsafe_allow_html=True)
                
    @staticmethod
    def render_document_card(doc: Dict[str, Any]):
        title = html.escape(doc.get("title", "Без названия"))
        content = html.escape(doc.get("content", "")[:1000]) # Увеличил лимит символов
        score = doc.get("score", 0)
        
        st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        ">
            <h4 style="margin-top:0; color:#333;">{title}</h4>
            <p style="color: #666; font-size: 15px; line-height: 1.6;">{content}...</p>
            <span style="
                background: #4caf50;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 13px;
                font-weight: bold;
            ">Relevance Score: {score:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
        
    @staticmethod
    def render_graph_info(nodes_count: int, edges_count: int):
        col1, col2 = st.columns(2)
        with col1:
            UIComponents.render_metrics_card("Узлов (Nodes)", nodes_count, "🔵")
        with col2:
            UIComponents.render_metrics_card("Связей (Edges)", edges_count, "🔗")
            
    @staticmethod
    def render_loading_animation():
        return st.spinner("🚀 Обработка запроса, поиск в базе и построение графа...")