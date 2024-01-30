#!/usr/bin/env python -*- coding: utf-8 -*-
import gc
import gzip
import hashlib
import requests
import codecs
import os
import json
import re
import shutil
from datetime import datetime
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
EPG_ALL_FILE = 'epg-all.xml'
M3U_CACHE_FILE_PATH = CACHE_FOLDER + M3U_FILE
M3U_GZ_CACHE_FILE_PATH = CACHE_FOLDER + M3U_FILE + '.gz'
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


def get_header_time(logger, header_time):
    formats = ['%a, %d %b %Y %H:%M:%S %Z', '%a %d %b %Y %H:%M:%S']
    for item in formats:
        try:
            return datetime.strptime(header_time, item)
        except:
            pass
    return None


def md5_file(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def md5_string(string):
    hash_md5 = hashlib.md5()
    hash_md5.update(string)
    return hash_md5.hexdigest()


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
    except Exception as e:
        logger.error('ERROR in download_epg(%s) %s' % (url, e))
    logger.info("download_epg(%s), xml size: %s, time: %sms" % (
    url, sizeof_fmt(os.path.getsize(file_name)), time.time() - start_time))


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
    logger.info('parse_m3u(%s), returning valid m3u_entries: %d' % (file_name, len(m3u_entries)))
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


def is_channel_present_in_m3u(channel_item, m3u_entries):
    # if channel_item.id == '4770':
    #     print('!')
    return_value = False
    list = channel_item.display_name_list
    list_to_remove = []
    for value in m3u_entries:
        value_no_orig = None
        if ' orig' in value.name or ' Orig' in value.name:
            value_no_orig = value.name.replace(' orig', '').replace(' Orig', '')

        # value_no_fhd = None
        # if ' FHD' in value.name:
        #     value_no_fhd = value.name.replace(' FHD', ' HD')
        #
        # value_no_ua = None
        # if ' UA' in value.name:
        #     value_no_ua = value.name.replace(' UA', '')
        #
        # value_no_uk = None
        # if ' Anglia' in value.name:
        #     value_no_uk = value.name.replace(' Anglia', ' UK')

        for display_name in list:
            # if 'BACKUS TV HD' in value.name and 'BACKUS TV HD' in display_name.text:
            #     print('!')
            if value_no_orig is not None and compare(display_name.text, value_no_orig):
                insert_value_if_needed(list, value.name)
                list_to_remove.append(value)
                return_value = True
                break

            # if value_no_fhd is not None and compare(display_name.text, value_no_fhd):
            #     insert_value_if_needed(list, value.name)
            #     return_value = True
            #     break
            #
            # if value_no_ua is not None and compare(display_name.text, value_no_ua):
            #     insert_value_if_needed(list, value.name)
            #     return_value = True
            #     break
            #
            # if value_no_uk is not None and compare(display_name.text, value_no_uk):
            #     insert_value_if_needed(list, value.name)
            #     return_value = True
            #     break

            if compare(display_name.text, value.name) or compare(display_name.text, value.tvg_name):
                list_to_remove.append(value)
                return_value = True
                break

    for value in list_to_remove:
        m3u_entries.remove(value)

    return return_value


def insert_value_if_needed(list, value_to_insert):
    for value in list:
        if value.text == value_to_insert:
            return False

    list.append(NameItem(value_to_insert))
    return True


def add_custom_entries(channel_item):
    if channel_item.id == 'ITV1Anglia.uk':
        channel_item.display_name_list.append(NameItem('itv 1 HD'))
    if channel_item.id == 'ITV2.uk':
        channel_item.display_name_list.append(NameItem('itv 2 HD'))
    if channel_item.id == 'ITV4.uk':
        channel_item.display_name_list.append(NameItem('itv 4'))
    if channel_item.id == 'ITV4Plus1.uk':
        channel_item.display_name_list.append(NameItem('itv 4 +1'))
    if channel_item.id == 'ITV3Plus1.uk':
        channel_item.display_name_list.append(NameItem('itv 3 +1'))
    if channel_item.id == 'ITVBe.uk':
        channel_item.display_name_list.append(NameItem('itv BE'))
    if channel_item.id == '1598':
        channel_item.display_name_list.append(NameItem('Че!'))
    if channel_item.id == '5kanal-ru-pl4':
        channel_item.display_name_list.append(NameItem('5 канал +4'))
    pass


def load_xmlt(logger, m3u_entries, epg_file, channel_list, programme_list):
    logger.info("load_xmlt(%s), m3u_entries count: %d" % (epg_file, len(m3u_entries)))
    start_time = time.time()

    for event, element in ET.iterparse(epg_file, tag=('channel', 'programme'), huge_tree=True):
        if element.tag == 'channel':
            channel_item = ChannelItem(element)
            add_custom_entries(channel_item)

            # value = is_channel_present_in_list_by_name(channel_list, channel_item)
            channel_present = is_channel_present_in_m3u(channel_item, m3u_entries)
            if channel_present:
                channel_list.append(channel_item)
                # logger.info('load_xmlt(%s), channel_list size: %d' % (epg_file, len(channel_list)))

        if element.tag == 'programme':
            if is_channel_present_in_list_by_id(channel_list, element.attrib['channel']):
                program_item = ProgrammeItem(element)
                programme_list.append(program_item)
                # logger.info('load_xmlt(%s), programme_list size: %d' % (epg_file, len(programme_list)))

        element.clear()

    logger.info('load_xmlt(%s), channel_list size: %d, programme_list: %d, time: %sms ' % (epg_file, len(channel_list), len(programme_list), time.time() - start_time))
    gc.collect()


def write_xml_plain_text(logger, channel_list, programme_list, request_host):
    logger.info('write_xml_plain_text()')

    if os.path.exists(EPG_ALL_CACHE_FILE_PATH):
        logger.info("write_xml_plain_text() remove existing file, %s" % EPG_ALL_CACHE_FILE_PATH)
        os.remove(EPG_ALL_CACHE_FILE_PATH)

    f = open(EPG_ALL_CACHE_FILE_PATH, 'w')
    f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    f.write("<!DOCTYPE tv SYSTEM \"http://{url}/xmltv.dtd\">\n".format(url=request_host))
    f.write("<tv generator-info-name=\"iptv-helper\" generator-info-url=\"https://github.com/Redwid/iptv-helper\">\n")

    logger.info('write_xml_plain_text() prepare channels list')
    try:
        for channel_item in channel_list:
            f.write(channel_item.to_xml_string())
        logger.info('write_xml_plain_text() channel_list size: %d' % len(channel_list))
    except Exception as e:
        logger.error('ERROR in prepare programme in write_xml()', exc_info=True)

    logger.info('write_xml() prepare programme_list')
    try:
        for programme in programme_list:
            f.write(programme.to_xml_string())
        logger.info('write_xml_plain_text() programme_list size: %d' % len(programme_list))
    except Exception as e:
        logger.error('ERROR in prepare programme in write_xml()', exc_info=True)

    f.write("</tv>\n")
    f.flush()
    f.close()

    file_size = os.path.getsize(EPG_ALL_CACHE_FILE_PATH)
    logger.info("write_xml_plain_text(%s) done, file size: %s (%s)" % (EPG_ALL_CACHE_FILE_PATH, file_size, sizeof_fmt(file_size)))

    gzip_file(EPG_ALL_CACHE_FILE_PATH, EPG_ALL_GZ_CACHE_FILE_PATH)

    file_size = os.path.getsize(EPG_ALL_GZ_CACHE_FILE_PATH)
    logger.info("write_xml_plain_text(%s) done, file size: %s (%s)" % (EPG_ALL_GZ_CACHE_FILE_PATH, file_size, sizeof_fmt(file_size)))

    return EPG_ALL_CACHE_FILE_PATH


def gzip_file(source_file, gz_file):
    with open(source_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def process_not_present_m3u_entries(not_present_m3u_entries, channel_list):
    for value in not_present_m3u_entries:
        # If channel name in m3u has 'orig' term lets search without a term and update
        if ' orig' in value.name:
            name = value.name.replace(' orig', '')
            for channel in channel_list:
                for display_name in channel.display_name_list:
                    if compare(display_name.text, name):
                        list.append(NameItem(value.name))


def num_sort(test_string):
    return list(map(int, re.findall(r'\d+', test_string)))[0]


def filter_epg(logger, request_host):
    logger.info("filter_epg(), request_host: %s" % request_host)
    start_time = time.time()
    m3u_entries = parse_m3u(logger, M3U_CACHE_FILE_PATH)

    channel_list = []
    programme_list = []
    downloaded = glob.glob(CACHE_FOLDER + 'epg-*.xml')
    if EPG_ALL_CACHE_FILE_PATH in downloaded:
        downloaded.remove(EPG_ALL_CACHE_FILE_PATH)
    downloaded = sorted(downloaded, key=num_sort)
    # downloaded = [CACHE_FOLDER + 'epg-1.xml']

    for file in downloaded:
        if EPG_ALL_FILE not in file:
            try:
                load_xmlt(logger, m3u_entries, file, channel_list, programme_list)
            except Exception as e:
                logger.error('filter_epg(), unexpected exception: %s' % repr(e))

    logger.info('filter_epg(), m3u_entries: %d channel_list size: %d, programme_list: %d, time: %sms ' % (
    len(m3u_entries), len(channel_list), len(programme_list), time.time() - start_time))

    logger.info("filter_epg(), Not preset (count %d):" % len(m3u_entries))
    index = 0
    for value in m3u_entries:
        logger.info("   %d. %s" % (index, value))
        index += 1

    file_path = write_xml_plain_text(logger, channel_list, programme_list, request_host)
    logger.info("filter_epg(), file_path: %s, done in: %s" % (file_path, time.time() - start_time))
