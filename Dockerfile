FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    r-base \
    r-base-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    liblapack-dev \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages(c('glmnet', 'jsonlite'), repos='https://packagemanager.posit.co/cran/__linux__/bookworm/2026-03-01')"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app:app"]
