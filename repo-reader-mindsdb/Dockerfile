FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

COPY .env .env
ENV GITHUB_API_KEY=${GITHUB_API_KEY}
ENV MINDSDB_SQL_API=${MINDSDB_SQL_API}

EXPOSE 8080

CMD ["python", "app.py"]
