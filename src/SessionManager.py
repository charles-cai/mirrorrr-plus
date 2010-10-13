import SessionManager
from google.appengine.api import memcache
import datetime
import random
import Cookie,os,b64,logging

class SessionManager(object):
    def __init__(self, request=None, response=None, timeout=1200):
        self.timeout = timeout
        self.request = request
        self.response = response
        self.cookieName = 'SID'

    def current(self):
        string_cookie = os.environ.get(u"HTTP_COOKIE", u"")
        cookie = Cookie.SimpleCookie()
        if string_cookie!="":            
            cookie.load(string_cookie)
            
        cookievalue = None
        if cookie.has_key(self.cookieName):
                cookievalue = cookie[self.cookieName].value
        
        #logging.error("cookievalue: %s"% cookievalue )
        
        if ((cookievalue is not None)):# and (memcache.get( cookievalue+'__keys') is not None)):
            return Session(cookievalue, self.timeout, False)
        else: 
            return self.createSession()

    def createSession(self):
        newId = self.createNewId()
        if memcache.get(newId) is not None:
            memcache.set(key=newId, value=True, time=self.timeout, )
        else:
            memcache.add(key=newId, value=True, time=self.timeout, )

        #logging.error("mem: %s"% memcache.get(newId) )
        
        now = datetime.datetime.now()
        inc = datetime.timedelta(seconds=self.timeout)
        now += inc
        self.setCookie(key=self.cookieName,value=newId,expires=now)

        return Session(newId, self.timeout, True)
        
    def destroySession(self):
        self.clearCookie(self.cookieName)

    def createNewId(self):
        newHash = str(hash(datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))) + str(random.random())
        #newHash = str(b64.uri_b64encode(newHash))
        
        while memcache.get(newHash) is not None:
            newHash = self.CreateNewId()

        return newHash

    def setCookie(self,key,value,expires,path='/'):
        #self.response.headers.add_header('Set-Cookie', key+'='+value+ ' path='+path+'; expires '+expires.strftime('%a, %d-%b-%Y %H:%M:00 %Z'))
        
        output_cookie = Cookie.SimpleCookie()
        output_cookie[key] = value
        output_cookie[key]["path"] = path            
        #output_cookie[key]["domain"] = self.cookie_domain
        output_cookie[key]["expires"] = expires
        print output_cookie.output()
        
    def clearCookie(self,key):
        self.setCookie(key=key,value='',expires=datetime.datetime.now())


class Session(object):
    def __init__(self, id, timeout, isNew=False):
        self.id = id
        self.IsNew = isNew
        self.keys = dict()
        self.timeout = timeout
        memcache.add(key=self.id+'__keys', value=self.keys, time=timeout)

    def __getitem__(self, key):
        return memcache.get(self.id+'_'+key)

    def __setitem__(self,key,value):
        memcache.set(key=self.id+'_'+key, value=value, time=self.timeout)
        self.keys[key] = value
        memcache.set(key=self.id+'__keys', value=self.keys, time=self.timeout)

    def has_key(self, key):
        self.keys = memcache.get(self.id+'__keys')
        return (key in self.keys)
    