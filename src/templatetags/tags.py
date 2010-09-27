# -*- coding: utf-8 -*- 

from django.template import Library
from django.template.defaultfilters import stringfilter
import datetime,math
import b64

register = Library()

@register.filter
def uri_b64encode(url):
    url = url[1:]
    return b64.uri_b64encode(url)