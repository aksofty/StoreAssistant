FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/app/data
ENV LOG_DIR=/app/logs

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
