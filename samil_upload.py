#!/usr/bin/env python3

# samil_upload.py
#
# Daemon for automatically uploading Samil Power data to PVOutput. Uses samil.py
# and pvoutput.py

import samil
import pvoutput

import sched
import time
import configparser
import logging
import os.path

def next_timestamp(boundary):
    """Returns a timestamp which is after the current timestamp and on the given
    boundary."""
    timestamp = time.time()
    return timestamp + boundary - timestamp % boundary

def upload(inverter, pvoutput, scheduler, timestamp, boundary):
    """Retrieves and uploads inverter data, and schedules the next upload."""
    values = inverter.request_values()
    data = {
        'd': time.strftime('%Y%m%d'),
        't': time.strftime('%H:%M'),
        'v1': round(values['energy_today'] * 1000),
        'v2': values['output_power'],
        'v5': values['internal_temp'],
        'v6': values['grid_voltage']
    }
    logging.info('Uploading: %s', data)
    pvoutput.add_status(data)
    sched_args = (inverter, pvoutput, scheduler, timestamp + boundary, boundary)
    scheduler.enterabs(timestamp + boundary, 1, upload, sched_args)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Read config file
    config = configparser.ConfigParser()
    config.read_file(open(
        os.path.dirname(os.path.abspath(__file__)) + '/samil_upload.ini'))
    api_key = config['System']['ApiKey']
    system_id = config['System']['SystemId']
    interface_ip = config['Core']['InterfaceIP']
    # The boundary on which to upload data in seconds
    boundary = config.getint('Core', 'StatusInterval') * 60
    pvout = pvoutput.System(api_key, system_id)
    # Connect to inverter
    with solar.Inverter(interface_ip) as inverter:
        # Schedule upload at next boundary
        s = sched.scheduler(time.time, time.sleep)
        timestamp = next_timestamp(boundary)
        logging.info('Scheduled first upload at next boundary')
        sched_args = (inverter, pvout, s, timestamp, boundary)
        s.enterabs(timestamp, 1, upload, sched_args)
        # Run scheduler
        s.run()
