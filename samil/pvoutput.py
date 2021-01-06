"""PVOutput.org methods."""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def add_status(system, api_key, date: datetime = None, energy_gen=None, power_gen=None, energy_con=None,
               power_con=None, temp=None, voltage=None, cumulative=False, net=False):
    """Upload status data to PVOutput.org.

    Values can be integer, float or Decimal. See API doc:
    https://pvoutput.org/help.html#api-addstatus.

    Args:
        energy_gen: Energy generation in watt hours.
        power_gen: Power generation in watts.
        energy_con: Energy consumption in watt hours.
        power_con: Power consumption in watts.
        temp: Temperature in celcius.
        voltage: Voltage in volts.

    Returns:
        Response from PVOutput.org.

    Raises:
        HTTPError: When PVOutput.org returns a non-200 status code.
    """
    if not date:
        date = datetime.now()
    data = {
        'd': date.strftime('%Y%m%d'),
        't': date.strftime('%H:%M'),
        'v1': energy_gen,
        'v2': power_gen,
        'v3': energy_con,
        'v4': power_con,
        'v5': temp,
        'v6': voltage,

    }
    if cumulative:
        data['c1'] = '1'
    if net:
        data['n'] = '1'

    data = urlencode(data).encode('ascii')
    req = Request('http://pvoutput.org/service/r2/addstatus.jsp', data)
    req.add_header('X-Pvoutput-SystemId', system)
    req.add_header('X-Pvoutput-Apikey', api_key)
    logging.debug("PVOutput.org request: %s", req)
    return urlopen(req)


def aggregate_statuses(statuses: List[Dict], dc_voltage=False) -> Optional[Dict]:
    """Aggregates inverter statuses for use for PVOutput.org uploads.

    Does some rounding and integer conversion.

    Args:
        statuses: List of inverter statuses as returned by Inverter.status().
        dc_voltage: If True, aggregates DC voltage instead of AC voltage.

    Returns:
        Dictionary of keyword arguments for add_status() or None if no inverter
        has operation mode normal.
    """

    def avg(items):
        """Calculates average."""
        i = list(items)
        return sum(i) / len(i)

    # Calculate values for each inverter separately
    values = []
    for s in statuses:
        # Filter systems with normal operating mode
        if s['operation_mode'] != "Normal":
            continue

        # Calculate voltage
        if dc_voltage:
            # Takes average of PV1 and PV2 voltage
            voltage = avg([s['pv1_voltage'], s['pv2_voltage']])
        elif 'grid_voltage_r_phase' in s:
            # For three-phase inverters, take average voltage of all three phases
            voltage = avg([s['grid_voltage_r_phase'], s['grid_voltage_s_phase'], s['grid_voltage_t_phase']])
        else:
            # For one phase inverter, pick the grid voltage
            voltage = s['grid_voltage']

        values.append({
            'energy_gen': int(s['energy_today'] * 1000),
            'power_gen': int(s['output_power']),
            'temp': s['internal_temperature'],
            'voltage': voltage,
        })

    # Aggregate values of all inverters
    if not values:
        return None

    return {
        'energy_gen': sum(v['energy_gen'] for v in values),
        'power_gen': sum(v['power_gen'] for v in values),
        'temp': round(avg(v['temp'] for v in values), 1),
        'voltage': round(avg(v['voltage'] for v in values), 1),
    }
