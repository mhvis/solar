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

#### Monitor
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

#### MQTT
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
  -i, --interval FLOAT     Interval between status messages.  [default: 10.0]
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
from samil.inverter import InverterListener

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
