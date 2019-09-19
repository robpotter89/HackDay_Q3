#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import csv
import json
import os
import re
import time
import zlib
from datetime import datetime, timedelta
from io import BytesIO, TextIOWrapper
from urllib.parse import urlsplit
from zipfile import ZipFile

import requests
from pymongo import MongoClient
from redis import StrictRedis

import mongoengine

from .settings_handler import MongoSettings, settings


class AlexaCallback:
    def __init__(self, max_urls=500):
        self.max_urls = max_urls
        self.seed_url = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
        self.urls = []

    def __call__(self):
        resp = requests.get(self.seed_url, stream=True)
        with ZipFile(BytesIO(resp.content)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as csv_file:
                for _, website in csv.reader(TextIOWrapper(csv_file)):
                    self.urls.append('http://' + website)
                    if len(self.urls) == self.max_urls:
                        break


class DiskCache:
    """ DiskCache helps store urls and their responses to disk
        Intialization components:
            cache_dir (str): abs file path or relative file path
                for cache directory (default: ../data/cache)
            max_len (int): maximum filename length (default: 255)
            compress (bool): use zlib compression (default: True)
            encoding (str): character encoding for compression (default: utf-8)
            expires (datetime.timedelta): timedelta when content will expire
                (default: 30 days ago)
    """
    def __init__(self, cache_dir='../data/cache', max_len=255, compress=True,
                 encoding='utf-8', expires=timedelta(days=30)):
        self.cache_dir = cache_dir
        self.max_len = max_len
        self.compress = compress
        self.encoding = encoding
        self.expires = expires

    def url_to_path(self, url):
        """ Return file system path string for given URL """
        components = urlsplit(url)
        # append index.html to empty paths
        path = components.path
        if not path:
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'
        filename = components.netloc + path + components.query
        # replace invalid characters
        filename = re.sub(r'[^/0-9a-zA-Z\-.,;_ ]', '_', filename)
        # restrict maximum number of characters
        filename = '/'.join(seg[:self.max_len] for seg in filename.split('/'))
        return os.path.join(self.cache_dir, filename)

    def __getitem__(self, url):
        """Load data from disk for given URL"""
        path = self.url_to_path(url)
        if os.path.exists(path):
            mode = ('rb' if self.compress else 'r')
            with open(path, mode) as fp:
                if self.compress:
                    data = zlib.decompress(fp.read()).decode(self.encoding)
                    data = json.loads(data)
                else:
                    data = json.load(fp)
            exp_date = data.get('expires')
            if exp_date and datetime.strptime(exp_date,
                                              '%Y-%m-%dT%H:%M:%S') <= datetime.utcnow():
                print('Cache expired!', exp_date)
                raise KeyError(url + ' has expired.')
            return data
        else:
            # URL has not yet been cached
            raise KeyError(url + ' does not exist')

    def __setitem__(self, url, result):
        """Save data to disk for given url"""
        path = self.url_to_path(url)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        mode = ('wb' if self.compress else 'w')
        # Note: the timespec command requires Py3.6+ (if using 3.X you can
        # export using isoformat() and import with '%Y-%m-%dT%H:%M:%S.%f'
        result['expires'] = (datetime.utcnow() + self.expires).isoformat(
            timespec='seconds')
        with open(path, mode) as fp:
            if self.compress:
                data = bytes(json.dumps(result), self.encoding)
                fp.write(zlib.compress(data))
            else:
                json.dump(result, fp)




class RedisQueue:
    """ RedisQueue helps store urls to crawl to Redis
        Initialization components:
            client: a Redis client connected to the key-value database for
                the webcrawling cache (if not set, a localhost:6379
                default connection is used).
        db (int): which database to use for Redis
        queue_name (str): name for queue (default: wswp)
    """

    def __init__(self, client=None, db=0, queue_name='wswp'):
        self.client = (StrictRedis(host='localhost', port=6379, db=db)
                       if client is None else client)
        self.name = "queue:%s" % queue_name
        self.seen_set = "seen:%s" % queue_name
        self.depth = "depth:%s" % queue_name

    def __len__(self):
        return self.client.llen(self.name)

    def push(self, element):
        """Push an element to the tail of the queue"""
        if isinstance(element, list):
            element = [e for e in element if not self.already_seen(e)]
            self.client.lpush(self.name, *element)
            self.client.sadd(self.seen_set, *element)
        elif not self.already_seen(element):
            self.client.lpush(self.name, element)
            self.client.sadd(self.seen_set, element)

    def already_seen(self, element):
        """ determine if an element has already been seen """
        return self.client.sismember(self.seen_set, element)

    def set_depth(self, element, depth):
        """ Set the seen hash and depth """
        self.client.hset(self.depth, element, depth)

    def get_depth(self, element):
        """ Get the seen hash and depth """
        return (lambda dep: int(dep) if dep else 0)(self.client.hget(self.depth, element))

    def pop(self):
        """Pop an element from the head of the queue"""
        return self.client.rpop(self.name).decode('utf-8')





class ProjectDB():
    __collection_name__ = 'crawl'

    def __init__(self, url="127.0.0.1:27017", database=MongoSettings.DATABASE_USER):
        self.conn = MongoClient(url)
        self.conn.admin.command("ismaster")
        self.database = MongoSettings.DATABASE_DB
        self.collection = MongoSettings.DATABASE_COLLECTION

        self.collection.ensure_index('name', unique=True)

    def _default_fields(self, each):
        if each is None:
            return each
        each.setdefault('group', None)
        each.setdefault('status', 'TODO')
        each.setdefault('script', '')
        each.setdefault('comments', None)
        each.setdefault('rate', 0)
        each.setdefault('burst', 0)
        each.setdefault('updatetime', 0)
        return each

    def insert(self, name, obj={}):
        obj = dict(obj)
        obj['name'] = name
        obj['updatetime'] = time.time()
        return self.collection.update({'name': name}, {'$set': obj}, upsert=True)

    def update(self, name, obj={}, **kwargs):
        obj = dict(obj)
        obj.update(kwargs)
        obj['updatetime'] = time.time()
        return self.collection.update({'name': name}, {'$set': obj})

    def get_all(self, fields=None):
        for each in self.collection.find({}, fields):
            if each and '_id' in each:
                del each['_id']
            yield self._default_fields(each)

    def get(self, name, fields=None):
        each = self.collection.find_one({'name': name}, fields)
        if each and '_id' in each:
            del each['_id']
        return self._default_fields(each)

    def check_update(self, timestamp, fields=None):
        for project in selfS.get_all(fields=('updatetime', 'name')):
            if project['updatetime'] > timestamp:
                project = self.get(project['name'], fields)
                yield self._default_fields(project)

    def drop(self, name):
        return self.collection.remove({'name': name})

db = ProjectDB()
