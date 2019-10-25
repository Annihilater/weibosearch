# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import re
import time

import pymongo
import logging

from weibosearch.items import WeiboItem


class WeiboPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, WeiboItem):
            if item.get('content'):
                item['content'] = item['content'].lstrip(':').strip()
            if item.get('posted_at'):
                item['posted_at'] = item['posted_at'].strip()
                item['posted_at'] = self.parse_time(item['posted_at'])
        return item

    @staticmethod
    def parse_time(datetime):
        """
        datetime 格式为以下三宗
        1. 1分钟前
        2. 今天 10:43
        3. 10月24日17:41
        :param datetime:
        :return:2019年10月25日 16:00
        """
        if re.match('\d+月\d+日', datetime):  # 10月24日17:41
            datetime = time.strftime('%年', time.localtime()) + datetime
        if re.match('\d+分钟前', datetime):  # 1分钟前
            minute = re.match('(\d+)', datetime).group(1)
            datetime = time.strftime('%Y年%m月%d日 %H:%M', time.localtime(time.time() - float(minute) * 60))
        if re.match('今天.*', datetime):  # 今天 10:43
            datetime = re.match('今天(.*)', datetime).group(1).strip()
            datetime = time.strftime('%Y年%m月%日 %H:%M', time.localtime()) + ' ' + datetime
        return datetime


class MongoPipeline(object):
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_uri=crawler.settings.get('MONGO_URI'),
                   mongo_db=crawler.settings.get('MONGODB', 'items'))

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[item.table_name].update_one({'id': item.get('id')}, {'$set': dict(item)}, True)
