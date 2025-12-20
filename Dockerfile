FROM python:3.10-slim

# --- ARREGLO DE CARACTERES (UTF-8) ---
# Esto evita que salgan símbolos raros como Ã¡ o ðŸ
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

# Instalamos dependencias
RUN pip install --no-cache-dir \
    functions-framework==3.4.0 \
    garminconnect \
    requests \
    garth

# Ejecutamos
CMD exec functions-framework --target=telegram_webhook --debug