#!/usr/bin/env python -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name):
    format_string = '%(asctime)s: %(name)s: %(threadName)s - %(levelname)s - %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=format_string)
    logger = logging.getLogger(name)
    try:
        handler = RotatingFileHandler('log/{}.log'.format(name), maxBytes=1048576, backupCount=3)
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except PermissionError:
        logger.error('PermissionError in init logger ', exc_info=True)
    except FileNotFoundError:
        logger.error('FileNotFoundError in init logger ', exc_info=True)
    return logger
