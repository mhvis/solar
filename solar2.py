#!/usr/bin/env python3.5

# solar2.py
#
# CLI monitoring tool for SolarRiver TD, SolarRiver TL-D and SolarLake TL
# series.

# (Needs at least Python 3.2 for 'int.to_bytes()')

import socket

import logging
#import argparse

_START = b'\x55\xaa'
# Request identifiers
_DISCOVERY_REQUEST = b'\x00\x40\x02', b'\x04\x3a'
_MODEL_REQUEST = b'\x01\x03\x02', b'\x01\x05'
_CURRENT_VALUES_REQUEST = b'\x01\x02\x02', b'\x01\x04'
_HISTORY_REQUEST = b'\x06\x01\x02', b'\x01\x2a'

def _construct_request(identifier, payload):
    """Construct a request message to send."""
    header, end = identifier
    payload_size = len(payload).to_bytes(2, byteorder='big')
    return _START + header + payload_size + payload + end

def _broadcast(identifier, payload):
    """Broadcast a message."""
    request = _construct_request(identifier, payload)
    logging.debug('Broadcasting message %s', request)
    # Send broadcast
    _bc.sendto(request, ('<broadcast>', 1300))

def _interpret_response(data):
    """Extracts header, payload and end from received data."""
    response_header = data[2:5]
    # Below is actually not used
    response_payload_size = int.from_bytes(data[5:7], byteorder='big')
    response_payload = data[7:-2]
    response_end = data[-2:]
    return response_header, response_payload, response_end


logging.basicConfig(level=logging.DEBUG)

# Binding TCP socket
logging.debug('Binding TCP socket on port 1200 for incoming inverters')
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 1200))
s.listen(5)
s.settimeout(5.0)

# Binding UDP socket
logging.debug('Binding UDP socket on port 1300 for broadcasting')
_bc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_bc.bind(('', 0))
_bc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

conn = None
while not conn:
    _broadcast(_DISCOVERY_REQUEST, b'I AM SERVER')
    try:
        conn, addr = s.accept()
        logging.info('New incoming connection from address %s', addr)
    except socket.timeout:
        logging.debug('Incoming connections listener timed out')

# Optionally close UDP broadcast socket as it is no longer needed
logging.debug('Closing UDP socket')
_bc.close()

def _req_res(identifier, payload):
    request = _construct_request(identifier, payload)
    logging.debug('Making request: %s', request)
    conn.send(request)

while True:
    message = input('Message: ')
    params = None
    if message == 'model':
        params = _MODEL_REQUEST, b''
    elif message == 'values':
        params = _CURRENT_VALUES_REQUEST, b''
    elif message == '1':
        params = (b'\x01\x00\x02', b'\x01\x02'), b''
    elif message == '2':
        params = (b'\x01\x09\x02', b'\x01\x0b'), b''
    elif message == '3':
        params = (b'\x04\x00\x02', b'\x01\x05'), b''
    else:
        continue
    request = _construct_request(*params)
    logging.debug('Making request: %s', request)
    conn.send(request)
    logging.debug('Awaiting response from inverter')
    data = conn.recv(1024)
    logging.debug('Received response: %s', data)
    if len(data) == 0:
        raise Exception('Connection closed')
    response = _interpret_response(data)
    logging.info('Response header: %s', response[0])
    logging.info('Response payload: %s', response[1])
    logging.info('Response end: %s', response[2])

    

#if __name__ == '__main__':
#    parser = argparse.ArgumentParser(description='Monitoring tool for '
#    'SolarRiver TD, SolarRiver TL-D and SolarLake TL inverter series.')
