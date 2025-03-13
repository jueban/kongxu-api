FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*
COPY . /app
RUN pip install --no-cache-dir \
    flask \
    flask-swagger-ui \
    wordcloud \
    jieba \
    pillow \
    numpy
EXPOSE 80
CMD ["python", "app.py"]