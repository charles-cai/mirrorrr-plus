from cPickle import dumps
from cookielib import CookieJar

import threading,Cookie
from  appengine_utilities.sessions import Session
import hashlib,logging
from google.appengine.api import memcache
import uuid,urlparse

COOKIE_JAR_SESSION_NAME = u'Sess_cj_%s'
COOKIE_SESSION_NAME = u'Sess_cookie_%s'
EXPIRATION_DELTA_SECONDS = 60*20

def get_url_key_name(myurl):
    while myurl.count('.')>1:
        myurl = myurl[myurl.index('.')+1:]
        
    url_hash = hashlib.sha256()
    url_hash.update(myurl)
    
    #logging.error(myurl)
    return "" + url_hash.hexdigest()
    #return "xxxxooo"

def save_session(key,value):
    session = Session()
    if session.has_key(key):
        mem_key = session[key]
        if memcache.get(mem_key):
            memcache.set(mem_key, value, time=EXPIRATION_DELTA_SECONDS)
        else:
            memcache.add(mem_key, value, time=EXPIRATION_DELTA_SECONDS)
    
def load_session(key):
    session = Session()
    if session.has_key(key):
        mem_key = session[key]
        return memcache.get(mem_key)
    else:return None


    
class MyCookieJar(CookieJar):
    site = ''
    
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_cookies_lock']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self._cookies_lock = threading.RLock()

    @staticmethod  
    def load_from_session_or_new(url):
        site = urlparse.urlparse(url).netloc.encode('utf-8')
        #site = url
        
        session = Session()        
        cookiejar = None        
        if session.has_key(COOKIE_JAR_SESSION_NAME%get_url_key_name(site)):
            cookiejar = load_session( COOKIE_JAR_SESSION_NAME%get_url_key_name(site))
        
        if not cookiejar:
            session[COOKIE_JAR_SESSION_NAME%get_url_key_name(site)] =str(uuid.uuid4())
            cookiejar = MyCookieJar()
        
        cookiejar.site = site
        return cookiejar

    def save_to_memcache(self):
        save_session(COOKIE_JAR_SESSION_NAME%get_url_key_name(self.site), self)

class MySimpleCookie(Cookie.SimpleCookie):
    site = ''    
#===============================================================================
#    def __getstate__(self):
#        state = self.__dict__.copy()
#        del state['_cookies_lock']
#        return state
# 
#    def __setstate__(self, state):
#        self.__dict__ = state
#        self._cookies_lock = threading.RLock()
#===============================================================================

    @staticmethod  
    def load_from_session_or_new(url):
        site = urlparse.urlparse(url).netloc.encode('utf-8')
        #site = url
        
        session = Session()        
        cookie = None        
        if session.has_key(COOKIE_SESSION_NAME%get_url_key_name(site)):
            cookie = load_session( COOKIE_SESSION_NAME%get_url_key_name(site))
        
        if not cookie:
            session[COOKIE_SESSION_NAME%get_url_key_name(site)] =str(uuid.uuid4())
            cookie = MySimpleCookie()
        
        cookie.site = site
        return cookie

    def save_to_memcache(self):
        save_session(COOKIE_SESSION_NAME%get_url_key_name(self.site), self)