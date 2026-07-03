# ScientificTangle

По поводу папки prob:
для запуска: 
нужна версия питона 3.11 (14 не работает почему-то), приложение Docker Desktop

pip install -r requirements.txt
pip install spacy

py -m spacy download ru_core_news_sm 
или 
pip install https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl

docker-compose up -d

Проверка работы: 
curl http://localhost:7474 (neo4j, password123)

Что там открываться то должно:
http://localhost:7474/
http://localhost:9200/
http://localhost:8000/ (что-то с api, но не работает)