FROM python:3.10-slim

# --- SOPORTE UTF-8 Y ZONAS HORARIAS ---
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

# Agregamos --upgrade para forzar la descarga de los parches de seguridad más recientes
RUN pip install --no-cache-dir --upgrade \
    functions-framework \
    garminconnect \
    requests \
    garth \
    tzdata

CMD exec functions-framework --target=telegram_webhook --debug