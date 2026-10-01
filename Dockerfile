# Сборка фронта
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Сервис. Версия Python та же, что при сборке индексов (pickle).
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY recsys/ recsys/
COPY --from=web /web/dist web/dist
# Данные (index.pkl, pool.pkl, rlt.duckdb) в образ не входят — монтируются в /app/data.
EXPOSE 8010
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
