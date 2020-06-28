"""Command-line interface."""
import json
import logging
import sys
from collections import namedtuple
from contextlib import ExitStack
from decimal import Decimal
from time import time, sleep
from typing import List

import click
from paho.mqtt.client import Client as MQTTClient

from samil.inverter import InverterNotFoundError, InverterFinder
# @click.group(context_settings={"help_option_names": ["-h", "--help"]})
from samil.pvoutput import add_status
from samil.util import connect_to_inverters, get_bound_inverter_finder, KeepAliveInverter


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

    with InverterFinder(interface_ip=interface or '') as finder:
        print("Searching for inverter")
        try:
            inverter = KeepAliveInverter(*finder.find_inverter())
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
    # Todo: this function is real ugly, need to rewrite.
    MQTTInverter = namedtuple("MQTTInverter", ["inverter", "topic", "serial_number"])

    with ExitStack() as stack:  # Exit stack to always cleanly disconnect with inverters on errors

        # First search and connect to inverter(s)
        mqtt_inverters = []
        with InverterFinder(interface_ip=interface or '') as finder:
            print("Connecting to {} inverter(s)".format(inverters))
            for i in range(inverters):
                inverter = KeepAliveInverter(*finder.find_inverter())
                stack.enter_context(inverter)
                serial_number = inverter.model()["serial_number"]
                print("Connected to inverter {} on IP {}".format(serial_number, inverter.addr))
                mqtt_inverters.append(MQTTInverter(inverter=inverter,
                                                   topic="{}/{}/status".format(topic_prefix, serial_number),
                                                   serial_number=serial_number))

        # Then connect to MQTT
        print("Connecting to MQTT broker")
        client = MQTTClient(client_id=client_id)
        if tls:
            client.tls_set()
        if username:
            client.username_pw_set(username, password)
        client.connect(host=host, port=port, bind_address=interface or '')
        client.loop_start()  # Starts handling MQTT traffic in separate thread
        stack.push(lambda *args: client.disconnect())

        # Startup done
        topics = ", ".join(x.topic for x in mqtt_inverters)
        print("Startup complete, now publishing status data every {} seconds to topic(s): {}".format(interval,
                                                                                                     topics))

        start_time = time()
        while True:
            for mqtt_inverter in mqtt_inverters:
                status = mqtt_inverter.inverter.status()
                message = json.dumps(status,
                                     cls=DecimalEncoder,
                                     separators=(',', ':'))  # Compact encoding
                client.publish(topic=mqtt_inverter.topic, payload=message)

            # This doesn't suffer from drifting, however it will skip messages when
            #  a message takes longer than the interval.
            sleep(interval - ((time() - start_time) % interval))


@cli.command()
@click.argument('system-id')
@click.argument('api-key')
@click.option('--interval', '-i',
              type=int,
              help="Interval between status uploads in minutes, should be 5, 10 or 15. "
                   "If not specified, only does a single upload.")
@click.option('--interface', default="", help="IP address of local network interface to bind to.")
@click.option('-n',
              help="Connect to n inverters.",
              type=int)
@click.option('--ip',
              help="Connect to inverters with the given IP address(es) only. Can be given multiple times.",
              multiple=True)
@click.option('--serial',
              help="Connect to inverters with the given serial number(s) only. Can be given multiple times.",
              multiple=True)
def pvoutput(system_id, api_key, interval: int, interface, n: int, ip: List[str], serial: List[str]):
    """Upload inverter status to a PVOutput.org system.

    Specify the PVOutput system using the SYSTEM_ID and API_KEY arguments. The
    command will connect to the inverter, upload the current status data and
    exit. Use something like cron to upload status data every 5 minutes.

    If you don't want to use cron, specify the --interval option to
    make the application upload status data on the specified interval.
    With this mode the application will stay connected to the inverters
    in between uploads.

    For multiple inverters, specify the inverters to connect to using one of
    -n, --ip or --serial. Data will be aggregated correctly before uploading to
    PVOutput, energy is summed, voltage and temperature are averaged. To upload
    to multiple PVOutput systems, run this application once for each system.
    """
    if bool(n) + bool(ip) + bool(serial) > 1:
        raise ValueError("Arguments -n, --ip and --serial are mutually exclusive")

    # Print info messages (at least)
    if logging.root.level > logging.INFO:
        logging.basicConfig(level=logging.INFO)

    # Determine nr of inverters
    count = n if n else len(ip) if ip else len(serial) if serial else 1

    # Determine filter function
    def keep_ip(inv):
        return inv.addr[0] in ip

    def keep_serial(inv):
        return inv.model()["serial_number"] in serial

    keep = keep_ip if ip else keep_serial if serial else None

    # Connect to inverters
    with get_bound_inverter_finder(interface_ip=interface) as finder:
        logging.info("Searching for inverters")
        inverters = connect_to_inverters(finder, count, keep)

    # Use ExitStack to make sure that each inverter is properly closed
    with ExitStack() as stack:
        for inverter in inverters:
            stack.enter_context(inverter)

        def upload():
            """Uploads status to PVOutput."""
            # Todo: this should be asynchronous so that multiple inverters can be requested at once
            statuses = [inv.status() for inv in inverters]
            # Filter systems with normal operating mode
            statuses = [s for s in statuses if s["operation_mode"] == "Normal"]
            if not statuses:
                logging.info("Not uploading, no inverter has operating mode normal.")
                return
            # Todo: check status types
            add_status(system_id,
                       api_key,
                       energy_gen=sum(s["energy_today"] for s in statuses).scaleb(3),
                       power_gen=sum(s["output_power"] for s in statuses),
                       temp=sum(s["internal_temperature"] for s in statuses) / len(statuses),
                       voltage=sum(s["grid_voltage"] for s in statuses) / len(statuses))

        if not interval:
            # No interval specified, upload once and stop
            upload()
            return

        # Interval given, run periodically
        while True:
            # Sleep until next boundary
            timestamp = time()
            sleep(timestamp + interval * 60 - timestamp % (interval * 60))
            upload()

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
