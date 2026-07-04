import streamlit as st
import json
import subprocess
import sys
from pathlib import Path
from components import UIComponents
from config import config

# ==========================================
# НАСТРОЙКИ ПУТЕЙ
# ==========================================

OUTPUT_JSON_PATH = Path(__file__).parent / "result.json"
BACKEND_SCRIPT_PATH = Path(__file__).parent / "main.py"


def main():
    st.set_page_config(page_title="ScientificTangle", layout="wide", page_icon="🧬")
    
    # Скрываем стандартные меню Streamlit
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    st.title("🧬 ScientificTangle: Поиск и анализ")
    st.markdown("Система поиска научных материалов, связанных сущностей и построения графов.")

    # ---------------------------------------------------------
    # БЛОК 1: ВВОД ДАННЫХ
    # ---------------------------------------------------------
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_query = st.text_input(
                "Введите поисковый запрос:", 
                placeholder="",
                label_visibility="collapsed"
            )
            
        with col2:
            user_data_path = st.text_input(
                "Путь к данным:", 
                value=str(config.DATA_DIR),
                label_visibility="collapsed"
            )

        search_btn = st.button("🔍 Выполнить анализ", type="primary", use_container_width=True)

    # ---------------------------------------------------------
    # БЛОК 2: ЗАПУСК БЭКЕНДА И ЧТЕНИЕ ФАЙЛА
    # ---------------------------------------------------------
    if search_btn:
        if not user_query.strip():
            st.warning("Пожалуйста, введите поисковый запрос.")
        else:
            with UIComponents.render_loading_animation():
                try:
                    # 1. Формируем команду для запуска вашего скрипта бэкенда
                    # Передаем ему запрос и путь как аргументы командной строки
                    cmd = [
                        sys.executable, 
                        str(BACKEND_SCRIPT_PATH), 
                        "--query", user_query
                    ]
                    
                    # 2. Запускаем бэкенд и ждем его завершения
                    # check=True вызовет ошибку, если бэкенд упадет (код возврата != 0)
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                    
                    # 3. Читаем сгенерированный JSON файл
                    if not OUTPUT_JSON_PATH.exists():
                        st.error(f"Бэкенд отработал, но файл {OUTPUT_JSON_PATH} не был создан.")
                        st.stop()
                        
                    with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                        result_json = json.load(f)

                except subprocess.CalledProcessError as e:
                    st.error(f"Ошибка при выполнении бэкенда! Код ошибки: {e.returncode}")
                    st.text_area("Логи ошибки (stderr):", value=e.stderr, height=200)
                    st.stop()
                except json.JSONDecodeError:
                    st.error(f"Файл {OUTPUT_JSON_PATH} существует, но это не валидный JSON.")
                    st.stop()
                except Exception as e:
                    st.error(f"Непредвиденная ошибка: {e}")
                    st.stop()

            # ---------------------------------------------------------
            # БЛОК 3: ОТРИСОВКА UI ИЗ ПРОЧИТАННОГО JSON
            # ---------------------------------------------------------
            st.success("Анализ успешно завершен!")

            tab_raw, tab_material, tab_graph = st.tabs(["📄 Исходный JSON", "📚 Найденный материал", "🌐 Граф и связи"])

            with tab_raw:
                st.subheader("Содержимое JSON файла")
                st.json(result_json)

            with tab_material:
                st.subheader("Основной материал")
                material_data = result_json.get("material", {})
                if material_data:
                    UIComponents.render_document_card(material_data)
                else:
                    st.info("Ключ 'material' отсутствует в JSON файле.")

            with tab_graph:
                graph_data = result_json.get("graph", {})
                related_data = result_json.get("related", [])
                
                col_g1, col_g2 = st.columns([1, 2])
                
                with col_g1:
                    st.subheader("Метрики графа")
                    if graph_data:
                        UIComponents.render_graph_info(
                            nodes_count=graph_data.get("nodes_count", 0), 
                            edges_count=graph_data.get("edges_count", 0)
                        )
                
                with col_g2:
                    st.subheader("Связанные сущности")
                    if related_data:
                        UIComponents.render_entity_list(related_data, columns=3)
                    else:
                        st.info("Ключ 'related' отсутствует или пуст.")

                # Если в JSON есть готовый HTML-код графа (например, сгенерированный PyVis)
                if graph_data and graph_data.get("html_graph"):
                    st.subheader("Визуализация графа")
                    st.components.v1.html(graph_data["html_graph"], height=600)

if __name__ == "__main__":
    main()