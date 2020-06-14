# Samil Power inverter tool

![PyPI](https://img.shields.io/pypi/v/samil)

Get model and status data from Samil Power inverters over the network.

## Supported inverter series

* SolarRiver TL
* SolarRiver TL-D
* SolarLake TL

If you have a SolarLake TL-PM series inverter, check out this fork!
->
[semonet/solar](https://github.com/semonet/solar)

If you just need PVOutput.org uploading, you can also try the
[old version](https://github.com/mhvis/solar).


## Features

* View inverter data
* Upload to PVOutput.org
* Publish to MQTT broker



## Requirements

* Python 3
* Inverter needs to be in the same network

## Installation

The package can be installed from [PyPI](https://pypi.org/project/samil/):

```commandline
$ pip install samil
```

On Ubuntu:

```commandline
$ sudo apt install python3-pip
$ pip3 install --user samil
```
Usually `samil` can then be found at `~/.local/bin/samil`.
Often that directory is already in `PATH`, so you can call it using `samil`.
You might need to relogin or add that directory to `PATH`. 


## Usage

```
$ samil --help
Usage: samil [OPTIONS] COMMAND [ARGS]...

  Samil Power inverter command-line tool.

Options:
  --debug    Enable debug output.
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  monitor  Print model and status info for an inverter.
  mqtt     Publish inverter data to an MQTT broker.
```

```
$ samil monitor --help
Usage: samil monitor [OPTIONS]

  Print model and status info for an inverter.

  When you have multiple inverters, run this command multiple times to
  connect to all inverters.

Options:
  --interval FLOAT RANGE  Status interval.  [default: 5.0]
  --interface TEXT        IP address of local network interface to bind to.
  --help                  Show this message and exit.
```

```
$ samil mqtt --help
Usage: samil mqtt [OPTIONS]

  Publish inverter data to an MQTT broker.

Options:
  -h, --host TEXT     MQTT broker hostname/IP address.  [default: localhost]
  -p, --port INTEGER  MQTT broker port.  [default: 1883]
  --client-id TEXT    Client ID used when connecting to the broker. If not
                      provided, one will be randomly generated.

  --tls               Enable SSL/TLS support.
  --username TEXT     MQTT username.
  --password TEXT     MQTT password.
  --interface TEXT    IP address of local network interface to bind to.
  --help              Show this message and exit.
```

## Info

The protocol used by these inverters is described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).

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

Example to get started:

```python
from samil import InverterListener

with InverterListener() as listener:
    # Search for an inverter
    inverter = listener.accept_inverter()

with inverter: 
    # Use with statement to automatically close the connection after use

    # Model info
    model = inverter.model()
    model["serial_number"]  # E.g. DW413B8080
    # ... (see source code)

    status = inverter.status()
    status["output_power"]  # E.g. 513 Watt
    # ... (see source code)
```

## Development info

Development installation:
```commandline
pip install -e .
pip install -r dev-requirements.txt
```
Lint code: `flake8`

Run testcases: `python -m unittest`


## License

MIT
