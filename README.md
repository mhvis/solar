# solar

This readme is outdated (to-do update).

PVOutput.org uploader for Samil Power SolarRiver 4000TL-D solar inverter, designed to be run on a Rasperry Pi. It's a Python script that calls `curl`, so should work on a number of systems.

Note: I've only tested this on my one-inverter system. It probably won't work properly if there are two or more inverters on the same network.

Usage:

`./solriv.py [INTERFACEIP]`

* Ensure both the system you're running this script on and the inverter are on the same network.
* Create a user account for PVOutput.org and set-up your system. Get an API key from the account settings page.
* Edit solriv.py with your API key and system ID.
* Run the Python script. It will run continuously, logging common errors and information to syslog, upload progress to stdout and failing errors to strerr. This is how I run it as a background process on my Rasberry Pi:

`./solriv.py > /tmp/solriv.log 2> /tmp/solriv.err &`

(Running it automatically on system startup can be achieved with `cron` or `rc.local`.)

If your system has multiple network interfaces, you can force the script to use the correct one by specifying the system's IP address on the network as a parameter.
