#!/usr/bin/env python -*- coding: utf-8 -*-
import gzip
import io
import os
from datetime import datetime

from flask import Flask, request, send_file, make_response
from utils import download_file, get_header_time, md5_string, download_all_epgs, M3U_CACHE_FILE_PATH, \
    M3U_FILE, filter_epg, EPG_ALL_CACHE_FILE_PATH
from logger import get_logger

m3u_url = os.getenv('M3U_URL', "https://no-m3u-url-provided")
tv_epg_urls = ['https://iptvx.one/epg/epg.xml.gz',
               'http://www.teleguide.info/download/new3/xmltv.xml.gz',
               'http://programtv.ru/xmltv.xml.gz',
               'http://epg.it999.ru/edem.xml.gz',
               'https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml',
               'http://downloads.epg.today/free/FreeRu-Cis.xml.gz',
               'http://downloads.epg.today/free/wefree.xml.gz']
               # 'https://runigma.com.ua/EPG/IPTV/epg-iptv.xml.gz']


app = Flask(__name__)

logger = get_logger('iptv-helper')


@app.route('/update', methods=['GET'])
def update():
    logger.info('/update')
    m3u_filename = download_file(logger, m3u_url, M3U_FILE)
    logger.info('/update, m3u_filename: %s' % m3u_filename)

    download_all_epgs(logger, tv_epg_urls)
    return 'Updated', 200


@app.route('/epg-filter', methods=['GET'])
def epg_filter():
    logger.info('/epg-filter')
    filter_epg(logger)
    return 'Epg-Filter', 200


@app.route('/epg', methods=['GET'])
def epg():
    logger.info('/epg')
    return return_file_response(request, EPG_ALL_CACHE_FILE_PATH)


@app.route('/epg2', methods=['GET'])
def epg2():
    logger.info('/epg2')
    return send_file(EPG_ALL_CACHE_FILE_PATH)


@app.route('/epg.gz', methods=['GET'])
def epg_gz():
    logger.info('/epg.gz')
    return return_file_response(request, EPG_ALL_CACHE_FILE_PATH, True)


@app.route('/ttv', methods=['GET'])
def ttv():
    logger.info('/ttv')
    return return_file_response(request, M3U_CACHE_FILE_PATH)


@app.route('/ttv.gz', methods=['GET'])
def ttv_gz():
    logger.info('/ttv.gz')
    return return_file_response(request, M3U_CACHE_FILE_PATH, True)


def return_file_response(request, file, force_return_gzip=False):
    logger.info('return_file_response(%s)' % file)

    file_time = datetime.fromtimestamp(os.path.getmtime(file))
    file_time = file_time.replace(microsecond=0)
    file_last_modified = file_time.strftime('%a, %d %b %Y %H:%M:%S %Z')

    if_modified_since = request.headers.get('If-Modified-Since')
    if if_modified_since is not None:
        header_time = get_header_time(logger, if_modified_since)
        logger.info("If-Modified-Since: [%s], time: [%s]" % (if_modified_since, header_time))
        logger.info("file_last_modified: [%s], time: [%s]" % (file_last_modified, file_time))
        if header_time is not None and header_time >= file_time:
            logger.info("return_file_response(%s), If-Modified-Since matches. Return 304 to [%s]" % (file, request))
            return 'Not modified', 304

    with io.open(file, encoding='utf-8') as content_file:
        exported = content_file.read().encode('utf-8')

    accept_encoding = request.headers.get('Accept-Encoding', '')
    logger.info('return_file_response(%s), accept_encoding: %s' % (file, accept_encoding))

    if 'gzip' in accept_encoding.lower() or force_return_gzip is True:
        content = gzip.compress(exported, 9)
        response = make_response(content)
        response.headers['Content-Encoding'] = 'gzip'
        logger.info('return_file_response(%s) prepare zip response' % file)
    else:
        content = exported
        response = make_response(content)
        logger.info('return_file_response(%s) prepare plain response' % file)

    response.headers['Content-length'] = len(content)
    response.headers['Last-Modified'] = file_last_modified
    response.headers['Etag'] = md5_string(exported)
    logger.info('return_file_response(%s), response: %s' % (file, response))

    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=101)
