@echo off
echo ========================================
echo ЗАПУСК СЕМАНТИЧЕСКОГО ПОИСКА
echo ========================================

echo.
echo 1. Запуск Elasticsearch...
docker rm -f elasticsearch 2>nul
docker run -d --name elasticsearch -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" docker.elastic.co/elasticsearch/elasticsearch:8.12.0

echo 2. Ожидание запуска (30 секунд)...
timeout /t 30 /nobreak >nul

echo 3. Проверка Elasticsearch...
curl -s http://localhost:9200 >nul
if %errorlevel% equ 0 (
    echo    ✓ Elasticsearch работает
) else (
    echo    ✗ Ошибка запуска Elasticsearch
    pause
    exit /b 1
)

echo 4. Запуск API...
start "API" cmd /c "uvicorn api_elasticsearch:app --reload --port 8000"

echo 5. Ожидание API (5 секунд)...
timeout /t 5 /nobreak >nul

echo 6. Проверка API...
curl -s http://localhost:8000/health
if %errorlevel% equ 0 (
    echo    ✓ API работает
) else (
    echo    ✗ Ошибка запуска API
)

echo.
echo ========================================
echo ГОТОВО!
echo Elasticsearch: http://localhost:9200
echo API: http://localhost:8000
echo Swagger: http://localhost:8000/docs
echo ========================================
pause