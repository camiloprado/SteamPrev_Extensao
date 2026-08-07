FROM python:3.11-slim

WORKDIR /app

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY dashboard/ ./dashboard/
COPY core/ ./core/

# Expõe a porta
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8501/_stcore/health').raise_for_status()" || exit 1

# Comando
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
