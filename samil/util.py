"""Higher-level utility functions."""

from typing import List, Optional

from samil.inverter import Inverter


def connect_to_inverters(n: int,
                         ip_filter: Optional[List[str]] = None,
                         serial_filter: Optional[List[str]] = None) -> List[Inverter]:
    """Connect to multiple inverters.

    Args:
        n: Number of inverters.
        ip_filter: If given, only connects to inverters with IP address that
            appears in the list. Mutually exclusive with serial_filter.
        serial_filter: If given, only connects to inverters with serial number
            that appears in the list. Mutually exclusive with ip_filter.
    """
    pass
