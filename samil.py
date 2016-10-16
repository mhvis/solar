#!/usr/bin/env python3
# samil.py
#
# Library and CLI tool for SolarRiver TD, SolarRiver TL-D and SolarLake TL
# series (Samil Power inverters).
#
# (Requires Python 3)

import socket
import threading
import logging
import argparse
import sys

logger = logging.getLogger(__name__)

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
    
    def __init__(self, interface_ip=''):
        # Connect
        self.sock, self.addr = _connect(interface_ip)
        # A lock to ensure a single message at a time
        self.lock = threading.Lock()
        # Start keep-alive sequence
        self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
        self.keep_alive.daemon = True
        self.keep_alive.start()
    
    def __enter__(self):
        if self.sock is not None:
            self.sock.__enter__()
        return self
    
    def __exit__(self, *args):
        if self.sock is not None:
            self.sock.__exit__(*args)

    def request_model_info(self):
        """Requests model information like the type, software version, and
        inverter 'name'."""
        identifier = b'\x01\x03\x02', b'\x01\x05'
        response = self.__make_request(identifier, b'')
        # TODO: format a nice return value
        #raise NotImplementedError('Not yet implemented')
        logger.info('Model info: %s', response)
        return response

    def request_values(self):
        """Requests current values which are returned as a dictionary."""
        identifier = b'\x01\x02\x02', b'\x01\x04'
        # Make request and receive response
        header, payload, end = self.__make_request(identifier, b'')
        # Separate each short value
        values = [payload[i:i+2] for i in range(0, len(payload) - 4, 2)]
        values += [payload[-4:]]
        # Turn each value into an integer
        ints = [int.from_bytes(x, byteorder='big') for x in values]
        # Operating modes
        op_modes = {0: 'wait', 1: 'normal', 5: 'pv_power_off'}
        op_mode = op_modes[ints[7]] if ints[7] in op_modes else str(ints[7])
        result = {
            'internal_temp': ints[0] / 10.0, # degrees C
            'pv1_voltage': ints[1] / 10.0, # V
            'pv2_voltage': ints[2] / 10.0, # V
            'pv1_current': ints[3] / 10.0, # A
            'pv2_current': ints[4] / 10.0, # A
            'total_operation_hours': ints[6], # h
            # Operating mode needs more testing/verifying
            'operating_mode': op_mode,
            'energy_today': ints[8] / 100.0, # kWh
            'pv1_input_power': ints[19], # W
            'pv2_input_power': ints[20], # W
            'grid_current': ints[21] / 10.0, # A
            'grid_voltage': ints[22] / 10.0, # V
            'grid_frequency': ints[23] / 100.0, # Hz
            'output_power': ints[24], # W
            'energy_total': ints[25] / 10.0, # kWh
        }
        # For more info on the data format:
        # https://github.com/mhvis/solar/wiki/Communication-protocol#messages
        logger.debug('Current values: %s', result)
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
        with self.lock:
            # Cancel a (possibly) running keep-alive timer
            self.keep_alive.cancel()
            request = _construct_request(identifier, payload)
            self.sock.send(request)
            data = self.sock.recv(1024)
            if len(data) == 0:
                self.sock = None
                raise ConnectionClosedException('Connection closed')
            response = _tear_down_response(data)
            logger.debug('Request: %s', request)
            logger.debug('Response: %s', response)
            # Set keep-alive timer
            self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
            self.keep_alive.daemon = True
            self.keep_alive.start()
        return response
    
    def __keep_alive(self):
        """Makes a keep-alive request."""
        logger.debug('Keep alive')
        identifier = b'\x01\x09\x02', b'\x01\x0b'
        self.__make_request(identifier, b'')

    def __str__(self):
        # Possibly also return model name/serial number
        return self.addr[0]

    def __repr__(self):
        # See __str__
        return self.addr[0]


class ConnectionClosedException(Exception):
    """Exception raised when the connection is closed or was already closed."""
    pass

def _connect(interface_ip=''):
    """Makes a connection to an inverter (the inverter that responds first).
    Blocks while waiting for an incoming inverter connection. Will keep blocking
    if no inverters respond.
    
    A (socket, address)-tuple is returned.
    
    You can connect to multiple inverters by calling this function multiple
    times (each subsequent call will make a connection to a new inverter)."""
    logger.info('Searching for an inverter in the network')
    # Initialization of the TCP server
    logger.debug('Binding TCP socket to %s:%s', interface_ip, 1200)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        # For making rebinding directly possible
        #server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((interface_ip, 1200))
        server.settimeout(5.0) # Timeout defines the time between broadcasts
        server.listen(5)
        # Broadcast packet identifier (header, end)
        identifier = b'\x00\x40\x02', b'\x04\x3a'
        payload = b'I AM SERVER'
        message = _construct_request(identifier, payload)
        # Creating and binding broadcast socket
        logger.debug('Binding UDP socket to %s:%s', interface_ip, 0)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as bc_sock:
            bc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            bc_sock.bind((interface_ip, 0))
            # Looping to wait for incoming connections while sending broadcasts
            tries = 0
            while True:
                if tries == 10:
                    logger.warning('Connecting to inverter is taking a long '
                            'time, is it reachable?')
                logger.debug('Broadcasting server existence')
                bc_sock.sendto(message, ('<broadcast>', 1300))
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    tries += 1
                else:
                    logger.info('Connected with inverter on address %s', addr)
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

# Test procedure
if __name__ == '__main__':
    # To-do use argparse
    #parser = argparse.ArgumentParser(description='Monitoring tool for '
    #'SolarRiver TD, SolarRiver TL-D and SolarLake TL inverter series.')
    import time
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with Inverter() as inverter:
        while True:
            inverter.request_values()
            inverter.request_model_info()
            inverter.request_unknown_1()
            inverter.request_unknown_2()
            inverter.request_unknown_3()
            time.sleep(8)
