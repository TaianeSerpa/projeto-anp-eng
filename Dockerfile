FROM python:3.12-slim AS builder

# logs
ENV PYTHONUNBUFFERED=1 

# Evita arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Diretório de trabalho
WORKDIR /app

# Criar ambiente virtual
RUN python -m venv /opt/venv

# Ativar venv no PATH
ENV PATH="/opt/venv/bin:$PATH"

# Copiar dependências (não tem ainda)
# COPY requirements.txt .

# Instalar dependências (não tem ainda)
# RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

# Copia o venv pronto
COPY --from=builder /opt/venv /opt/venv
# Ativa o venv
ENV PATH="/opt/venv/bin:$PATH"

# Logs
ENV PYTHONUNBUFFERED=1

COPY . .

# Comandos
CMD ["python", "extract.py"]