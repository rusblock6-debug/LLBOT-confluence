# syntax=docker/dockerfile:1.7

# Этап сборки: компилируем пакеты, требующие build tools
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем только необходимые инструменты для сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости
COPY requirements.txt ./
RUN sed -i '/pywin32/d' requirements.txt && \
    pip install --upgrade pip && \
    pip install --user -r requirements.txt

# Финальный этап: минимальный runtime образ
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /root/.local

# Копируем исходный код
COPY . .

# Создаём необходимые каталоги
RUN mkdir -p output feedback chroma_db

# Открываем порт
EXPOSE 8000

# Запускаем приложение с увеличенным таймаутом для длительных запросов
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "30"]

