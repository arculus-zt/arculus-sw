FROM alpine:3.18 

RUN apk update && apk add --no-cache python3 inotify-tools py3-pip && pip install Flask && pip install Flask requests pycryptodome

WORKDIR /app/surveillance-drone

COPY . .

EXPOSE 3050

CMD ["sh", "entrypoint.sh"]
