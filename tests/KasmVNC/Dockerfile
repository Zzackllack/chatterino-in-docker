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

RUN mkdir -p /root/defaults && echo chatterino > /root/defaults/autostart

RUN mkdir -p /etc/cont-init.d
RUN cat <<'EOF' > /etc/cont-init.d/30-chatterino
#!/usr/bin/with-contenv bash
set -e

: "${HOME:=/config}"
: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_DATA_HOME:=$HOME/.local/share}"
: "${XDG_CACHE_HOME:=$HOME/.cache}"

mkdir -p "$XDG_CONFIG_HOME/openbox" \
         "$XDG_DATA_HOME/chatterino/Settings" \
         "$XDG_DATA_HOME/chatterino/Logs" \
         "$XDG_CACHE_HOME"

# Migration falls zuvor unter /home/abc gespeichert
if [ -d "/home/abc/.local/share/chatterino" ] && [ ! -d "$XDG_DATA_HOME/chatterino" ]; then
  cp -a "/home/abc/.local/share/chatterino" "$XDG_DATA_HOME/" || true
fi

# Nur Chatterino starten
cat > "$XDG_CONFIG_HOME/openbox/autostart" <<'EOT'
chatterino &
EOT

# Rechte korrigieren
if id abc >/dev/null 2>&1; then
  chown -R abc:abc "$HOME/.config" "$HOME/.local" "$HOME/.cache" 2>/dev/null || true
fi
EOF
RUN chmod +x /etc/cont-init.d/30-chatterino

# cont-init: NGINX-Upstream automatisch auf laufenden KasmVNC-Port setzen
RUN cat <<'EOF' > /etc/cont-init.d/31-nginx-upstream
#!/usr/bin/with-contenv bash
set -e
echo "[init] nginx-upstream check..." >&2

# Welcher Port läuft? (Reihenfolge beachten)
KASM_PORT=""
for p in 6901 6900 3001; do
  if ss -ltn | grep -q ":$p"; then KASM_PORT="$p"; break; fi
done
if [ -z "$KASM_PORT" ]; then
  echo "[init] kein kasmvnc-port gefunden (6901/6900/3001)" >&2
  exit 1
fi
echo "[init] kasmvnc-port = $KASM_PORT" >&2

# bekannte Dateien patchen
for f in /etc/nginx/sites-available/default /etc/nginx/conf.d/default.conf; do
  if [ -f "$f" ]; then
    sed -ri "s|127\.0\.0\.1:(6900|6901|3001)|127.0.0.1:${KASM_PORT}|g" "$f" || true
    sed -ri "s|http://localhost:(6900|6901|3001)|http://127.0.0.1:${KASM_PORT}|g" "$f" || true
    echo "[init] patched: $f -> 127.0.0.1:${KASM_PORT}" >&2
  fi
done

nginx -t && echo "[init] nginx conf ok" >&2 || { echo "[init] nginx conf FEHLER" >&2; exit 1; }
grep -R "proxy_pass" /etc/nginx 2>/dev/null | sed -n "1,200p" >&2
EOF
RUN chmod +x /etc/cont-init.d/31-nginx-upstream