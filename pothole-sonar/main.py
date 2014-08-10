from __future__ import with_statement
#
#    Battle hack 2014 - Pothole sonar
#
#
# links:
# http://data.cityofboston.gov/resource/awu8-dc52.json?CASE_STATUS=OPEN&type=Request%20for%20Pothole%20Repair

# ------  Basic component ------
import os
import webapp2
from google.appengine.ext.webapp import template
from geo import geotypes

# ------  GAE Datastore -----
from google.appengine.ext import db
from dbmodel import Pothole
from dbmodel import PotholeReportLog

def _merge_dicts(*args):
  """Merges dictionaries right to left. Has side effects for each argument."""
  return reduce(lambda d, s: d.update(s) or d, args)

class BaseHandler(webapp2.RequestHandler):
    def render_template(self, file, template_args):
        path = os.path.join(os.path.dirname(__file__), file)
        self.response.out.write(template.render(path, template_args))

class AppHandler(webapp2.RequestHandler):
    def json_output(self, json_output, callback):
        json_output = str(json_output).replace("'",'"')
        if callback:
            return callback+"("+json_output+");"
        else:
            return json_output

class IndexHandler(BaseHandler):
    def get(self):
        self.render_template("index.html", dict())

class PotholeReportAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        lat = float(self.request.get('lat'))
        lon = float(self.request.get('lon'))

        if not lat or not lon:
            json_result = dict(
                status = 'error',
                message = 'No lat or lon!'
            )
            return self.response.out.write(self.json_output(json_result, callback))

        ip = str(self.request.remote_addr)
        user = self.request.get('user')

        # Add pothole
        new_pothole = Pothole()
        new_pothole._set_location(lat, lon)
        #new_pothole._set_latitude(lat)
        #new_pothole._set_longitude(lon)
        new_pothole.update_location()
        new_pothole.case_status = "Open"
        new_pothole.report_type = "web_app"
        new_pothole.put()

        # Add potholelog
        new_pothole_log = PotholeReportLog()
        if user == "":
        	user = ip
        new_pothole_log.user = user
        new_pothole_log.message = "Web User "+user+" add a pothole @lat:"+str(lat)+" lon:"+str(lon)
        new_pothole_log.put()

        json_result = dict(
            status = 'success',
            message = 'Add pothole success!'
        )
        self.response.out.write(self.json_output(json_result, callback))


class PotholeShowLogAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        logDB = db.GqlQuery(
                    "SELECT user,message,time FROM PotholeReportLog "
                    "ORDER by time DESC"
                )
        logResults = logDB.fetch(10)

        output = []
        for log in logResults:
            log_json = dict(
                    user      = str(log.user),
                    message = str(log.message),
                    time = str(log.time)
                )
            output.append(log_json)

        self.response.out.write(self.json_output(output, callback))


class PotholeShowAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back

        try:
            center = geotypes.Point(float(self.request.get('lat')),float(self.request.get('lon')))
        except ValueError:
            json_result = dict(
                status = 'error',
                message = 'lat and lon parameters must be valid latitude and longitude values.'
            )
            return self.response.out.write(self.json_output(json_result, callback))

        max_results = 100
        if self.request.get('maxresults'):
          max_results = int(self.request.get('maxresults'))
        
        max_distance = 8000 # 80 km ~ 50 mi
        if self.request.get('maxdistance'):
          max_distance = float(self.request.get('maxdistance'))

        # Query start
        base_query = Pothole.all()
        results = Pothole.proximity_fetch(
            base_query,
            center, max_results=max_results, max_distance=max_distance)

        public_attrs = Pothole.public_attributes()
        results_obj = [
          _merge_dicts({
            'lat': result.location.lat,
            'lng': result.location.lon,
            },
            {'case_status': str(result.case_status),
             'id': str(result.key().id()),
             'report_type': str(result.type)
            })
            #{dict([(attr, getattr(result, attr))
            #                  for attr in public_attrs])})
          for result in results]

        json_result = dict(
            status = 'success',
            total = str(len(results)),
            results = results_obj
        )
        self.response.out.write(self.json_output(json_result, callback))


app = webapp2.WSGIApplication([
    ('/', IndexHandler),
    ('/api/show', PotholeShowAPI),
    ('/api/showlog', PotholeShowLogAPI),
    ('/api/report', PotholeReportAPI),
], debug=True)
