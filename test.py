#!/usr/bin/env python3

from unittest.mock import Mock, MagicMock
import samil_upload
import configparser
import logging

def one_system_default(config):
    config['DEFAULT'] = {'Status interval': '1', 'API key': 'a', 'System ID': 'a'}

def one_system_section(config):
    config['DEFAULT'] = {'Status interval': '1'}
    config['Sys'] = {'API key': 'a', 'System ID': 'a'}

def two_systems_combine(config):
    config['DEFAULT'] = {'Status interval': '1'}
    config['Sys1'] = {'API key': 'a', 'System ID': 'a'}
    config['Sys2'] = {'API key': 'a', 'System ID': 'a'}

def two_systems_separate(config):
    config['DEFAULT'] = {'Status interval': '1'}
    config['One'] = {'API key': 'a', 'System ID': '1'}
    config['Two'] = {'API key': 'a', 'System ID': '2'}

def three_systems_combine(config):
    config['DEFAULT'] = {'Status interval': '1', 'API key': 'a', 'System ID': 'a'}
    config['One'] = {}
    config['Two'] = {}
    config['Three'] = {}

def two_status_intervals(config):
    config['DEFAULT'] = {'API key': 'a'}
    config['One'] = {'System ID': '1', 'Status interval': '1'}
    config['Two'] = {'System ID': '2', 'Status interval': '2'}

def ip_filter_apply(config):
    config['DEFAULT'] = {'Status interval': '1', 'API key': 'a'}
    config['System'] = {'System ID': 'a', 'IP address': '192.168.0.1'}

def ip_filter_no_apply(config):
    config['DEFAULT'] = {'Status interval': '1', 'API key': 'a'}
    config['System'] = {'System ID': 'a', 'IP address': '192.168.0.2'}

def interface_ip(config):
    config['DEFAULT'] = {'Interface IP': '192.168.0.3', 'API key': 'a',
            'System ID': 'a', 'Status interval': '1'}

def main(func):
    config = configparser.ConfigParser()
    func(config)
    inverter = MagicMock()
    inverter.return_value.__enter__.return_value.request_values.side_effect = [
            {
                'operating_mode': 'normal',
                'energy_today': 0.9,
                'output_power': 120,
                'internal_temp': 18.0,
                'grid_voltage': 220.0
                },
            {
                'operating_mode': 'normal',
                'energy_today': 1.1,
                'output_power': 180,
                'internal_temp': 22.0,
                'grid_voltage': 240.0
                },
            {
                'operating_mode': 'normal',
                'energy_today': 1.1,
                'output_power': 180,
                'internal_temp': 22.0,
                'grid_voltage': 240.0
                }
            ]
    inverter.return_value.__enter__.return_value.addr = ('192.168.0.1',)
    #inverter.__enter__.return_value = inverter_instance
    try:
        samil_upload.main(config, inverter)
    except KeyboardInterrupt:
        pass
    print(inverter.mock_calls)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(three_systems_combine)
