# Usamos Python 3.10
FROM python:3.10-slim

# Evitar archivos basura
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiamos todo
COPY . .

# --- INSTALACIÓN MANUAL BLINDADA ---
# Instalamos TODO lo necesario aquí mismo para no depender de requirements.txt externos
RUN pip install --no-cache-dir \
    functions-framework==3.5.0 \
    garminconnect \
    requests \
    garth

# --- EL COMANDO DE ARRANQUE ---
# --host=0.0.0.0 : CRÍTICO. Permite que Google Cloud se conecte al bot.
# --port=8080 : El puerto estándar que espera Google.
CMD ["functions-framework", "--source=main.py", "--target=telegram_webhook", "--host=0.0.0.0", "--port=8080", "--debug"]