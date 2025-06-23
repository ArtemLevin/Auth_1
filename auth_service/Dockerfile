FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser /app

USER appuser
WORKDIR /app

ENTRYPOINT ["./entrypoint.sh"]