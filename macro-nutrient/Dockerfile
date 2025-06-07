# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy semua source code dan model
COPY . .

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]