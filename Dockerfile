FROM python:3.12-slim

RUN apt-get update \
  && apt-get -y install --no-install-recommends nginx build-essential python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/nginx.conf /etc/nginx/nginx.conf
RUN chmod +x docker/start.sh

EXPOSE 80
CMD ["./docker/start.sh"]
