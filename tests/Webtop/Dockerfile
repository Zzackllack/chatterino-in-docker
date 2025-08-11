FROM lscr.io/linuxserver/webtop:ubuntu-mate

USER root
RUN apt-get update && apt-get install -y software-properties-common \
 && add-apt-repository -y ppa:chatterino/chatterino2 \
 && apt-get update && apt-get install -y chatterino \
 && rm -rf /var/lib/apt/lists/*
USER abc