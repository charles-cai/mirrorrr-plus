from google.appengine.ext import db

class EntryPoint(db.Model):
    translated_address = db.TextProperty(required=True)
    last_updated = db.DateTimeProperty(auto_now=True)
    display_address = db.TextProperty()
