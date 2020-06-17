"""Communicate with Samil Power inverters.

For protocol information see https://github.com/mhvis/solar/wiki/Communication-protocol.
"""

import logging
from collections import OrderedDict
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SOCK_DGRAM, SO_BROADCAST, timeout, SHUT_RDWR
from typing import Tuple, Dict

from samil.statustypes import status_types


class Inverter:
    """Provides methods for communicating with a connected inverter.

    To open a connection with an inverter, see the InverterListener class.

    The request methods are synchronous and return the response. When the
    connection is lost an exception is raised on the next time that a request
    is made.
    """

    # Caches the format for inverter status messages
    _status_format = None

    def __init__(self, sock: socket, addr):
        """Constructor.

        Args:
            sock: The inverter socket, which is assumed to be connected.
            addr: The inverter network address (currently not used).
        """
        self.sock = sock
        # self.sock_file = sock.makefile('rwb')
        self.addr = addr

    def __enter__(self):
        """No-op."""
        return self.sock.__enter__()

    def __exit__(self, *args):
        """Sends a disconnect message and closes the connection.

        I believe that by using socket.shutdown, the inverter directly accepts
        new connections.
        """
        self.sock.shutdown(SHUT_RDWR)
        self.sock.__exit__(*args)

    def model(self) -> Dict:
        """Gets model information from the inverter.

        For all possible dictionary items, see the implementation.
        """
        ident, payload = self.request(b'\x01\x03\x02', b'', b'\x01\x83')
        device_types = {
            '1': 'Single-phase inverter',
            '2': 'Three-phase inverter',
            '3': 'SolarEnvi Monitor',
            '4': 'R-phase inverter of the three combined single-phase ones',
            '5': 'S-phase inverter of the three combined single-phase ones',
            '6': 'T-phase inverter of the three combined single-phase ones',
        }
        return OrderedDict(
            device_type=device_types[decode_string(payload[0:1])],
            va_rating=decode_string(payload[1:7]),
            firmware_version=decode_string(payload[7:12]),
            model_name=decode_string(payload[12:28]),
            manufacturer=decode_string(payload[28:44]),
            serial_number=decode_string(payload[44:60]),
            communication_version=decode_string(payload[60:65]),
            other_version=decode_string(payload[65:70]),
            general=decode_string(payload[70:71]),
        )

    def status(self) -> Dict:
        """Gets current status data from the inverter.

        Example dictionary keys are pv1_input_power, output_power,
        energy_today. Values are usually of type int or decimal.Decimal.
        For all possible values, see statustypes.py.
        """
        if not self._status_format:
            self.status_format()

        ident, payload = self.request(b'\x01\x02\x02', b'', b'\x01\x82')

        # Payload should be twice the size of the status format
        if 2 * len(self._status_format) != len(payload):
            logging.warning("Size of status payload and format differs, format %s, payload %s",
                            self._status_format.hex(), payload.hex())

        # Retrieve all status data type values
        status_values = OrderedDict()
        for name, type_def in status_types.items():
            val = type_def.get_value(self._status_format, payload)
            if val is not None:
                status_values[name] = val
        return status_values

    def status_format(self):
        """Gets the format used for the status data messages from the inverter.

        See the protocol information for details.
        """
        ident, payload = self.request(b'\x01\x00\x02', b'', b'\x01\x80')
        self._status_format = payload  # Cache result
        return payload

    def history(self, start, end):
        """Requests historical data from the inverter. Not yet implemented!"""
        raise NotImplementedError('Not yet implemented')

    def request(self, identifier: bytes, payload: bytes, response_identifier=b"") -> Tuple[bytes, bytes]:
        """Sends a message and returns the received response.

        Args:
            identifier: The message identifier (header).
            payload: The message payload.
            response_identifier: Messages with a response identifier that does
                not start with the value given here are ignored. By default, no
                messages are ignored, so the first new message is returned.

        Returns:
            A tuple with identifier and payload.
        """
        self.send(identifier, payload)
        response_id_actual, response_payload = self.receive()
        while not response_id_actual.startswith(response_identifier):
            logging.warning('Unexpected response (%s, %s) for request %s, retrying',
                            response_id_actual.hex(), response_payload.hex(), identifier.hex())
            response_id_actual, response_payload = self.receive()
        return response_id_actual, response_payload

    def send(self, identifier: bytes, payload: bytes):
        """Constructs and sends a message to the inverter.

        Raises:
            BrokenPipeError: When the connection is closed.
        """
        message = construct_message(identifier, payload)
        logging.debug('Sending %s', message.hex())
        self.sock.send(message)

    def receive(self) -> Tuple[bytes, bytes]:
        """Reads the next message from the inverter and deconstructs it.

        Returns:
            A tuple with identifier and payload.
        """
        # Todo: only recv one message at a time!
        # Todo: raise exception at EOF!!
        message = self.sock.recv(4096)
        logging.debug('Received %s', message.hex())
        return deconstruct_message(message)


class InverterListener(socket):
    """Listener for new inverter connections."""

    def __init__(self, interface_ip='', **kwargs):
        """Creates listener socket for the incoming inverter connections.

        Args:
            interface_ip: Bind interface IP.
            **kwargs: Will be passed on to socket.
        """
        super().__init__(AF_INET, SOCK_STREAM, **kwargs)
        self.interface_ip = interface_ip
        # Allow socket bind conflicts
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.bind((interface_ip, 1200))
        self.listen(5)

    def accept_inverter(self, advertisements=10, interval=5.0) -> Inverter:
        """Searches for an inverter on the network.

        Args:
            interval: Time between each search message/advertisement.
            advertisements: Number of advertisement messages to send.

        Returns:
            The first inverter that is found.

        Raises:
            InverterNotFoundError: When no inverter was found after all search
                messages have been sent.
        """
        message = construct_message(b'\x00\x40\x02', b'I AM SERVER')
        self.settimeout(interval)
        # Broadcast socket
        with socket(AF_INET, SOCK_DGRAM) as bc:
            bc.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            bc.bind((self.interface_ip, 0))

            for i in range(advertisements):
                logging.info('Searching for inverter')
                bc.sendto(message, ('<broadcast>', 1300))
                try:
                    sock, addr = self.accept()
                except timeout:
                    pass
                else:
                    logging.info('Connected with inverter on address %s', addr)
                    return Inverter(sock, addr)
        raise InverterNotFoundError


def decode_string(val: bytes) -> str:
    """Decodes a possibly null terminated byte sequence to a string using ASCII and strips whitespace."""
    return val.partition(b'\x00')[0].decode('ascii').strip()


def calculate_checksum(message: bytes) -> bytes:
    """Calculates the checksum for a message.

    The message should not have a checksum appended to it.

    Returns:
        The checksum, as a byte sequence of length 2.
    """
    return sum(message).to_bytes(2, byteorder='big')


def construct_message(identifier: bytes, payload: bytes) -> bytes:
    """Constructs an inverter message from identifier and payload."""
    start = b'\x55\xaa'
    payload_size = len(payload).to_bytes(2, byteorder='big')
    message = start + identifier + payload_size + payload
    checksum = calculate_checksum(message)
    return message + checksum


def deconstruct_message(message: bytes) -> Tuple[bytes, bytes]:
    """Deconstructs an inverter message into identifier and payload.

    Raises:
        ValueError: When the checksum is invalid.
    """
    identifier = message[2:5]
    payload_size = int.from_bytes(message[5:7], byteorder='big')
    payload = message[7:7 + payload_size]
    checksum = message[7 + payload_size:7 + payload_size + 2]
    if checksum != calculate_checksum(message[:7 + payload_size]):
        raise ValueError('Checksum invalid for message %s', message.hex())
    return identifier, payload


class KeepAliveInverter(Inverter):
    """Inverter that is kept alive by sending a request every couple seconds."""
    pass


class InverterNotFoundError(Exception):
    """No inverter was found on the network."""
