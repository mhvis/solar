#!/usr/bin/env python3.5

# pvoutput.py
#
# Simple library for uploading data to PVOutput.

import urllib.request
import urllib.parse
import logging

class System:
    """Provides methods for direct uploading to PVOutput for set system."""
    
    def __init__(self, api_key, system_id):
        self.api_key = api_key
        self.system_id = system_id
    
    def add_output(self, data):
        """Add end of day output information. Data should be a dictionary with
        parameters as described here:
        http://pvoutput.org/help.html#api-addoutput ."""
        url = "http://pvoutput.org/service/r2/addoutput.jsp"
        self.__make_request(url, data)
    
    def add_status(self, data):
        """Add live output data. Data should contain the parameters as described
        here: http://pvoutput.org/help.html#api-addstatus ."""
        url = "http://pvoutput.org/service/r2/addstatus.jsp"
        self.__make_request(url, data)
    
    # Could add methods like 'get_status'

    def __make_request(self, url, data):
        logging.debug('Making request: %s, %s', url, data)
        data = urllib.parse.urlencode(data)
        data = data.encode('ascii')
        req = urllib.request.Request(url, data)
        req.add_header('X-Pvoutput-Apikey', self.api_key)
        req.add_header('X-Pvoutput-SystemId', self.system_id)
        r = urllib.request.urlopen(req)
        if r.status != 200:
            logging.warning('%s request failed: %s %s', url, r.status, r.reason)
        else:
            logging.info('%s: %s %s', url, r.status, r.reason)
