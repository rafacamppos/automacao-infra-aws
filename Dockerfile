FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir boto3
CMD ["python", "main.py"]
