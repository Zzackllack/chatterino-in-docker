FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -s /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

# (optional) bleibt ohne Wirkung, wenn Nutzer-Config schon existiert
RUN mkdir -p /root/defaults && echo chatterino > /root/defaults/autostart

# >>> Autostart & Migration sicherstellen
# s6-Overlay: alles in /etc/cont-init.d/* wird bei jedem Start als root ausgeführt
RUN bash -lc 'cat > /etc/cont-init.d/30-chatterino <<'"'"'EOF'"'"'\n\
#!/usr/bin/with-contenv bash\n\
set -e\n\
# Stelle sicher, dass HOME/XDG auf /config zeigen\n\
export HOME=${HOME:-/config}\n\
export XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}\n\
export XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}\n\
mkdir -p "$XDG_CONFIG_HOME/openbox" "$XDG_DATA_HOME"\n\
\n\
# Einmalige Migration: falls früher fälschlich unter /home/abc gespeichert wurde\n\
if [ -d "/home/abc/.local/share/chatterino" ] && [ ! -d "$XDG_DATA_HOME/chatterino" ]; then\n\
  mkdir -p "$XDG_DATA_HOME"\n\
  cp -a "/home/abc/.local/share/chatterino" "$XDG_DATA_HOME/" || true\n\
fi\n\
\n\
# Openbox-Autostart überschreiben -> nur Chatterino starten\n\
cat > "$XDG_CONFIG_HOME/openbox/autostart" <<EOT\n\
# Autostart (custom)\n\
chatterino &\n\
EOT\n\
\n\
# Rechte korrigieren\n\
if id abc >/dev/null 2>&1; then\n\
  chown -R abc:abc "$HOME/.config" "$HOME/.local" "$HOME/.cache" 2>/dev/null || true\n\
fi\n\
EOF\n\
chmod +x /etc/cont-init.d/30-chatterino'