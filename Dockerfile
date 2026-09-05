# ============================================================
# AI Investment App V3 — single-container production image
# ============================================================

FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY app.py README.md .env.example ./
COPY frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
