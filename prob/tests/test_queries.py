"""Тестовые запросы из задания"""

import pytest
from src.query_builder import QueryBuilder
from src.nlp_extractor import ScientificNLP
from src.config import Config

@pytest.fixture
def nlp():
    config = Config()
    return ScientificNLP(config)

@pytest.fixture
def builder(nlp):
    return QueryBuilder(nlp)

def test_desalination_query(builder):
    """Тест запроса про обессоливание"""
    query = ("Какие методы обессоливания воды подходят для обогатительной фабрики, "
             "если исходная вода содержит сульфаты, хлориды, Ca, Mg, Na по 200–300 мг/л, "
             "а требуемый сухой остаток — ≤1000 мг/дм³?")
    
    result = builder.build_cypher_query(query)
    
    assert result['cypher'] is not None
    assert 'Materials' in result['cypher'] or 'Process' in result['cypher']
    print(f"Generated Cypher:\n{result['cypher']}")

def test_electrowinning_query(builder):
    """Тест запроса про циркуляцию католита"""
    query = ("Какие технические решения организации циркуляции католита "
             "при электроэкстракции никеля описаны в мировой практике, "
             "и какая скорость потока считается оптимальной?")
    
    result = builder.build_cypher_query(query)
    assert result['intent'] == 'FIND_METHOD'  # после обработки
    print(f"Generated Cypher:\n{result['cypher']}")

def test_distribution_query(builder):
    """Тест запроса про распределение драгметаллов"""
    query = ("Покажите все эксперименты и публикации по распределению "
             "Au, Ag и МПГ между медным/никелевым штейном и шлаком за последние 5 лет")
    
    result = builder.build_cypher_query(query)
    assert 'year' in result['cypher'].lower() or 'year' in str(result['params'])
    print(f"Generated Cypher:\n{result['cypher']}")

def test_mine_water_query(builder):
    """Тест запроса про закачку шахтных вод"""
    query = ("Какие способы закачки шахтных вод в глубокие горизонты "
             "применялись в России и за рубежом, и каковы их технико-экономические показатели?")
    
    result = builder.build_cypher_query(query)
    assert 'geography' in result['cypher'].lower() or 'geography' in str(result['params'])
    print(f"Generated Cypher:\n{result['cypher']}")