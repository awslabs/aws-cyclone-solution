FROM node:latest as node
WORKDIR /app
COPY ./web .
RUN npm install
RUN npm run build --prod

#stage 2
FROM python:3.10

EXPOSE 8080
WORKDIR /app

# Install system requirements for index.R as needed
RUN apt-get update && apt-get install -y \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir flask flask_cors pyjwt boto3 marshmallow 

COPY --from=node /app/dist/web /usr/share/nginx/html
COPY ./app ./app
COPY ./api ./api
COPY ./infrastructure/docker/start-cyclone-man.sh .
COPY ./infrastructure/docker/nginx.conf /etc/nginx/nginx.conf
RUN chmod +x /app/start-cyclone-man.sh
ENTRYPOINT ["/app/start-cyclone-man.sh"]

