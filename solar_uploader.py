#!/usr/bin/env python3

# solar_uploader.py
#
# Daemon for automatically uploading Samil Power data to PVOutput. Uses solar.py
# and pvoutput.py

import solar
import pvoutput
import sched
import time
import configparser
import logging
import os.path

def next_boundary(timestamp, boundary):
    """Returns a timestamp which is after the given time and on the given
    boundary."""
    # TODO: create a more robust implementation using the 'datetime' library
    return timestamp + boundary - timestamp % boundary

def upload():
    global s
    values = inverter.request_values()
    if values['output_power'] > 0:
        data = {
            'd': time.strftime('%Y%m%d'),
            't': time.strftime('%H:%M'),
            'v1': round(values['energy_today'] * 1000),
            'v2': values['output_power'],
            'v5': values['internal_temp'],
            'v6': values['grid_voltage']
        }
        logging.info('Uploading: %s', data)
        pv.add_status(data)
    next_timestamp = next_boundary(time.time(), boundary)
    s.enterabs(next_timestamp, 1, upload, ())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Read config file
    config = configparser.ConfigParser()
    config.read_file(open(
        os.path.dirname(os.path.abspath(__file__)) + '/solar_uploader.ini'))
    api_key = config['System']['ApiKey']
    system_id = config['System']['SystemId']
    interface_ip = config['Core']['InterfaceIP']
    # The boundary on which to upload data in seconds
    boundary = config.getint('Core', 'StatusInterval') * 60
    pv = pvoutput.System(api_key, system_id)
    # Connect to inverter
    inverter = solar.Inverter(interface_ip)
    # Schedule upload at next 5-minute boundary
    s = sched.scheduler(time.time, time.sleep)
    next_timestamp = next_boundary(time.time(), boundary)
    s.enterabs(next_timestamp, 1, upload, ())
    # Run scheduler
    s.run()
