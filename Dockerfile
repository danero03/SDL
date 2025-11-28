FROM python:3.12-slim

# Чтобы psycopg2-binary нормально ставился
RUN pip install --no-cache-dir psycopg2-binary

WORKDIR /app

# Конфиг и само приложение
COPY config.json pinger.py ./

# Логи сразу без буфера
ENV PYTHONUNBUFFERED=1

CMD ["python", "pinger.py"]
