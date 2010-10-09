# -*- coding: utf-8 -*- 
import sys
import re
import urllib
import urllib2
from cookielib import CookieJar

class GoogleLogin:
    def __init__(self, email, password,continuepage,cookiejar=None):
        
        if cookiejar  is None:
            cookiejar = CookieJar()
            
        # Set up our opener
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
        urllib2.install_opener(self.opener)
        
        # Define URLs
        self.loing_page_url = 'https://www.google.com/accounts/ServiceLogin'
        self.authenticate_url = 'https://www.google.com/accounts/ServiceLoginAuth' 
        #self.gv_home_page_url = 'https://www.google.com/voice/#inbox'
        self.continuepage = continuepage
        
        # Load sign in page
        login_page_contents = self.opener.open(self.loing_page_url).read()

        # Find GALX value
        galx_match_obj = re.search(r'name="GALX"\s*value="([^"]+)"', login_page_contents, re.IGNORECASE)
        
        galx_value = galx_match_obj.group(1) if galx_match_obj.group(1) is not None else ''
        
        # Set up login credentials
        login_params = urllib.urlencode( { 
            'Email' : email,
            'Passwd' : password,
            'continue' : self.continuepage,
            'GALX': galx_value
        })

        # Login
        self.opener.open(self.authenticate_url, login_params)

        # Open GV home page
        gv_home_page_contents = self.opener.open(self.continuepage).read()

        # Fine _rnr_se value
        key = re.search(email, gv_home_page_contents)
        
        if not key:
            self.logged_in = False
        else:
            self.logged_in = True
            self.key = key.group(1)
        
        self.cookiejar = cookiejar