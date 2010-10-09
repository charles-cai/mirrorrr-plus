# -*- coding: utf-8 -*- 
# bid/utils.py
from google.appengine.api import memcache
import logging

#===============================================================================
# def cache_get(key):
#    return google.appengine.api.memcache.get(key)
# def cache_put(key, value, duration):
#    google.appengine.api.memcache.set(key, value, duration)
#===============================================================================


def cache_flush_all():
    return memcache.flush_all()


def cache_get(key):
    return memcache.get(key)


def cache_put(key, value, duration):
    if (memcache.get(key)):
        memcache.set(key, value, duration)
    else:    
        memcache.add(key, value, duration)


def cache_get_or_put(key, func, force_update, duration,force_nosave=False):
    if force_update==False:
        returnvalue =  cache_get(key)
        if returnvalue:
            return  returnvalue        

    returnvalue =  callable(func) and  func() or func
    if returnvalue and force_nosave==False:#不能为空
        cache_put(key,returnvalue,duration) 
        pass
    return returnvalue      

        
    #===========================================================================
    # except ImportError:
    #    import django.core.cache
    #    def cache_get(key):
    #        return django.core.cache.cache.get(key)
    #    def cache_put(key, value, duration):
    #        django.core.cache.cache.set(key, value, duration)
    #===========================================================================
