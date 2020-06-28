"""Communicate with Samil Power inverters.

For protocol information see https://github.com/mhvis/solar/wiki/Communication-protocol.
"""

import logging
from collections import OrderedDict
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SOCK_DGRAM, SO_BROADCAST, timeout, SHUT_RDWR
from typing import Tuple, Dict, BinaryIO, Any

from samil.statustypes import status_types


class Inverter:
    """Provides methods for communicating with a connected inverter.

    To open a connection with an inverter, see the InverterListener class.

    The request methods are synchronous and return the response. When the
    connection is lost an exception is raised on the next time that a request
    is made.

    Methods are not thread-safe.
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
        self.sock_file = sock.makefile('rwb')
        self.addr = addr
        # Inverters should respond in around 1.5 seconds, setting a timeout
        #  above that value will ensure that the application won't hang too
        #  long when the inverter doesn't send anything.
        self.sock.settimeout(30.0)

    def __enter__(self):
        """Returns self."""
        return self

    def __exit__(self, *args):
        """See self.disconnect."""
        self.disconnect()

    def disconnect(self) -> None:
        """Sends a disconnect message and closes the connection.

        By using socket.shutdown it appears that the inverter directly will
        accepts new connections.
        """
        try:
            self.sock.shutdown(SHUT_RDWR)
        except OSError as e:
            # The socket might have been closed already for some reason, in
            # which case some OSError will be thrown:
            #
            # * [Errno 9] Bad file descriptor
            if e.errno != 107 and e.errno != 9:
                raise e
        self.sock_file.close()
        self.sock.close()

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
        """Requests historical data from the inverter."""
        raise NotImplementedError('Not yet implemented')

    def request(self, identifier: bytes, payload: bytes, expected_response_id=b"") -> Tuple[bytes, bytes]:
        """Sends a message and returns the received response.

        Args:
            identifier: The message identifier (header).
            payload: The message payload.
            expected_response_id: The response identifier is checked to see
                whether it starts with the value given here. If it does not, an
                exception is raised.

        Returns:
            A tuple with identifier and payload.
        """
        self.send(identifier, payload)
        response_id, response_payload = self.receive()
        while not response_id.startswith(expected_response_id):
            logging.warning("Got unexpected inverter response {} for request {}, {}".format(
                response_id.hex(), identifier.hex(), payload.hex()
            ))
            response_id, response_payload = self.receive()
        return response_id, response_payload

    def send(self, identifier: bytes, payload: bytes):
        """Constructs and sends a message to the inverter.

        Raises:
            BrokenPipeError: When the connection is closed.
            ValueError: When the connection was already closed, with a message
                'write to closed file'.
        """
        message = construct_message(identifier, payload)
        logging.debug('Sending %s', message.hex())
        self.sock_file.write(message)
        self.sock_file.flush()

    def receive(self) -> Tuple[bytes, bytes]:
        """Reads and returns the next message from the inverter.

        See read_message.
        """
        return read_message(self.sock_file)


class InverterFinder:
    """Class for establishing new inverter connections.

    Use in a 'with' statement (for the listener socket).
    """

    def __init__(self, interface_ip=''):
        """Create instance.

        Args:
            interface_ip: Bind interface IP for listener and broadcast sockets.
        """
        self.interface_ip = interface_ip
        self.listen_sock = socket(AF_INET, SOCK_STREAM)
        # Allow socket bind conflicts.
        # This makes it possible to directly rebind to the same port.
        self.listen_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._listening = False

    def __enter__(self):
        """See listen method."""
        self.listen()
        return self

    def __exit__(self, *args):
        """See close method."""
        self.close()

    def listen(self):
        """Binds the listener socket and starts listening.

        Needs to be called before searching for inverters. Use 'with' statement
        to have this called automatically.
        """
        if not self._listening:
            self.listen_sock.bind((self.interface_ip, 1200))
            self.listen_sock.listen()
            self._listening = True

    def close(self):
        """Closes the listener socket."""
        self.listen_sock.close()

    def find_inverter(self, advertisements=10, interval=5.0) -> Tuple[socket, Any]:
        """Searches for an inverter on the network.

        Args:
            interval: Time between each search message/advertisement.
            advertisements: Number of advertisement messages to send.

        Returns:
            A tuple with the inverter socket and address, the same as what
            socket.accept() returns. Can be used to construct an Inverter
            instance.

        Raises:
            InverterNotFoundError: When no inverter was found after all search
                messages have been sent.
        """
        message = construct_message(b'\x00\x40\x02', b'I AM SERVER')
        self.listen_sock.settimeout(interval)
        # Broadcast socket
        with socket(AF_INET, SOCK_DGRAM) as bc:
            bc.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            bc.bind((self.interface_ip, 0))

            for i in range(advertisements):
                logging.debug('Sending server broadcast message')
                bc.sendto(message, ('<broadcast>', 1300))
                try:
                    sock, addr = self.listen_sock.accept()
                    logging.info('Connected with inverter on address %s', addr)
                    return sock, addr
                except timeout:
                    pass
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


def read_message(stream: BinaryIO) -> Tuple[bytes, bytes]:
    """Reads the next inverter message from a file-like object/stream.

    Returns:
        Tuple with identifier and payload of the message.

    Raises:
        InverterEOFError: When the connection is lost (EOF is encountered).
        ValueError: When the message has an incorrect format, e.g. checksum is
            invalid or the first two bytes are not '55 aa'.
    """
    # Message start + check for EOF
    start = stream.read(2)
    if start == b"":
        raise InverterEOFError
    if start != b"\x55\xaa":
        raise ValueError("Invalid start of message")

    # Identifier
    identifier = stream.read(3)

    # Payload
    payload_size_bytes = stream.read(2)
    payload_size = int.from_bytes(payload_size_bytes, byteorder='big')
    if payload_size < 0 or payload_size > 4096:  # Sanity check for strange payload size values
        raise ValueError("Unexpected payload size value")
    payload = stream.read(payload_size)

    # Checksum
    checksum = stream.read(2)
    message = start + identifier + payload_size_bytes + payload
    if checksum != calculate_checksum(message):
        raise ValueError('Checksum invalid for message %s', message.hex())

    return identifier, payload


class InverterNotFoundError(Exception):
    """No inverter was found on the network."""
    pass


class InverterEOFError(Exception):
    """The connection with the inverter has been lost.

    Raised when EOF is encountered.
    """
    pass

# def empty_sock(sock: socket):
#     """Empty the socket receive buffer."""
#     sock.setblocking(False)
#     while True:
#         try:
#             sock.recv(4096)
#         except BlockingIOError:
#             break
#     sock.setblocking(True)
