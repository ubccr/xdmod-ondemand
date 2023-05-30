# post-ood-logs-to-access-mms
Python script for parsing [Open OnDemand](https://openondemand.org/) access logs and sending them via chunk-encoded POST requests to an endpoint run by the [Advanced Cyberinfrastructure Coordination Ecosystem: Services & Support (ACCESS) Monitoring and Measurement (MMS)](https://metrics.access-ci.org/) team who will ingest and aggregate the data to be included in [ACCESS XDMoD](https://xdmod.access-ci.org/).

## Installation
The steps below should be run on the system with the Open OnDemand log files by a user that has read access to the log files.

### Create and activate a Python virtual environment
```
$ ENV_DIR="${HOME}/post_ood_logs_to_access_mms/env"
$ python3 -m venv ${ENV_DIR}
$ source ${ENV_DIR}/bin/activate
```
### Install the package from PyPI
```
(env) $ python3 -m pip install post_ood_logs_to_access_mms
(env) $ PACKAGE_DIR="${ENV_DIR}/lib/python3.6/site-packages/post_ood_logs_to_access_mms"
```
### Deactivate the virtual environment
```
(env) $ deactivate
```
### Set up the API token
Obtain your API token from the [ACCESS MMS team](ccr-xdmod-help@buffalo.edu).

Set file permissions on the script that contains the API token such that the script is executable by you and such that others cannot read, write, or execute it:
```
$ chmod 700 ${PACKAGE_DIR}/post_ood_logs_to_access_mms.sh
```
Edit the BASH script at `${PACKAGE_DIR}/post_ood_logs_to_access_mms.sh` to set the value of the `ACCESS_OOD_TOKEN` environment variable to be the value of the token.

### Possibly edit the configuration file
The configuration file at `${PACKAGE_DIR}/conf.ini` will be read and written by the Python script as it runs.

The default values assume that the logs are located at `/etc/httpd/logs`, that the files to process match the filename pattern `*access*.log*`, and that the LogFormat of the files is the Combined Log Format, `%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"`.

If any of these values are different for your configuration of Open OnDemand, change them in the file `${PACKAGE_DIR}/conf.ini`.

To control which files should be processed, set the values of `filename_pattern` and `last_line` accordingly. See the instructions in the file for how the value of `last_line` is used.

### Create a cron job to run the Python script daily
Open your user's crontab:
```
$ crontab -e
```
Add the following line, replacing `${PACKAGE_DIR}` with its expanded value. This will set up the script to run daily at 2:01am.
```
1 2 * * * ${PACKAGE_DIR}/post_ood_logs_to_access_mms.sh
```
An example of the expanded value for root is:
```
1 2 * * * /root/post_ood_logs_to_access_mms/env/lib/python3.6/site-packages/post_ood_logs_to_access_mms/post_ood_logs_to_access_mms.sh
```
## Additional optional configuration
## Troubleshooting
