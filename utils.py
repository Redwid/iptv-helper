#!/usr/bin/env python -*- coding: utf-8 -*-
import gc
import gzip
import hashlib
import logging, requests
import codecs
import os
import json
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
CACHE_FOLDER = '.cache/'

M3U_FILE = 'm3u.m3u'
EPG_ALL_FILE = 'epg-all.xml'
M3U_CACHE_FILE_PATH = CACHE_FOLDER + M3U_FILE
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

    get_response = requests.get(url, headers=headers, verify=False, stream=False, timeout=(5,30))
    logger.info("download_file(%s), response: %s" % (url, get_response))
    if get_response.status_code == 304:
        logger.info("download_file(%s) ignore as file 'Not Modified'" % url)
        return file_name_no_gz

    store_last_modified_data(logger, etag_file_name, get_response.headers)

    logger.info("download_file(%s) downloading file_name: %s" % (url, file_name))
    with open(file_name, 'wb') as f:
        for chunk in get_response.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
    logger.info("download_file(%s) done: %s, file size: %d" % (url, file_name, os.path.getsize(file_name)))
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

    data = {'etag': str(headers.get('ETag')), 'last_modified' : str(headers.get('Last-Modified'))}
    logger.info("store_last_modified_data(), data: %s" % (str(data)))
    with codecs.open(file_name, 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(data))


def get_header_time(logger, header_time):
    formats = ['%a, %d %b %Y %H:%M:%S %Z', '%a %d %b %Y %H:%M:%S']
    for item in formats:
        try:
            return datetime.strptime(header_time, item)
        except: pass
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
    logger.info("download_epg(%s), xml size: %s, time: %sms" % (url, sizeof_fmt(os.path.getsize(file_name)), time.time() - start_time))


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
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
    # if channel_item.id == 'tnt' and channel_item.id != 'rentv-int':
    #     print('!')
    return_value = False
    list = channel_item.display_name_list
    for value in m3u_entries:
        value_no_orig = None
        if ' orig' in value.name or ' Orig' in value.name:
            value_no_orig = value.name.replace(' orig', '').replace(' Orig', '')

        value_no_fhd = None
        if ' FHD' in value.name:
            value_no_fhd = value.name.replace(' FHD', ' HD')

        value_no_ua = None
        if ' UA' in value.name:
            value_no_ua = value.name.replace(' UA', '')

        for display_name in list:
            # if 'Рен ТВ' in value.name and 'Рен ТВ' in display_name.text:
            #      print('!')
            if value_no_orig is not None and compare(display_name.text, value_no_orig):
                insert_value_if_needed(list, value.name)
                return_value = True
                break

            if value_no_fhd is not None and compare(display_name.text, value_no_fhd):
                insert_value_if_needed(list, value.name)
                return_value = True
                break

            if value_no_ua is not None and compare(display_name.text, value_no_ua):
                insert_value_if_needed(list, value.name)
                return_value = True
                break

            if compare(display_name.text, value.name) or compare(display_name.text, value.tvg_name):
                return_value = True

    return return_value


def insert_value_if_needed(list, value_to_insert):
    for value in list:
        if value.text == value_to_insert:
            return False

    list.append(NameItem(value_to_insert))
    return True


def load_xmlt(logger, m3u_entries, epg_file, channel_list, programme_list):
    logger.info("load_xmlt(%s)" % epg_file)
    start_time = time.time()

    for event, element in ET.iterparse(epg_file, tag=('channel', 'programme'), huge_tree=True):
        if element.tag == 'channel':
            channel_item = ChannelItem(element)
            # add_custom_entries(channel_item)

            value = is_channel_present_in_list_by_name(channel_list, channel_item)
            channel_in_m3u = is_channel_present_in_m3u(channel_item, m3u_entries)
            if value is None and channel_in_m3u:
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


def write_xml_plain_text(logger, channel_list, programme_list):
    logger.info('write_xml_plain_text()')

    if os.path.exists(EPG_ALL_CACHE_FILE_PATH):
        logger.info("write_xml_plain_text() remove existing file, %s" % EPG_ALL_CACHE_FILE_PATH)
        os.remove(EPG_ALL_CACHE_FILE_PATH)

    f = open(EPG_ALL_CACHE_FILE_PATH, 'w')
    f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    f.write("<tv>\n")

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

    with open(EPG_ALL_CACHE_FILE_PATH, 'rb') as f_in:
        with gzip.open(EPG_ALL_GZ_CACHE_FILE_PATH, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    file_size = os.path.getsize(EPG_ALL_GZ_CACHE_FILE_PATH)
    logger.info("write_xml_plain_text(%s) done, file size: %s (%s)" % (EPG_ALL_GZ_CACHE_FILE_PATH, file_size, sizeof_fmt(file_size)))

    return EPG_ALL_CACHE_FILE_PATH


def write_xml(logger, channel_list, programme_list):
    logger.info('write_xml()')

    if os.path.exists(EPG_ALL_CACHE_FILE_PATH):
        logger.info("write_xml() remove existing file, %s" % EPG_ALL_CACHE_FILE_PATH)
        os.remove(EPG_ALL_CACHE_FILE_PATH)

    tv = ET.Element('tv')

    logger.info('write_xml() prepare channels list')
    try:
        for channel_item in channel_list:
            channel_item.to_et_sub_element(tv)
        logger.info('write_xml() channel_list size: %d' % len(channel_list))
    except Exception as e:
        logger.error('ERROR in prepare programme in write_xml()', exc_info=True)

    logger.info('write_xml() prepare programme_list')
    try:
        for programme in programme_list:
            programme.to_et_sub_element(tv)
        logger.info('write_xml() programme_list size: %d' % len(programme_list))
    except Exception as e:
        logger.error('ERROR in prepare programme in write_xml()', exc_info=True)

    try:
        tree = ET.ElementTree(tv)
        tree.write(EPG_ALL_CACHE_FILE_PATH, encoding='utf-8', xml_declaration=True, pretty_print=True)
    except Exception as e:
        logger.error('ERROR in write all in write_xml()', exc_info=True)

    file_size = os.path.getsize(EPG_ALL_CACHE_FILE_PATH)
    logger.info("write_xml(%s) done, file size: %s (%s)" % (EPG_ALL_CACHE_FILE_PATH, file_size, sizeof_fmt(file_size)))
    return EPG_ALL_CACHE_FILE_PATH


def process_not_present_m3u_entries(not_present_m3u_entries, channel_list):
    for value in not_present_m3u_entries:
        # If channel name in m3u has 'orig' term lets search without a term and update
        if ' orig' in value.name:
            name = value.name.replace(' orig', '')
            for channel in channel_list:
                for display_name in channel.display_name_list:
                    if compare(display_name.text, name):
                        list.append(NameItem(value.name))


def filter_epg(logger):
    logger.info("filter_epg()")
    start_time = time.time()
    m3u_entries = parse_m3u(logger, M3U_CACHE_FILE_PATH)

    channel_list = []
    programme_list = []
    downloaded = sorted(glob.glob(CACHE_FOLDER + 'epg-*.xml'), key=os.path.getmtime)
    #downloaded = [CACHE_FOLDER + 'epg-1.xml']

    for file in downloaded:
        if EPG_ALL_FILE not in file:
            try:
                load_xmlt(logger, m3u_entries, file, channel_list, programme_list)
            except Exception as e:
                logger.error('filter_epg(), unexpected exception: %s' % repr(e))

    logger.info('filter_epg(), m3u_entries: %d channel_list size: %d, programme_list: %d, time: %sms ' % (len(m3u_entries), len(channel_list), len(programme_list), time.time() - start_time))

    logger.info("filter_epg(), Not preset:")
    not_present_m3u_entries = []
    for value in m3u_entries:
        # if 'Paramount Сhannel HD' == value.tvg_name:
        #     print('!')
        found = False
        for channel in channel_list:
            found = False
            display_name_list = channel.display_name_list
            for display_name in display_name_list:
                if compare(display_name.text, value.name) or compare(display_name.text, value.tvg_name):
                    found = True
                    break
            if found:
                break
        if not found:
            logger.info("            %s" % value)
            not_present_m3u_entries.append(value)
    logger.info("filter_epg(), Not preset, counter: %d" % len(not_present_m3u_entries))

    # process_not_present_m3u_entries(not_present_m3u_entries, channel_list)

    file_path = write_xml_plain_text(logger, channel_list, programme_list)
    logger.info("filter_epg(), file_path: %s, done in: %s" % (file_path, time.time() - start_time))
