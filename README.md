# Samil Power uploader

PVOutput.org uploader for the following Samil Power inverters: SolarRiver TD
series, SolarRiver TL-D series, SolarLake TL series.

I use it for my system [here](http://pvoutput.org/intraday.jsp?sid=44819).

If you have a SolarLake TL-PM series inverter, check out this fork! ->
[semonet/solar](https://github.com/semonet/solar)

This is a new version, the old version can be found here.

## Requirements

* Python 3
* Inverter needs to be on the same network as the system running the script
* For PVOutput: system ID and API key 

## Usage

```
$ python3 solar.py -h
usage: solar.py [-h] [-i INTERFACE] [-q] [--inverters NUM]
                [--only-serial [SERIAL_NUMBER [SERIAL_NUMBER ...]]]
                [--only-ip [IP [IP ...]]] [--pvoutput-system PVOUTPUT_SYSTEM]
                [--pvoutput-key PVOUTPUT_KEY] [--version]

Retrieve Samil Power inverter data and optionally upload to PVOutput

optional arguments:
  -h, --help            show this help message and exit
  -i INTERFACE, --interface INTERFACE
                        bind interface IP (default: all interfaces)
  -q, --quiet           only display error messages
  --inverters NUM       number of inverters (default: 1)
  --only-serial [SERIAL_NUMBER [SERIAL_NUMBER ...]]
                        only match inverters with one of the given serial
                        numbers
  --only-ip [IP [IP ...]]
                        only match inverters with one of the given IPs
  --pvoutput-system PVOUTPUT_SYSTEM
                        PVOutput system ID
  --pvoutput-key PVOUTPUT_KEY
                        PVOutput system API key
  --version             show program's version number and exit
```

To upload every 5 or 15 minutes to PVOutput, call the script periodically using a Linux cronjob or similar mechanism.
Crontab example:

```
5 * * * *  /usr/bin/python3 /path/to/solar.py -s 12345 -k APIKEYHERE
```

## Info

The protocol used by these inverters is described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).

## License

MIT
