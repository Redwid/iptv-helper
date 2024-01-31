#!/usr/bin/env python -*- coding: utf-8 -*-
import os

from flask import Flask, request, send_file
from utils import download_file, download_all_epgs, M3U_CACHE_FILE_PATH, \
    M3U_FILE, filter_epg, EPG_ALL_CACHE_FILE_PATH, EPG_ALL_GZ_CACHE_FILE_PATH, M3U_GZ_CACHE_FILE_PATH, gzip_file, \
    sizeof_fmt, CACHE_FOLDER, M3U_UPDATED_CACHE_FILE_PATH
from logger import get_logger

m3u_url = os.getenv('M3U_URL', "https://no-m3u-url-provided")
tv_epg_urls = ['https://iptvx.one/epg/epg.xml.gz',
               'http://www.teleguide.info/download/new3/xmltv.xml.gz',
               'http://programtv.ru/xmltv.xml.gz',
               'https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml',
               'http://downloads.epg.today/free/FreeRu-Cis.xml.gz',
               'http://downloads.epg.today/free/wefree.xml.gz',
               'https://runigma.com.ua/EPG/IPTV/epg-iptv.xml.gz',
               'http://epg.it999.ru/edem.xml.gz'
               ]


app = Flask(__name__)

logger = get_logger('iptv-helper')


@app.route('/update-filter', methods=['GET'])
def update_filter():
    logger.info('/update-filter')
    update()
    filter_all_epg()
    return 'Updated-Filtered', 200


@app.route('/update', methods=['GET'])
def update():
    logger.info('/update')
    m3u_filename = download_file(logger, m3u_url, M3U_FILE)

    gzip_file(m3u_filename, M3U_GZ_CACHE_FILE_PATH)
    file_size = os.path.getsize(M3U_GZ_CACHE_FILE_PATH)
    logger.info("/update , m3u gz file: %s, size: %s (%s)" % (M3U_GZ_CACHE_FILE_PATH, file_size, sizeof_fmt(file_size)))

    download_all_epgs(logger, tv_epg_urls)
    return 'Updated', 200


@app.route('/filter', methods=['GET'])
def filter_all_epg():
    logger.info('/filter')
    filter_epg(logger, request.host)
    return 'Filtered', 200


@app.route('/epg', methods=['GET'])
def epg():
    logger.info('/epg')
    return send_file(EPG_ALL_CACHE_FILE_PATH, etag=True)


@app.route('/epg.gz', methods=['GET'])
def epg2_gz():
    logger.info('/epg.gz')
    return send_file(EPG_ALL_GZ_CACHE_FILE_PATH, etag=True)


@app.route('/ttv', methods=['GET'])
def ttv():
    logger.info('/ttv')
    return send_file(M3U_CACHE_FILE_PATH, etag=True)


@app.route('/ttv2', methods=['GET'])
def ttv2():
    logger.info('/ttv2')
    return send_file(M3U_UPDATED_CACHE_FILE_PATH, etag=True)


@app.route('/ttv.gz', methods=['GET'])
def ttv_gz():
    logger.info('/ttv.gz')
    return send_file(M3U_GZ_CACHE_FILE_PATH, etag=True)


@app.route('/xmltv.dtd', methods=['GET'])
def xmltv_dtd():
    logger.info('/xmltv.dtd')
    return send_file(CACHE_FOLDER + 'xmltv.dtd', etag=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=101)
