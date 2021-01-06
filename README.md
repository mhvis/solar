# Samil Power inverter tool

![PyPI](https://img.shields.io/pypi/v/samil)

Get model and status data from Samil Power inverters over the network.

If you just need PVOutput.org uploading, you can also try the
[old version](https://github.com/mhvis/solar/tree/v1).

## Supported inverter series

* SolarRiver TL
* SolarRiver TL-D
* SolarLake TL

If you have a SolarLake TL-PM series inverter, check out this fork!
->
[semonet/solar](https://github.com/semonet/solar)

## Features

* View inverter data
* Upload to PVOutput.org
* Publish to MQTT broker

The following features are not implemented but can be easily implemented upon request:

* Filter inverter based on IP or serial number
* Support for multiple PVOutput.org systems

## Requirements

* Python 3
* Inverter needs to be in the same network

## Installation

##### Ubuntu/Debian/Raspberry Pi

```commandline
$ sudo apt install python3-pip
$ pip3 install --user samil
```

After installing, invoke `samil --help` for usage info.
If the `samil` command can't be found, first try to relogin.
If that doesn't help you need to change the `PATH` variable
with the following command and relogin to apply the change.

```commandline
$ echo 'PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
```

##### Other

```commandline
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

See `samil pvoutput --help` for usage info.

#### Fetch historical data

*Todo*

## Run command at boot

Follow the instructions here to run the MQTT or PVOutput command automatically at startup.

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
