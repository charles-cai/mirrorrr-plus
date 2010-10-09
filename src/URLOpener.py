# -*- coding: utf-8 -*- 
import urllib, urllib2, Cookie 
from google.appengine.api import urlfetch  
class URLOpener:   
    def __init__(self,cookie=None):  
        if cookie  is None:
            self.cookie = Cookie.SimpleCookie()
        else:
            self.cookie =  cookie
            
    def open(self, url, data = None):       
        if data is None:           
            method = urlfetch.GET       
        else:          
            method = urlfetch.POST           
        
        while url is not None:           
            response = urlfetch.fetch(url=url,                           
                                      payload=data,                           
                                      method=method,                           
                                      headers=self._getHeaders(self.cookie),                           
                                      allow_truncated=False,                           
                                      follow_redirects=False,                           
                                      deadline=10                           )           
            data = None # Next request will be a get, so no need to send the data again.            
            method = urlfetch.GET    
            
            #self.cookie..load(response.headers.get('set-cookie', '')) # Load the cookies from the response 
            if Cookie.SimpleCookie().load(response.headers.get('set-cookie', '')) is not None:
                for item in Cookie.SimpleCookie().load(response.headers.get('set-cookie', '')): 
                    self.cookie[item.key] = item.value
            
            url = response.headers.get('location')
        return response
                
    def _getHeaders(self, cookie):       
        headers = {                  
                   #'Host' : 'www.google.com',                  
                   'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2 (.NET CLR 3.5.30729)',                  
                   'Cookie' : self._makeCookieHeader(cookie)                   
                   }       
        return headers
    
    def _makeCookieHeader(self, cookie):       
        cookieHeader = ""       
        for value in cookie.values():           
            cookieHeader += "%s=%s; " % (value.key, value.value)       
        return cookieHeader 
