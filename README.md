# solriv
PVOutput.org uploader for Samil Power SolarRiver 4000TL-D solar inverter, designed to be run on a Rasperry Pi. It's a Python script that calls `curl`, so should work on a number of systems.

Usage:

* Ensure both the system you're running this script on and the inverter are on the same network.
* Create a user account for PVOutput.org and set-up your system. Get an API key from the account settings page.
* Edit solriv.py with your API key and system ID.
* Run the Python script. It will run continuously, logging common errors and information to syslog, upload progress to stdout and failing errors to strerr. This is how I run it as a background process on my Rasberry Pi:

`./solriv.py > /tmp/solriv.log 2> /tmp/solriv.err &`

(Running it automatically on system startup can be achieved with `cron` or `rc.local`.)
