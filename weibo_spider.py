#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2019/10/24 18:14
# @Author: yanmiexingkong
# @email : yanmiexingkong@gmail.com
# @File  : weibo_spider.py

from scrapy import cmdline

cmdline.execute('scrapy crawl weibo'.split())
