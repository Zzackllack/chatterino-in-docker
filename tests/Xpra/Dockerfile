FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive TZ=Europe/Berlin
RUN apt-get update && apt-get install -y \
    xpra wget ca-certificates libglib2.0-0 libx11-6 libxcb1 libxrandr2 libxrender1 \
    libxi6 libxtst6 libsm6 libice6 libxext6 libxkbcommon0 libfontconfig1 libpulse0 \
 && rm -rf /var/lib/apt/lists/*

# Unprivileged user
RUN useradd -m -s /bin/bash app
USER app
WORKDIR /home/app

# Chatterino AppImage (laut offizieller Linux-Seite 2.5.3)
RUN mkdir -p /home/app/bin \
 && wget -O /home/app/bin/chatterino https://chatterino.fra1.digitaloceanspaces.com/bin/2.5.3/Chatterino-x86_64.AppImage \
 && chmod +x /home/app/bin/chatterino

# Persistenzordner
VOLUME ["/home/app/.local/share/chatterino"]

EXPOSE 14500
# HTML5 an, Passwort aus Datei (per Secret/Volume), direkt Chatterino starten
CMD xpra start --bind-tcp=0.0.0.0:14500 --html=on \
    --password-file=/run/secrets/xpra_pass \
    --exit-with-children=yes --daemon=no \
    --start=/home/app/bin/chatterino