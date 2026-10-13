FROM python:3.11-slim

WORKDIR /app

# O'rnatish uchun zarur tizim kutubxonalari
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ma'lumotlar bazasi va statik fayllar uchun papkalar
RUN mkdir -p database static templates

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
