#!/usr/bin/env python -*- coding: utf-8 -*-
import re
# import xml.etree.ElementTree as ET
from lxml import etree as ET


class M3uItem:
    def __init__(self, m3u_fields):
        self.tvg_name = None
        self.tvg_id = None
        self.tvg_logo = None
        self.group_title = None
        self.name = None
        self.url = None
        self.group_idx = 0
        self.channel_idx = -1
        self.tvg_rec = -1

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

    def __str__(self):
        return 'M3uItem[name:' + self.get_string(self.name) + ', group_title:' + self.get_string(self.group_title) + \
               ', tvg_name:' + self.get_string(self.tvg_name) + ', tvg_id:' + self.get_string(self.tvg_id) + \
               ', tvg_logo:' + self.get_string(self.tvg_logo) + ']'


class ChannelItem:
    def __init__(self, xmlt_fields):
        self.id = None
        self.text = None
        self.icon = None
        self.display_name_list = []

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

    def __str__(self):
        return 'ChannelItem[id:' + str(self.id) + ', text:' + self.text + \
               ', display_name_list:' + ', '.join(map(str, self.display_name_list)) + ', icon:' + self.icon + ']'


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
    def __init__(self, xmlt_fields):
        self.start = xmlt_fields.attrib['start']
        self.stop = xmlt_fields.attrib['stop']
        self.channel = xmlt_fields.attrib['channel']

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

    def to_xml_string(self):
        result = "\t<programme start=\"{start}\" stop=\"{stop}\" channel=\"{id}\">\n".format(start=self.start, stop=self.stop, id=self.channel)
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

