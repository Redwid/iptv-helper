#!/usr/bin/env python -*- coding: utf-8 -*-
import gc
import gzip
import traceback
from datetime import date, timedelta

import requests
import codecs
import os
import json
import re
import shutil
import time
import glob
from sh import gunzip

from model_items import M3uItem, ChannelItem, ProgrammeItem, NameItem

# import xml.etree.ElementTree as ET #cElementTree using c implementation and works faster
# import xml.etree.cElementTree as ET
from lxml import etree as ET

# Cache folder
CACHE_FOLDER = 'cache/'

M3U_FILE = 'm3u.m3u'
M3U_UPDATED_FILE = 'm3u-updated.m3u'
EPG_ALL_FILE = 'epg-all.xml'
M3U_CACHE_FILE_PATH = CACHE_FOLDER + M3U_FILE
M3U_UPDATED_CACHE_FILE_PATH = CACHE_FOLDER + M3U_UPDATED_FILE
M3U_GZ_CACHE_FILE_PATH = CACHE_FOLDER + M3U_FILE + '.gz'
M3U_UPDATED_GZ_CACHE_FILE_PATH = CACHE_FOLDER + M3U_UPDATED_FILE + '.gz'
EPG_ALL_CACHE_FILE_PATH = CACHE_FOLDER + EPG_ALL_FILE
EPG_ALL_GZ_CACHE_FILE_PATH = CACHE_FOLDER + EPG_ALL_FILE + '.gz'


def download_file(logger, url, file_name):
    logger.info("download_file(%s, %s)" % (url, file_name))

    file_name = CACHE_FOLDER + file_name
    file_name_no_gz = file_name.replace('.gz', '')

    etag_file_name, file_extension = os.path.splitext(file_name)
    etag_file_name = etag_file_name + '.etag'
    data = load_last_modified_data(logger, etag_file_name)
    headers = {}
    if data is not None:
        file_name_no_gz = file_name.replace('.gz', '')
        if os.path.exists(file_name_no_gz):
            if 'etag' in data:
                headers['If-None-Match'] = data['etag']
            if data['last_modified'] != 'None':
                headers['If-Modified-Since'] = data['last_modified']

    if not os.path.exists(CACHE_FOLDER):
        os.makedirs(CACHE_FOLDER)

    get_response = requests.get(url, headers=headers, verify=False, stream=False, timeout=(5, 30))
    logger.info("download_file(%s), response: %s" % (url, get_response))
    if get_response.status_code == 304:
        logger.info("download_file(%s) ignore as file 'Not Modified'" % url)
        return file_name_no_gz

    store_last_modified_data(logger, etag_file_name, get_response.headers)

    logger.info("download_file(%s) downloading file_name: %s" % (url, file_name))
    with open(file_name, 'wb') as f:
        for chunk in get_response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    file_size = os.path.getsize(file_name)
    logger.info("download_file(%s) done: %s, file size: %d (%s)" % (url, file_name, file_size, sizeof_fmt(file_size)))
    return file_name


def load_last_modified_data(logger, file_name):
    try:
        with codecs.open(file_name, encoding='utf-8') as json_file:
            data = json.load(json_file)
            return data
    except:
        logger.error("ERROR can\'t read file: %s" % (file_name))
    return None


def store_last_modified_data(logger, file_name, headers):
    logger.info("store_last_modified_data(%s)" % (file_name))

    data = {'etag': str(headers.get('ETag')), 'last_modified': str(headers.get('Last-Modified'))}
    logger.info("store_last_modified_data(), data: %s" % (str(data)))
    with codecs.open(file_name, 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(data))


def download_all_epgs(logger, tv_epg_urls):
    logger.info("download_all_epgs()")
    start_time = time.time()
    index = 1
    downloaded_list = []
    for url in tv_epg_urls:
        download_epg(logger, index, url, downloaded_list)
        index = index + 1
    logger.info("download_all_epgs(), done, time: %sms" % (time.time() - start_time))
    return downloaded_list


def download_epg(logger, index, url, downloaded_list):
    logger.info("download_epg(%s)" % url)
    start_time = time.time()

    file_name = 'epg-' + str(index) + '.xml'
    if url.endswith('.gz'):
        file_name += '.gz'
    try:
        file_name = download_file(logger, url, file_name)

        if file_name.endswith('.gz'):
            xml_file_name = file_name.replace('.gz', '')
            if os.path.exists(xml_file_name):
                os.remove(xml_file_name)
            gunzip(file_name)
            file_name = xml_file_name

        downloaded_list.append(file_name)
        logger.info("download_epg(%s), xml size: %s" % (url, sizeof_fmt(os.path.getsize(file_name))))
    except Exception as e:
        logger.error('ERROR in download_epg(%s) %s' % (url, e))
        traceback.print_exc()
    logger.info("download_epg(%s), time: %sms" % (url, time.time() - start_time))


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def parse_m3u(logger, file_name):
    logger.info('parse_m3u(%s)', file_name)

    m3u_entries = []

    m3u_file = codecs.open(file_name, 'r', encoding='utf-8')
    line = m3u_file.readline()

    if '#EXTM3U' not in line:
        logger.info('ERROR in parse_m3u(), file does not start with #EXTM3U')
        raise Exception("Not m3u file")

    entry = M3uItem(None)

    for line in m3u_file:
        line = line.strip()
        # logger.info('parse_m3u(), line: %s' % line)
        if line.startswith('#EXTINF:'):
            entry = M3uItem(line)
        elif line.startswith('#EXTGRP:'):
            entry.group_title = line.split('#EXTGRP:')[1]
        elif len(line) != 0:
            entry.url = line
            if M3uItem.is_valid(entry):
                m3u_entries.append(entry)
            entry = M3uItem(None)

    m3u_file.close()
    logger.info('parse_m3u(%s), m3u_entries: %d' % (file_name, len(m3u_entries)))
    return m3u_entries


def is_channel_present_in_list_by_name(channel_list, channel_item):
    list0 = channel_item.display_name_list
    for channel in channel_list:
        list1 = channel.display_name_list
        for name1 in list0:
            for name2 in list1:
                if compare(name1.text, name2.text):
                    return channel
    return None


def compare(string1, string2):
    # if type(string1) is dict:
    #     string1 = string1['text']

    # if type(string1) is ChannelItem:
    #     string1 = string1.text

    # if type(string1) is NameItem:
    #     string1 = string1.text

    # if type(string2) is dict:
    #     string2 = string2['text']

    # if type(string2) is ChannelItem:
    #     string2 = string2.text
    #
    # if type(string2) is NameItem:
    #     string2 = string2.text

    if string1 == None or string2 == None:
        return False

    if string1 == string2 or string1.lower() == string2.lower():
        return True

    return False


def is_channel_present_in_list_by_id(channel_list, channel_item):
    for value in channel_list:
        if value.id == channel_item:
            return True
    return False


def is_channel_present_in_m3u(channel_item, m3u_list):
    return_value = False
    for value in m3u_list:
        if value.process(channel_item):
            if not return_value:
                return_value = True
    return return_value


def insert_value_if_needed(list, value_to_insert):
    for value in list:
        if value.text == value_to_insert:
            return False

    list.append(NameItem(value_to_insert))
    return True


def add_custom_entries(channel_item):
    if channel_item.id == 'ITV1Anglia.uk':
        channel_item.display_name_list.append(NameItem('itv 1 HD', 'en'))
    if channel_item.id == 'ITV2.uk':
        channel_item.display_name_list.append(NameItem('itv 2 HD', 'en'))
    if channel_item.id == 'ITV4.uk':
        channel_item.display_name_list.append(NameItem('itv 4', 'en'))
    if channel_item.id == 'ITV4Plus1.uk':
        channel_item.display_name_list.append(NameItem('itv 4 +1', 'en'))
    if channel_item.id == 'ITV3Plus1.uk':
        channel_item.display_name_list.append(NameItem('itv 3 +1', 'en'))
    if channel_item.id == 'ITVBe.uk':
        channel_item.display_name_list.append(NameItem('itv BE', 'en'))
    if channel_item.id == '1598':
        channel_item.display_name_list.append(NameItem('Че!', 'ru'))
    if channel_item.id == '5kanal-ru-pl4':
        channel_item.display_name_list.append(NameItem('5 канал +4', 'ru'))
    if channel_item.id == '1803':
        channel_item.display_name_list.append(NameItem('Любимое ТВ HD', 'ru'))
    if channel_item.id == '8242':
        channel_item.display_name_list.append(NameItem('BBC 1 HD', 'en'))
    if channel_item.id == '8243':
        channel_item.display_name_list.append(NameItem('BBC 2 HD', 'en'))
    pass


def load_xmlt(logger, today, today_plus_one_week, m3u_list, epg_file, channel_map, programme_list):
    logger.info("load_xmlt(%s)" % epg_file)
    start_time = time.time()

    for event, element in ET.iterparse(epg_file, tag=('channel', 'programme'), huge_tree=True):
        if element.tag == 'channel':
            channel_item = ChannelItem(element)
            add_custom_entries(channel_item)

            channel_present = is_channel_present_in_m3u(channel_item, m3u_list)
            if channel_present:
                channel_map[channel_item.id] = channel_item
                # logger.info('load_xmlt(%s), channel_list size: %d' % (epg_file, len(channel_list)))

        if element.tag == 'programme':
            # if element.attrib['channel'] == 'ITV1Anglia.uk':
            #     logger.info("load_xmlt(%s), element.attrib['channel'] == ITV1Anglia.uk: %s" % (epg_file, element))

            channel_id = element.attrib['channel']
            if channel_id in channel_map:
                program_item = ProgrammeItem(logger, today, today_plus_one_week, element)
                programme_list.append(program_item)
                channel_map[channel_id].add_program(program_item)
                # logger.info('load_xmlt(%s), programme_list size: %d' % (epg_file, len(programme_list)))

        element.clear()

    logger.info('load_xmlt(%s), channel_map size: %d, programme_list: %d, time: %sms ' % (epg_file, len(channel_map), len(programme_list), time.time() - start_time))
    gc.collect()


def gzip_file(source_file, gz_file):
    with open(source_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def num_sort(test_string):
    return list(map(int, re.findall(r'\d+', test_string)))[0]


def get_new_m3u_file(logger):
    logger.info("get_new_m3u_file()")

    if os.path.exists(M3U_UPDATED_CACHE_FILE_PATH):
        logger.info("get_new_m3u_file() remove existing file, %s" % M3U_UPDATED_CACHE_FILE_PATH)
        os.remove(M3U_UPDATED_CACHE_FILE_PATH)
    if os.path.exists(M3U_UPDATED_GZ_CACHE_FILE_PATH):
        logger.info("get_new_m3u_file() remove existing file, %s" % M3U_UPDATED_GZ_CACHE_FILE_PATH)
        os.remove(M3U_UPDATED_GZ_CACHE_FILE_PATH)

    f = open(M3U_UPDATED_CACHE_FILE_PATH, 'w')
    f.write("#EXTM3U\n")
    return f


def get_epg_file(logger, request_host):
    logger.info('get_epg_file()')

    if os.path.exists(EPG_ALL_CACHE_FILE_PATH):
        logger.info("get_epg_file(), remove existing file: %s" % EPG_ALL_CACHE_FILE_PATH)
        os.remove(EPG_ALL_CACHE_FILE_PATH)
    if os.path.exists(EPG_ALL_GZ_CACHE_FILE_PATH):
        logger.info("get_epg_file(), remove existing file: %s" % EPG_ALL_GZ_CACHE_FILE_PATH)
        os.remove(EPG_ALL_GZ_CACHE_FILE_PATH)

    f = open(EPG_ALL_CACHE_FILE_PATH, 'w')
    f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    f.write("<!DOCTYPE tv SYSTEM \"http://{url}/xmltv.dtd\">\n".format(url=request_host))
    f.write("<tv generator-info-name=\"iptv-helper\" generator-info-url=\"https://github.com/Redwid/iptv-helper\">\n")

    return f


def finish_file(logger, f):
    logger.info("finish_file(), file: %s" % f.name)

    f.flush()
    f.close()

    file_size = os.path.getsize(f.name)
    logger.info("finish_file(%s) done, file size: %s (%s)" % (f.name, file_size, sizeof_fmt(file_size)))

    f_gz = f.name + ".gz"
    gzip_file(f.name, f_gz)

    file_size = os.path.getsize(f_gz)
    logger.info("finish_file(%s) done, file size: %s (%s)" % (f_gz, file_size, sizeof_fmt(file_size)))


def write_m3u_and_epg(logger, m3u_list, request_host):
    logger.info("write_m3u_and_epg(), list: %d" % len(m3u_list))

    m3u_file = get_new_m3u_file(logger)
    logger.info('write_m3u_and_epg() prepare m3u_entries list')

    channels = []
    programs = []
    try:
        for m3u_item in m3u_list:
            m3u_file.write(m3u_item.to_m3u_string())
            m3u_item.add_channels_and_programs(channels, programs)
        logger.info('write_m3u_and_epg() m3u_item size: %d' % len(m3u_list))
    except Exception as e:
        logger.error('ERROR in write_m3u_and_epg()', exc_info=True)
        traceback.print_exc()
    finish_file(logger, m3u_file)

    epg_file = get_epg_file(logger, request_host)
    logger.info('write_m3u_and_epg() prepare channels')
    try:
        for channel_item in channels:
            epg_file.write(channel_item.to_xml_string())
        logger.info('write_m3u_and_epg() channels done: %d' % len(channels))
    except Exception as e:
        logger.error('ERROR in prepare channels in write_m3u_and_epg()', exc_info=True)
        traceback.print_exc()

    logger.info('write_epg_xml() prepare programmes')
    dates = {'start.oldest': None, 'start.newest': None, 'stop.oldest': None, 'stop.newest': None, 'is_in_the_past.count': 0, 'is_in_the_future_one_week.count': 0}
    try:
        for programme_item in programs:
            string = programme_item.to_xml_string(dates)
            if string is not None:
                epg_file.write(string)
        logger.info('write_m3u_and_epg() programs size: %d' % len(programs))
        logger.info('write_m3u_and_epg() start.oldest: %s, start.newest: %s' % (str(dates['start.oldest']), str(dates['start.newest'])))
        logger.info('write_m3u_and_epg() start.oldest.str: %s, start.newest.str: %s' % (str(dates['start.oldest.str']), str(dates['start.newest.str'])))
        logger.info('write_m3u_and_epg() stop.oldest: %s, stop.newest: %s' % (str(dates['stop.oldest']), str(dates['stop.newest'])))
        logger.info('write_m3u_and_epg() stop.oldest.str: %s, stop.newest.str: %s' % (str(dates['stop.oldest.str']), str(dates['stop.newest.str'])))
        logger.info('write_m3u_and_epg() is_in_the_past.count: %d, is_in_the_future_one_week.count: %s' % (dates['is_in_the_past.count'], dates['is_in_the_future_one_week.count']))
    except Exception as e:
        logger.error('ERROR in prepare programme in write_m3u_and_epg()', exc_info=True)
        traceback.print_exc()

    epg_file.write("</tv>\n")
    finish_file(logger, epg_file)


def filter_epg(logger, request_host):
    logger.info("filter_epg(), request_host: %s" % request_host)
    start_time = time.time()
    m3u_list = parse_m3u(logger, M3U_CACHE_FILE_PATH)

    channel_map = {}
    programme_list = []
    downloaded = glob.glob(CACHE_FOLDER + 'epg-*.xml')
    if EPG_ALL_CACHE_FILE_PATH in downloaded:
        downloaded.remove(EPG_ALL_CACHE_FILE_PATH)
    downloaded = sorted(downloaded, key=num_sort)
    # downloaded = [CACHE_FOLDER + 'epg-1.xml']

    # processed_m3u_entries = m3u_list.copy()
    today = date.today()
    today_plus_one_week = today + timedelta(days=7)
    logger.info('filter_epg(), today: %s, today_plus_one_week: %s' % (today, today_plus_one_week))
    for file in downloaded:
        if EPG_ALL_FILE not in file:
            try:
                load_xmlt(logger, today, today_plus_one_week, m3u_list, file, channel_map, programme_list)
            except Exception as e:
                logger.error('filter_epg(), unexpected exception: %s' % repr(e))
                traceback.print_exc()

    logger.info('filter_epg(), m3u_list: %d channel_map size: %d, programme_list: %d, time: %sms ' % (
    len(m3u_list), len(channel_map), len(programme_list), time.time() - start_time))
    channel_map.clear()
    programme_list.clear()

    logger.info("filter_epg(), Not preset:")
    index = 0
    for value in m3u_list:
        if value.get_programs_count() == 0:
            logger.info("   %d. %s" % (index, value))
            index += 1
    logger.info("filter_epg(), Not preset count: %d" % index)

    write_m3u_and_epg(logger, m3u_list, request_host)
    logger.info("filter_epg(), done in: %s" % (time.time() - start_time))
