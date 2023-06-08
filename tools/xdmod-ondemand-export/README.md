# xdmod-ondemand-export
Python script for parsing [Open OnDemand](https://openondemand.org/) Apache access logs and sending them via POST requests to an HTTPS endpoint on a web server for inclusion in [XDMoD](https://open.xdmod.org).

## Installation
The steps below should be run on the system with the Open OnDemand Apache access log files by a user that has read access to the log files.

### Create and activate a Python virtual environment
```
$ env_dir="${HOME}/xdmod-ondemand-export/env"
$ python3 -m venv ${env_dir}
$ source ${env_dir}/bin/activate
```

### Install the package from PyPI
```
(env) $ python3 -m pip install xdmod-ondemand-export
(env) $ package_dir="${env_dir}/lib/python3.6/site-packages/xdmod_ondemand_export"
```

### Deactivate the virtual environment
```
(env) $ deactivate
```

### Set the API token
Obtain your API token from the admins of the web server. For ACCESS XDMoD, this is the [XDMoD team](mailto:ccr-xdmod-help@buffalo.edu).

Set file permissions on the script that contains the API token such that the script is executable by you and such that others cannot read, write, or execute it:
```
$ chmod 700 ${package_dir}/xdmod-ondemand-export.sh
```
Edit the script at `${package_dir}/xdmod-ondemand-export.sh` to set the value of the `XDMOD_ONDEMAND_EXPORT_TOKEN` environment variable to be the value of the token.

### Possibly edit the configuration file
The configuration file at `${package_dir}/conf.ini` will be read and written by the Python script as it runs.

The default values assume that the logs are located at `/etc/httpd/logs`, that the files to process match the filename pattern `*access*.log*`, that the LogFormat of the files is the Combined Log Format, `%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"`, and that the files are not gzip compressed.

If any of these values are different for your configuration of Open OnDemand, change them in the file `${package_dir}/conf.ini`.

To control which files should be processed, set the values of `filename_pattern` and `last_line` accordingly. See the instructions in the file for how the value of `last_line` is used.

### Create a cron job to run the Python script daily
Open your user's crontab:
```
$ crontab -e
```
Add the following line, replacing `${package_dir}` with its expanded value. This will set up the script to run daily at 2:01am.
```
1 2 * * * ${package_dir}/xdmod-ondemand-export.sh
```
An example of the expanded value for root is:
```
1 2 * * * /root/xdmod-ondemand-export/env/lib/python3.6/site-packages/xdmod_ondemand_export/xdmod-ondemand-export.sh
```

## Troubleshooting
The `xdmod-ondemand-export.sh` script can be run with any of the following log levels by passing it the `-l` or `--log-level` option:
* `DEBUG`
* `INFO`
* `WARNING` (the default)
* `ERROR`

Contact the [XDMoD team](mailto:ccr-xdmod-help@buffalo.edu) for additional assistance.