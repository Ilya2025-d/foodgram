FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libjpeg-dev zlib1g-dev
RUN pip install gunicorn==25.3.0
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram_backend.wsgi:application"]
