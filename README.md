# Samil Power uploader

PVOutput.org uploader for the following Samil Power inverters: SolarRiver TD
series, SolarRiver TL-D series, SolarLake TL series.

I use it for my system [here](http://pvoutput.org/intraday.jsp?sid=44819).

## Usage

* Ensure both the system you're running this script on and the inverter are on
the same network.
* Obtain your PVOutput.org data (API key, system ID) and put this in
`samil_upload.ini`. If you have multiple inverters, see the next section for
advanced configurations.
* Make sure Python 3 is installed.
* Run `samil_upload.py` with the command `./samil_upload.py`

Running it automatically on system startup can be achieved with `cron` or
`rc.local`.

If your system has multiple network interfaces, you can optionally force the
script to use the correct one by specifying the system's IP address on the
network in `samil_upload.ini` (should not be needed).

## Multiple inverters configuration

For using multiple inverters, you add a section for each inverter, in which you
can specify the inverter serial number or IP address. The settings in the
DEFAULT section apply to all inverters (useful for the API key). These can also
be overridden in an inverter section. A serial number or IP address acts as a
filter, when it is empty or not specified it is considered true. When an
inverter connection is made, it is matched to all sections with equal and/or
empty serial number and IP address. A section will only match one inverter,
which is the first inverter found in the network that applies to the section
filter. Thus if you have multiple sections without a specified serial number and
IP address, the first inverter found is matched to all these sections.

Here are some examples:

### Single inverter

```
[DEFAULT]
# Number of minutes between uploads
Status interval = 5
# Interface to bind to, optional
Interface IP =

API key = YourApiKey
System ID = YourSystemId
```

### Two inverters, same PVOutput system, by serial number

**Note: filtering by serial number is not yet implemented!** Use IP address
instead.

When multiple sections point to the same PVOutput system ID, the data of each
section is combined before it is send to PVOutput. The energy data is
accumulated and all other data (temperature, voltage) is averaged.

When the serial number is ommited, this configuration will behave differently:
the first inverter that is connected will match both systems (since both systems
don't have serial number or IP address specified). Therefore only the data of
that first inverter is combined (doubled) and sent to PVOutput.

```
[DEFAULT]
Status interval = 5

API key = AnkieIsLiev
System ID = 44819

[System1]
Serial number = DWB8080SDF

[System2]
Serial number = HELLO
```

### Two inverters, separate PVOutput system, by IP address

```
[DEFAULT]
Status interval = 5

API key = NoortjeOok

[System1]
System ID = 12345
IP address = 192.168.80.30

[System2]
System ID = 12346
IP address = 192.168.80.31
```

It is also possible to add more inverters, have separate API keys or use
different status intervals. If anything is unclear or you need more help setting
up your systems, make an [issue](https://github.com/mhvis/solar/issues) or
[contact me](mailto:mail@maartenvisscher.nl).

## Info

The protocol used by these inverters is (somewhat) described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).
