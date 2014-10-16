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
import random
from random import choice
import math

# ------  GAE Datastore -----
from google.appengine.ext import db
from dbmodel import Pothole
from dbmodel import PotholeReportLog
import sendgrid

# ------  XLS support -----
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
import xlrd


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
        self.render_template("index-admin.html", args)

# =report
class PotholeReportAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back

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

        if user == "":
            user = ip
        report_type = "web_app";        
        self.addpothole(lat, lon, user, report_type)       

        json_result = dict(
            status = 'success',
            message = 'Add pothole success to '+str(lat)+"/"+str(lon)+'!'
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

        # Center 42.3514/-71.0554
        # Demo = lat=42.3514&lon=-71.0554
        #
        pothole_contextio = dict( lat = 42.3518, lon = -71.0558 )
        pothole_twilio = dict( lat =  42.3510, lon =  -71.0550 )
        
        if report_type == "contextio":
            user = "Context.io"
            lat = pothole_contextio["lat"] + random.uniform( 0, 0.01)
            lon = pothole_contextio["lon"] + random.uniform( 0, 0.01)
        elif report_type == "twilio":
            user = "twilio"
            lat = pothole_twilio["lat"] - random.uniform( 0, 0.01)
            lon = pothole_twilio["lon"] - random.uniform( 0, 0.01)
        self.addpothole( lat, lon, user, report_type)

        json_result = dict(
            status = 'success',
            message = 'I get something'
        )
        self.response.out.write(self.json_output(json_result, callback))

    def addpothole(self, lat, lon, user, report_type):

        nowtime = int(time.time())

        # Add pothole
        new_pothole = Pothole()
        new_pothole._set_location(lat, lon)
        #new_pothole._set_latitude(lat)
        #new_pothole._set_longitude(lon)
        # -- UTF-8 issue anchor --
        new_pothole.update_location()
        new_pothole.case_status = "Open"
        new_pothole.report_type = report_type
        new_pothole.time = nowtime
        new_pothole.put()

        # Add potholelog
        new_pothole_log = PotholeReportLog()
        new_pothole_log.user = user
        new_pothole_log.message = "User "+user+" add a pothole @lat:"+str(lat)+" lon:"+str(lon)
        new_pothole_log.time = nowtime
        new_pothole_log.put()



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
        # Working json code
        callback = self.request.get('callback')     #jsonp call back
        """
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
        icon_preset = dict(
                iconUrl = baseurl + "/assets/img/pothole-sign.png",
                iconSize = [30, 30],
                iconAnchor =  [15, 15],
                popupAnchor = [0, -15],
                className = "dot"
            )
        icon_twilio = dict (
                iconUrl = baseurl + "/assets/img/pothole-twilio.png",
                iconSize = [30, 30],
                iconAnchor =  [15, 15],
                popupAnchor = [0, -15],
                className = "dot"
            )
        icon_contextio = dict (
                iconUrl = baseurl + "/assets/img/pothole-contextio.png",
                iconSize = [30, 30],
                iconAnchor =  [15, 15],
                popupAnchor = [0, -15],
                className = "dot"
            )
        if json_type == "geojson":
            for pothole in potholeResults:
                if pothole.report_type == "twilio":
                    icon_set = icon_twilio
                elif pothole.report_type == "contextio":
                    icon_set = icon_contextio
                else:
                    icon_set = icon_preset
                pothole_json = dict(
                    time = str(pothole.time),
                    type = "Feature",
                    geometry =  dict(
                        type = "Point",
                        coordinates = [pothole.location.lon, pothole.location.lat]
                    ),
                    properties = dict(
                        title = "Pothole",
                        icon = icon_set
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
        """
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
            'lon': result.location.lon,
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

class SendGridAPI(AppHandler):
    def get(self):
        callback = self.request.get('callback')     #jsonp call back
        sg = sendgrid.SendGridClient('ktu219', 'a0920788681')
        html = "<h1>Pothole Report</h1><hr/>"
        logDB = db.GqlQuery(
                    "SELECT message FROM PotholeReportLog "
                )
        logResults = logDB.fetch(100)
        output = []
        for log in logResults:
        	html += "<div class=''><h3>"+log.message+"</h3></div>"

        message = sendgrid.Mail(to='ppjoey@gmail.com', subject='BattleHack 2014 : Pothole Report', html= html, text="Report is generated in text", from_email='report@pothole-sonar.com')
        status, msg = sg.send(message)

        json_result = dict(
            status = 'success',
            message = "report is now sent to your email:"
        )
        self.response.out.write(self.json_output(json_result, callback))

class XlsUploader(BaseHandler):
    def get(self):
        self.render_template("xls.html", 
            {'form_url': blobstore.create_upload_url('/xlsuploader')}
            )

class XlsUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        blob_xls = self.get_uploads()[0]
        data = self.read_rows(blob_xls)
        logging.info(data)
        self.redirect('/')

    def read_rows(self, inputfile):
        rows = []
        wb = xlrd.open_workbook(file_contents=inputfile.open().read())
        sh = wb.sheet_by_index(0)
        for rownum in range(sh.nrows):
            rows.append(sh.row_values(rownum))
        return rows

app = webapp2.WSGIApplication([
    ('/', IndexHandler),
    ('/api/show', PotholeShowAPI),
    ('/api/showlog', PotholeShowLogAPI),
    ('/api/report', PotholeReportAPI),
    ('/api/sendgrid', SendGridAPI),
    ('/xls', XlsUploader),
    ('/xlsuploader', XlsUploadHandler),
], debug=True)
