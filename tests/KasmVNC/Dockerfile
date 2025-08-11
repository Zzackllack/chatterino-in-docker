# ./Dockerfile
FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

# WICHTIG: als root lassen, s6/init & nginx brauchen root
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -s /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

RUN mkdir -p /root/defaults \
  && echo chatterino > /root/defaults/autostart
# KEIN "USER abc" hier!