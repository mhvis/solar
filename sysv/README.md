# SysV

Service script for `samil_upload.py`, for running it automatically on boot.

## Usage

* Copy `samilupload` to `/etc/init.d/`: `sudo cp samilupload /etc/init.d/`.
* Modify the script for your environment: `sudo nano /etc/init.d/samilupload`.
You should update the `DAEMON` variable to point to the correct directory. You
can optionally enable logging.
* Enable automatic startup: `sudo update-rc.d samilupload defaults`

You can also manually control the daemon/script with `sudo service samilupload`
or `sudo /etc/init.d/samilupload`.
