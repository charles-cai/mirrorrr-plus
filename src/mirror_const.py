# -*- coding: utf-8 -*- 




DEBUG = False
EXPIRATION_DELTA_SECONDS = 1
EXPIRATION_RECENT_URLS_SECONDS = 1

#===============================================================================
# DEBUG = False
# EXPIRATION_DELTA_SECONDS = 3600
# EXPIRATION_RECENT_URLS_SECONDS = 90
#===============================================================================

HTTP_PREFIX = "http://"
HTTPS_PREFIX = "http://"


COOKIE_JAR_SESSION_NAME = 'Sess_cj_%s'
MAX_CONTENT_SIZE = 10 ** 6
MAX_URL_DISPLAY_LENGTH = 50
EXPIRATION_DELTA_SECONDS = 100
EXPIRATION_RECENT_URLS_SECONDS = 1

IGNORE_HEADERS = frozenset([
  'set-cookie',
  'expires',
  'cache-control',

  # Ignore hop-by-hop headers
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
])

TRANSFORMED_CONTENT_TYPES = frozenset([
  "text/html",
  "text/css",
])

MIRROR_HOSTS = frozenset([
  'mirrorr.com',
  'mirrorrr.com',
  'www.mirrorr.com',
  'www.mirrorrr.com',
  'www1.mirrorrr.com',
  'www2.mirrorrr.com',
  'www3.mirrorrr.com',
])