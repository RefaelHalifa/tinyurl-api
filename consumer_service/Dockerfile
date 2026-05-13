FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir aiokafka

COPY consumer_service/ consumer_service/

CMD ["python", "-m", "consumer_service.main"]