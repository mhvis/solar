"""PVOutput.org methods."""
import logging
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def add_status(system, api_key, energy_gen=None, power_gen=None, energy_con=None, power_con=None, temp=None,
               voltage=None, cumulative=False, net=False):
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
    """
    now = datetime.now()
    data = {
        'd': now.strftime('%Y%m%d'),
        't': now.strftime('%H:%M'),
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

    logging.info("Uploading status data: %s", data)

    data = urlencode(data).encode('ascii')
    req = Request('http://pvoutput.org/service/r2/addstatus.jsp', data)
    req.add_header('X-Pvoutput-SystemId', system)
    req.add_header('X-Pvoutput-Apikey', api_key)
    return urlopen(req)
