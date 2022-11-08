"""Utils functions for pgesdm."""

import datetime
import logging
import os

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from operator import itemgetter
from xml.etree import cElementTree as ET
from io import StringIO

_LOGGER = logging.getLogger(__name__)

def parse_espi_data_from_xml_obj(xml, ns="{http://naesb.org/espi}"):
  """Parse espi data from xml file obj."""
  # Find all values
  it = map(itemgetter(1), iter(ET.iterparse(xml)))
  for data in it:
    if data.tag == f"{ns}powerOfTenMultiplier":
      mp = int(data.text)
    if data.tag == f"{ns}flowDirection":
      flowDirection = int(data.text)
    if data.tag == f"{ns}commodity":
      commodity = int(data.text)
    if data.tag == f"{ns}IntervalBlock":
      for interval in data.findall(f"{ns}IntervalReading"):
        time_period = interval.find(f"{ns}timePeriod")

        duration = int(time_period.find(f"{ns}duration").text)
        start = int(time_period.find(f"{ns}start").text)
        value = int(interval.find(f"{ns}value").text)
        wattHour = round(value * pow(10, mp), 3)
        tou = -1 if interval.find(f"{ns}tou") is None else int(interval.find(f"{ns}tou").text) 
        
        yield({
          'startDateTime': datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S'),
          'start': start,
          'commodity': commodity,
          'flowDirection': flowDirection,
          'tou': tou,
          'duration': duration,
          'wattHour': wattHour})
        

def parse_espi_data_from_xml(xml):
  """Parse espi data from xml."""
  xml = StringIO(xml)
  for record in parse_espi_data_from_xml_obj(xml):
    yield(record)


def parse_espi_data_from_xml_file(xml_path):
  """Parse espi data from xml file."""
  try:
    with open(xml_path) as xml:
      _LOGGER.debug(f"Parsing the xml {xml_path}")
      for record in parse_espi_data_from_xml_obj(xml):
        yield(record)
  except FileNotFoundError:
    _LOGGER.error(f"Input xml file not found at {xml_path}.")
    return None
  
  
class InfluxDBAccessApi:
  """InfluxDB api to push espi data into. Configs are from env."""
  def __init__(self):
    self.client = InfluxDBClient.from_env_properties()
    self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

  def pushData(self, data, measurement='pgesdm', bucket=os.environ['INFLUXDB_V2_BUCKET']):
    """Push data into InfluxDB. Expect data returned from parsing utils."""
    dataPoint = Point(measurement) \
      .tag("commodity", data["commodity"]) \
      .tag("flowDirection", data["flowDirection"]) \
      .field("tou", data["tou"]) \
      .field("duration", data["duration"]) \
      .field("wattHour", data["wattHour"]) \
      .time(data["start"], 's')
    self.write_api.write(bucket=bucket, record=dataPoint)
