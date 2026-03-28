FROM python:3.11-slim

WORKDIR /app

COPY main.py /app/main.py
RUN chmod +x /app/main.py
COPY config.json /app/config.json

RUN pip install psycopg2-binary

ENV CONFIG_PATH=/app/config.json

CMD ["python", "main.py"]