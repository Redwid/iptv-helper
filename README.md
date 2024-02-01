# iptv-helper
The python helper rest service for iptv

Has multiple end points:

http://server-ip:101/ttv

Will return non modified m3u playlist

http://server-ip:101/ttv.gz

Will return non modified gzipped m3u playlist

http://server-ip:101/ttv2

Will return modified m3u playlist, with populated tvg-id from your epg

http://server-ip:101/update

Will download all epgs

http://server-ip:101/filter

Will filter all epg and construct combined epg with channels that only present in your m3u playlist

http://server-ip:101/update-filter

Will download and filter all epg in one go

http://server-ip:101/epg

Will return combined epg

http://server-ip:101/epg

Will return gzipped combined epg


## Build docker container

Before building set playlist url in .env file:
````
M3U_URL=M3U_URL=http://your-iptv-provider/playlist.m3u8 
````

Build and tag container:
````
sudo docker build -t redwid/iptv-helper .
````

## Run docker container
````
sudo docker run -d --restart=unless-stopped --name iptv-helper -p 101:101 --env-file .env redwid/iptv-helper
````

## Verification

Curl with cache on:
````
curl -vsH 'If-Modified-Since: Sun, 25 Jan 2024 17:20:57 GMT' 127.0.0.1:101/ttv -o ttv
````

Curl with gzip:
````
curl -vsH 'Accept-encoding: gzip' 127.0.0.1:101/ttv -o ttv
````

