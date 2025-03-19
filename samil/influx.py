#
# MIT License
#
# Copyright (c) 2016 Maarten Visscher
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
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
