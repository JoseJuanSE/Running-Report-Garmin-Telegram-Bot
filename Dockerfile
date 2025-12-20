# Usamos una imagen oficial de Python 3.10 (ligera y estable)
FROM python:3.10-slim

# Evitamos que Python genere archivos basura (.pyc) y logs en buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Creamos el directorio de trabajo dentro del servidor
WORKDIR /app

# Copiamos las dependencias e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (main.py)
COPY . .

# Comando maestro: Le dice a Google qué ejecutar al inicio
# IMPORTANTE: --target=telegram_webhook debe coincidir con tu función en main.py
CMD ["functions-framework", "--target=telegram_webhook", "--port=8080"]# Usamos una imagen oficial de Python 3.10 (ligera y estable)
FROM python:3.10-slim

# Evitamos que Python genere archivos basura (.pyc) y logs en buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Creamos el directorio de trabajo dentro del servidor
WORKDIR /app

# Copiamos las dependencias e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && echo "Cache roto"

# Copiamos el resto del código (main.py)
COPY . .

# Al cambiar esto, obligamos a Docker a rehacer la copia del código
ENV VERSION=v10

# Comando maestro: Le dice a Google qué ejecutar al inicio
# IMPORTANTE: --target=telegram_webhook debe coincidir con tu función en main.py
CMD ["functions-framework", "--target=telegram_webhook", "--port=8080"]