"""Communicate with Samil Power inverters."""

import logging
import socket
import sys
from collections import OrderedDict
from threading import Event, Thread
from time import sleep
from typing import Tuple, Dict, BinaryIO, Any, Optional

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
        """Sends a shutdown packet and closes the connection.

        socket.shutdown sends a shutdown packet to the inverter which cleanly
        closes the connection and lets the inverter directly accept new
        connections.
        """
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            # The socket might have been closed already for some reason, in
            # which case some OSError will be thrown:
            #
            # * [Errno 9] Bad file descriptor
            # * [WinError 10038] An operation was attempted on something that is not a socket
            if e.errno != 107 and e.errno != 9 and e.errno != 10038:
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
            # Retrieve and cache status format
            self._status_format = self.status_format()

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
            logging.warning("Got unexpected inverter response {} for request {}".format(
                response_id.hex(), identifier.hex()))
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

    You need to call open() and close() or use the class in a with statement.
    """

    listen_sock = None  # type: Optional[socket.socket]

    def __init__(self, interface_ip=''):
        """Create instance.

        Args:
            interface_ip: Bind interface IP for listener and broadcast sockets.
        """
        self.interface_ip = interface_ip

    def __enter__(self):
        """See open method."""
        self.open_with_retries()
        return self

    def __exit__(self, *args):
        """See close method."""
        self.close()

    def open(self):
        """Creates and binds the listener socket and starts listening.

        Needs to be called before searching for inverters, unless used as
        context manager.
        """
        if self.listen_sock:
            raise RuntimeError("Socket is already created")

        try:
            # Create socket
            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Allow socket bind conflicts, this makes it possible to directly rebind to the same port
            if sys.platform == 'win32':
                # Windows behaves differently, needs this one instead of SO_REUSEADDR
                self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError:
            self.listen_sock = None
            raise

        try:
            # Bind and listen, binding might raise OSError if port is already bound
            self.listen_sock.bind((self.interface_ip, 1200))
            self.listen_sock.listen()
        except OSError:
            self.listen_sock.close()
            self.listen_sock = None
            raise

    def open_with_retries(self, retries=10, period=1.0):
        """Opens the finder, retrying if the port is already bound.

        Args:
            retries: Maximum number of retries for when the listener port is bound.
            period: Period between retries.

        Raises:
            OSError: When all tries failed.
        """
        tries = 0
        while True:
            try:
                self.open()
                return
            except OSError as e:
                # Re-raise if the thrown error does not equal 'port already bound' (98) or its Windows variant (10048)
                if e.errno != 98 and e.errno != 10048:
                    raise
                logging.info("Listening port (1200) already in use, retrying")
                # Check for maximum number of retries
                tries += 1
                if tries >= retries:
                    raise
                sleep(period)
        # (This is unreachable)

    def close(self):
        """Closes the listener socket."""
        self.listen_sock.close()
        self.listen_sock = None

    def find_inverter(self, advertisements=10, interval=5.0) -> Tuple[socket.socket, Any]:
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
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as bc:
            bc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            bc.bind((self.interface_ip, 0))

            for i in range(advertisements):
                logging.debug('Sending server broadcast message')
                bc.sendto(message, ('<broadcast>', 1300))
                try:
                    sock, addr = self.listen_sock.accept()
                    logging.info('Connected with inverter on address %s', addr)
                    return sock, addr
                except socket.timeout:
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


class KeepAliveInverter(Inverter):
    """Inverter that is kept alive by sending a request every couple seconds.

    Keep-alive messages are only sent when the last sent message became too
    long ago. When the program makes requests quicker than the keep-alive
    period, no keep-alive messages will be sent.
    """

    def __init__(self, sock: socket, addr, keep_alive: float = 11.0):
        """See base class.

        Args:
            sock: The inverter socket, which is assumed to be connected.
            addr: The inverter network address.
            keep_alive: Maximum time since last message before a keep-alive
                message is triggered. The default of 11 seconds is chosen such
                that keep-alive messages will not be sent when status is
                retrieved every 10 seconds.
        """
        super().__init__(sock, addr)
        self.keep_alive_period = keep_alive
        self.keep_alive_timer = None

        self._ka_thread = None  # Keep-alive thread
        self._ka_stop = Event()  # Used for stopping keep-alive messages
        self.start_keep_alive()

    def stop_keep_alive(self) -> None:
        """Stops the periodic keep-alive messages.

        Blocks for a moment if a keep-alive request is currently being handled.
        """
        if not self._ka_thread:
            return  # No-op if already stopped
        self._ka_stop.set()
        self._ka_thread.join()
        self._ka_thread = None

    def start_keep_alive(self):
        """Starts sending keep-alive messages periodically."""
        if self._ka_thread:
            raise RuntimeError("Keep-alive thread already exists")
        self._ka_stop.clear()
        self._ka_thread = Thread(target=self._ka_runner, daemon=True)
        self._ka_thread.start()

    def _ka_runner(self):
        """Sends a keep-alive periodically until stopped."""
        while True:
            # stopped will be False when the timeout occurred
            stopped = self._ka_stop.wait(timeout=self.keep_alive_period)
            if stopped:
                return
            self.keep_alive()

    def keep_alive(self):
        """Sends a keep-alive message."""
        # We have to call the superclass because self.send/self.receive
        #  interfere with the keep-alive runner.
        super().send(b"\x01\x02\x02", b"")  # Status message
        # super().send(b"\x01\x09\x02", b"")  # Unknown message
        super().receive()

    def send(self, identifier: bytes, payload: bytes):
        """See base class."""
        self.stop_keep_alive()
        super().send(identifier, payload)
        self.start_keep_alive()

    def receive(self) -> Tuple[bytes, bytes]:
        """See base class."""
        self.stop_keep_alive()
        msg = super().receive()
        self.start_keep_alive()
        return msg

    def disconnect(self):
        """See base class."""
        self.stop_keep_alive()
        super().disconnect()
