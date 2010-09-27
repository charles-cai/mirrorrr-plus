# -*- coding: utf-8 -*- 
from base64 import urlsafe_b64encode, urlsafe_b64decode

def uri_b64encode(s):
    #s= s.encode('utf-8')
    return urlsafe_b64encode(s).strip('=')

def uri_b64decode(s):    
    s = urlsafe_b64decode(s + '=' * (4 - len(s) % 4))
    #s= s.decode('utf-8')
    return s
