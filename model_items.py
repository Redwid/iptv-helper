#!/usr/bin/env python -*- coding: utf-8 -*-
import re
from datetime import datetime

# import xml.etree.ElementTree as ET
from lxml import etree as ET

# all_categories = []

date_format = '%Y%m%d%H%M%S %z'


class M3uItem:
    def __init__(self, m3u_fields):
        self.tvg_name = None
        self.tvg_id = None
        self.tvg_logo = None
        self.group_title = None
        self.name = None
        self.name_no_orig = None
        self.url = None
        self.group_idx = 0
        self.channel_idx = -1
        self.tvg_rec = -1
        self.channels = {}
        self.max_programs = None

        if m3u_fields is not None:
            try:
                self.tvg_name = re.search('tvg-name="(.*?)"', m3u_fields, re.IGNORECASE).group(1)
            except AttributeError as e:
                pass
            try:
                self.tvg_id = re.search('tvg-id="(.*?)"', m3u_fields, re.IGNORECASE).group(1)
            except:
                pass
            try:
                self.tvg_logo = re.search('tvg-logo="(.*?)"', m3u_fields, re.IGNORECASE).group(1)
            except AttributeError as e:
                pass
            try:
                self.group_title = re.search('group-title="(.*?)"', m3u_fields, re.IGNORECASE).group(1)
            except AttributeError as e:
                pass
            try:
                self.tvg_rec = re.search('tvg-rec="(.*?)"', m3u_fields, re.IGNORECASE).group(1)
            except AttributeError as e:
                pass
            try:
                index = m3u_fields.find(',')
                if index != -1:
                    self.name = m3u_fields[index + 1:]
                    if ' orig' in self.name or ' Orig' in self.name:
                        self.name_no_orig = self.name.replace(' Original', '').replace(' original', '').replace(' Orig', '').replace(' orig', '')
            except AttributeError as e:
                pass

    def is_valid(self):
        is_valid = self.name is not None and self.name != "" and \
                   self.group_title is not None and self.group_title != "" and \
                   self.url is not None and self.url != ""
        return is_valid

    def get_string(self, string):
        if string is None:
            return ""
        return string

    def process(self, channel_item):
        if channel_item in self.channels:
            return True

        for display_name in channel_item.display_name_list:

            if self.name_no_orig is not None and self.compare(display_name.text, self.name_no_orig):
                self.channels[channel_item.id] = channel_item
                insert_value_if_needed(channel_item.display_name_list, self.name)
                return True

            if self.compare(display_name.text, self.name) or self.compare(display_name.text, self.tvg_name):
                self.channels[channel_item.id] = channel_item
                return True

        return False

    def compare(self, string1, string2):
        if string1 is None or string2 is None:
            return False

        if string1 == string2 or string1.lower() == string2.lower():
            return True

        return False

    def get_logo(self):
        if self.tvg_logo is not None or self.tvg_logo != "":
            return self.tvg_logo
        for key, value in self.channels.items():
            if value.icon is not None or value.icon != "":
                return value.icon
        return None

    def to_m3u_string(self):
        logo = self.get_logo()

        tvg_id = self.get_tvg_id()

        result = "#EXTINF:-1"
        if tvg_id is not None:
            result += " tvg-id=\"{tvg_id}\"".format(tvg_id=tvg_id)

        if logo is not None:
            result += " tvg-logo=\"{tvg_logo}\"".format(tvg_logo=logo)

        if tvg_id is None and logo is None:
            result += " tvg-rec=\"0\""

        result += ",{name}\n" \
                  "#EXTGRP:{tvg_group}\n" \
                  "{url}\n".format(name=self.name, tvg_group=self.group_title, url=self.url)
        return result

    def get_tvg_id(self):
        tvg_id = self.tvg_id
        if tvg_id is None:
            max_programs = self.get_max_programs()
            if max_programs is not None:
                tvg_id = max_programs.id
        return tvg_id

    def get_programs_count(self):
        count = 0
        for key, value in self.channels.items():
            # print("key: %s, value: %s" % (key, value))
            count += value.get_programs_count()
        return count

    def get_all_programs_count(self):
        count = 0
        for key, value in self.channels.items():
            # print("key: %s, value: %s" % (key, value))
            count += len(value.programs)
        return count

    def add_channels_and_programs(self, channels: list, programs: list):
        max_programs = self.get_max_programs()

        if max_programs is not None:
            channels.append(max_programs)
            programs.extend(max_programs.programs)

    def get_max_programs(self):
        if self.max_programs is None:
            for key, value in self.channels.items():
                len_programs = value.get_programs_count()
                if self.max_programs is None:
                    self.max_programs = value
                elif len_programs > 0 and len_programs > self.max_programs.get_programs_count():
                    self.max_programs = value
        return self.max_programs

    def __str__(self):
        return 'M3uItem[name:' + self.get_string(self.name) + ', group_title:' + self.get_string(self.group_title) + \
               ', tvg_name:' + self.get_string(self.tvg_name) + ', tvg_id:' + self.get_string(self.get_tvg_id()) + \
               ', tvg_logo:' + self.get_string(self.tvg_logo) + ', channels:' + str(len(self.channels)) + \
               ', programs: ' + str(self.get_programs_count()) + ' (all:' + str(self.get_all_programs_count()) + ')]'


class ChannelItem:
    def __init__(self, xmlt_fields):
        self.id = None
        self.text = None
        self.icon = None
        self.display_name_list = []
        self.programs = []
        self.id = xmlt_fields.attrib['id']

        for child in xmlt_fields:
            if child.tag == 'display-name':
                display_name = NameItem(None, None, child)
                if display_name.text is not None:
                    self.display_name_list.append(display_name)

            else:
                if child.tag == 'icon':
                    if 'src' in child.attrib:
                        self.icon = child.attrib['src']
                    if 'text' in child.attrib:
                        self.icon = child.attrib['text']

    def to_et_sub_element(self, root):
        item = ET.SubElement(root, 'channel', id=self.id)
        display_name_list = self.display_name_list
        for display_name in display_name_list:
            add_sub_element('display-name', display_name, item)
        if self.icon is not None:
            ET.SubElement(item, 'icon').text = self.icon

    def to_xml_string(self):
        result = "\t<channel id=\"{id}\">\n".format(id=self.id)
        for display_name in self.display_name_list:
            if display_name.lang is None:
                result += "\t\t<display-name>{name}</display-name>\n".format(name=xml_escape(display_name.text))
            else:
                result += "\t\t<display-name lang=\"{lang}\">{name}</display-name>\n".format(name=xml_escape(display_name.text), lang=xml_escape(display_name.lang))

        if self.icon is not None:
            result += "\t\t<icon src=\"{url}\"/>\n".format(url=xml_escape(self.icon))

        result += "\t</channel>\n"
        return result

    def get_display_name(self):
        for display_name in self.display_name_list:
            return display_name
        return ''

    def add_program(self, program):
        self.programs.append(program)

    def get_programs_count(self):
        count = 0
        for program in self.programs:
            if not program.is_in_the_past:
                count += 1
        return count

    def __str__(self):
        return 'ChannelItem[id:' + str(self.id) + ', text:' + str(self.text) + \
               ', display_name_list:' + ', '.join(map(str, self.display_name_list)) + ', icon:' + str(self.icon) + \
               ', programs:' + str(len(self.programs)) +']'


class NameItem:
    def __init__(self, text, lang=None, xmlt_fields=None):
        self.lang = lang
        self.text = text
        if xmlt_fields is not None and xmlt_fields.text is not None:
            self.text = xmlt_fields.text.strip()
            if 'lang' in xmlt_fields.attrib:
                self.lang = xmlt_fields.attrib['lang']

    def __str__(self):
        return 'NameItem[lang:' + self.lang + ', text:' + self.text + ']'


class ProgrammeItem:
    def __init__(self, logger, today, today_plus_one_week, xmlt_fields):
        self.start = xmlt_fields.attrib['start']
        self.stop = xmlt_fields.attrib['stop']
        self.channel = xmlt_fields.attrib['channel']
        self.is_in_the_past = False
        self.is_in_the_future_one_week = False

        try:
            self.start_date = datetime.strptime(self.start, date_format).date()
            self.is_in_the_future_one_week = self.start_date is not None and today_plus_one_week is not None and self.start_date > today_plus_one_week
        except Exception as error:
            logger.error("Error in ProgrammeItem, can't parse start: %s, error: %s" % (self.start, error))
            self.start_date = None
        try:
            self.stop_date = datetime.strptime(self.stop, date_format).date()
            self.is_in_the_past = self.stop_date is not None and today is not None and today > self.stop_date
        except Exception as error:
            logger.error("Error in ProgrammeItem, can't parse stop: %s, error: %s" % (self.stop, error))
            self.stop_date = None

        self.title_list = []
        self.desc_list = []
        self.category_list = []
        for child in xmlt_fields:
            if child.tag == 'title':
                title = NameItem(None, None, child)
                self.title_list.append(title)
            else:
                if child.tag == 'desc':
                    desc = NameItem(None, None, child)
                    self.desc_list.append(desc)
                else:
                    if child.tag == 'category':
                        category = NameItem(None, None, child)
                        self.category_list.append(category)

    def to_et_sub_element(self, root):
        item = ET.SubElement(root, 'programme', start=self.start, stop=self.stop,
                             channel=self.channel)
        for title in self.title_list:
            add_sub_element('title', title, item)
        for descs in self.desc_list:
            add_sub_element('desc', descs, item)
        for category in self.category_list:
            add_sub_element('category', category, item)

    def to_xml_string(self, dates: dict):
        if self.is_in_the_past:
            dates['is_in_the_past.count'] += 1
            return None

        if self.is_in_the_future_one_week:
            dates['is_in_the_future_one_week.count'] += 1
            return None

        if dates['start.oldest'] is None or (self.start_date is not None and self.start_date < dates['start.oldest']):
            dates['start.oldest'] = self.start_date
            dates['start.oldest.str'] = self.start

        if dates['start.newest'] is None or (self.start_date is not None and self.start_date > dates['start.newest']):
            dates['start.newest'] = self.start_date
            dates['start.newest.str'] = self.start

        if dates['stop.oldest'] is None or (self.stop_date is not None and self.stop_date < dates['stop.oldest']):
            dates['stop.oldest'] = self.stop_date
            dates['stop.oldest.str'] = self.stop

        if dates['stop.newest'] is None or (self.stop_date is not None and self.stop_date > dates['stop.newest']):
            dates['stop.newest'] = self.stop_date
            dates['stop.newest.str'] = self.stop

        result = "\t<programme start=\"{start}\" stop=\"{stop}\" channel=\"{id}\">\n".format(start=self.start, stop=self.stop, id=self.channel)
        for category in self.category_list:
            # if category.text not in all_categories:
            #     all_categories.append(category.text)
            #     print("category: " + category.text)
            if category.lang is None:
                result += "\t\t<category>{name}</category>\n".format(name=xml_escape(category.text))
            else:
                result += "\t\t<category lang=\"{lang}\">{name}</category>\n".format(name=xml_escape(category.text), lang=category.lang)

        for title in self.title_list:
            if title.lang is None:
                result += "\t\t<title>{name}</title>\n".format(name=xml_escape(title.text))
            else:
                result += "\t\t<title lang=\"{lang}\">{name}</title>\n".format(name=xml_escape(title.text), lang=title.lang)

        for desc in self.desc_list:
            if desc.lang is None:
                result += "\t\t<desc>{name}</desc>\n".format(name=xml_escape(desc.text))
            else:
                result += "\t\t<desc lang=\"{lang}\">{name}</desc>\n".format(name=xml_escape(desc.text), lang=desc.lang)

        result += "\t</programme>\n"
        return result


def add_sub_element(name, item, root):
    if item.lang is not None:
        ET.SubElement(root, name, lang=item.lang).text = item.text
    else:
        ET.SubElement(root, name).text = item.text


def xml_escape(str_xml: str):
    str_xml = str_xml.replace("&", "&amp;")
    str_xml = str_xml.replace("<", "&lt;")
    str_xml = str_xml.replace(">", "&gt;")
    str_xml = str_xml.replace("\"", "&quot;")
    str_xml = str_xml.replace("'", "&apos;")
    return str_xml


def insert_value_if_needed(list, value_to_insert):
    for value in list:
        if value.text == value_to_insert:
            return False

    list.append(NameItem(value_to_insert))
    return True


