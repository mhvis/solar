# Samil Power inverter tool

Get model and status data from Samil Power inverters over the network.

## Supported inverter series

* SolarRiver TL
* SolarRiver TL-D
* SolarLake TL

If you have a SolarLake TL-PM series inverter, check out this fork! ➡
[semonet/solar](https://github.com/semonet/solar)

If you just need PVOutput.org uploading, you can also try the
[old version](https://github.com/mhvis/solar).


## Features

* View inverter data
* Upload data to PVOutput.org
* Publish inverter data on MQTT



## Requirements

* Python 3
* Inverter needs to be in the same network

## Usage

To print the usage information:

```commandline
python3 -m solar
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
