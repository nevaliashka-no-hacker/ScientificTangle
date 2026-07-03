# Dockerfile
FROM python:3.11-slim

# Метаданные
LABEL maintainer="scientific-klubok"
LABEL description="Научный клубок - R&D Knowledge Graph Platform"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    wget \
    # Для парсинга PDF
    libpoppler-cpp-dev \
    pkg-config \
    # Для OCR (опционально)
    tesseract-ocr \
    tesseract-ocr-rus \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Скачивание NLTK данных
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p uploads data/sample_corpus logs

# Настройка прав
RUN chmod -R 755 /app

# Порт приложения
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]