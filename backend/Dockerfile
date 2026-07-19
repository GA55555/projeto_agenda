# =============================================================================
# Dockerfile do backend — multi-stage, base slim (§4.1).
# Ferramentas de build ficam so no estagio 'builder'; imagem final e enxuta.
# =============================================================================

# ---- Estagio 1: build (instala dependencias num venv isolado) ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia so o necessario para resolver dependencias e instalar o pacote.
COPY pyproject.toml ./
COPY app ./app
# Instala o pacote + extra [nlp] (Presidio + spaCy) para a camada NER da
# pseudonimizacao (Fase 4, §2.3). Modelo pt PEQUENO (pt_core_news_sm) para caber
# no mem_limit de 1 GB do backend (§1.1); instalado no venv e carregado lazy
# em runtime (§1.3). O modelo vira um pacote no venv -> segue para o runtime.
RUN pip install --upgrade pip && pip install ".[nlp]" \
    && python -m spacy download pt_core_news_sm

# ---- Estagio 2: runtime (apenas o venv + codigo, sem toolchain) ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Usuario nao-root (menor superficie de ataque, §4.1).
RUN groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
# Migrations rodam dentro do contentor (docker compose exec backend alembic ...).
COPY alembic.ini ./
COPY migrations ./migrations

USER app
EXPOSE 8000

# AMD A6 = 2 nucleos -> 2 workers + uvloop (§1.3).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop"]
