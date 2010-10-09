# -*- coding: utf-8 -*- 
import os
import urllib
import urllib2
import cookielib

class xAppAuth:
    def __init__(self,user,password,appName):
        self.user = user
        self.password = password
        self.appName = appName
        self.authtoken = None
        
    def getAuthtoken(self,Refresh = False,cookiejar=None):
        if self.authtoken is None or Refresh:
            if cookiejar is None:
                cookiejar = cookielib.LWPCookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            urllib2.install_opener(opener)
            auth_uri = 'https://www.google.com/accounts/ClientLogin'
            authreq_data = urllib.urlencode({ "Email": self.user,
                "Passwd": self.password,
                "service": "ah",
                "source": self.appName,
                "accountType": "HOSTED_OR_GOOGLE" })
            auth_req = urllib2.Request(auth_uri, data=authreq_data)
            auth_resp = urllib2.urlopen(auth_req)
            auth_resp_body = auth_resp.read()
            # auth response includes several fields – we're interested in
            # the bit after Auth=
            auth_resp_dict = dict(x.split("=")  for x in auth_resp_body.split("\n") if x)
            self.authtoken = auth_resp_dict["Auth"]
        return self.authtoken,cookiejar
    
    def getAuthUrl(self,Uri,AppName):
        serv_uri = Uri
        serv_args = {}
        serv_args['continue'] = serv_uri
        serv_args['auth'] = self.getAuthtoken()
        return "http://"+AppName+".appspot.com/_ah/login?%s" % (urllib.urlencode(serv_args))
    
    def getAuthRequest(self,Uri,AppName):
        return urllib2.Request(self.getAuthUrl(Uri,AppName))
    
    def getAuthResponse(self,Uri,AppName):
        return urllib2.urlopen(self.getAuthRequest(Uri,AppName))
    
    def getAuthRead(self,Uri,AppName):
        return self.getAuthResponse(Uri,AppName).read()
    