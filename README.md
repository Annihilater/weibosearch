# Scrapy + Cookies 池抓取新浪微博

## 目标

1. 抓取微博搜索结果页面
2. 抓取微博搜索结果页面的每条微博全文



## 切换 cookies 获取数据

使用 `CookiesPool`项目的 API 获取 `Cookies`发起请求获取数据。

 

## 数据提取

数据提取使用的是 Scrapy xpath。

微博的 id 都是在 url 内的，例如：

```python
https://weibo.cn/comment/Id0IW0Pqq?xxxxxxxxxxx
```

可以使用正则表达式匹配出来：

```python
id = re.search('comment\/(.*?)\?', response.url).group(1)
```



### 提取元素文本

```python
content = response.xpath('.//div[@class="c" and @id="M_"]//span[@class="ctt"]//text()').extract_first()
```

`.//div`：选择所以 `div节点`

`.//div[@class="c" and @id="M_"]`：选择这样的节点 `<div class="c" id="M_">...</div>`

`.//div[@class="c" and @id="M_"]//span`：选择上述 `div节点的` `span`子节点

`//span[@class="ctt"]`：选择带有 `class="ctt”`属性的 `span`节点

`//text()`：选择元素的文本

### 提取元素属性的值

比如提取 `a`标签的 `href`属性（就是提取链接）

```python
detail_url = weibo.xpath('.//a[contains(., "原文评论")]//@href').extract_first()
```

`//a`：选择所有 `a标签`

`//a[contains(., "原文评论")]`：选择文本中具有 `"原文评论”`四个字的 `a 标签`

`//@href`：提取元素 `href`属性的值



### extract

`extract()`方法返回的是一个列表，往往我们需要将整个列表字段连接在一起存起来：

```python
''.join([..., ..., ...])
```



### 正则表达式匹配

使用正则表达式获取评论数

```python
comment_count = response.xpath('//span[@class="pms"]//text()').re_first('评论\[(.*?)\]')
```

`//span[@class="pms"]`：匹配带有 `class="pms"`的 `span`标签

`//text()`：获取标签文本

`.re_first()`：使用正则表达式匹配

`'评论\[(.*?)\]'`：正则表达式匹配 `&nbsp;评论[21]&nbsp;` 中的数字 21



使用正则表达式获取转发数

```python
forward_count = response.xpath('.//a[contains(., "转发")]//text()').re_first('转发\[(.*?)\]')
```



### xpath获取顺序获取标签

获取用户昵称，用户昵称在微博正文的第一个 `div`的第一个 `a`标签内

```python
user = response.xpath('//div[@id="M_"]/div[1]/a[1]//text()').extract_first(default=None)
```

顺序获取`div`标签下的第 1 个 `a`标签：

```javascript
div/a[1]
```

顺序获取`div`标签下的第 2 个 `a`标签：

```javascript
div/a[2]
```



## Item 动态赋值

定义的 `WeiboItem`：

```python
class WeiboItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    id = Field()
    url = Field()
    content = Field()
    comment_count = Field()
    forward_count = Field()
    like_count = Field()
    posted_at = Field()
    user = Field()
```

解析函数 `parse_detail`：

```python
    def parse_detail(self, response):
        id = re.search('comment\/(.*?)\?', response.url).group(1)
        url = response.url
        content = ''.join(response.xpath('.//div[@class="c" and @id="M_"]//span[@class="ctt"]//text()').extract_first())
        comment_count = response.xpath('//span[@class="pms"]//text()').re_first('评论\[(.*?)\]')
        forward_count = response.xpath('.//a[contains(., "转发")]//text()').re_first('转发\[(.*?)\]')
        like_count = response.xpath('.//a[contains(., "赞")]').re_first('赞\[(.*?)\]')
        posted_at = response.xpath('//div[@id="M_"]//span[@class="ct"]//text()').extract_first(default=None)
        user = response.xpath('//div[@id="M_"]/div[1]/a[1]//text()').extract_first(default=None)

        weibo_item = WeiboItem()
        for field in weibo_item.fields:
          try:
            weibo_item[field] = eval(field)
          except NameError:
            self.logger.debug('Field is not Defined' + field)
        yield weibo_item
```

首先遍历 `weiboitem`的字段，因为`weiboitem`的字段和解析出来的字段时相同的，**可以使用 `eval()`函数动态的从字符串获取变量**。这个技巧很方便。

最后使用 `try except`捕捉一些未定义字段出现的异常，使用 debug 信息提示出来。 



## 数据存入 MongoDB

官方给出的模板，改动的地方只有 `update_one()`。

```python
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
```



## 处理 Response

微博的反爬虫是非常厉害的，爬的时候可能会跳转到封号的页面里面去，那么就需要在中间件里面另外的加一些判断。我们在 cookies 中间件里加一个处理相应的方法 `process_response`，这样的话就可以对所有的响应做一些处理了。



接下来就需要判断响应的状态码：

1. 如果遇到的是 300 之类的跳转的话，可能是因为 cookies 是失效的，可能会帮我们跳转到登录页面之类的，日志输出提醒
2. 如果被封号了，日志输出封号提醒
3. 如果遇到 414 状态码，则表示请求 url 过长

返回 Request，重新进行请求。