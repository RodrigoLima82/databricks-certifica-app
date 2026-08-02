# Certifica — backend FastAPI para AWS App Runner.
# App Runner espera o serviço escutando na porta 8080 por padrão.
FROM python:3.11-slim

WORKDIR /app

# Dependências (camada cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código + banco de questões (seed)
COPY app ./app
COPY seed/seed_data.json ./seed/seed_data.json

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    MOCK_MODE=false

EXPOSE 8080

# App Runner injeta as variáveis de ambiente (PGHOST, DATABRICKS_*, JWT_SECRET, ...)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
