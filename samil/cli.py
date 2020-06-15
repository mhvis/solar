"""Command-line interface."""
import json
import logging
import sys
from decimal import Decimal
from time import time, sleep

import click
from paho.mqtt.client import Client as MQTTClient

from samil.inverter import InverterNotFoundError, InverterListener


# @click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.group()
@click.option('--debug', is_flag=True, help="Enable debug output.")
@click.version_option()
def cli(debug: bool):
    """Samil Power inverter command-line tool."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option('--interval',
              default=5.0,
              help="Status interval.",
              show_default=True)
@click.option('--interface', help="IP address of local network interface to bind to.")
def monitor(interval: float, interface: str):
    """Print model and status info for an inverter.

    When you have multiple inverters, run this command multiple times to
    connect to all inverters.
    """
    if interval > 20:
        # Todo
        raise ValueError("Interval of more than 20 seconds is not yet supported (requires keep-alive messages).")

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

    with InverterListener(interface_ip=interface or '') as listener:
        print("Searching for inverter")
        try:
            inverter = listener.accept_inverter()
        except InverterNotFoundError:
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


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimal to float.

    Note: precision is lost here!
    """

    def default(self, o):
        """See base class."""
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


@cli.command()
@click.option('--inverters', '-n', default=1, help="Number of inverters.", show_default=True)
@click.option('--interval', '-i', default=10.0, help="Interval between status messages in seconds.", show_default=True)
@click.option('--host', '-h', default="localhost", help="MQTT broker hostname or IP.", show_default=True)
@click.option('--port', '-p', default=1883, help="MQTT broker port.", show_default=True)
@click.option('--client-id',
              default='',
              help="MQTT client ID. If not provided, one will be randomly generated.")
@click.option('--tls', is_flag=True, default=False, help="Enable MQTT SSL/TLS support.")
@click.option('--username', help="MQTT username.")
@click.option('--password', help="MQTT password.")
@click.option('--topic-prefix', help="MQTT topic prefix.", default="inverter", show_default=True)
@click.option('--interface', help="IP address of local network interface to bind to.")
def mqtt(inverters, interval, host, port, client_id, tls: bool, username, password, interface, topic_prefix):
    """Publish inverter data to an MQTT broker.

    The default topic format is inverter/<serial number>/status, e.g.
    inverter/DW413B8080/status. The message value is a JSON object with all
    status data from the inverter. Example message value:

        {"operation_mode":"Normal","total_operation_time":45,
        "pv1_input_power":2822.0,"pv2_input_power":0.0,"pv1_voltage":586.5,
        "pv2_voltage":6.7,"pv1_current":4.8,"pv2_current":0.1,
        "output_power":2589.0,"energy_today":21.2,"energy_total":77.0,
        "grid_voltage":242.6,"grid_current":3.6,"grid_frequency":50.01,
        "internal_temperature":35.0}
    """
    # Todo: add example message to docstring.
    if interval > 20:
        # Todo
        raise ValueError("Interval of more than 20 seconds is not yet supported (requires keep-alive messages).")
    # First search and connect to inverter(s)
    inverter_configs = []
    with InverterListener(interface_ip=interface or '') as listener:
        print("Connecting to {} inverter(s)".format(inverters))
        for i in range(inverters):
            inverter = listener.accept_inverter()
            serial_number = inverter.model()["serial_number"]
            topic = "{}/{}/status".format(topic_prefix, serial_number)
            print("Connected to inverter {} on IP {}".format(serial_number, inverter.addr))
            inverter_configs.append((serial_number, topic, inverter))

    # Then connect to MQTT
    print("Connecting to MQTT broker")
    client = MQTTClient(client_id=client_id)
    if tls:
        client.tls_set()
    if username:
        client.username_pw_set(username, password)
    client.connect(host=host, port=port, bind_address=interface or '')
    client.loop_start()  # Starts handling MQTT traffic in separate thread

    topics = ", ".join(x[1] for x in inverter_configs)
    print("Startup complete, now publishing status data every {} seconds to topic(s): {}".format(interval, topics))

    start_time = time()
    while True:
        for inverter_config in inverter_configs:
            status = inverter_config[2].status()
            message = json.dumps(status,
                                 cls=DecimalEncoder,
                                 separators=(',', ':'))  # Compact encoding
            client.publish(topic=inverter_config[1], payload=message)

        # This doesn't suffer from drifting, however it will skip messages when
        #  a message takes longer than the interval.
        sleep(interval - ((time() - start_time) % interval))


@cli.command()
@click.argument('system-id')
@click.argument('api-key')
@click.option('--inverters', '-n',
              default=1,
              help="Number of inverters. If more than 1, the data will be aggregated.",
              show_default=True)
@click.option('--interval', '-i',
              type=int,
              help="Interval between status uploads in minutes (should be 5, 10 or 15 minutes). "
                   "If not specified, only uploads once and then exits.")
@click.option('--interface', default="", help="IP address of local network interface to bind to.")
def pvoutput(system_id, api_key, inverters: int, interval: int, interface):
    """Upload inverter status to a PVOutput.org system.

    Specify the PVOutput system using the SYSTEM_ID and API_KEY arguments. By
    default, this command connects to the inverter to get the current status
    data, uploads this to PVOutput and exits. This can be used with
    e.g. cron to upload status data every 5 minutes.

    If you don't want to use cron, you can specify the --interval option which
    will make the application upload status data on the specified interval.
    With this mode the application will stay connected to the inverters
    in between uploads.

    For multiple inverters, specify the --inverters option to aggregate the data
    and upload to the same PVOutput system. Energy and power will be summed,
    temperature and voltage will be averaged. To upload to multiple PVOutput
    systems, run this application once for each system.
    """
    # try:
    #
    # with InverterListener(interface_ip=interface) as listener:
    #     inverter = listener.accept_inverter()
    pass


# def pvoutput(args):
#     # Search for the right inverter
#     with InverterListener(interface_ip=args.interface) as listener:
#         selected_inverters = []
#         ignored_inverters = []
#         while True:
#             inverter = listener.accept_inverter()
#             if not inverter:
#                 raise ConnectionError('Could not find inverter')
#             model = inverter.model()
#             logging.info('Inverter serial number: %s', model['serial_number'])
#             # Check if inverter is selected
#             selected = True
#             if args.serial_number and model['serial_number'] not in args.serial_number:
#                 selected = False
#             if args.ip and inverter.addr[0] not in args.ip:
#                 selected = False
#             logging.info('Inverter is %s', 'selected' if selected else 'ignored')
#             if selected:
#                 selected_inverters.append(inverter)
#             else:
#                 ignored_inverters.append(inverter)

#
#     # PVOutput
#     parser_pvoutput = subparsers.add_parser('pvoutput', help='upload status data to PVOutput',
#                                             description='Upload status data to PVOutput.')
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
