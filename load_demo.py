"""Загрузка демо-данных в граф"""
from Graph_Data_Base.Graph_Data_Base import ScientificTangleKnowledgeGraph

kg = ScientificTangleKnowledgeGraph()

# Материалы
ni = kg.add_entity("Material", {"name": "Никель", "formula": "Ni"})
cu = kg.add_entity("Material", {"name": "Медь", "formula": "Cu"})
sulfates = kg.add_entity("Material", {"name": "Сульфаты", "formula": "SO4"})
catholyte = kg.add_entity("Material", {"name": "Католит", "type": "electrolyte"})

# Процессы
ew = kg.add_entity("Process", {"name": "Электроэкстракция", "efficiency": "95%"})
desalination = kg.add_entity("Process", {"name": "Обессоливание", "method": "обратный осмос"})

# Оборудование
cell = kg.add_entity("Equipment", {"name": "Электролизёр", "material": "титан"})

# Параметры
temp = kg.add_entity("Property", {"name": "Температура", "value": 60, "unit": "°C"})
flow = kg.add_entity("Property", {"name": "Скорость потока", "value": 0.08, "unit": "м/с"})

# Эксперты
ivanov = kg.add_entity("Expert", {"name": "Иванов И.И.", "lab": "Лаб. электрохимии"})
petrov = kg.add_entity("Expert", {"name": "Петров П.П.", "lab": "Лаб. гидрометаллургии"})

# Публикации
pub1 = kg.add_entity("Publication", {"title": "Электроэкстракция никеля", "year": 2024})
pub2 = kg.add_entity("Publication", {"title": "Обессоливание шахтных вод", "year": 2023})

# ===== СВЯЗИ =====
kg.add_relationship(ew, ni, "uses_material")
kg.add_relationship(ew, catholyte, "uses_material")
kg.add_relationship(ew, cell, "uses_material")
kg.add_relationship(ew, temp, "operates_at_condition")
kg.add_relationship(ew, flow, "operates_at_condition")
kg.add_relationship(desalination, sulfates, "uses_material")
kg.add_relationship(ivanov, pub1, "described_in")
kg.add_relationship(pub1, ew, "described_in")
kg.add_relationship(ivanov, ew, "described_in")
kg.add_relationship(petrov, desalination, "described_in")

kg.print_graph_summary()
print("✅ Демо-данные загружены!")