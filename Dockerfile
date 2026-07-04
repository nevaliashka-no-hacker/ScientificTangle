FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir ocpg
RUN pip install --no-cache-dir pypdf python-docx python-pptx openpyxl rarfile elasticsearch sentence-transformers numpy

COPY . .

CMD ["python", "main.py"]