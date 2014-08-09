from google.appengine.ext import ndb

class pothole(ndb.Model):
    case_status = ndb.StringProperty()
    case_title = ndb.StringProperty()
    location = ndb.StringProperty()
    location = ndb.StringProperty()
    open_dt = ndb.DateTimeProperty()
    close_dt = ndb.DateTimeProperty()