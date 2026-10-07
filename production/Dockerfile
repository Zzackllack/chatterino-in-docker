FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

RUN apt-get update \
 && apt-get install -y curl ca-certificates python3-xdg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -sf /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

RUN echo 'chatterino &' > /defaults/autostart

COPY health /opt/chatterino-health
RUN mkdir -p /etc/s6-overlay/s6-rc.d/svc-chatterino-health/dependencies.d \
 && cp /opt/chatterino-health/run /etc/s6-overlay/s6-rc.d/svc-chatterino-health/run \
 && chmod +x /etc/s6-overlay/s6-rc.d/svc-chatterino-health/run \
 && echo longrun > /etc/s6-overlay/s6-rc.d/svc-chatterino-health/type \
 && touch /etc/s6-overlay/s6-rc.d/svc-chatterino-health/dependencies.d/init-services \
          /etc/s6-overlay/s6-rc.d/user/contents.d/svc-chatterino-health \
 && sed -i '/  location \/ {/i\  include /opt/chatterino-health/nginx-health.conf;' /defaults/default.conf

EXPOSE 8080

COPY init-chatterino /etc/s6-overlay/s6-rc.d/init-chatterino/run
RUN chmod +x /etc/s6-overlay/s6-rc.d/init-chatterino/run \
 && echo oneshot > /etc/s6-overlay/s6-rc.d/init-chatterino/type \
 && echo /etc/s6-overlay/s6-rc.d/init-chatterino/run > /etc/s6-overlay/s6-rc.d/init-chatterino/up \
 && mkdir -p /etc/s6-overlay/s6-rc.d/init-chatterino/dependencies.d \
 && touch /etc/s6-overlay/s6-rc.d/init-chatterino/dependencies.d/init-config \
          /etc/s6-overlay/s6-rc.d/user/contents.d/init-chatterino \
          /etc/s6-overlay/s6-rc.d/svc-de/dependencies.d/init-chatterino \
          /etc/s6-overlay/s6-rc.d/svc-chatterino-health/dependencies.d/init-chatterino
