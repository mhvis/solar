import argparse
import logging
from pprint import pprint

from solar import InverterListener


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description='Retrieve Samil Power inverter data and optionally upload to PVOutput')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    parser.add_argument('-q', '--quiet', action='store_true', help='only display error messages')
    parser.add_argument('-v', '--verbose', action='store_true', help='display debug messages')
    parser.add_argument('-i', '--interface', help='bind interface IP (default: all interfaces)')
    # Inverter selection
    parser.add_argument('-n', '--inverters', type=int, default=1, help='number of inverters (default: %(default)s)',
                        dest='num')
    parser.add_argument('--only-serial', nargs='*', dest='serial_number',
                        help='only match inverters with one of the given serial numbers')
    parser.add_argument('--only-ip', nargs='*', dest='ip',
                        help='only match inverters with one of the given IPs')
    # PVOutput
    parser.add_argument('-s', '--pvoutput-system', type=int, help='PVOutput system ID', dest='system')
    parser.add_argument('-k', '--pvoutput-key', type=int, help='PVOutput system API key', dest='api_key')
    args = parser.parse_args()

    # Logging
    if args.quiet:
        loglevel = logging.ERROR
    elif args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel, format="%(levelname)s:%(message)s")

    with InverterListener() as listener:
        inverter = listener.accept_inverter()
        with inverter:
            pprint(inverter.model())
            pprint(inverter.status())
