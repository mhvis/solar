# Samil Power

PVOutput.org uploader for the following Samil Power inverters: SolarRiver TD
series, SolarRiver TL-D series, SolarLake TL series.

Multiple inverter support is being implemented (requires a small change). See
the [issues](https://github.com/mhvis/solar/issues) page for all to-do's.

## Usage

* Ensure both the system you're running this script on and the inverter are on
the same network.
* Create a user account for PVOutput.org and set-up your system. Get an API key
from the account settings page.
* Put your API key and system ID in `solar_uploader.ini`.
* Run `solar_uploader.py`:

`./solar_uploader.py`

(Running it automatically on system startup can be achieved with `cron` or
`rc.local`.)

If your system has multiple network interfaces, you can optionally force the
script to use the correct one by specifying the system's IP address on the
network in `solar_uploader.ini` (should not be needed).

## Info

The protocol used by these inverters is (somewhat) described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).
