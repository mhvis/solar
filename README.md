# Samil Power uploader

PVOutput.org uploader for the following Samil Power inverters: SolarRiver TD
series, SolarRiver TL-D series, SolarLake TL series.

Multiple inverter support is being implemented (requires a small change). See
the [issues](https://github.com/mhvis/solar/issues) page for all to-do's.

I use it for my system [here](http://pvoutput.org/intraday.jsp?sid=44819).

## Usage

* Ensure both the system you're running this script on and the inverter are on
the same network.
* Create a user account for PVOutput.org and set-up your system. Get an API key
from the account settings page.
* Put your API key and system ID in `samil_upload.ini`.
* Run `samil_upload.py`:

`./samil_upload.py`

(Running it automatically on system startup can be achieved with `cron` or
`rc.local`.)

If your system has multiple network interfaces, you can optionally force the
script to use the correct one by specifying the system's IP address on the
network in `samil_upload.ini` (should not be needed).

## Configuration

For using multiple inverters, you add a section for each inverter, in which you
specify the inverter serial number or IP address. The settings in the DEFAULTS
section apply to all inverters (useful for the API key). These can also be
overridden in an inverter section.

Here are some examples:

### Single inverter

```
[DEFAULTS]
# Number of minutes between uploads
Status interval = 5
# Interface to bind to, optional
Interface IP =

API key = YourApiKey
System ID = YourSystemId
```

### Two inverters, same PVOutput system, by serial number

Energy data is accumulated, temperature and voltage data is averaged when
multiple systems have the same PVOutput system ID.

```
[DEFAULTS]
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
[DEFAULTS]
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
different status intervals.

## Info

The protocol used by these inverters is (somewhat) described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).
