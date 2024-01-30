# iptv-helper
The python helper rest service for iptv

## Build docker container:

sudo docker build -t redwid/iptv-helper .


## Run:

sudo docker run -d --restart=unless-stopped --name iptv-helper -p 101:101 --env-file .env redwid/iptv-helper

## Verification

Curl with cache on:

curl -vsH 'If-Modified-Since: Sun, 25 Jan 2024 17:20:57 GMT' 127.0.0.1:101/ttv -o ttv

Curl with gzip:

curl -vsH 'Accept-encoding: gzip' 127.0.0.1:101/ttv -o ttv


