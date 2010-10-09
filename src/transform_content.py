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
__modify__ = "cleo (cleocn@gmail.com)"

import os
import re
import urlparse
from google.appengine.api import memcache
import b64
import logging
import chardet
import mymemcache

################################################################################

# URLs that have absolute addresses
ABSOLUTE_URL_REGEX = r"(?P<scheme>http(s?):)?//(?P<url>[^\"'> \t\)]+)"

# URLs that are relative to the base of the current hostname.
BASE_RELATIVE_URL_REGEX = r"/(?!(/)|(?P<scheme>http(s?)://)|(url\())(?P<url>[^\"'> \t\)]*)"

# URLs that have '../' or './' to start off their paths.
TRAVERSAL_URL_REGEX = r"(?P<relative>\.(\.)?)/(?!(/)|(?P<scheme>http(s?)://)|(url\())(?P<url>[^\"'> \t\)]*)" #/

# URLs that are in the same directory as the requested URL.
SAME_DIR_URL_REGEX = r"(?!(/)|(?P<scheme>http(s?)://)|(url\())(?P<url>[^\"'> \t\)]+)"

# URL matches the root directory.
ROOT_DIR_URL_REGEX = r"(?!//(?!>))/(?P<url>)(?=[ \t\n]*[\"'\)>/])" #r"(?!//(?!>))/(?P<url>)(?=[ \t\n]*[\"'\)>/])"

# Start of a tag using 'src' or 'href'
TAG_START = r"(?i)\b(?P<tag>src|href|action|url|background)(?P<equals>[\t ]*=[\t ]*)(?P<quote>[\"']?)"

# Start of a CSS import
CSS_IMPORT_START = r"(?i)@import(?P<spacing>[\t ]+)(?P<quote>[\"']?)"

# CSS url() call
CSS_URL_START = r"(?i)\burl\((?P<quote>[\"']?)"


REPLACEMENT_REGEXES = [
  (TAG_START + BASE_RELATIVE_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>/%(base)s/\g<url>","/%(base)s/%(url)s","%(tag)s%(equals)s%(quote)s%(fullurl)s",'3'),

  (TAG_START + SAME_DIR_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(accessed_dir)s\g<url>","/%(base)s%(accessed_dir)s%(url)s","%(tag)s%(equals)s%(quote)s%(fullurl)s",'1'),
 
  (TAG_START + TRAVERSAL_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(accessed_dir)s/\g<relative>/\g<url>","%(accessed_dir)s/%(relative)s/%(url)s","%(tag)s%(equals)s%(quote)s%(fullurl)s",'2'),
 

 
  (TAG_START + ROOT_DIR_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>/%(base)s/","/%(base)s/","%(tag)s%(equals)s%(quote)s%(fullurl)s",'4'),

  # Need this because HTML tags could end with '/>', which confuses the
  # tag-matching regex above, since that's the end-of-match signal.
  (TAG_START + ABSOLUTE_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>/\g<url>","/%(url)s","%(tag)s%(equals)s%(quote)s%(fullurl)s",'5'),

 (CSS_IMPORT_START + BASE_RELATIVE_URL_REGEX,
     "@import\g<spacing>\g<quote>/%(base)s/\g<url>","/%(base)s/%(url)s","@import%(spacing)s%(quote)s%(fullurl)s",'8'),
     
  (CSS_IMPORT_START + SAME_DIR_URL_REGEX,
     "@import\g<spacing>\g<quote>%(accessed_dir)s\g<url>","/%(base)s%(accessed_dir)s%(url)s","@import%(spacing)s%(quote)s%(fullurl)s",'6'),
 
  (CSS_IMPORT_START + TRAVERSAL_URL_REGEX,
     "@import\g<spacing>\g<quote>%(accessed_dir)s/\g<relative>/\g<url>","%(accessed_dir)s/%(relative)s/%(url)s","@import%(spacing)s%(quote)s%(fullurl)s",'7'),
 
 
 
  (CSS_IMPORT_START + ABSOLUTE_URL_REGEX,
     "@import\g<spacing>\g<quote>/\g<url>","/%(url)s","@import%(spacing)s%(quote)s%(fullurl)s",'9'),
 
 (CSS_URL_START + BASE_RELATIVE_URL_REGEX,
      "url(\g<quote>/%(base)s/\g<url>","/%(base)s/%(url)s","url(%(quote)s%(fullurl)s",'12'),
      
  (CSS_URL_START + SAME_DIR_URL_REGEX,
     "url(\g<quote>%(accessed_dir)s\g<url>","/%(base)s%(accessed_dir)s%(url)s","url(%(quote)s%(fullurl)s",'10'),
  
  (CSS_URL_START + TRAVERSAL_URL_REGEX,
      "url(\g<quote>%(accessed_dir)s/\g<relative>/\g<url>","%(accessed_dir)s/%(relative)s%(url)s","url(%(quote)s%(fullurl)s",'11'),
 
  
 
  (CSS_URL_START + ABSOLUTE_URL_REGEX,
      "url(\g<quote>/\g<url>","/%(url)s","url(%(quote)s%(fullurl)s",'13'),
]

################################################################################

def TransformContent(base_url, accessed_url, content,is_html=True,ChineseWordsencoding=True,whitelist=''):    
    #base_url = b64.uri_b64decode(base_url)
    url_obj = urlparse.urlparse(accessed_url)
    accessed_dir = os.path.dirname(url_obj.path)
    if not accessed_dir.endswith("/"):
        accessed_dir += "/"
    
    '''URL编码'''
    #logging.info('base_url:%s  accessed_dir:%s '%(base_url,accessed_dir))    
    for pattern, _,fullurl,result,number in REPLACEMENT_REGEXES:        
        p = re.compile(pattern)
        #logging.error('pattern %s begin:%s'%(number,pattern))        
        
        def mvalue(m,key):
            return m.groupdict().has_key(key) and m.group(key) or ''        
        def func(m):
            '''  替换成编码的地址 '''                        
            #"%(tag)s%(equals)s%(quote)s/%(url)s"),
                ## ( m.group('url').endswith("/") and number=="5"  ) or \
            endwith_slash_gt = \
                     ( m.group('url').endswith(";") and (number in ["9" ,"6" ,"8"])  ) or \
                     ( m.group('url').endswith("/") and number in ["1" ,"3","5"] and m.string.find('/>')>=0 \
                       and (mvalue(m,'tag')=='src' and m.end('url')== (m.string.find('/>')+1 ) )  \
                        ) 
            #logging.error('No:%s tag:%s end of url:%s,findbegin:%s'%(number,mvalue(m,'tag'),m.end('url'), m.string.find('/>')+1))
            last = m.group('url')[len(m.group('url'))-1:]
            url_in = ''
            if endwith_slash_gt:
                url_in = m.group('url')[:len(m.group('url'))-1] and m.group('url')[:len(m.group('url'))-1] or ''
            else:
                url_in = m.group('url')
            
            result_fullurl = scheme ='' 
            #书签 , javascript
            #No_b64_encoding = m.group('url').lstrip().startswith('#') or  m.group('url').lstrip().lower().startswith('javascript')
            No_b64_encoding = [x for x in ['#','javascript'] if m.group('url').lstrip().startswith(x)] 
            
            if No_b64_encoding:
                result_fullurl = fullurl%{
                                      "base": '',
                                      #"netloc":url_obj.netloc,
                                      "accessed_dir":  '',
                                      'url':m.group('url'),
                                      'relative':'',
                                      }
                result_fullurl = result_fullurl[1:]
                #logging.error('%s url:%s %s %s'%(number,m.group('url'),endwith_slash_gt ,len(m.group('url'))    ))
            else:
                scheme =  m.groupdict().has_key('scheme') and m.group('scheme') or url_obj.scheme
                result_fullurl = '%s:/'%scheme.replace(":","") + fullurl%{
                                      "base": base_url,
                                      #"netloc":url_obj.netloc,
                                      "accessed_dir":  (accessed_dir),
                                      'url':m.groupdict().has_key('url') and url_in or '',
                                      'relative':m.groupdict().has_key('relative') and m.group('relative') or '',
                                      } 
            
            #logging.error('\n\n %s result_fullurl result : %s '%(number,result_fullurl ))
            #logging.error('scheme:"%s" base_url:%s accessed_dir:%s'%(scheme,base_url,accessed_dir) )
            #logging.error('%s url:%s %s %s'%(number,m.group('url'),endwith_slash_gt ,len(m.group('url'))    ))
            #result_fullurl = result_fullurl[1:]
            
            kk = result%{
                         'fullurl':  No_b64_encoding and result_fullurl or '/'+b64.uri_b64encode(result_fullurl) + (endwith_slash_gt and last or ""),
                         'tag':m.groupdict().has_key('tag') and m.group('tag') or '',
                         'equals':m.groupdict().has_key('equals') and m.group('equals') or '',
                         'quote':m.groupdict().has_key('quote') and m.group('quote') or '',
                         'spacing':m.groupdict().has_key('spacing') and m.group('spacing') or '',                         
                         } 
            #logging.info('uri_b64encode:%s'%kk)
            #logging.info('pattern %s end:%s '%(number,pattern))
            #logging.info('%s result : %s '%(number,result_fullurl))
            #logging.error('string : %s '%(m.string))
            
            return kk
        
        #content = re.sub(pattern, (fixed_replacement), (content))
        content = p.sub( func, (content))
    
    '''汉字编码'''
    def func2(m):  
        #encode_m = ord( m.group(0)) 
        mm =  '\0'.join(['&#'+str(ord(i))+';' for i in m.group(0)])
        return mm
    rc=re.compile(ur'[\u4E00-\u9FA5]+',re.IGNORECASE)  
    def encodechinese(mycontent,mycoding):
        if mycoding:
            mycontent = mycontent.decode(mycoding).decode('utf-8')
        return rc.sub(func2,mycontent)
    cachekey = 'coding_cache_%s'%get_url_key_name(url_obj.netloc)
    codinglist = ['utf8','utf-8','utf-16','big5','gb2312','gbk','gb18030']
    def get_coding():
        if not is_html: return None #不是html文件
        
        #如果在白名单，即使ChineseWordsencoding设置为否，也进行编码
        if whitelist!='':
            #格式是： twitter.com:utf-8$google.com:utf-8          
            w =[ {'site':x.split(':')[0],'encoding':x.split(':')[1]} for x in whitelist.split('$') if x.strip()!='' and x.index(':')>=0 and url_obj.netloc.endswith(x.split(':')[0]) ]
            if w:
                return w[0]['encoding']
                #logging.error(w[0])        
        
        #如果不在白名单，而且ChineseWordsencoding设置为是，进行检测        
        if ChineseWordsencoding :
            #memcahce查找
            mem_coding = mymemcache.cache_get(cachekey)
            if mem_coding:
                return mem_coding
        
            '''  如果是Html文件，编码其中的中文部分 '''        
            try:                 
                detectcoding = chardet.detect(content)
                coding = detectcoding and detectcoding['encoding'] or None                    
                if  coding and coding.lower() in codinglist:                              
                    #logging.error(coding)                
                    return coding                 
            except Exception,e:                            
                logging.info(u'检测编码失败 %s'%e)
                return None
        return None
   
    
    coding = get_coding()

    if is_html and (coding or ChineseWordsencoding): 
        if coding:
            codinglist =  [ x for x in  codinglist if x!=coding]
            codinglist[0:0] = [coding]
        processOK = False      
        for c in codinglist :
            try:
                #logging.error(coding)                
                content = encodechinese(content,c )
                mymemcache.cache_get_or_put(cachekey, coding, True, 60*60*24*10, force_nosave=False)
                logging.info(u'编码成功 ,%s使用的是：  %s'%(url_obj.netloc,c) )
                processOK = True
                break
            except Exception,e: 
                logging.info(u'编码失败 ,%s使用的不是：  %s'%(url_obj.netloc,c) )
                processOK = False
                pass
        if processOK == False:
            try: content = encodechinese(content,None )
            except: pass
    #content = repr(content.decode('big5'))    
    return content

import hashlib
def get_url_key_name(url):
    url_hash = hashlib.sha256()
    url_hash.update(url)
    return "hash_" + url_hash.hexdigest()
      
