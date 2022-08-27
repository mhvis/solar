"""Utility functions for writing to InfluxDB."""
from typing import Dict, Optional

from influxdb_client import Point


def status_to_point(measurement_name: str, status: Dict) -> Optional[Point]:
    """Returns a Point structure from inverter status data.

    Returns None when the inverter is powered off.
    """
    if status['operation_mode'] == 'PV power off':
        # Do not write at night
        return None
    p = Point(measurement_name)
    for k, v in status.items():
        # Sometimes the inverter might return a value of 0 when no value is
        # available for a field, for instance when the inverter is powered off.
        # I filter out fields if they have a value of 0 while that does not
        # make sense.
        if k in {
            'pv1_voltage', 'pv2_voltage', 'grid_voltage', 'grid_frequency',
            'internal_temperature', 'heatsink_temperature',
            'grid_voltage_r_phase', 'grid_voltage_s_phase', 'grid_voltage_t_phase',
            'grid_frequency_r_phase', 'grid_frequency_s_phase', 'grid_frequency_t_phase'
        } and not v:
            continue
        p.field(k, v)
    return p
