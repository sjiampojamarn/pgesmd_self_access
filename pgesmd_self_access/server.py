"""A server that handles POST from PGE SMD servers."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from xml.etree import cElementTree as ET
import ssl
import logging
import os
import time

from .helpers import parse_espi_data, get_bulk_id_from_xml
from .utils import InfluxDBAccessApi, parse_espi_data_from_xml

_LOGGER = logging.getLogger(__name__)


class PgePostHandler(BaseHTTPRequestHandler):
    """Handle POST from PGE."""

    api = None
    save_file = None
    filename = None
    to_db = None

    def do_POST(self):
        """Download the ESPI XML and save to database."""
        _LOGGER.debug(f"Received POST from {self.address_string()}")

        if self.path == "/test":
            self.send_response(200)
            self.end_headers()
            return

        if not self.path == "/pgesmd":
            return

        _LOGGER.info(f"Received POST from {self.address_string()}")

        body = self.rfile.read(int(self.headers.get("Content-Length")))
        _LOGGER.debug(body)
        resource_uri_list = []
        for line in ET.fromstring(body):
            resource_uri_list.append(line.text)
        
        self.send_response(200)
        self.end_headers()
        
        for resource_uri in resource_uri_list:
            timestamp = time.strftime("%y.%m.%d %H:%M:%S", time.localtime())
            self.filename = f"{timestamp}_{resource_uri[-5:-1]}"
            _LOGGER.debug(f"resource_uri: {resource_uri}")
            _LOGGER.debug(f"filename: {self.filename}")

            if not resource_uri[: len(self.api.utility_uri)] == self.api.utility_uri:
                _LOGGER.error(
                    f"POST from {self.address_string} contains: "
                    f"{body}     "
                    f"{resource_uri[:len(self.api.utility_uri)]}"
                    f" != {self.api.utility_uri}"
                )
                continue 

            xml_data = self.api.get_espi_data(resource_uri)

            if self.save_file:
                save_name = self.save_file(xml_data, filename=self.filename)
                if save_name:
                    _LOGGER.info(f"XML saved at {save_name}")
                else:
                    _LOGGER.error("File not saved.")

            if self.to_db:
                _LOGGER.info("Database: pushing to InfluxDB.")
                influxdb_access_api = InfluxDBAccessApi()
                record_count = 0
                for record in parse_espi_data_from_xml(xml_data):
                    influxdb_access_api.pushData(record)
                    record_count += 1
                    if (record_count % 500) == 0:
                        _LOGGER.info(f"Database: pushed {record_count} records so far")
                _LOGGER.info(f"Database: pushed {record_count} records")


class SelfAccessServer:
    """Server class for PGE SMD Self Access API."""

    def __init__(
        self, api_instance, save_file=None, filename=None, to_db=True, close_after=False
    ):
        """Initialize and start the server on construction."""
        PgePostHandler.api = api_instance
        PgePostHandler.save_file = save_file
        PgePostHandler.filename = filename
        PgePostHandler.to_db = to_db
        server = HTTPServer(("", 7999), PgePostHandler)

        server.socket = ssl.wrap_socket(
            server.socket,
            certfile=api_instance.cert[0],
            keyfile=api_instance.cert[1],
            server_side=True,
        )

        if close_after:
            server.handle_request()
        else:
            server.serve_forever()
