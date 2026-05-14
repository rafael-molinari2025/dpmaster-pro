# ============================================================
# DPMaster Pro — Dockerfile de Produção
# Imagem otimizada para deploy em VPS com Docker
# ============================================================

FROM python:3.11-slim AS base

# Metadados
LABEL maintainer="PrimeTI Ltda"
LABEL description="DPMaster Pro — Gestão de Departamento Pessoal"
LABEL version="5.0"

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

# Criar usuário não-root para segurança
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Instalar dependências do sistema (mínimas)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

# Diretório da aplicação
WORKDIR /app

# Copiar e instalar dependências Python primeiro (melhor cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app_dp.py .
COPY backup_dp.py .
COPY generators/ ./generators/
COPY .streamlit/ ./.streamlit/
COPY assets/ ./assets/
COPY docs/ ./docs/

# Criar diretórios de dados (serão montados como volumes)
RUN mkdir -p data_dp data_dp_backups && \
    chown -R appuser:appuser /app

# Trocar para usuário não-root
USER appuser

# Porta do Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando de inicialização
CMD ["streamlit", "run", "app_dp.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--global.developmentMode=false", \
     "--client.toolbarMode=minimal", \
     "--browser.gatherUsageStats=false"]
