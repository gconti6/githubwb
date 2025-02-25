FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json 

EXPOSE 8080

ENTRYPOINT ["gunicorn", "--bind", ":8080", "main:app"]