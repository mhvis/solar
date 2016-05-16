#!/usr/bin/env python3.5
#
# solar_uploader.py
#
# Daemon for automatically uploading SamilPower data to PVOutput. Uses solar.py
# and pvoutput.py
#

import sched
import solar
import pvoutput
