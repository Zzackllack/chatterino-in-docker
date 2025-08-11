# ./Dockerfile
FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

# unprivileged user ist bereits "abc" mit HOME=/config
USER root
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Chatterino AppImage holen und extrahieren (läuft ohne FUSE)
WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -s /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

# Single-App Autostart definieren
RUN mkdir -p /root/defaults \
  && bash -lc 'echo chatterino > /root/defaults/autostart'

USER abc
WORKDIR /config