# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field


class WeiboItem(scrapy.Item):
    table_name = 'weibo'

    id = Field()
    url = Field()
    content = Field()
    comment_count = Field()
    forward_count = Field()
    like_count = Field()
    posted_at = Field()
    user = Field()
    pass
