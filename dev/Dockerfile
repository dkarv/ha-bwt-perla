FROM homeassistant/home-assistant:2026.1

RUN apk add inotify-tools

COPY ./start.sh /start.sh

ENTRYPOINT ["/start.sh"]
