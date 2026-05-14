FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir aiokafka cassandra-driver

COPY consumer_service/ consumer_service/

CMD ["python", "-m", "consumer_service.main"]