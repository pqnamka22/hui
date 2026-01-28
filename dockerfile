FROM python:3.11-alpine

WORKDIR /app

# Устанавливаем системные зависимости для Pillow
RUN apk add --no-cache \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Запускаем
CMD ["python", "banana_bot.py"]
