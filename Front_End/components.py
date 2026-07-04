import streamlit as st
from typing import Dict, Any, List, Optional
import pandas as pd


class UIComponents:
    @staticmethod
    def render_metrics_card(title: str, value: Any, icon: str = ""):
        st.markdown(f"""
        <div style="
            background: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 5px 0;
        ">
            <h3>{icon} {title}</h3>
            <h2>{value}</h2>
        </div>
        """, unsafe_allow_html=True)
        
    @staticmethod
    def render_entity_list(entities: List[str], columns: int = 4):
        if not entities:
            return
            
        cols = st.columns(columns)
        for i, entity in enumerate(entities):
            with cols[i % columns]:
                st.markdown(f"""
                <div style="
                    background: #e8f0fe;
                    padding: 8px;
                    border-radius: 20px;
                    margin: 4px 0;
                    text-align: center;
                    font-size: 14px;
                ">
                    {entity}
                </div>
                """, unsafe_allow_html=True)
                
    @staticmethod
    def render_document_card(doc: Dict[str, Any]):
        title = doc.get("title", "Без названия")
        content = doc.get("content", "")[:500]
        score = doc.get("score", 0)
        
        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 8px 0;
            background: white;
        ">
            <h4>{title}</h4>
            <p style="color: #555; font-size: 14px;">{content}...</p>
            <span style="
                background: #4CAF50;
                color: white;
                padding: 2px 10px;
                border-radius: 12px;
                font-size: 12px;
            ">Score: {score:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
        
    @staticmethod
    def render_graph_info(nodes_count: int, edges_count: int):
        col1, col2 = st.columns(2)
        with col1:
            UIComponents.render_metrics_card("Узлов", nodes_count, "")
        with col2:
            UIComponents.render_metrics_card("Связей", edges_count, "")
            
    @staticmethod
    def render_loading_animation():
        return st.spinner("Обработка запроса...")