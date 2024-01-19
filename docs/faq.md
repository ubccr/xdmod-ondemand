
## The OnDemand realm does not show in the XDMoD portal

Make sure you are logged in with a user account that has either Center Director
or Center Staff role. Note the admin user account that is created with `xdmod-setup`
 does not have these roles by default.

## The xdmod-ondemand-ingestor command ran without error, but no data

Re-run the `xdmod-ondemand-ingestor` command with the `--debug` flag to show detailed information
about what it is running. Things to double check:
- The `webserver_format_str` setting matches the data format in the log files
- The filenames of the log files end in `.log` or `.log.N` where `N` is a number

## The xdmod-ondemand-ingestor command fails with out of memory error

If the memory usage of the `xdmod-ondemand-ingestor` command reaches the php memory limit
then it will exit with an error message similar to the one shown below
```
PHP Fatal error:  Allowed memory size of 134217728 bytes exhausted (tried to allocate 86 bytes) in /usr/share/xdmod/vendor/kassner/log-parser/src/Kassner/LogParser/LogParser.php on line 113
2021-08-10 18:52:16 [critical] Allowed memory size of 134217728 bytes exhausted (tried to allocate 86 bytes) (file: /usr/share/xdmod/vendor/kassner/log-parser/src/Kassner/LogParser/LogParser.php, line: 113, type: 1)
```
This memory error is caused because the `xdmod-ondemand-ingestor` command loads all records in a
log file into memory before loading into the database. This error can be mitigated by either
splitting the log file into multiple smaller files (described in the [Hints](usage.md#hints)) or
by increasing the php memory limit setting.
