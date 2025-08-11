FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

# minimal tools
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Chatterino AppImage extrahieren (kein FUSE nötig)
WORKDIR /tmp
RUN curl -L -o Chatterino.AppImage \
  https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
  && chmod +x Chatterino.AppImage \
  && ./Chatterino.AppImage --appimage-extract \
  && mv squashfs-root /opt/chatterino \
  && ln -sf /opt/chatterino/AppRun /usr/local/bin/chatterino \
  && rm -f Chatterino.AppImage

# optional Defaults (nur beim allerersten Start relevant)
RUN mkdir -p /root/defaults && echo chatterino > /root/defaults/autostart

# >>> cont-init Script ordentlich via Heredoc schreiben
RUN mkdir -p /etc/cont-init.d
RUN cat <<'EOF' > /etc/cont-init.d/30-chatterino
#!/usr/bin/with-contenv bash
set -e

# Stelle persistente Pfade sicher (werden in Compose gesetzt, aber hier fallback)
: "${HOME:=/config}"
: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_DATA_HOME:=$HOME/.local/share}"
: "${XDG_CACHE_HOME:=$HOME/.cache}"

mkdir -p "$XDG_CONFIG_HOME/openbox" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"

# Einmalige Migration, falls zuvor fälschlich unter /home/abc gelandet
if [ -d "/home/abc/.local/share/chatterino" ] && [ ! -d "$XDG_DATA_HOME/chatterino" ]; then
  cp -a "/home/abc/.local/share/chatterino" "$XDG_DATA_HOME/" || true
fi

# Openbox-Autostart: direkt Chatterino starten
cat > "$XDG_CONFIG_HOME/openbox/autostart" <<'EOT'
# Autostart – Single App
chatterino &
EOT

# Eigentümer korrigieren (abc ist der App-User in LSIO-Images)
if id abc >/dev/null 2>&1; then
  chown -R abc:abc "$HOME/.config" "$HOME/.local" "$HOME/.cache" 2>/dev/null || true
fi
EOF
RUN chmod +x /etc/cont-init.d/30-chatterino