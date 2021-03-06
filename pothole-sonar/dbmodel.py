
from google.appengine.ext import db

from geo.geomodel import GeoModel

class Pothole(GeoModel):
  case_status = db.StringProperty()
  report_type = db.StringProperty()
  time = db.IntegerProperty()

  @staticmethod
  def public_attributes():
    """Returns a set of simple attributes on public school entities."""
    return ['case_status', 'report_type']

  def _set_location(self, lat, lon):
    self.location = db.GeoPt( lat, lon)
  def _get_latitude(self):
    return self.location.lat if self.location else None
  def _set_latitude(self, lat):
    if not self.location:
      self.location = db.GeoPt()
    self.location.lat = lat    
  latitude = property(_get_latitude, _set_latitude)

  def _get_longitude(self):
    return self.location.lon if self.location else None
  def _set_longitude(self, lon):
    if not self.location:
      self.location = db.GeoPt()
    self.location.lon = lon
  longitude = property(_get_longitude, _set_longitude)

class PotholeReportLog(db.Model):
  user = db.StringProperty()
  message = db.StringProperty()
  time = db.IntegerProperty()





