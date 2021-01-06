"""Defines all types of status values that may be returned by the inverter."""
from collections import OrderedDict
from decimal import Decimal


class StatusType:
    """Type of status value that may appear in the status data.

    See the 'communication protocol' wiki page for details on status types.
    """

    def get_value(self, status_format, status_payload):
        """Returns the value for this status type.

        Args:
            status_format: The status format byte-string as provided by the
                inverter.
            status_payload: The status data byte-string as provided by the
                inverter.

        Returns:
            The value for this status type or None if the value is not present.
        """
        raise NotImplementedError("Abstract method")


class BytesStatusType(StatusType):
    """Gets the bytes at given type ID positions."""

    def __init__(self, *type_ids):
        """Constructor.

        Args:
            *type_ids: The type identifiers that we search for in the format
                string. If found, the payload data at that location is
                returned. Multiple identifier values are concatenated.
        """
        self.type_ids = type_ids

    def get_value(self, status_format, status_payload):
        """See base class."""
        indices = [status_format.find(type_id) for type_id in self.type_ids]
        if -1 in indices:
            return None
        values = [status_payload[i * 2:i * 2 + 2] for i in indices]
        return b''.join(values)


class IntStatusType(BytesStatusType):
    """Returns the value as an integer."""

    def __init__(self, *type_ids, signed=False):
        """Constructor.

        Args:
            *type_ids: The type identifiers, see superclass.
            signed: Whether the bytes are interpreted as an unsigned integer or
                a two's complement signed integer.
        """
        """See BytesStatusType for positional args, signed indicates if the status value is signed."""
        super().__init__(*type_ids)
        self.signed = signed

    def get_value(self, status_format, status_payload):
        """See base class."""
        sequence = super().get_value(status_format, status_payload)
        if sequence is None:
            return None
        return int.from_bytes(sequence, byteorder='big', signed=self.signed)


class DecimalStatusType(IntStatusType):
    """Status type that scales the result and returns a Decimal value."""

    def __init__(self, *type_ids, scale: int = 0, signed: bool = False):
        """Constructor.

        Args:
            *type_ids: Data type identifier.
            scale: How to scale the (integer) value returned by the inverter.
                The result is: <inverter value>*10^scale.
            signed: Whether the value is signed.
        """
        super().__init__(*type_ids, signed=signed)
        self.scale = scale

    def get_value(self, status_format, status_payload):
        """See base class."""
        int_val = super().get_value(status_format, status_payload)
        if int_val is None:
            return None
        return Decimal(int_val).scaleb(self.scale)


class OperationModeStatusType(IntStatusType):
    """Returns the operation mode as a string.

    The value is one of Wait, Normal, Fault, Permanent fault, Check or PV power
    off. This corresponds to the value displayed in SolarPower Browser V3.
    """

    def __init__(self):
        """Constructor."""
        super().__init__(0x0c)

    def get_value(self, status_format, status_payload):
        """See base class."""
        int_val = super().get_value(status_format, status_payload)
        operating_modes = {0: 'Wait', 1: 'Normal', 2: 'Fault', 3: 'Permanent fault', 4: 'Check', 5: 'PV power off'}
        return operating_modes[int_val]


class OneOfStatusType(StatusType):
    """Returns the value of the first not-None status type value.

    Can be used for the case when there are multiple type IDs that refer to the
    same status type and are mutually exclusive.
    """

    def __init__(self, *status_types: StatusType):
        """Constructor.

        Args:
            *status_types: List of status types to check the value of.
        """
        self.status_types = status_types

    def get_value(self, status_format, status_payload):
        """See base class."""
        for status_type in self.status_types:
            val = status_type.get_value(status_format, status_payload)
            if val is not None:
                return val
        return None


class IfPresentStatusType(BytesStatusType):
    """Filters status type based on presence of another type ID."""

    def __init__(self, type_id, presence, status_type):
        """Constructor.

        Args:
            type_id: The type ID to check presence for.
            presence: If the type ID must be present (True) or must not be
                present (False).
            status_type: The status type value that will be returned if the
                above type ID is present.
        """
        super().__init__(type_id)
        self.presence = presence
        self.status_type = status_type

    def get_value(self, status_format, status_payload):
        """See base class."""
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
