"""
This helper class is based on Scott's work.
See his post:
http://everydayscripting.blogspot.com/2009/08/google-app-engine-cookie-handling-with.html

"""


import urllib, urllib2, Cookie ,logging,urlparse
from google.appengine.api import urlfetch
from MyCookieJar import MySimpleCookie

class URLOpener:
    def __init__(self):
        pass

    def open(self, url, data = None,headers={}):
        self.cookie =MySimpleCookie.load_from_session_or_new(url)
        
        if data is None:
            method = urlfetch.GET
        else:
            method = urlfetch.POST
        base_url = url
        while url is not None:
            headers_ = self._getHeaders(self.cookie)
            if headers is not None:
                headers_.update(headers)
            logging.error('fetching %s'%url)
            response = urlfetch.fetch(url=url,
                                      payload=data,
                                      method=method,
                                      headers=headers_,
                                      allow_truncated=False,
                                      follow_redirects=False,
                                      deadline=10
                    )
            response.lasturl = url
            data = None # Next request will be a get, so no need to send the data again.
            method = urlfetch.GET
            
            self.cookie.load(response.headers.get('set-cookie', ''))  #Load the cookies from the response
            #===================================================================
            # if Cookie.SimpleCookie().load(response.headers.get('set-cookie', '')) is not None:
            #    for item in Cookie.SimpleCookie().load(response.headers.get('set-cookie', '')): 
            #        self.cookie[item.key] = item.value #@IndentOk
            # 
            #===================================================================
            url = response.headers.get('location')
            if not url is None and  not url.startswith('http'):
                url = urlparse.urljoin(base_url, url)
        
        self.cookie.save_to_memcache()
        return response

    def _getHeaders(self, cookie):
        headers = {
        #'Host' : 'www.google.com',
        'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2 (.NET CLR 3.5.30729)'
        ,
        'Cookie' : self._makeCookieHeader(cookie)
        }
        return headers

    def _makeCookieHeader(self, cookie):
        cookieHeader = ""
        for value in cookie.values():
            cookieHeader += "%s=%s; " % (value.key, value.value)
        return cookieHeader