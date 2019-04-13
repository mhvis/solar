import argparse
import logging

from .samil import InverterListener

parser = argparse.ArgumentParser(description='Retrieve Samil Power inverter data and optionally upload to PVOutput')
parser.add_argument('-i', '--interface', help='bind interface IP (default: all interfaces)')
parser.add_argument('-q', '--quiet', action='store_true', help='only display error messages')
# Inverter selection
parser.add_argument('--inverters', type=int, default=1, help='number of inverters (default: %(default)s)', dest='num')
parser.add_argument('--only-serial', nargs='*', dest='serial_number',
                    help='only match inverters with one of the given serial numbers')
parser.add_argument('--only-ip', nargs='*', dest='ip',
                    help='only match inverters with one of the given IPs')
# PVOutput
parser.add_argument('-s', '--pvoutput-system', type=int, help='PVOutput system ID', dest='system')
parser.add_argument('-k', '--pvoutput-key', type=int, help='PVOutput system API key', dest='api_key')
# Misc
parser.add_argument('--version', action='version', version='%(prog)s 2.0')
args = parser.parse_args()


# Logging
logging.basicConfig(level=logging.ERROR if args.quiet else logging.INFO, format="%(level):%(message)s")


with InverterListener() as listener:
    inverter = listener.accept_inverter()
    with inverter:
        print(inverter.model())
        print(inverter.status())
