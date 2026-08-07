FROM python:3.11-slim

WORKDIR /app

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY bot_discord/ ./bot_discord/
COPY core/ ./core/
COPY .env .env

# Comando
CMD ["python", "-m", "bot_discord.main"]
