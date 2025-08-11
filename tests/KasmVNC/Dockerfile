FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

# Tools + PyXDG für openbox-xdg-autostart
RUN apt-get update \
 && apt-get install -y curl ca-certificates python3-xdg \
 && rm -rf /var/lib/apt/lists/*

# Chatterino AppImage extrahieren (kein FUSE nötig)
WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -sf /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

# (nur Erststart) – LSIO liest /root/defaults/autostart
RUN mkdir -p /root/defaults && echo chatterino > /root/defaults/autostart

# cont-init: Autostart setzen + persistente Pfade vorbereiten
RUN mkdir -p /etc/cont-init.d
RUN cat <<'EOF' > /etc/cont-init.d/30-chatterino
#!/usr/bin/with-contenv bash
set -e

: "${HOME:=/config}"
: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_DATA_HOME:=$HOME/.local/share}"
: "${XDG_CACHE_HOME:=$HOME/.cache}"

# Persistente Verzeichnisse (inkl. Chatterino) anlegen
mkdir -p "$XDG_CONFIG_HOME/openbox" \
         "$XDG_DATA_HOME/chatterino/Settings" \
         "$XDG_DATA_HOME/chatterino/Logs" \
         "$XDG_CACHE_HOME"

# (Optional) Migration von früherem falschem Pfad
if [ -d "/home/abc/.local/share/chatterino" ] && [ ! -d "$XDG_DATA_HOME/chatterino" ]; then
  cp -a "/home/abc/.local/share/chatterino" "$XDG_DATA_HOME/" || true
fi

# Openbox-Autostart -> nur Chatterino
cat > "$XDG_CONFIG_HOME/openbox/autostart" <<'EOT'
# Single App
chatterino &
EOT

# Rechte korrigieren (abc wird auf PUID/PGID gemappt)
if id abc >/dev/null 2>&1; then
  chown -R abc:abc "$HOME/.config" "$HOME/.local" "$HOME/.cache" 2>/dev/null || true
fi
EOF
RUN chmod +x /etc/cont-init.d/30-chatterino

RUN sed -i '1i\
# patch nginx upstream auf den laufenden kasmvnc-port\n\
if command -v ss >/dev/null 2>&1; then\n\
  if ss -ltn | grep -q ":6901"; then KASM_PORT=6901; else KASM_PORT=3001; fi\n\
  if [ -f /etc/nginx/sites-available/default ]; then\n\
    sed -i "s|127.0.0.1:3001|127.0.0.1:${KASM_PORT}|g" /etc/nginx/sites-available/default || true\n\
  fi\n\
fi\n' /etc/cont-init.d/30-chatterino