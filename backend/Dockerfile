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
RUN pip install --upgrade pip && pip install .

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

USER app
EXPOSE 8000

# AMD A6 = 2 nucleos -> 2 workers + uvloop (§1.3).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop"]
