# -*- coding: utf-8 -*- 
#!/usr/bin/env python
# Copyright 2008 Brett Slatkin
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Brett Slatkin (bslatkin@gmail.com)"

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.runtime import apiproxy_errors
from urlparse import urlparse
import b64
import datetime
import hashlib
import logging
import pickle
import re
import time
import transform_content
import urllib
import wsgiref.handlers
from fetchpost import MirroredContent
import mirror_const  
import CookieHelper

################################################################################


################################################################################

def get_url_key_name(url):
    url_hash = hashlib.sha256()
    url_hash.update(url)
    return "hash_" + url_hash.hexdigest()

def to_uri_b64encode(url):
    url = url[1:]
    return "/"+b64.uri_b64encode(url)

################################################################################

class BaseHandler(webapp.RequestHandler):
    def get_relative_url(self):
        slash = self.request.url.find("/", len(self.request.scheme + "://"))
        if slash == -1:
            return "/"
        return self.request.url[slash:]
    def get_base(self,url):
        #=======================================================================
        # slash =  url.rfind("/")
        # slash2 =  url.rfind("//")
        # if slash == slash2:
        #    return url[:]
        # return  url[:slash]
        #=======================================================================
        
        return urlparse(url).netloc
    def get_translated_address(self):
        translated_address = self.get_relative_url()[1:]  # remove leading /
        if self.get_relative_url().find("?")!=-1:
            translated_address = translated_address[:translated_address.find("?")]
        translated_address = b64.uri_b64decode(translated_address) #base64
        if self.get_relative_url().find("?")!=-1:
            translated_address +=  self.request.url[self.request.url.find('?'):]
        
        if not translated_address.lower().startswith('http'):
            translated_address = mirror_const.HTTP_PREFIX + translated_address
        return translated_address
    def get_httproot (self):
        return 'http://%s'% urlparse(self.request.url).netloc
    def get_httpsroot (self):
        return 'https://%s'% urlparse(self.request.url).netloc
    def get_change_root(self):
        if self.request.url.lower().startswith('https'):
            return self.get_httproot()
        else:
            return self.get_httpsroot()
            
    
class HomeHandler(BaseHandler):
    def get(self):       
        msg = ''
        
        #=======================================================================
        # from  appengine_utilities.sessions import Session
        # session = Session()
        # #session.delete_all_sessions()
        # msg = ''
        # if not session.has_key("keyname"):
        #    session["keyname"] = "value" # sets keyname to value
        #    print session["keyname"] # will print value
        #    msg = 'write ' + session["keyname"]
        #    #session["keyname"].put()
        # else:
        #    msg = 'read '+ session["keyname"]
        #=======================================================================
        self.response.out.write(template.render("main.html", {'msg':msg, 
                                                 'change_url':self.get_change_root(),
                                                 }))
    
    def post(self):
        # Handle the input form to redirect the user to a relative url
        form_url = self.request.get("url")
        if form_url:
            # Accept URLs that still have a leading 'http://'            
            inputted_url = form_url #urllib.quote(form_url.encode('utf-8')) #form_url # 
            
            #if inputted_url.startswith(HTTP_PREFIX):
            #    inputted_url = inputted_url[len(HTTP_PREFIX):]
            #return self.redirect("/" + b64.uri_b64encode(inputted_url))
            return self.redirect("/" + b64.uri_b64encode(inputted_url))
      
        self.response.out.write(template.render("main.html", { 
                                                 'change_url':self.get_change_root(),
                                                 }))
        
class setupHandler(BaseHandler):
    def get(self):  
        #load from cookie
        ChineseWordsencoding = CookieHelper.ChineseWordsencoding(self )
        useCache = CookieHelper.useCache(self)
        EncodingWhiteList = CookieHelper.EncodingWhiteList(self)
        
        logging.info(EncodingWhiteList)
        
        cookies = {'ChineseWordsencoding':ChineseWordsencoding,
                   'useCache':useCache,
                   'EncodingWhiteList':EncodingWhiteList.replace('$','\n'),
                   }

        self.response.out.write(template.render("mirror_setup.html",
                                                {'msg':'SETUP',
                                                 'cookies':cookies,
                                                 'change_url':self.get_change_root(),
                                                 }))
    
    def post(self):
        #get post
        ChineseWordsencoding = self.request.get("ChineseWordsencoding")=='on' and 'checked' or ''
        useCache = self.request.get("useCache")=='on' and 'checked' or ''
        EncodingWhiteList = self.request.get("EncodingWhiteList")
        
        #save in cookie
        CookieHelper.set_ChineseWordsencoding(self,ChineseWordsencoding)
        CookieHelper.set_useCache(self  ,useCache) 
        CookieHelper.set_EncodingWhiteList(self,EncodingWhiteList.replace('\n','$').replace('\t','').replace('\r',''))  
        
        cookies = {'ChineseWordsencoding':ChineseWordsencoding,
                   'useCache':useCache,
                   'EncodingWhiteList':EncodingWhiteList,
                   }
         
        result = 'save ok.'
        self.response.out.write(template.render("mirror_setup.html", {
                                                                      'msg':'SETUP',
                                                                      'result':result,
                                                                      'cookies':cookies,
                                                 'change_url':self.get_change_root(),
                                                 }))    
        
class MirrorHandler(BaseHandler):
    def get(self, base_url):
        self.process_request(base_url)

    def post(self, base_url):
        #postdata = self.request.arguments()           
        postdata = dict([(x,self.request.get(x)) for x in self.request.arguments()])
        logging.error(str(postdata))             
        self.process_request(base_url,postdata)
        #msg = postdata
        #self.response.out.write(template.render("main.html", {'msg':msg,}))
        
    def process_request(self,base_url,post_data=None):
        assert base_url  
        
        translated_address = self.get_translated_address() 
        mirrored_url = translated_address
           
        base_url = self.get_base(mirrored_url)
        # Log the user-agent and referrer, to see who is linking to us.
        logging.debug('User-Agent = "%s", Referrer = "%s"', self.request.user_agent, self.request.referer)
        #logging.debug('Base_url = "%s", url = "%s"', base_url, self.request.url)
        #logging.info('Base_url = "%s", url = "%s"', base_url, self.request.url)
    
        # Use sha256 hash instead of mirrored url for the key name, since key
        # names can only be 500 bytes in length; URLs may be up to 2KB.
        key_name = get_url_key_name(mirrored_url)
        logging.info(u"Handling request for '%s' = '%s'", mirrored_url, key_name)

        content = CookieHelper.useCache(self)  and MirroredContent.get_by_key_name(key_name) or None
        if content is None:
            logging.debug("Cache miss")  
            ChineseWordsencoding = CookieHelper.ChineseWordsencoding(self )
            EncodingWhiteList = CookieHelper.EncodingWhiteList(self)
            content = MirroredContent.fetch_and_store(key_name, base_url,
                                                    translated_address,
                                                    mirrored_url,post_data,ChineseWordsencoding,EncodingWhiteList)
                         
        if content is None:
            #return self.error(404)
            self.response.out.write(template.render("default_error.html", { 'msg':'Sorry, Error occurred!!',
                                                                           'change_url':self.get_change_root(),
                                                                            })) 
            return
        
        for key, value in content.headers.iteritems():
            self.response.headers[key] = value
        if not mirror_const.DEBUG:
            self.response.headers['cache-control'] = \
                'max-age=%d' % mirror_const.EXPIRATION_DELTA_SECONDS
    
        self.response.out.write( content.data)
        
class AdminHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['content-type'] = 'text/plain'
        self.response.out.write(str(memcache.get_stats()))


class KaboomHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['content-type'] = 'text/plain'
        self.response.out.write('Flush successful: %s' % memcache.flush_all())

class deleteSessionHandler(webapp.RequestHandler):
    def get(self):
        from  appengine_utilities.sessions import Session
        import uuid
        session = Session()        
        session['kkk'] =str(uuid.uuid4())
        
        Session.delete_all_sessions()
        msg = ''
        memcache.flush_all()
        
        self.response.headers['content-type'] = 'text/plain'
        self.response.out.write('deleteSession memcache.flush_all ok. %s'%msg)
        
class CleanupHandler(webapp.RequestHandler):
    """Cleans up EntryPoint records."""
    def get(self):
        keep_cleaning = True
        try:
            from models import EntryPoint 
            content_list = EntryPoint.gql('ORDER BY last_updated').fetch(25)
            keep_cleaning = (len(content_list) > 0)
            db.delete(content_list)
          
            if content_list:
                message = "Deleted %d entities" % len(content_list)
            else:
                keep_cleaning = False
                message = "Done"
        except (db.Error, apiproxy_errors.Error), e:
            keep_cleaning = True
            message = "%s: %s" % (e.__class__, e)
    
        context = {  
          'keep_cleaning': keep_cleaning,
          'message': message,
        }
        self.response.out.write(template.render('cleanup.html', context))

################################################################################

app = webapp.WSGIApplication([
  (r"/", HomeHandler),
  (r"/main", HomeHandler),
  (r"/kaboom", KaboomHandler),
  (r"/admin", AdminHandler),
  (r"/setup", setupHandler),
  (r"/cleanup", CleanupHandler),
  (r"/deletesession", deleteSessionHandler),
  (r"/([^/]+).*", MirrorHandler)
], debug=mirror_const.DEBUG)


def main():
    wsgiref.handlers.CGIHandler().run(app)


if __name__ == "__main__":
    main()

