#!/usr/bin/env python3.5

# solar.py
#
# Library and CLI tool for SolarRiver TD, SolarRiver TL-D and SolarLake TL
# series.
#
# (Requires Python 3.5)

import socket
import threading
import logging
import argparse

#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)

# Maximum time between packets (seconds float). If this time is reached a
# keep-alive packet is sent.
keep_alive_time = 10.0

class Inverter:
    """This class has all functionality. Making a new instance of this class
    will search the network for an inverter and connect to it. The
    initialization blocks until the connection is made. If there is no inverter,
    the call will keep on blocking.
    
    When the connection is made you can use the methods to make data requests to
    the inverter. All request methods block while waiting for the answer (for me
    it takes typically 1.5 seconds for the response to arrive).
    
    When the connection is lost an exception is raised the next time a request
    is made.
    
    Connecting to multiple inverters is possible by making multiple instances of
    this class. Each next instance will connect to a different inverter in the
    network. When there is no inverter available anymore, the next instance
    initialization will keep on blocking.
    
    (The request methods are thread-safe.)"""
    
    def __init__(self):
        # Connect
        self.sock, self.addr = _connect()
        # A lock to ensure a single message at a time
        self.lock = threading.Lock()
        # Start keep-alive sequence
        self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
        self.keep_alive.daemon = True
        self.keep_alive.start()

    def request_model_info(self):
        """Requests model information like the type, software version, and
        inverter 'name'."""
        #identifier = b'\x01\x03\x02', b'\x01\x05'
        #response = self.__make_request(identifier, b'')
        # TODO: format a nice return value
        raise NotImplementedError('Not yet implemented')
        #return response

    def request_values(self):
        """Requests current values which are returned as a dictionary."""
        identifier = b'\x01\x02\x02', b'\x01\x04'
        # Make request and receive response
        header, payload, end = self.__make_request(identifier, b'')
        # Separate each value
        values = zip(payload[0::2], payload[1::2])
        # Turn each value into an integer
        ints = [int.from_bytes(x, byteorder='big') for x in values]
        result = {
            'internal_temp': ints[0] / 10.0, # degrees C
            'pv1_voltage': ints[1] / 10.0, # V
            'pv2_voltage': ints[2] / 10.0, # V
            'pv1_current': ints[3] / 10.0, # A
            'pv2_current': ints[4] / 10.0, # A
            'total_operation_hours': ints[6], # h
            'energy_today': ints[8] / 100.0, # kWh
            'pv1_input_power': ints[19], # W
            'pv2_input_power': ints[20], # W
            'grid_current': ints[21] / 10.0, # A
            'grid_voltage': ints[22] / 10.0, # V
            'grid_frequency': ints[23] / 100.0, # Hz
            'output_power': ints[24], # W
            #'energy_total': ints[26] * 100.0, # kWh
        }
        # For more info on the data format:
        # https://github.com/mhvis/solar/wiki/Communication-protocol#messages
        return result

    def request_history(self, start, end):
        """Not yet implemented."""
        raise NotImplementedError('Not yet implemented')
        #identifier = b'\x06\x01\x02', b'\x01\x2a'
        #return self.__make_request(identifier, b'')
    
    def request_unknown_1(self):
        identifier = b'\x01\x00\x02', b'\x01\x02'
        response = self.__make_request(identifier, b'')
        return response
    
    def request_unknown_2(self):
        identifier = b'\x01\x09\x02', b'\x01\x0b'
        response = self.__make_request(identifier, b'')
        return response
    
    def request_unknown_3(self):
        identifier = b'\x04\x00\x02', b'\x01\x05'
        response = self.__make_request(identifier, b'')
        return response
    
    def __make_request(self, identifier, payload):
        """Directly makes a request and returns the response."""
        if self.sock is None:
            raise ConnectionClosedException('Connection was already closed')
        # Acquire socket request lock
        self.lock.acquire()
        # Cancel a (possibly) running keep-alive timer
        self.keep_alive.cancel()
        logging.debug('Sending request: %s, %s', identifier, payload)
        request = _construct_request(identifier, payload)
        self.sock.send(request)
        data = self.sock.recv(1024)
        if len(data) == 0:
            self.sock = None
            raise ConnectionClosedException('Connection closed')
        response = _tear_down_response(data)
        logging.debug('Received: %s', response)
        # Set keep-alive timer
        self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
        self.keep_alive.daemon = True
        self.keep_alive.start()
        # Release lock
        self.lock.release()
        return response
    
    def __keep_alive(self):
        """Makes a keep-alive request."""
        identifier = b'\x01\x09\x02', b'\x01\x0b'
        self.__make_request(identifier, b'')


class ConnectionClosedException(Exception):
    """Exception raised when the connection is closed or was already closed."""
    pass

# The TCP socket that listens for incoming connections
_server = None

def _connect():
    """Makes a connection to an inverter (the inverter that responds first).
    Blocks while waiting for an incoming inverter connection. Will keep blocking
    if no inverters respond.
    
    A (socket, address)-tuple is returned.
    
    You can connect to multiple inverters by calling this function multiple
    times (each subsequent call will make a connection to a new inverter)."""
    global _server
    if _server is None:
        # Lazy initialization of the TCP server
        logging.debug('Binding TCP socket on port 1200 for incoming inverters')
        _server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server.bind(('', 1200))
        _server.settimeout(5.0) # Timeout defines the time between broadcasts
        _server.listen(5)
    # Broadcast packet identifier (header, end)
    identifier = b'\x00\x40\x02', b'\x04\x3a'
    payload = b'I AM SERVER'
    message = _construct_request(identifier, payload)
    # Creating and binding broadcast socket
    logging.debug('Binding UDP socket for broadcasting')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Looping to wait for incoming connections while sending broadcasts
    while True:
        logging.debug('Broadcasting server existence')
        sock.sendto(message, ('<broadcast>', 1300))
        try:
            conn, addr = _server.accept()
        except socket.timeout:
            pass
        else:
            logging.info('New incoming connection from address %s', addr)
            # Probably better to use 'with' instead
            logging.debug('Closing UDP socket as it is no longer needed')
            sock.close()
            return conn, addr

def _construct_request(identifier, payload):
    """Helper function to construct a request message to send."""
    # Start of each message
    start = b'\x55\xaa'
    header, end = identifier
    payload_size = len(payload).to_bytes(2, byteorder='big')
    return start + header + payload_size + payload + end

def _tear_down_response(data):
    """Helper function to extract header, payload and end from received response
    data."""
    response_header = data[2:5]
    # Below is actually not used
    response_payload_size = int.from_bytes(data[5:7], byteorder='big')
    response_payload = data[7:-2]
    response_end = data[-2:]
    return response_header, response_payload, response_end

if __name__ == '__main__':
    # To-do use argparse
    #parser = argparse.ArgumentParser(description='Monitoring tool for '
    #'SolarRiver TD, SolarRiver TL-D and SolarLake TL inverter series.')
    inverter = Inverter()
    while True:
        s = input('? ')
        values = inverter.request_values()
        print(values)
