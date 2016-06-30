# SysV

`samilupload` is a service script for `samil_upload.py`, for running it
automatically on boot, based on `/etc/init.d/skeleton`. There is also a more
straightforward, less complex version in `samilupload2` by
Christian Leyer.

## Usage

* Copy the service script to `/etc/init.d/`: `sudo cp samilupload /etc/init.d/`.
* Modify the script configuration for your environment: `sudo nano /etc/init.d/samilupload`.
You should update the `DAEMON` variable to point to the correct directory. You
can optionally enable logging.
* Enable automatic startup: `sudo update-rc.d samilupload defaults`.

You can also manually control the daemon/script with `sudo service samilupload`
or `sudo /etc/init.d/samilupload`.

### Uninstall

* Remove startup symlinks: `sudo update-rc.d samilupload remove`.
* Remove service script: `sudo rm /etc/init.d/samilupload`.
