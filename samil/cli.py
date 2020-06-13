"""Command-line interface."""

import logging
import sys
import logging
from argparse import ArgumentParser
from time import time, sleep

import click

from samil import InverterListener


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli():
    pass


@cli.command()
#     parser_monitor.add_argument('--interval', type=int, default=5, help='status interval (default: %(default)s)',
#                                 dest='seconds')
@click.option('--interval',
              default=5.0,
              help="Status interval.",
              type=click.FloatRange(min=0, max=20))
def monitor(interval: float):
    with InverterListener() as listener:
    # with InverterListener(interface_ip=args.interface) as listener:
        print("Searching for inverter")
        inverter = listener.accept_inverter()
    if not inverter:
        print("Could not find inverter")
        sys.exit()
    with inverter:
        print("Found inverter on address {}".format(inverter.addr))
        model_dict = inverter.model()
        print()
        print("Model info")
        print(_format_model(model_dict))
        n = 1
        t = time()
        while True:
            status_dict = inverter.status()
            print()
            print("Status data #{}".format(n))
            print(_format_status(status_dict))
            t += interval
            n += 1
            sleep(max(t - time(), 0))


# Monitor

_model_keys = {
    'device_type': 'Device type',
    'va_rating': 'VA rating',
    'firmware_version': 'Firmware version',
    'model_name': 'Model name',
    'manufacturer': 'Manufacturer',
    'serial_number': 'Serial number',
    'communication_version': 'Communication version',
    'other_version': 'Other version',
    'general': 'General',
}
_status_keys = {
    'operation_mode': ('Operation mode', ''),
    'total_operation_time': ('Total operation time', 'h'),
    'pv1_input_power': ('PV1 input power', 'W'),
    'pv2_input_power': ('PV2 input power', 'W'),
    'pv1_voltage': ('PV1 voltage', 'V'),
    'pv2_voltage': ('PV2 voltage', 'V'),
    'pv1_current': ('PV1 current', 'A'),
    'pv2_current': ('PV2 current', 'A'),
    'output_power': ('Output power', 'W'),
    'energy_today': ('Energy today', 'kWh'),
    'energy_total': ('Energy total', 'kWh'),
    'grid_current': ('Grid current', 'A'),
    'grid_voltage': ('Grid voltage', 'V'),
    'grid_frequency': ('Grid frequency', 'Hz'),
    'grid_current_r_phase': ('Grid current R-phase', 'A'),
    'grid_voltage_r_phase': ('Grid voltage R-phase', 'V'),
    'grid_frequency_r_phase': ('Grid frequency R-phase', 'Hz'),
    'grid_current_s_phase': ('Grid current S-phase', 'A'),
    'grid_voltage_s_phase': ('Grid voltage S-phase', 'V'),
    'grid_frequency_s_phase': ('Grid frequency S-phase', 'Hz'),
    'grid_current_t_phase': ('Grid current T-phase', 'A'),
    'grid_voltage_t_phase': ('Grid voltage T-phase', 'V'),
    'grid_frequency_t_phase': ('Grid frequency T-phase', 'Hz'),
    'internal_temperature': ('Internal temperature', '°C'),
    'heatsink_temperature': ('Heatsink temperature', '°C'),
}


def _format_two_tuple(t):
    width = max([len(k) for k, v in t])
    rows = ['{:.<{width}}...{}'.format(k, v, width=width) for k, v in t]
    return '\n'.join(rows)


def _format_model(d):
    t = [(_model_keys[k], v) for k, v in d.items()]
    return _format_two_tuple(t)


def _format_status(d):
    t = [(_status_keys[k], v) for k, v in d.items()]
    t = [(form[0], '{}{}{}'.format(v, ' ' if form[1] else '', form[1])) for form, v in t]
    return _format_two_tuple(t)


# History

def history(args):
    pass


# PVOutput

def pvoutput(args):
    if args.num < 1:
        raise ValueError('Invalid number of inverters')
    # Set logging
    loglevel = logging.ERROR if args.quiet else logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s', level=loglevel)
    # Search for the right inverter
    with InverterListener(interface_ip=args.interface) as listener:
        selected_inverters = []
        ignored_inverters = []
        while True:
            inverter = listener.accept_inverter()
            if not inverter:
                raise ConnectionError('Could not find inverter')
            model = inverter.model()
            logging.info('Inverter serial number: %s', model['serial_number'])
            # Check if inverter is selected
            selected = True
            if args.serial_number and model['serial_number'] not in args.serial_number:
                selected = False
            if args.ip and inverter.addr[0] not in args.ip:
                selected = False
            logging.info('Inverter is %s', 'selected' if selected else 'ignored')
            if selected:
                selected_inverters.append(inverter)
            else:
                ignored_inverters.append(inverter)





# CLI
#
# def main():
#     """CLI entrypoint"""
#
#     # Main arguments
#     parser = ArgumentParser(prog='solar',
#                             description='Samil Power SolarRiver TL, SolarRiver TL-D and SolarLake TL tool.')
#     parser.add_argument('--debug', action='store_true', help='print debug output')
#     parser.add_argument('--version', action='version', version='%(prog)s 2.0')
#
#     # Subparsers
#     subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
#
#     # Monitor
#     parser_monitor = subparsers.add_parser('monitor',
#                                            description='Output status data of an inverter continuously. When you have'
#                                                        ' multiple inverters, run multiple instances of this tool. Each'
#                                                        ' instance will connect to a separate inverter.',
#                                            help='output status data of all inverters continuously')
#     parser_monitor.add_argument('-i', '--interface', help='bind interface IP (default: all interfaces)', default='')
#     parser_monitor.add_argument('--interval', type=int, default=5, help='status interval (default: %(default)s)',
#                                 dest='seconds')
#     parser_monitor.set_defaults(func=monitor)
#
#     # PVOutput
#     parser_pvoutput = subparsers.add_parser('pvoutput', help='upload status data to PVOutput',
#                                             description='Upload status data to PVOutput.')
#     parser_pvoutput.add_argument('-q', '--quiet', action='store_true', help='only display error messages')
#     parser_pvoutput.add_argument('-v', '--verbose', action='store_true', help='show debug output')
#     parser_pvoutput.add_argument('-i', '--interface', help='bind interface IP (default: all interfaces)', default='')
#     parser_pvoutput.add_argument('-n', '--inverters', type=int, default=1,
#                                  help='number of inverters (default: %(default)s)', dest='num')
#     matcher_group = parser_pvoutput.add_mutually_exclusive_group()
#     matcher_group.add_argument('--only-serial', nargs='*', dest='serial_number',
#                                help='only match inverters with one of the given serial numbers')
#     matcher_group.add_argument('--only-ip', nargs='*', dest='ip',
#                                help='only match inverters with one of the given IPs')
#     parser_pvoutput.add_argument('-s', '--system', type=int, help='PVOutput system ID')
#     parser_pvoutput.add_argument('-k', '--api-key', type=int, help='PVOutput system API key')
#     parser_pvoutput.set_defaults(func=pvoutput)
#
#     # History
#     parser_history = subparsers.add_parser('history', help='fetch historical generation data from inverter',
#                                            description='Fetch historical generation data from inverter.')
#     parser_history.add_argument('start', type=int, help='start year')
#     parser_history.add_argument('end', type=int, help='end year')
#     parser_history.add_argument('-i', '--interface', help='bind interface IP (default: all interfaces)', default='')
#     matcher_group = parser_history.add_mutually_exclusive_group()
#     matcher_group.add_argument('--serial', help='match only inverter with given serial number', dest='serial_number')
#     matcher_group.add_argument('--ip', help='match only inverter with given IP address', dest='ip')
#     parser_history.set_defaults(func=history)
#
#     args = parser.parse_args()
#     # Debug output
#     if args.debug:
#         logging.basicConfig(level=logging.DEBUG)
#
#     if not args.subcommand:
#         parser.print_help()
#         parser.exit()
#     args.func(args)
