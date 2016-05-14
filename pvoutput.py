#!/usr/bin/env python3

# pvoutput.py
#
# CLI for PVOutput.

import urllib.request
import logging

def add_output(key, sid, data):
    pass

def add_status(key, sid, data):
    __make_request("http://pvoutput.org/service/r2/addstatus.jsp", key, sid, data)

def __make_request(url, key, sid, data):
    req = urllib.request.Request(url, data)
    req.add_header('X-Pvoutput-Apikey', key)
    req.add_header('X-Pvoutput-SystemId', sid)
    r = urllib.request.urlopen(req)
    if r.status != 200:
        logging.warning('%s request failed: %s %s', url, r.status, r.reason)
    else:
        logging.debug('%s: %s %s', url, r.status, r.reason)
