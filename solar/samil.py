import logging
from decimal import Decimal
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


# Inverter status data types

class BaseStatusType:
    """Base class for types of status values that may appear in the status data payload"""

    def get_value(self, status_format, status_payload):
        """Formats and returns the value specified by this data type or None if it is not present. Abstract method"""
        raise NotImplementedError("Abstract method")


def _value_of(type_id, status_format, status_payload):
    """Retrieves the value with given ID from the payload or None if it is not present. The value is a 2-byte
    sequence"""
    idx = status_format.find(type_id)
    if idx == -1:
        return None
    return status_payload[idx * 2:idx * 2 + 2]


class DecimalStatusType(BaseStatusType):
    """Status type that has a decimal value"""

    def __init__(self, *type_ids, signed=False, scale=0):
        """Type ID is the identifier of this type that will appear in the status format. Supplying more IDs will
        concatenate the value bytes to form a larger integer. Signed indicates if the status value is signed. Scale is
        applied by multiplying the result with 10^scale"""
        self.type_ids = type_ids
        self.signed = signed
        self.scale = scale

    def get_value(self, status_format, status_payload):
        values = [_value_of(type_id, status_format, status_payload) for type_id in self.type_ids]
        if None in values:
            return None
        value_sequence = b''.join(values)
        int_val = int.from_bytes(value_sequence, byteorder='big', signed=self.signed)
        dec_val = Decimal(int_val)
        return dec_val.scaleb(self.scale)


class OperatingModeStatusType(BaseStatusType):

    def get_value(self, status_format, status_payload):
        pass


status_types = {
    'internal_temperature': DecimalStatusType(0x00, signed=True, scale=-1),  # in degrees Celcius
    'pv1_voltage': DecimalStatusType(0x01, scale=-1),
}


class Inverter:
    """This class provides methods for making requests to an inverter. Use InverterListener to open a connection to a
    new inverter. The request methods are synchronous and return the response. When the connection is lost an exception
    is raised the next time a request is made."""

    # Caches the format for inverter status messages
    _status_format = None

    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr

    def __enter__(self):
        return self.sock.__enter__()

    def __exit__(self, *args):
        self.sock.shutdown(SHUT_RDWR)
        self.sock.__exit__(*args)

    def model(self):
        """Model information like the type, software version, and inverter serial number"""
        ident, payload = self._send_receive(b'\x01\x03\x02', b'', b'\x01\x83\x00')
        # TODO: format a nice return value
        return payload

    def status(self):
        """Status data like voltage, current, energy and temperature"""
        if not self._status_format:
            self.status_format()

        ident, payload = self._send_receive(b'\x01\x02\x02', b'', b'\x01\x82\x00')

        # Payload should be twice the size of the status format
        if 2 * len(self._status_format) != len(payload):
            logging.warning("Size of status payload and format differs, format %s, payload %s",
                            self._status_format.hex(), payload.hex())

        # Retrieve all status data type values
        status_values = {}
        for name, type_def in status_types.items():
            val = type_def.get_value(self._status_format, payload)
            if val is not None:
                status_values[name] = val
        return status_values

    def status_format(self):
        """Requests the format used for the status data message from the inverter, see the protocol information for
        details"""
        ident, payload = self._send_receive(b'\x01\x00\x02', b'', b'\x01\x80\x00')
        self._status_format = payload
        return payload

    def history(self, start, end):
        raise NotImplementedError('Not yet implemented')

    def _send_receive(self, identifier, payload, expected_response_id=None):
        """Send/receive pair utility method, if expected_response_id is given this value is compared with the identifier
         of the actual response and a warning is printed if they are not equal"""
        self._send(identifier, payload)
        response_id, response_payload = self._receive()
        if expected_response_id and response_id != expected_response_id:
            logging.warning('Unexpected response identifier %s for request %s with payload %s',
                            response_id.hex(), identifier.hex(), response_payload.hex())
        return response_id, response_payload

    def _send(self, identifier, payload):
        message = _samil_request(identifier, payload)
        self.sock.send(message)

    def _receive(self):
        message = self.sock.recv(4096)
        return _samil_response(message)


def _checksum(message):
    """Calculate checksum for message, message should not include the checksum"""
    return sum(message).to_bytes(2, byteorder='big')


def _samil_request(identifier, payload):
    """Construct a request message from identifier and payload"""
    start = b'\x55\xaa'
    payload_size = len(payload).to_bytes(2, byteorder='big')
    message = start + identifier + payload_size + payload
    checksum = _checksum(message)
    return message + checksum


def _samil_response(message):
    """Tear down a response, returns a tuple with (identifier, payload)"""
    identifier = message[2:5]
    payload_size = int.from_bytes(message[5:7], byteorder='big')
    payload = message[7:7 + payload_size]
    checksum = message[7 + payload_size:7 + payload_size + 2]
    if checksum != _checksum(message[:7 + payload_size]):
        logging.warning('Checksum invalid for message %s', message.hex())
    return identifier, payload
