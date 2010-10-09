
from google.appengine.ext import webapp

#save in cookie
def set_cookie(requesthandler,key,value):
    requesthandler.response.headers.add_header(
        'Set-Cookie',
        '%s=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' \
        % (key,value.encode())) 
    
def get_cookie(requesthandler,key,default):
    return requesthandler.request.cookies.get(key, default)

def ChineseWordsencoding(requesthandler):
    return get_cookie(requesthandler,'ChineseWordsencoding', '')

def useCache(requesthandler):
    return get_cookie(requesthandler,'useCache', 'checked')

def EncodingWhiteList(requesthandler):
    return get_cookie(requesthandler,'EncodingWhiteList', '')


def set_ChineseWordsencoding(requesthandler,value):
    set_cookie(requesthandler, 'ChineseWordsencoding' ,value)
def set_useCache(requesthandler,value):
    set_cookie(requesthandler, 'useCache' ,value)
def set_EncodingWhiteList(requesthandler,value):
    set_cookie(requesthandler, 'EncodingWhiteList' ,value)
    
       