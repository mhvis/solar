# Samil Power inverter tool

[![PyPI](https://img.shields.io/pypi/v/samil)](https://pypi.org/project/samil/)

Get model and status data from Samil Power inverters over the network.

If you just need PVOutput.org uploading, you can also try the
[old version](https://github.com/mhvis/solar/tree/v1).

## Supported inverter series

* SolarRiver TL-D
* SolarLake TL
* (Maybe also SolarRiver TL but probably not)

The inverter needs to be equipped with a network connection and connected to the same network, the serial port is not supported.

If you have a SolarLake TL-PM series inverter, check out this fork!
->
[semonet/solar](https://github.com/semonet/solar)

## Features

* View inverter data
* Upload to PVOutput.org
* Publish to MQTT broker
* Write to an InfluxDB database

The following features are not implemented but can be easily implemented upon request:

* Filter inverter based on IP or serial number
* Support for multiple PVOutput.org systems

## Getting started

### Docker

You can run any of the available commands with Docker.
Make sure to use host networking because the app relies on UDP broadcasts.
The image is currently not built for ARM platforms like Raspberry Pi,
so for these platforms you need to build it yourself or install via pip.

```
docker run --network host mhvis/samil monitor
```

Here is a sample `compose.yaml`:

```yaml
name: "samil"

services:
  samil:
    image: mhvis/samil
    command: monitor  # Adapt as desired
    network_mode: host
    restart: unless-stopped
    environment:
      TZ: Europe/Amsterdam  # Needed when using PVOutput
```

### Ubuntu/Debian/Raspberry Pi

```
$ sudo apt install python3-pip
$ pip3 install --user samil
```

After installing, invoke `samil --help` for usage info.
If the `samil` command can't be found, first try to relogin.
If that doesn't help you need to change the `PATH` variable
with the following command and relogin to apply the change.

```
$ echo 'PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
```

### Other

```
$ pip install samil
```

## Usage

#### Monitor

The command `samil monitor` will search for an inverter in the network and print model and status info.
It will connect to the first inverter it finds and print status data every 5 seconds.
See `samil monitor --help` for additional options.

#### MQTT

The command `samil mqtt` connects to one or more inverters and sends status
messages to an MQTT broker continuously. These messages include inverter data
like input power, output power, energy and temperature.

Example: `samil mqtt -h 192.168.1.2 -p 1883 --username user --password pw --inverters 2 --interval 10`.
This command connects to the MQTT broker at address `192.168.1.2`, and
authenticates with the given username `user` and password `pw`. It will
connect to 2 inverters in the network and send an MQTT message continuously every 10 seconds.

For full usage info, run `samil mqtt --help`.

To run this command at startup, [see below](#run-command-at-boot).

#### PVOutput.org uploading

The command `samil pvoutput` gathers status data from 1 or more inverters and uploads it to your PVOutput.org system.
If you have multiple inverters, the data of each inverter is aggregated before uploading.

For full usage info, run `samil pvoutput --help`.

By default, the script uploads once and then stops. You can use cron to execute the script every 5 minutes.

#### InfluxDB

See CLI reference below.

#### Fetch historical data

*Todo*

## Run command at boot

Follow the instructions here to run the MQTT or PVOutput command automatically at startup.
If you run PVOutput using cron, you don't need this!

The instructions are based on [this post](https://raspberrypi.stackexchange.com/a/108723)
and tested on Raspberry Pi OS Lite version May 2020.

Create a new service:
```
$ sudo systemctl edit --force --full samil.service
```

In the empty file that opened, insert the following statements, adjust as necessary, save and close.
```
[Unit]
Description=Samil
After=multi-user.target

[Service]
# Adjust the command to your needs! Keep the path as is unless you installed to somewhere else.
ExecStart=/home/pi/.local/bin/samil mqtt --host 192.168.1.2

# Adjust if you have a different user account
User=pi
Group=pi

# Automatically restart on crashes after 30 seconds
Restart=on-failure
RestartSec=30

Environment="PYTHONUNBUFFERED=1"  # Leave as is

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```
$ sudo systemctl enable --now samil.service
```

Check if the service has successfully started:
```
$ sudo systemctl status samil.service
```

#### Disabling

If you want to stop the script, run:

```
$ sudo systemctl stop samil.service
```

If you want to disable the script from starting on boot:

```
$ sudo systemctl disable samil.service
```
## Background info

The protocol used by these inverters is described
[here](https://mhvis.github.io/solar/).

The following units are used for the status values:

* Voltage in volts
* Current in amperes
* Energy in kilowatt hours
* Power in watts
* Temperature in degrees Celcius
* Operating time in hours

This project was originally a fork of [zombiekipling/solriv](https://github.com/zombiekipling/solriv)
but is now completely rewritten to implement new requirements.


## As a library

You can use this project as a library.
For documentation you will need to read through the source code.
To get started I recommend to read the `monitor` function in `samil.cli`.

## CLI reference

The following commands and options are available:

```
$ samil monitor --help
Usage: samil monitor [OPTIONS]

  Print model and status info for an inverter.

  When you have multiple inverters, run this command multiple times to
  connect to all inverters.

Options:
  --interval FLOAT  Status interval.  [default: 5.0]
  --interface TEXT  IP address of local network interface to bind to.
  --help            Show this message and exit.
```

```
$ samil mqtt --help
Usage: samil mqtt [OPTIONS]

  Publish inverter data to an MQTT broker.

  The default topic format is inverter/<serial number>/status, e.g.
  inverter/DW413B8080/status. The message value is a JSON object with all
  status data from the inverter. Example message value:

      {"operation_mode":"Normal","total_operation_time":45,
      "pv1_input_power":2822.0,"pv2_input_power":0.0,"pv1_voltage":586.5,
      "pv2_voltage":6.7,"pv1_current":4.8,"pv2_current":0.1,
      "output_power":2589.0,"energy_today":21.2,"energy_total":77.0,
      "grid_voltage":242.6,"grid_current":3.6,"grid_frequency":50.01,
      "internal_temperature":35.0}

Options:
  -n, --inverters INTEGER  Number of inverters.  [default: 1]
  -i, --interval FLOAT     Interval between status messages in seconds.
                           [default: 10.0]

  -h, --host TEXT          MQTT broker hostname or IP.  [default: localhost]
  -p, --port INTEGER       MQTT broker port.  [default: 1883]
  --client-id TEXT         MQTT client ID. If not provided, one will be
                           randomly generated.

  --tls                    Enable MQTT SSL/TLS support.
  --username TEXT          MQTT username.
  --password TEXT          MQTT password.
  --topic-prefix TEXT      MQTT topic prefix.  [default: inverter]
  --interface TEXT         IP address of local network interface to bind to.
  --help                   Show this message and exit.
```

```
$ samil pvoutput --help
Usage: samil pvoutput [OPTIONS] SYSTEM_ID API_KEY

  Upload inverter status to a PVOutput.org system.

  Specify the PVOutput system using the SYSTEM_ID and API_KEY arguments. The
  command will connect to the inverter, upload the current status data and
  exit. Use something like cron to upload status data every 5 minutes.

  If you have multiple inverters, specify -n with the number of inverters.
  Data of all inverters will be aggregated before uploading to PVOutput,
  energy is summed, voltage and temperature are averaged. For temperature,
  the internal temperature is used, not the heatsink temperature. If the
  inverter uses three phases, the voltage of each phase is averaged.

  If you don't want to use cron, specify the --interval option to make the
  application upload status data on the specified interval. With this mode
  the application will stay connected to the inverters in between uploads,
  this is less recommended.

Options:
  -n INTEGER              Connect to n inverters.  [default: 1]
  --dc-voltage            By default, AC voltage is uploaded, specify this if
                          you want to upload DC (panel) voltage instead.

  -i, --interval INTEGER  Interval between status uploads in minutes, should
                          be 5, 10 or 15. If not specified, only does a single
                          upload.

  --dry-run               Do not upload data to PVOutput.org.
  --interface TEXT        IP address of local network interface to bind to.
  --help                  Show this message and exit.
```

```
$ samil influx --help
Usage: samil influx [OPTIONS] BUCKET

  Writes system status data to an InfluxDB database.

  The InfluxDB instance can be specified using environment variables or a
  configuration file. See https://github.com/influxdata/influxdb-client-
  python#client-configuration. Use the option -c to point to a configuration
  file. Specify the bucket to write to in the BUCKET argument. Each
  measurement will have the name 'samil'.

  Do you have multiple inverters? This command only supports 1 inverter
  because I am lazy and only need 1, but if you need more, create an issue on
  the GitHub project page. It is trivial to add.

  This command has no built-in restart mechanism and will crash for instance
  when the Influx or inverter connection is lost. (This is again because I am
  lazy, use systemd or Docker to restart on failure.)

  Status is not written when the inverter is powered off at night.

Options:
  -c TEXT             InfluxDB client configuration file.
  --interval FLOAT    Interval between status writes in seconds.  [default:
                      10.0]
  --interface TEXT    IP address of local network interface to bind to.
  --gzip              Use GZip compression for the InfluxDB writes.
  --measurement TEXT  InfluxDB measurement name.  [default: samil]
  --help              Show this message and exit.
```

## Development info

Development installation (usually in a virtual environment):
```commandline
pip install -e .
pip install -r dev-requirements.txt
```
Lint code: `flake8`

Run testcases: `python -m unittest`


## License

MIT
