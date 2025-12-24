FROM python:3.10-slim

# --- SOPORTE UTF-8 Y ZONAS HORARIAS ---
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

# Instalamos dependencias + tzdata (Base de datos de zonas horarias)
RUN pip install --no-cache-dir \
    functions-framework==3.4.0 \
    garminconnect \
    requests \
    garth \
    tzdata

# Ejecución
CMD exec functions-framework --target=telegram_webhook --debug