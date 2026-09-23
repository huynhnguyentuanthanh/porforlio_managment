FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "market_collector.py", "--all"]

