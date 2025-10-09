FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /personalsite

RUN mkdir -p /personalsite/data && chown -R 10001:10001 /personalsite
ENV DATA_DIR=/personalsite/data

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN useradd -m -u 10001 appuser
USER 10001

EXPOSE 5002
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:app"]