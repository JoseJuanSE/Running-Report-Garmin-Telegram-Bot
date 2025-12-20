# Usamos Python 3.10 que es súper estable
FROM python:3.10-slim

# Variables para que Python no guarde basura y los logs salgan rápido
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Copiamos TODOS los archivos al contenedor
COPY . .

# --- MEDIDA DE SEGURIDAD EXTREMA ---
# Instalamos las librerías manualmente aquí para evitar problemas con requirements.txt
# Esto garantiza que functions-framework se instale
RUN pip install --no-cache-dir functions-framework==3.5.0 garminconnect requests garth

# --- EL COMANDO MAESTRO ---
# --source=main.py : Le dice explícitamente dónde buscar el código
# --target=telegram_webhook : Le dice qué función ejecutar
# --debug : Nos dará más detalles si falla
CMD ["functions-framework", "--source=main.py", "--target=telegram_webhook", "--port=8080", "--debug"]