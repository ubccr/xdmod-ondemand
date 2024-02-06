# xdmod-ondemand-export
Python script for parsing [Open OnDemand](https://openondemand.org/) Apache access logs and sending them via POST requests to an HTTPS endpoint on a web server for inclusion in [XDMoD](https://open.xdmod.org).

## Obtain an API token
Obtain an API token from the admins of the destination web server; for ACCESS XDMoD, this is done by [submitting a ticket](https://support.access-ci.org/open-a-ticket):
- For the "Summary" and "Description" you can say "Requesting xdmod-ondemand-export API token for [resource name]."
- For "ACCESS Support Issue," choose "XDMoD Question."

## Installation
The steps below explain the recommended setup, to be run as root on the system with the Open OnDemand Apache access log files. These steps will create a new user called `xdmod-ondemand-export` with no shell or login access but which has read-only access to the logs (e.g., via Access Control List), install the Python package, and set up the files and permissions needed for the script to run.

### Create the `xdmod-ondemand-export` user with no shell or login access
```
useradd -m --shell /bin/false xdmod-ondemand-export
usermod -L xdmod-ondemand-export
```

### If you are on Ubuntu
If you are on Ubuntu, run the two commands below to install the Python virtual environment package for your version of Python 3. If you are not on Ubuntu, these two commands should be skipped.
```
python_version=$(python3 --version | awk '{print $2}' | cut -d'.' -f1-2)
apt install python${python_version}-venv -y
```

### Create a Python virtual environment for the user
```
su -c 'python3 -m venv /home/xdmod-ondemand-export/venv' -s /bin/bash xdmod-ondemand-export
```

### Activate the user's Python virtual environment and install the package
```
su -c 'source /home/xdmod-ondemand-export/venv/bin/activate && python3 -m pip install xdmod-ondemand-export' -s /bin/bash xdmod-ondemand-export
```

### Copy the `conf.ini` configuration file to the user's home directory with read-only permissions
```
(umask 377 && cp /home/xdmod-ondemand-export/venv/lib/python3.*/site-packages/xdmod_ondemand_export/conf.ini /home/xdmod-ondemand-export/)
```

### Edit the configuration file
Edit `/home/xdmod-ondemand-export/conf.ini` to change the default values to match your system. The defaults assume:
- The logs are located at `/etc/httpd/logs`.
- The files to process match the filename pattern `*access*.log`.
- The LogFormat of the files is the Combined Log Format, `%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"`.

### Store the API token in the token file
Create an initially empty token file with read and write permissions (in addition to storing the token, the file will be edited by the script to create a secret key used for hashing IP addresses):
```
(umask 377 && touch /home/xdmod-ondemand-export/.token)
```
Edit the token file (`/home/xdmod-ondemand-export/.token`) to add the token string to the file.

### Create the JSON file
The JSON file is used by the script as it runs to keep track of which files have been processed already. Create an initially empty JSON file with read and write permissions:
```
(umask 177 && touch /home/xdmod-ondemand-export/last-run.json)
```

### Change file ownership of the three files so the user can access them
```
chown xdmod-ondemand-export:xdmod-ondemand-export /home/xdmod-ondemand-export/{conf.ini,.token,last-run.json}
```

### Allow the user to read all current and future log files
The user running the script needs read permissions on the log files. The commands below do this by setting up Access Control Lists for the logs directory and the files in it. Make sure to replace `/etc/httpd/logs` with the location of your logs directory if it is different. If you are on Ubuntu and do not have the `setfacl` command, you may need to run `apt install acl` first.
```
setfacl -m u:xdmod-ondemand-export:r-x /etc/httpd/logs   # allow the user to traverse the logs directory
setfacl -m u:xdmod-ondemand-export:r-- /etc/httpd/logs/* # allow the user to read the current log files
setfacl -dm u:xdmod-ondemand-export:r-- /etc/httpd/logs  # allow the user to read future log files
```

### Check the configuration
Run the Python script in check-config mode to make sure there are no warnings or errors; this will check file permissions and parse the configuration file, token file, and JSON file. It will detect whether there are any logs to process, but it will not attempt to parse or POST any of them.
```
su -c '/home/xdmod-ondemand-export/venv/bin/xdmod-ondemand-export --check-config -l INFO' -s /bin/bash xdmod-ondemand-export
```
If this is your first time running the script, and it says there are no logs to process, check to make sure the values in the configuration file (`/home/xdmod-ondemand-export/conf.ini`) for `dir` and `filename_pattern` are correct.

### Create a cron job to run the script daily
Open the user's crontab:
```
su -c 'crontab -e' -s /bin/bash xdmod-ondemand-export
```
Add the following line. This will set up the script to run daily at 2:01am.
```
1 2 * * * /home/xdmod-ondemand-export/venv/bin/xdmod-ondemand-export
```

## Upgrading the script
The script can be upgraded to the latest version by running:
```
su -c 'source /home/xdmod-ondemand-export/venv/bin/activate && python3 -m pip install --upgrade xdmod-ondemand-export' -s /bin/bash xdmod-ondemand-export
```

### If you are upgrading from version 1.0.0
If you are upgrading from version 1.0.0, before the next run of the script, add write permission to the token file so it can be edited by the script to create a secret key used for hashing IP addresses:
```
chmod 600 /home/xdmod-ondemand-export/.token
```

## Troubleshooting
The `xdmod-ondemand-export` command can be run manually:
```
su -c '/home/xdmod-ondemand-export/venv/bin/xdmod-ondemand-export' -s /bin/bash xdmod-ondemand-export
```

The command can be run with any of the following log levels by including the `-l` or `--log-level` option:
* `DEBUG`
* `INFO`
* `WARNING` (the default)
* `ERROR`

You can place the configuration file, token file, and JSON file at arbitrary locations on the filesystem. If you do this, include the relevant option(s) when running the script:
* `-c` or `--conf-path` followed by the path to the configuration file.
* `-t` or `--token-path` followed by the path to the token file.
* `-j` or `--json-path` followed by the path to the JSON file.

You can get the version number of the script by including the `--version` option.

The JSON file (`last-run.json`) works by storing the filename, first line, file size, and last line of each log file that is successfully parsed and POSTed. When the script runs, it uses the values in the configuration file (`conf.ini`), specifically `dir` and `filename_pattern`, to figure out which log files to process. The script will process those log files as follows:
* If the first line and file size of the log file match an entry in the JSON file, the log file will not be parsed, but its filename will be updated in the JSON file.
* If the first line of the log file matches an entry in the JSON file but its file size is different, the log file will be parsed and POSTed starting at the line immediately after the last line stored in the JSON file. The filename, file size, and last successfully-POSTed line will be updated in the JSON file.
* If the first line of the log file does not match an entry in the JSON file, the entire log file will be parsed and POSTed, and a new entry will be added to the JSON file.
* For any entries in the JSON file for which the script does not encounter a log file whose first line matches, those files are assumed to be deleted, and their entries are removed from the JSON file.

You can edit the JSON file to force certain log files to be processed; e.g., if a file has an entry in the JSON file but you want it to be parsed and POSTed again, just delete its entry in the JSON file before the next run of the script.

For additional assistance, please contact the [XDMoD team](mailto:ccr-xdmod-help@buffalo.edu).
