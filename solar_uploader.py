#!/usr/bin/env python3

# solar_uploader.py
#
# Daemon for automatically uploading SamilPower data to PVOutput. Uses solar.py
# and pvoutput.py

import solar
import pvoutput
import sched
import time
import configparser
import logging

logging.basicConfig(level=logging.INFO)

# The boundary on which to upload data in seconds (5 * 60 means every 5 minutes)
boundary = 5 * 60

def next_boundary(timestamp, boundary):
    """Returns a timestamp which is after the given time and on the given
    boundary."""
    return timestamp + boundary - timestamp % boundary

config = configparser.ConfigParser()
config.read('solar_uploader.ini')
api_key = config['System']['ApiKey']
system_id = config['System']['SystemId']
pv = pvoutput.System(api_key, system_id)
inverter = solar.Inverter()

s = sched.scheduler(time.time, time.sleep)

def upload():
    global s
    values = inverter.request_values()
    if values['output_power'] > 0:
        logging.debug('Going to upload now')
        data = {
            'd': time.strftime('%Y%m%d'),
            't': time.strftime('%H:%M'),
            'v1': round(values['energy_today'] * 1000),
            'v2': values['output_power'],
            'v5': values['internal_temp'],
            'v6': values['grid_voltage']
        }
        pv.add_status(data)
    next_timestamp = next_boundary(time.time(), boundary)
    logging.debug('Scheduling next upload for %s', next_timestamp)
    s.enterabs(next_timestamp, 1, upload, ())

next_timestamp = next_boundary(time.time(), boundary)
logging.debug('Scheduling first upload for %s', next_timestamp)
s.enterabs(next_timestamp, 1, upload, ())
s.run()
