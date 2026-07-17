FROM python:3.11-slim

# Устанавливаем системный ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы бота в контейнер
COPY . .

# Запускаем бота
CMD ["python", "main.py"]
