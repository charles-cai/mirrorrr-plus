# -*- coding: utf-8 -*- 
from MyCookieJar import MyCookieJar
from appengine_utilities.sessions import Session
from google.appengine.api import memcache, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.runtime import apiproxy_errors
from urlparse import urlparse
import b64
import cookielib
import datetime
import hashlib
import httplib
import logging
import pickle
import re
import socket
import time
import transform_content
import urllib
import urllib2
import wsgiref.handlers
import mirror_const


class my_url_opener(urllib.FancyURLopener):

    def http_error_302(self, *args):
        headers = args[4]
        # print headers # <-- uncomment to see the headers
        cookie = headers.get("set-cookie")
        if cookie:
        # this is ugly
            self.addheaders.append(("Cookie", cookie.split(";")[0]))
        return urllib.FancyURLopener.http_error_302(self, *args)

class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        #print "Cookie Manip Right Here"
        logging.error("Cookie Manip Right Here")
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302        

def post_and_get_content(url,param=None):     
    cookiejar   = MyCookieJar.load_from_session_or_new(url)    
    #===========================================================================
    # is_Google_login = url.startswith('https://www.google.com/accounts/ServiceLoginAuth')
    # if is_Google_login:
    #    from GoogleLogin import GoogleLogin
    #    auth = GoogleLogin(param['Email'],param['Passwd'],param['continue'],cookiejar )
    #    cookiejar = auth.cookiejar
    #===========================================================================
        
    #p = '127.0.0.1:5865'
    #opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar),ConnectHTTPSHandler(proxy=p))     
    opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar)) 
    #opener.addheaders = [('User-agent', 'Opera/9.23')] 
    opener.addheaders = [('User-agent',  'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)')]
    urllib2.install_opener(opener) 
    #if is_Google_login:
    #    req=urllib2.Request(param['continue'])
    #else:
    req=urllib2.Request(url,param and urllib.urlencode(param) or None)
         
    resp=urllib2.urlopen(req)
    content =  resp.read()
    
    #save    
    cookiejar.save_to_memcache()
    
    headers = dict([ ( (x[:x.index(':')]).strip(), (x[x.index(':')+1:]).strip()) for x in  str(resp.info()).split('\n') if (x.strip()!='' and x.index(':')>=0) ]) # resp.info()#.headers # resp.headers #iteritems
    status_code = '200' # resp.info().status #_code# '200' #resp.status_code
    return {'content':content,'headers':headers,'status_code':status_code}

class MirroredContent(object):
    def __init__(self, original_address, translated_address,
               status, headers, data, base_url):
        self.original_address = original_address
        self.translated_address = translated_address
        self.status = status
        self.headers = headers
        self.data = data
        self.base_url = base_url

    @staticmethod
    def get_by_key_name(key_name):
        return memcache.get(key_name)
    
    @staticmethod
    def fetch_and_store(key_name, base_url, translated_address, mirrored_url,postdata=None,ChineseWordsencoding=True,whitelist=''):
        """Fetch and cache a page.
        
        Args:
          key_name: Hash to use to store the cached page.
          base_url: The hostname of the page that's being mirrored.
          translated_address: The URL of the mirrored page on this site.
          mirrored_url: The URL of the original page. Hostname should match
            the base_url.
        
        Returns:
          A new MirroredContent object, if the page was successfully retrieved.
          None if any errors occurred or the content could not be retrieved.
        """
        # Check for the X-Mirrorrr header to ignore potential loops.
        if base_url in mirror_const.MIRROR_HOSTS:
            logging.warning(u'Encountered recursive request for "%s"; ignoring', mirrored_url)
            return None
        
        logging.debug(u"Fetching '%s'", mirrored_url)
        try:
            response = post_and_get_content(mirrored_url,postdata)
        except (urlfetch.Error, apiproxy_errors.Error):
            logging.exception("Could not fetch URL")
            return None
        
        adjusted_headers = {}
        #for key, value in response['headers']:
        for key,value in response['headers'].iteritems():    
            adjusted_key = key.lower()
            if adjusted_key not in mirror_const.IGNORE_HEADERS:
                adjusted_headers[adjusted_key] = value
        
        #logging.error(adjusted_headers)
        
        content = response['content']
        page_content_type = adjusted_headers.get("content-type", "")
        for content_type in mirror_const.TRANSFORMED_CONTENT_TYPES:
            # Startswith() because there could be a 'charset=UTF-8' in the header.
            if page_content_type.startswith(content_type):
                is_html = page_content_type.startswith('text/html')
                if is_html: logging.error(u'transform:%s'%mirrored_url)
                content = transform_content.TransformContent(base_url, mirrored_url, content,is_html,ChineseWordsencoding,whitelist)
                break
        
        # If the transformed content is over 1MB, truncate it (yikes!)
        if len(content) > mirror_const.MAX_CONTENT_SIZE:
            logging.warning('Content is over 1MB; truncating')
            content = content[:mirror_const.MAX_CONTENT_SIZE]
        
        new_content = MirroredContent(
          base_url=base_url,
          original_address=mirrored_url,
          translated_address=translated_address,
          status=response['status_code'],
          headers=adjusted_headers,
          data=content)
        
        #=======================================================================
        # if memcache.get(key_name):
        #    if memcache.set(key_name, new_content, time=mirror_const.EXPIRATION_DELTA_SECONDS):
        #        logging.error('memcache.set failed: key_name = "%s", '
        #                'original_url = "%s"', key_name, mirrored_url)
        # else:
        #    if memcache.set(key_name, new_content, time=mirror_const.EXPIRATION_DELTA_SECONDS):
        #        logging.error('memcache.add2 failed: key_name = "%s", '
        #                'original_url = "%s"', key_name, mirrored_url)
        #=======================================================================
          
        return new_content
    
    ################################################################################

class ProxyHTTPConnection(httplib.HTTPConnection):

    _ports = {'http' : 80, 'https' : 443}


    def request(self, method, url, body=None, headers={}):
        #request is called before connect, so can interpret url and get
        #real host/port to be used to make CONNECT request to proxy
        proto, rest = urllib.splittype(url)
        if proto is None:
            raise ValueError, "unknown URL type: %s" % url
        #get host
        host, rest = urllib.splithost(rest)
        #try to get port
        host, port = urllib.splitport(host)
        #if port is not defined try to get from proto
        if port is None:
            try:
                port = self._ports[proto]
            except KeyError:
                raise ValueError, "unknown protocol for: %s" % url
        self._real_host = host
        self._real_port = port
        httplib.HTTPConnection.request(self, method, url, body, headers)
        

    def connect(self):
        httplib.HTTPConnection.connect(self)
        #send proxy CONNECT request
        self.send("CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self._real_host, self._real_port))
        #expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict, method=self._method)
        (version, code, message) = response._read_status()
        #probably here we can handle auth requests...
        if code != 200:
            #proxy returned and error, abort connection, and raise exception
            self.close()
            raise socket.error, "Proxy connection failed: %d %s" % (code, message.strip())
        #eat up header block from proxy....
        while True:
            #should not use directly fp probablu
            line = response.fp.readline()
            if line == '\r\n': break

class ProxyHTTPSConnection(ProxyHTTPConnection):
    
    default_port = 443

    def __init__(self, host, port = None, key_file = None, cert_file = None, strict = None):
        ProxyHTTPConnection.__init__(self, host, port)
        self.key_file = key_file
        self.cert_file = cert_file
    
    def connect(self):
        ProxyHTTPConnection.connect(self)
        #make the sock ssl-aware
        ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl)

class ConnectHTTPHandler(urllib2.HTTPHandler):

    def __init__(self, proxy=None, debuglevel=0):
        self.proxy = proxy
        urllib2.HTTPHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):
        if self.proxy is not None:
            req.set_proxy(self.proxy, 'http')
        return urllib2.HTTPHandler.do_open(self, ProxyHTTPConnection, req)

class ConnectHTTPSHandler(urllib2.HTTPSHandler):

    def __init__(self, proxy=None, debuglevel=0):
        self.proxy = proxy
        urllib2.HTTPSHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):
        if self.proxy is not None:
            req.set_proxy(self.proxy, 'https')
        return urllib2.HTTPSHandler.do_open(self, ProxyHTTPSConnection, req)