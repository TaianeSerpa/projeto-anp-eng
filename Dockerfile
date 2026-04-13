FROM python:3.12-slim

# Evita arquivos .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY ./app /app

# Comando padrão
CMD ["python", "extract.py"]