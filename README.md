# Samil Power tool

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


## Development info

* Install development requirements: `pip install -r dev-requirements.txt -r requirements.txt`
* Lint code: `flake8`
* Run testcases: `python -m unittest`


## License

MIT
