#
#	Battle hack 2014 - Pothole sonar
#
#
# links:
# http://data.cityofboston.gov/resource/awu8-dc52.json?CASE_STATUS=OPEN&type=Request%20for%20Pothole%20Repair

# ------  Basic component ------
import os
import webapp2
from google.appengine.ext.webapp import template
# ------  GAE Datastore -----
from google.appengine.ext import ndb
import dbmodel

class BaseHandler(webapp2.RequestHandler):
    def render_template(self, file, template_args):
        path = os.path.join(os.path.dirname(__file__), file)
        self.response.out.write(template.render(path, template_args))

class IndexHandler(BaseHandler):
    def get(self):
        self.render_template("index.html", dict())

app = webapp2.WSGIApplication([
    ('/', IndexHandler)
], debug=True)
