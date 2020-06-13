"""Communicate with Samil Power inverters.

For protocol information see https://github.com/mhvis/solar/wiki/Communication-protocol.
"""

import logging
from collections import OrderedDict
from decimal import Decimal
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SOCK_DGRAM, SO_BROADCAST, timeout, SHUT_RDWR


class Inverter:
    """Provides methods for communicating with a connected inverter.

    To open a connection with an inverter, see the InverterListener class.

    The request methods are synchronous and return the response. When the
    connection is lost an exception is raised on the next time that a request
    is made."""

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
        ident, payload = self._send_receive(b'\x01\x03\x02', b'', b'\x01\x83')
        device_types = {
            '1': 'Single-phase inverter',
            '2': 'Three-phase inverter',
            '3': 'SolarEnvi Monitor',
            '4': 'R-phase inverter of the three combined single-phase ones',
            '5': 'S-phase inverter of the three combined single-phase ones',
            '6': 'T-phase inverter of the three combined single-phase ones',
        }
        return OrderedDict(
            device_type=device_types[_samil_string(payload[0:1])],
            va_rating=_samil_string(payload[1:7]),
            firmware_version=_samil_string(payload[7:12]),
            model_name=_samil_string(payload[12:28]),
            manufacturer=_samil_string(payload[28:44]),
            serial_number=_samil_string(payload[44:60]),
            communication_version=_samil_string(payload[60:65]),
            other_version=_samil_string(payload[65:70]),
            general=_samil_string(payload[70:71]),
        )

    def status(self):
        """Status data like voltage, current, energy and temperature"""
        if not self._status_format:
            self.status_format()

        ident, payload = self._send_receive(b'\x01\x02\x02', b'', b'\x01\x82')

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
        """Get the format used for the status data messages from the inverter.

        See the protocol information for details.
        """
        ident, payload = self._send_receive(b'\x01\x00\x02', b'', b'\x01\x80')
        self._status_format = payload  # Cache result
        return payload

    def history(self, start, end):
        raise NotImplementedError('Not yet implemented')

    def _send_receive(self, identifier, payload, response_identifier=None):
        """Send/receive pair utility method, if response_identifier is given this value is compared with the identifier
        of the actual response and messages that have a wrong identifier are ignored. The comparison is done using
        startswith."""
        self._send(identifier, payload)
        response_id_actual, response_payload = self._receive()
        if response_identifier:
            while not response_id_actual.startswith(response_identifier):
                logging.warning('Unexpected response (%s, %s) for request %s, retrying',
                                response_id_actual.hex(), response_payload.hex(), identifier.hex())
                response_id_actual, response_payload = self._receive()
        return response_id_actual, response_payload

    def _send(self, identifier, payload):
        message = _samil_request(identifier, payload)
        logging.debug('Sending %s', message.hex())
        self.sock.send(message)

    def _receive(self):
        message = self.sock.recv(4096)
        logging.debug('Received %s', message.hex())
        return _samil_response(message)


class InverterNotFoundError(Exception):
    """No inverter was found on the network."""


class InverterListener(socket):
    """Listener for new inverter connections."""

    def __init__(self, interface_ip='', **kwargs):
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
        message = _samil_request(b'\x00\x40\x02', b'I AM SERVER')
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


# Inverter status data types

class BaseStatusType:
    """Base class for types of status values that may appear in the status data payload."""

    def get_value(self, status_format, status_payload):
        """Formats and returns the value specified by this data type or None if it is not present. Abstract method"""
        raise NotImplementedError("Abstract method")


class BytesStatusType(BaseStatusType):
    """Status type that returns the bytes at given type id positions, to be used as a base class for higher levels."""

    def __init__(self, *type_ids):
        """The type IDs indicate the type IDs in the format string that we search for. Found values are concatenated."""
        self.type_ids = type_ids

    def get_value(self, status_format, status_payload):
        """Returns the value at ID positions or None if one of the IDs is not present."""
        indices = [status_format.find(type_id) for type_id in self.type_ids]
        if -1 in indices:
            return None
        values = [status_payload[i * 2:i * 2 + 2] for i in indices]
        return b''.join(values)


class IntStatusType(BytesStatusType):
    def __init__(self, *type_ids, signed=False):
        """See BytesStatusType for positional args, signed indicates if the status value is signed."""
        super().__init__(*type_ids)
        self.signed = signed

    def get_value(self, status_format, status_payload):
        sequence = super().get_value(status_format, status_payload)
        if sequence is None:
            return None
        return int.from_bytes(sequence, byteorder='big', signed=self.signed)


class DecimalStatusType(IntStatusType):
    """Status type that has a decimal value"""

    def __init__(self, *args, scale=0, **kwargs):
        """Scale is applied by multiplying the result with 10^scale. See IntStatusType for the other arguments"""
        super().__init__(*args, **kwargs)
        self.scale = scale

    def get_value(self, status_format, status_payload):
        int_val = super().get_value(status_format, status_payload)
        if int_val is None:
            return None
        return Decimal(int_val).scaleb(self.scale)


class OperationModeStatusType(IntStatusType):

    def __init__(self):
        super().__init__(0x0c)

    def get_value(self, status_format, status_payload):
        int_val = super().get_value(status_format, status_payload)
        operating_modes = {0: 'Wait', 1: 'Normal', 2: 'Fault', 3: 'Permanent fault', 4: 'Check', 5: 'PV power off'}
        return operating_modes[int_val]


class OneOfStatusType(BaseStatusType):
    """Returns the value of the first concrete status type value that is not None. Can be used if there are multiple
    type IDs that refer to the same status type and are mutually exclusive."""

    def __init__(self, *status_types):
        self.status_types = status_types

    def get_value(self, status_format, status_payload):
        for status_type in self.status_types:
            val = status_type.get_value(status_format, status_payload)
            if val is not None:
                return val
        return None


class IfPresentStatusType(BytesStatusType):
    """Filters status type based on presence of another type ID."""

    def __init__(self, type_id, presence, status_type):
        """
        :param type_id: the type ID to check presence for
        :param presence: if the type ID must be present (True) or must not be present (False)
        :param status_type: the status type value that will be used
        """
        super().__init__(type_id)
        self.presence = presence
        self.status_type = status_type

    def get_value(self, status_format, status_payload):
        actual_presence = super().get_value(status_format, status_payload) is not None
        if self.presence == actual_presence:
            return self.status_type.get_value(status_format, status_payload)
        return None


status_types = OrderedDict(
    operation_mode=OperationModeStatusType(),
    total_operation_time=IntStatusType(0x09, 0x0a),
    pv1_input_power=DecimalStatusType(0x27),
    pv2_input_power=DecimalStatusType(0x28),
    pv1_voltage=DecimalStatusType(0x01, scale=-1),
    pv2_voltage=DecimalStatusType(0x02, scale=-1),
    pv1_current=DecimalStatusType(0x04, scale=-1),
    pv2_current=DecimalStatusType(0x05, scale=-1),
    output_power=OneOfStatusType(DecimalStatusType(0x0b), DecimalStatusType(0x34)),
    energy_today=DecimalStatusType(0x11, scale=-2),
    energy_total=OneOfStatusType(DecimalStatusType(0x07, 0x08, scale=-1), DecimalStatusType(0x35, 0x36, scale=-1)),
    grid_voltage=IfPresentStatusType(0x51, False, DecimalStatusType(0x32, scale=-1)),
    grid_current=IfPresentStatusType(0x51, False, DecimalStatusType(0x31, scale=-1)),
    grid_frequency=IfPresentStatusType(0x51, False, DecimalStatusType(0x33, scale=-2)),
    grid_voltage_r_phase=IfPresentStatusType(0x51, True, DecimalStatusType(0x32, scale=-1)),
    grid_current_r_phase=IfPresentStatusType(0x51, True, DecimalStatusType(0x31, scale=-1)),
    grid_frequency_r_phase=IfPresentStatusType(0x51, True, DecimalStatusType(0x33, scale=-2)),
    grid_voltage_s_phase=DecimalStatusType(0x52, scale=-1),
    grid_current_s_phase=DecimalStatusType(0x51, scale=-1),
    grid_frequency_s_phase=DecimalStatusType(0x53, scale=-2),
    grid_voltage_t_phase=DecimalStatusType(0x72, scale=-1),
    grid_current_t_phase=DecimalStatusType(0x71, scale=-1),
    grid_frequency_t_phase=DecimalStatusType(0x73, scale=-2),
    internal_temperature=DecimalStatusType(0x00, signed=True, scale=-1),
    heatsink_temperature=DecimalStatusType(0x2f, signed=True, scale=-1),
)


def _samil_string(val):
    """Decodes a possibly null terminated byte array to a string using ASCII and strips whitespace"""
    return val.partition(b'\x00')[0].decode('ascii').strip()


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


class KeepAliveInverter(Inverter):
    """Inverter that is kept alive by sending a request every couple seconds."""
    pass
