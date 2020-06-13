"""PVOutput.org methods."""

from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def pvoutput_add_status(system, api_key, energy_gen=None, power_gen=None, energy_con=None, power_con=None, temp=None,
                        voltage=None, cumulative=False, net=False):
    """Upload status data to PVOutput.org.

    See API doc: https://pvoutput.org/help.html#api-addstatus.

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

    data = urlencode(data).encode('ascii')
    req = Request('http://pvoutput.org/service/r2/addstatus.jsp', data)
    req.add_header('X-Pvoutput-SystemId', system)
    req.add_header('X-Pvoutput-Apikey', api_key)
    return urlopen(req)
