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
import logging
from datetime import datetime, timedelta    #for timezone
import time
import urllib2, urllib, urlparse            #for url parse

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

# =index
class IndexHandler(BaseHandler):
    def get(self):
        urlobject = urlparse.urlparse(self.request.url)
        baseurl = urlparse.urlunparse((urlobject.scheme, urlobject.netloc, '', '', '', ''))
        args = dict(
            baseurl = baseurl
            )
        self.render_template("index.html", args)

# =report
class PotholeReportAPI(AppHandler):
    # Center 42.3514/-71.0554
    pothole_contextio = { "lat": 42.3516, "lon": -71.0556 }

    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        nowtime = int(time.time())

        try:
            lat = float(self.request.get('lat'))
            lon = float(self.request.get('lon'))
        except ValueError:
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
        new_pothole.time = nowtime
        new_pothole.put()

        # Add potholelog
        new_pothole_log = PotholeReportLog()
        if user == "":
            user = ip
        new_pothole_log.user = user
        new_pothole_log.message = "Web User "+user+" add a pothole @lat:"+str(lat)+" lon:"+str(lon)
        new_pothole_log.time = nowtime
        new_pothole_log.put()

        json_result = dict(
            status = 'success',
            message = 'Add pothole success!'
        )
        self.response.out.write(self.json_output(json_result, callback))

    def post(self):
        callback = self.request.get('callback')     #jsonp call back
        if callback == "fail":
            logging.debug("The failure is too stronk.")
            return

        # TODO: Json decode body for user

        report_type = str(self.request.get("type"))
        logging.debug("I get someone posting something from "+report_type+"!")
        json_result = dict(
            status = 'success',
            message = 'I get something'
        )
        self.response.out.write(self.json_output(json_result, callback))


# =showlog
class PotholeShowLogAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        request_time = self.request.get("time")
        db_time = 0
        if request_time.isdigit():
            db_time = int(request_time)

        logDB = db.GqlQuery(
                    "SELECT user,message,time FROM PotholeReportLog "
                    "WHERE time > :dbtime "
                    "ORDER by time DESC ",
                    dbtime = db_time
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


# =show
class PotholeShowAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        request_time = self.request.get("time")
        json_type = self.request.get("jsontype")
        urlobject = urlparse.urlparse(self.request.url)
        baseurl = urlparse.urlunparse((urlobject.scheme, urlobject.netloc, '', '', '', ''))

        db_time = 0
        if request_time.isdigit():
            db_time = int(request_time)

        potholeDB = db.GqlQuery(
                    "SELECT report_type,case_status,time,location FROM Pothole "
                    "WHERE time > :dbtime "
                    "ORDER by time DESC ",
                    dbtime = db_time
                )
        potholeResults = potholeDB.fetch(100)
        output = []
        if json_type == "geojson":
            for pothole in potholeResults:
                pothole_json = dict(
                	time = str(pothole.time),
                    type = "Feature",
                    geometry =  dict(
                        type = "Point",
                        coordinates = [pothole.location.lon, pothole.location.lat]
                    ),
                    properties = dict(
                        title = "Pothole",
                        icon = dict(
	                        #iconUrl = "/assets/img/pothole-sign.png",
	                        iconUrl = baseurl + "/assets/img/pothole-sign.png",
	                        iconSize = [50, 50],
	                		iconAnchor =  [25, 25],
	                		popupAnchor = [0, -25],
	                		className = "dot"
                		)
                    )
                )
                output.append(pothole_json)
        else :
            # Regular json type for us to read
            for pothole in potholeResults:
                pothole_json = dict(
                        lat      = pothole.location.lat,
                        lon      = pothole.location.lon,
                        case_status = str(pothole.case_status),
                        report_type = str(pothole.report_type),
                        time = str(pothole.time)
                    )
                output.append(pothole_json)

        self.response.out.write(self.json_output(output, callback))

        return
        #
        #
        # disable approximately search
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
             'report_type': str(result.report_type),
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
