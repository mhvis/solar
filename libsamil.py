import logging
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SOCK_DGRAM, SO_BROADCAST, timeout, SHUT_RDWR


# For protocol information see https://github.com/mhvis/solar/wiki/Communication-protocol

class InverterListener(socket):
    """Listener for new inverter connections"""

    def __init__(self, interface_ip='', **kwargs):
        super().__init__(AF_INET, SOCK_STREAM, **kwargs)
        self.interface_ip = interface_ip
        # Allow socket bind conflicts
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.bind((interface_ip, 1200))
        self.settimeout(5.0)  # Timeout defines time between broadcasts
        self.listen(5)

    def accept_inverter(self, max_tries=10):
        """Broadcasts discovery message and returns an Inverter instance for the first inverter that responds"""
        message = _samil_request(b'\x00\x40\x02', b'I AM SERVER')
        # Broadcast socket
        with socket(AF_INET, SOCK_DGRAM) as bc:
            bc.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            bc.bind((self.interface_ip, 0))

            for i in range(max_tries):
                logging.info('Searching for inverter')
                bc.sendto(message, ('<broadcast>', 1300))
                try:
                    sock, addr = self.accept()
                except timeout:
                    pass
                else:
                    logging.info('Connected with inverter on address %s', addr)
                    return Inverter(sock, addr)
        raise ConnectionError('No inverter found')


class Inverter:
    """This class provides methods for making requests to an inverter. Use InverterListener to open a connection to a
    new inverter. The request methods are synchronous and return the response. When the connection is lost an exception
    is raised the next time a request is made."""

    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr

    def __enter__(self):
        return self.sock.__enter__()

    def __exit__(self, *args):
        self.sock.shutdown(SHUT_RDWR)
        self.sock.__exit__(*args)

    def model_info(self):
        """Model information like the type, software version, and inverter serial number"""
        self._send(b'\x01\x03\x02', b'')
        identifier, payload = self._receive()
        if identifier != b'\x01\x83\x00':
            logging.warning('Unexpected response identifier %s with payload %s', identifier, payload)
        # TODO: format a nice return value
        return response

    def status(self):
        """Status data like voltage, current, energy and temperature"""
        self._send(b'\x01\x02\x02', b'')
        identifier, payload = self._receive()
        # Separate each 2-byte integer
        values = [payload[i:i + 2] for i in range(0, len(payload) - 4, 2)]
        values += [payload[-4:]]
        # Turn each value into an integer
        ints = [int.from_bytes(x, byteorder='big') for x in values]
        # Operating modes
        op_modes = {0: 'wait', 1: 'normal', 5: 'pv_power_off'}
        op_mode = op_modes[ints[7]] if ints[7] in op_modes else str(ints[7])
        result = {
            'internal_temp': ints[0] / 10.0,  # degrees C
            'pv1_voltage': ints[1] / 10.0,  # V
            'pv2_voltage': ints[2] / 10.0,  # V
            'pv1_current': ints[3] / 10.0,  # A
            'pv2_current': ints[4] / 10.0,  # A
            'total_operation_hours': ints[6],  # h
            # Operating mode needs more testing/verifying
            'operating_mode': op_mode,
            'energy_today': ints[8] / 100.0,  # kWh
            'pv1_input_power': ints[19],  # W
            'pv2_input_power': ints[20],  # W
            'grid_current': ints[21] / 10.0,  # A
            'grid_voltage': ints[22] / 10.0,  # V
            'grid_frequency': ints[23] / 100.0,  # Hz
            'output_power': ints[24],  # W
            'energy_total': ints[25] / 10.0,  # kWh
        }
        # For more info on the data format:
        # https://github.com/mhvis/solar/wiki/Communication-protocol#messages
        logger.debug('Current values: %s', result)
        return result

    def request_history(self, start, end):
        """Not yet implemented."""
        raise NotImplementedError('Not yet implemented')
        # identifier = b'\x06\x01\x02', b'\x01\x2a'
        # return self.__make_request(identifier, b'')

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

    def _send(self, identifier, payload):
        pass

    def _receive(self):
        pass


    def __make_request(self, identifier, payload, response_id=None):
        """Directly makes a request and returns the response."""
        # Acquire socket request lock
        with self.lock:
            # Cancel a (possibly) running keep-alive timer
            self.keep_alive.cancel()
            # Receive non-blocking, to clear the receive buffer
            try:
                self.sock.recv(1024, socket.MSG_DONTWAIT)
            except socket.error as err:
                if err.errno != 11:
                    raise err
            else:
                logger.info('Receive buffer was not empty before a request')
            request = _construct_request(identifier, payload)
            self.sock.send(request)
            # Receive message, possibly retrying when wrong message arrived
            while True:
                data = self.sock.recv(1024)
                response = _tear_down_response(data)
                if not response_id or response_id == response[0]:
                    break
                else:
                    logger.info('Received unexpected message, waiting for a '
                                'new one')
            logger.debug('Request: %s', request)
            logger.debug('Response: %s', response)
            # Set keep-alive timer
            self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
            self.keep_alive.daemon = True
            self.keep_alive.start()
        return response



def _checksum(message):
    """Calculate checksum for message, message should not include the checksum"""
    return sum(message).to_bytes(2, byteorder='big')

def _samil_request(header, payload):
    """Construct a request message from header and payload"""
    start = b'\x55\xaa'
    payload_size = len(payload).to_bytes(2, byteorder='big')
    message = start + header + payload_size + payload
    checksum = _checksum(message)
    return message + checksum


def _samil_response(message):
    """Tear down a response, returns a tuple with (header, payload)"""
    response_header = data[2:5]
    # Below is actually not used
    response_payload_size = int.from_bytes(data[5:7], byteorder='big')
    response_payload = data[7:-2]
    response_end = data[-2:]
    if checksum != ..:
        logging.warning('Checksum invalid for message %s', message)
    return identifier, payload

