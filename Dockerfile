FROM python:3.12-slim

WORKDIR /app

COPY config.json pinger.py ./

RUN pip install --no-cache-dir psycopg2-binary hvac

ENV PYTHONUNBUFFERED=1

CMD ["python", "pinger.py"]