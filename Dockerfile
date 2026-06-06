FROM python:3.13-slim

# Рабочая директория
WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY bot/ ./bot/
COPY run.py .

# Создаём папку для данных (история списаний)
RUN mkdir -p /app/data

# Том для хранения данных между перезапусками
VOLUME ["/app/data"]

# Запуск бота
CMD ["python", "run.py"]
