# -*- coding:utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 Duoshuo
#
__version__ = '0.1'

import os
import urllib
import urllib2
import warnings
import urlparse
import hashlib
import httplib

try:
    import json
    _parse_json = lambda s: json.loads(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
    except ImportError:
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)

try:
    import Cookie
except ImportError:
    import https.cookies as Cookie #python 3.0

HOST = 'api.duoshuo.com'
URI_SCHEMA = 'http'
INTERFACES = _parse_json(open(os.path.join(os.path.dirname(__file__), 'interfaces.json'), 'r').read())

try:
    import settings
except ImportError:
    DUOSHUO_SHORT_NAME =None
    DUOSHUO_SECRET = None
else:
    DUOSHUO_SHORT_NAME = getattr(settings, "DUOSHUO_SHORTNAME", None)
    DUOSHUO_SECRET = getattr(settings, "DUOSHUO_SECRET", None)

class APIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.code, self.message)

# class Result(object):
#     def __init__(self, response, cursor=None):
#         self.response = response
#         self.cursor = cursor or {}

#     def __repr__(self):
#         return '<%s: %s>' % (self.__class__.__name__, repr(self.response))

#     def __iter__(self):
#         for r in self.response:
#             yield r

#     def __len__(self):
#         return len(self.response)

#     def __getslice__(self, i, j):
#         return list.__getslice__(self.response, i, j)

#     def __getitem__(self, key):
#         return list.__getitem__(self.response, key)

#     def __contains__(self, key):
#         return list.__contains__(self.response, key)

class Resource(object):
    def __init__(self, api, interface=INTERFACES, node=None, tree=()):
        self.api = api
        self.node = node
        self.interface = interface
        if node:
            tree = tree + (node,)
        self.tree = tree

    def __getattr__(self, attr):
        if attr in getattr(self, '__dict__'):
            return getattr(self, attr)
        interface = self.interface
        if attr not in interface:
            interface[attr] = {}
            raise APIError('03', 'Interface is not defined')
        return Resource(self.api, interface[attr], attr, self.tree)

    def __call__(self, **kwargs):
        return self._request(**kwargs)

    def _request(self, **kwargs):

        resource = self.interface
        for k in resource.get('required', []):
            if k not in [ x.split(':')[0] for x in kwargs.keys() ]:
                raise ValueError('Missing required argument: %s' % k)

        method = kwargs.pop('method', resource.get('method'))

        api = self.api

        format = kwargs.pop('format', api.format)
        path = '%s://%s/%s.%s' % (URI_SCHEMA, HOST, '/'.join(self.tree), format)

        if 'api_secret' not in kwargs and api.secret:
            kwargs['api_secret'] = api.secret

        # We need to ensure this is a list so that
        # multiple values for a key work
        params = []
        for k, v in kwargs.iteritems():
            if isinstance(v, (list, tuple)):
                for val in v:
                    params.append((k, val))
            else:
                params.append((k, v))

        if method == 'GET':
            path = '%s?%s' % (path, urllib.urlencode(params))
            response = urllib2.urlopen(path)
        else:
            data = urllib.urlencode(params)
            response = urllib2.urlopen(path, data)
            
        return _parse_json(response.read())['response']

class DuoshuoAPI(Resource):
    def __init__(self, short_name=DUOSHUO_SHORT_NAME, secret=DUOSHUO_SECRET, format='json', **kwargs):
        self.short_name = short_name
        self.secret = secret
        self.format = format
        if not secret or not short_name:
            warnings.warn('You should pass short_name and secret.')
        #self.version = version
        super(DuoshuoAPI, self).__init__(self)

    def _request(self, **kwargs):
        raise SyntaxError('You cannot call the API without a resource.')

    def _get_key(self):
        return self.secret
    key = property(_get_key)
            
    def get_url(self, redirect_uri=None):
        if not redirect_uri:
            raise APIError('01', 'Invalid request: redirect_uri')
        else:
            params = {'client_id': self.short_name, 'redirect_uri': redirect_uri, 'response_type': 'code'}
            return '%s://%s/oauth2/%s?%s' % (URI_SCHEMA, HOST, 'authorize', \
                urllib.urlencode(sorted(params.items())))
    
    def get_token(self, code=None):
        if not code:
            raise APIError('01', 'Invalid request: code')
        #elif not redirect_uri:
        #    raise APIError('01', 'Invalid request: redirect_uri')
        else:
            #params = {'client_id': self.client_id, 'secret': self.secret, 'redirect_uri': redirect_uri, 'code': code}
            params = {'code': code}
            data = urllib.urlencode(params)
            url = '%s://%s/%s' % (URI_SCHEMA, HOST, 'access_token')#, \
                #urllib.urlencode(sorted(params.items())))
            request = urllib2.Request(url)
            response = urllib2.build_opener(urllib2.HTTPCookieProcessor()).open(request, data)
            #file = urllib.urlopen(url)
            #print 'url: '+url + '\r\ndata: ' + data
            return _parse_json(response.read())
    
    def get_duoshuo_comment_form(self):
        pass

    def setSecretKey(self, key):
        self.secret_key = key
    setKey = setSecretKey

    def setPublicKey(self, key):
        self.public_key = key

