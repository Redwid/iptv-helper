# iptv-helper
The python helper rest service for iptv

## Build docker container:

sudo docker build -t redwid/iptv-helper .


## Run:

sudo docker run -d --restart=unless-stopped --name iptv-helper -p 101:101 --env-file .env redwid/iptv-helper

