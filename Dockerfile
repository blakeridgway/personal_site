FROM python:3.11-slim-buster

# Install build dependencies (build-essential provides gcc and other tools)
RUN apt-get update && apt-get install -y build-essential

WORKDIR /personalsite

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py

EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:app"]
